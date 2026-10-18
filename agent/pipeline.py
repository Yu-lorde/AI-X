import json
import re
from pathlib import Path

from compliance import check_text
from config import DEFAULT_KB_NAME, credential_status, env, load_env_file
from ima_client import ImaError, cached_image_path, find_knowledge_base, list_knowledge, read_media, search_knowledge
from llm_client import LlmError, chat_json
from local_kb import LocalError, collect as collect_local
from prompts import SYSTEM_PROMPT
from scenario_router import resolve_scenario
from strategy import classify_title, is_product_fact, missing_questions, platform_rules


def run(product: str, audience: str, scene: str, platform: str, note: str = "") -> dict:
    load_env_file()
    questions = missing_questions(product, audience, scene, platform)
    if questions:
        return {
            "ok": False,
            "stage": "追问",
            "message": "信息不够，先补充下面几项再生成。",
            "questions": questions,
            "export_text": "",
        }

    route = resolve_scenario(audience, scene, note)
    strategy = {"product": product.strip(), "audience": audience.strip(), "scene": scene, **platform_rules(platform), **route}
    if route["status"] != "matched":
        return {
            "ok": False,
            "stage": "追问",
            "message": "场景母文档已经对上，行业模块还需要确认。",
            "questions": route["questions"],
            "strategy": strategy,
            "export_text": "",
        }

    source = "ima 共享知识库"
    try:
        if not (env("IMA_OPENAPI_CLIENTID") or env("IMA_CLIENT_ID")) or not (env("IMA_OPENAPI_APIKEY") or env("IMA_API_KEY")):
            raise ImaError("未配置 ima 凭证")
        kb = find_knowledge_base(env("IMA_KB_NAME", DEFAULT_KB_NAME))
        scenario_docs = _collect_scenario_docs(kb["kb_id"], route)
        platform_doc = _open_platform_template(kb["kb_id"], strategy)
        documents, images, nearby = _collect_sources(kb["kb_id"], strategy["product"])
        if _pack_incomplete(scenario_docs, platform_doc, documents):
            raise ImaError("远程知识库没有返回完整的场景文档、平台模板或 P1 产品事实")
    except ImaError:
        try:
            pack = collect_local(route, strategy)
        except LocalError as exc:
            return _error("本地知识库也不可用", str(exc), strategy)
        scenario_docs = pack["scenario_docs"]
        platform_doc = pack["platform_doc"]
        documents, images, nearby = pack["documents"], pack["images"], pack["nearby"]
        source = pack["source"]

    if not documents and nearby:
        names = "、".join(item["title"] for item in nearby[:6])
        return _error(
            "型号需要确认",
            f"没有检索到与「{strategy['product']}」一致的资料，但找到相近型号：{names}。请改成完整型号后再生成。",
            strategy,
        )
    missing_roles = [item["role"] for item in scenario_docs if not item["text"] and item["role"] in ("母文档", "客户画像", "方案输出模板")]
    if missing_roles:
        found = "、".join(item["title"] for item in scenario_docs if item["text"]) or "无"
        return _error(
            "场景文档不完整",
            f"已映射到《{route['parent_title']}》的 {route['module_id']}，但{source}没有取到：{'、'.join(missing_roles)}。已取到：{found}。",
            strategy,
        )
    if not platform_doc["text"]:
        return _error(
            "没有检索到平台模板",
            f"{source}中没有找到 P6/02 的《{strategy['template_query']}》或《{strategy['template_file']}》，因此不生成该平台成稿。",
            strategy,
        )
    if not documents:
        return _error(
            "没有检索到 P1 产品事实",
            f"场景已映射到《{route['parent_title']}》/{route['module_id']}。{source}里没有与「{strategy['product']}」一致的产品事实，因此不写参数。",
            strategy,
            scenario_docs=scenario_docs,
            source=source,
        )

    source_text = "\n".join(item["text"] for item in documents)
    try:
        draft = _write(strategy, scenario_docs, platform_doc, documents, images, note)
    except LlmError as exc:
        return _error(
            str(exc),
            "场景文档、平台模板和 P1 事实已经准备好，补上 LLM_API_KEY 后可以继续生成。",
            strategy,
            documents,
            images,
            scenario_docs,
            source,
        )

    article = _normalize_article(draft, images, strategy)
    issues = check_text(_article_text(article), source_text, strategy["platform"])
    pending = [str(item) for item in draft.get("pending") or [] if str(item).strip()]
    if issues:
        try:
            revised = _rewrite(strategy, scenario_docs, platform_doc, documents, images, article, issues)
            article = _normalize_article(revised, images, strategy)
            issues = check_text(_article_text(article), source_text, strategy["platform"])
            extra_pending = [str(item) for item in revised.get("pending") or [] if str(item).strip()]
            pending = list(dict.fromkeys(pending + extra_pending))
        except LlmError:
            pending.append("自动改写没有完成，下面的合规问题需要人工删除。")

    for image in article["images"]:
        image["source_label"] = source
    verification = _verification(article, documents, images, issues, pending, nearby, strategy)
    export_text = _export(strategy, scenario_docs, platform_doc, documents, article, verification)
    return {
        "ok": True,
        "stage": "完成",
        "message": f"已按《{route['parent_title']}》映射到 {route['module_id']}，成稿遵循《{platform_doc['title']}》。资料来源：{source}。",
        "source": source,
        "strategy": strategy,
        "documents": documents,
        "scenario_docs": scenario_docs,
        "platform_doc": platform_doc,
        "images": images,
        "article": article,
        "verification": verification,
        "export_text": export_text,
        "credentials": credential_status(),
    }


def _pack_incomplete(scenario_docs: list[dict], platform_doc: dict, documents: list[dict]) -> bool:
    missing = [item["role"] for item in scenario_docs if not item["text"] and item["role"] in ("母文档", "客户画像", "方案输出模板")]
    return bool(missing) or not platform_doc.get("text") or not documents


def _collect_scenario_docs(kb_id: str, route: dict) -> list[dict]:
    docs = [_open_named(kb_id, route["parent_title"], [route["parent_title"]], "母文档", "先按母文档的角色、任务链、证据边界和模块导航执行。")]
    folder_items = _folder_items(kb_id, route.get("module_id") or route["module_name"])
    for child in route["children"]:
        opened = _open_from_items(folder_items, [child["role"]], child["role"], child["use"])
        if not opened["text"]:
            fallback = _open_named(
                kb_id,
                child["query"],
                [route["module_name"], child["role"]],
                child["role"],
                child["use"],
            )
            if fallback["text"]:
                opened = fallback
        docs.append(opened)
    return docs


def _folder_items(kb_id: str, folder_name: str) -> list[dict]:
    folders = [
        item
        for item in search_knowledge(kb_id, folder_name)
        if item.get("media_type") == 99 and folder_name in item["title"]
    ]
    if not folders:
        return []
    return list_knowledge(kb_id, folders[0]["media_id"])


def _open_from_items(items: list[dict], required: list[str], role: str, use: str) -> dict:
    chosen = next((item for item in items if item.get("media_type") != 99 and all(part in item["title"] for part in required)), None)
    if chosen is None:
        return {"role": role, "use": use, "title": "、".join(required), "text": ""}
    text = _read_text(chosen["media_id"]) or chosen.get("highlight") or ""
    return {"role": role, "use": use, "title": chosen["title"], "text": text[:2500]}


def _open_named(kb_id: str, query: str, required: list[str], role: str, use: str) -> dict:
    chosen = None
    for item in search_knowledge(kb_id, query):
        if item.get("media_type") == 99:
            continue
        if all(part in item["title"] for part in required):
            chosen = item
            break
    if chosen is None:
        return {"role": role, "use": use, "title": query, "text": ""}
    text = _read_text(chosen["media_id"]) or chosen.get("highlight") or ""
    return {"role": role, "use": use, "title": chosen["title"], "text": text[:2500]}


def _read_text(media_id: str) -> str:
    try:
        return (read_media(media_id).get("text") or "").strip()
    except ImaError as exc:
        if "上限" in str(exc) or "明天" in str(exc):
            raise
        return ""


def _collect_sources(kb_id: str, product: str) -> tuple[list[dict], list[dict], list[dict]]:
    merged = {}
    for query in (product, f"{product} 产品事实", f"{product} 规格", f"{product} 图片"):
        for item in search_knowledge(kb_id, query):
            merged.setdefault(item["media_id"], item)

    documents = []
    images = []
    nearby = []
    for item in merged.values():
        if item.get("media_type") == 99:
            continue
        kind = classify_title(product, item["title"])
        if kind == "nearby":
            nearby.append(item)
            continue
        if kind != "exact":
            continue
        cached = cached_image_path(item["media_id"]) if item.get("media_type") == 9 else ""
        if cached:
            detail = {"kind": "image", "text": "", "path": cached}
        else:
            detail = {"kind": "file", "text": ""}
            try:
                detail = read_media(item["media_id"])
            except ImaError as exc:
                if "上限" in str(exc) or "明天" in str(exc):
                    raise
                detail = {"kind": "file", "text": ""}
        text = (detail.get("text") or "").strip() or item["highlight"]
        record = {
            "title": item["title"],
            "media_id": item["media_id"],
            "text": text[:4000],
            "kind": detail.get("kind") or "file",
            "path": detail.get("path") or "",
        }
        if item.get("media_type") == 9 or record["kind"] == "image" or _is_image_title(item["title"]):
            record["kind"] = "image"
            record["theme"] = _image_theme(item["title"])
            if record["path"]:
                images.append(record)
        elif text and is_product_fact(item["title"]):
            documents.append(record)
        if len(documents) >= 3 and len(images) >= 12:
            break
    return documents[:3], _prefer_varied_images(images), nearby


def _open_platform_template(kb_id: str, strategy: dict) -> dict:
    use = "成稿的篇幅、结构、图文节奏、正反例边界和发布前检查以这份 P6/02 模板为准。不要套用其他平台，也不要照抄正例原句。"
    for query in (strategy["template_query"], strategy["template_file"]):
        found = _open_named(kb_id, query, [query], "平台模板", use)
        if found["text"]:
            return found
    found = _open_named(kb_id, strategy["template_query"], strategy["template_match"], "平台模板", use)
    if found["text"]:
        return found
    return {"role": "平台模板", "use": use, "title": strategy["template_query"], "text": ""}


def _prefer_varied_images(images: list[dict]) -> list[dict]:
    seen = set()
    primary = []
    extra = []
    for image in images:
        if image.get("theme") in seen:
            extra.append(image)
        else:
            seen.add(image.get("theme"))
            primary.append(image)
    return (primary + extra)[:8]


def _image_theme(title: str) -> str:
    parts = re.split(r"[_\-.]+", Path(title).stem)
    named = [part for part in parts if re.search(r"[\u4e00-\u9fff]", part)]
    return named[-1] if named else Path(title).stem


def _is_image_title(title: str) -> bool:
    lowered = title.lower().split("?")[0]
    return lowered.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))


def _write(strategy: dict, scenario_docs: list[dict], platform_doc: dict, documents: list[dict], images: list[dict], note: str) -> dict:
    return chat_json(SYSTEM_PROMPT, _user_prompt(strategy, scenario_docs, platform_doc, documents, images, note))


def _rewrite(strategy: dict, scenario_docs: list[dict], platform_doc: dict, documents: list[dict], images: list[dict], article: dict, issues: list[str]) -> dict:
    feedback = "\n".join(f"- {item}" for item in issues)
    user = _user_prompt(strategy, scenario_docs, platform_doc, documents, images, "")
    user += (
        "\n\n上一次输出没有通过核验，请重新生成完整 JSON，并删掉这些问题：\n"
        + feedback
        + "\n上一稿仅供改写，其中没有依据的句子不能保留：\n"
        + json.dumps(article, ensure_ascii=False)
    )
    return chat_json(SYSTEM_PROMPT, user)


def _user_prompt(strategy: dict, scenario_docs: list[dict], platform_doc: dict, documents: list[dict], images: list[dict], note: str) -> str:
    scenario_blocks = []
    for doc in scenario_docs:
        body = doc["text"] or "（ima 未返回这份文档，不能用其他文档补写它的要求）"
        scenario_blocks.append(f"【{doc['role']}】{doc['title']}\n使用方式：{doc['use']}\n{body[:1600]}")
    fact_blocks = [f"[{index}] 标题：{doc['title']}\n摘录：{doc['text'][:1500]}" for index, doc in enumerate(documents, start=1)]
    image_lines = [
        f"{item['title']}｜画面：{item.get('theme') or '产品图'}｜已从共享库下载"
        for item in images
    ] or ["（本次没有检索到该型号图片，images 输出空数组）"]
    revision = f"\n用户的临时修改要求：{note.strip()}" if note.strip() else ""
    return f"""请为下面的任务写图文软文。场景任务来自 P8，成稿形态严格按 P6/02 平台模板，产品参数只来自 P1。

型号：{strategy['product']}
人群：{strategy['audience']}
营销场景：{strategy['scene']}
P8 母文档：{strategy['parent_title']}
P8 行业模块：{strategy['module_id']} {strategy['module_brief']}
发布平台：{strategy['platform']}
{revision}

P6/02 平台模板：
【{platform_doc['role']}】{platform_doc['title']}
使用方式：{platform_doc['use']}
{platform_doc['text'][:3500]}

P8 场景文档：
{chr(10).join(scenario_blocks)}

P1 产品事实：
{chr(10).join(fact_blocks)}

可选图片（只能使用这些文件名，张数按平台模板，目标 {strategy['image_min']}–{strategy['image_max']} 张）：
{chr(10).join(image_lines)}
"""


def _normalize_article(draft: dict, images: list[dict], strategy: dict) -> dict:
    by_title = {item["title"]: item for item in images}
    selected = []
    used = set()
    for image in draft.get("images") or []:
        if not isinstance(image, dict):
            continue
        name = str(image.get("name") or image.get("source") or "").strip()
        source = str(image.get("source") or name).strip()
        origin = by_title.get(name) or by_title.get(source)
        if origin is None or origin["title"] in used or not origin.get("path"):
            continue
        used.add(origin["title"])
        selected.append(
            {
                "name": origin["title"],
                "source": origin["title"],
                "position": str(image.get("position") or "正文中部"),
                "caption": str(image.get("caption") or origin.get("theme") or ""),
                "path": origin["path"],
                "theme": origin.get("theme") or "",
            }
        )
    for origin in images:
        if len(selected) >= strategy["image_min"]:
            break
        if origin["title"] in used or not origin.get("path"):
            continue
        used.add(origin["title"])
        slot = len(selected) + 1
        selected.append(
            {
                "name": origin["title"],
                "source": origin["title"],
                "position": f"第{slot}段之后",
                "caption": origin.get("theme") or "产品画面",
                "path": origin["path"],
                "theme": origin.get("theme") or "",
            }
        )
    selected = selected[: strategy["image_max"]]
    paragraphs = [str(item).strip() for item in draft.get("paragraphs") or [] if str(item).strip()]
    tags = [str(item).strip() for item in draft.get("tags") or [] if str(item).strip()]
    if not strategy["use_tags"]:
        tags = []
    title_options = [str(item).strip() for item in draft.get("title_options") or [] if str(item).strip()][:3]
    return {
        "title": str(draft.get("title") or "").strip(),
        "title_options": title_options,
        "lead": str(draft.get("lead") or "").strip(),
        "paragraphs": paragraphs,
        "cta": str(draft.get("cta") or "").strip(),
        "tags": tags,
        "images": selected,
        "facts": [
            {"point": str(item.get("point") or "").strip(), "source_title": str(item.get("source_title") or "").strip()}
            for item in draft.get("facts") or []
            if isinstance(item, dict) and str(item.get("point") or "").strip()
        ],
    }


def _article_text(article: dict) -> str:
    parts = [article["title"], article["lead"], *article["paragraphs"], article["cta"], *article["tags"]]
    parts.extend(image["caption"] for image in article["images"])
    return "\n".join(part for part in parts if part)


def _verification(article, documents, images, issues, pending, nearby, strategy=None) -> dict:
    source_titles = {item["title"] for item in documents}
    fact_lines = []
    for fact in article["facts"]:
        if fact["source_title"] in source_titles:
            fact_lines.append(f"通过：{fact['point']}（{fact['source_title']}）")
        else:
            fact_lines.append(f"待确认：{fact['point']}（未对上资料标题）")
    if not fact_lines:
        fact_lines.append("待确认：模型没有列出可回链的事实点。")
    image_lines = []
    if article["images"]:
        image_lines.extend(f"通过：{item['name']}，插在{item['position']}" for item in article["images"])
        minimum = (strategy or {}).get("image_min") or 0
        if minimum and len(article["images"]) < minimum:
            image_lines.append(f"待确认：平台模板建议至少 {minimum} 张，本次该型号只配到 {len(article['images'])} 张。")
    elif images:
        image_lines.append("待确认：检索到了图片，但成稿没有选用。")
    else:
        image_lines.append("待确认：本次检索没有返回该型号图片，成稿未配图。")
    for item in nearby:
        image_lines.append(f"已排除相近型号资料：{item['title']}")
    compliance = issues or ["通过：没有发现绝对化用语、无依据价格或虚假体验。"]
    pending_lines = pending or ["没有额外待确认项。"]
    return {
        "facts": fact_lines,
        "images": image_lines,
        "compliance": compliance,
        "pending": pending_lines,
    }


def _export(strategy: dict, scenario_docs: list[dict], platform_doc: dict, documents: list[dict], article: dict, verification: dict) -> str:
    fact_lines = [f"- {item['point']} / {item['source_title']}" for item in article["facts"]] or ["- 无"]
    source_lines = [f"- [P1] {item['title']}" for item in documents]
    scenario_lines = [f"- [P8/{item['role']}] {item['title']}" for item in scenario_docs]
    paragraphs = "\n\n".join(article["paragraphs"]) or "（无）"
    tags = " ".join(f"#{tag.lstrip('#')}" for tag in article["tags"])
    image_lines = [
        f"- {item['name']} / 来源：{item['source']} / 位置：{item['position']} / 说明：{item['caption']}"
        for item in article["images"]
    ] or ["- 本次未配图"]
    return "\n".join(
        [
            "一、场景判断",
            f"- 目标人群：{strategy['audience']}",
            f"- 营销场景：{strategy['scene']}",
            f"- P8 母文档：{strategy.get('parent_title', '')}",
            f"- P8 行业模块：{strategy.get('module_id', '')} {strategy.get('module_brief', '')}",
            f"- 发布平台：{strategy['platform']}",
            f"- P6/02 模板：{platform_doc['title']}",
            "",
            "二、知识库依据",
            f"- 产品型号：{strategy['product']}",
            "- 场景文档：",
            *scenario_lines,
            "- 产品事实：",
            *fact_lines,
            *source_lines,
            "",
            "三、图文软文",
            "- 标题备选：" + ("；".join(article.get("title_options") or []) or "无"),
            f"- 采用标题：{article['title']}",
            f"- 导语：{article['lead']}",
            "",
            paragraphs,
            "",
            f"- 行动引导：{article['cta']}",
            f"- 标签：{tags or '无'}",
            *image_lines,
            "",
            "四、核验结果",
            "- 产品事实：",
            *[f"  {line}" for line in verification["facts"]],
            "- 图片型号：",
            *[f"  {line}" for line in verification["images"]],
            "- 合规：",
            *[f"  {line}" for line in verification["compliance"]],
            "- 待确认信息：",
            *[f"  {line}" for line in verification["pending"]],
        ]
    )


def _error(message: str, detail: str, strategy: dict | None = None, documents=None, images=None, scenario_docs=None, source: str = "") -> dict:
    return {
        "ok": False,
        "stage": "停止",
        "message": message,
        "detail": detail,
        "strategy": strategy,
        "documents": documents or [],
        "images": images or [],
        "scenario_docs": scenario_docs or [],
        "source": source,
        "export_text": "",
    }
