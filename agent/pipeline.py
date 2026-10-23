import json
import re
from pathlib import Path

from compliance import check_text
from config import credential_status, load_env_file
from exemplars import select_exemplars
from humanizer import check_style
from llm_client import LlmError, chat_json
from local_kb import LocalError, collect as collect_local
from prompts import SYSTEM_PROMPT
from scenario_router import generic_route, resolve_scenario
from strategy import canonical_perspective, missing_questions, perspective_brief, platform_rules

MAX_REWRITES = 3  # 生成后最多重写几轮，直到合规和 AI 味核验通过


def run(product: str, audience: str, scene: str, platform: str, note: str = "", perspective: str = "") -> dict:
    load_env_file()
    product = (product or "").strip()
    audience = (audience or "").strip()
    scene = (scene or "").strip()
    platform = (platform or "").strip()
    questions = missing_questions(product, audience, scene, platform)
    if questions:
        return {
            "ok": False,
            "stage": "追问",
            "message": "信息不够，先补充下面几项再生成。",
            "questions": questions,
            "export_text": "",
        }

    # 人群留空、或场景选「无明确」时，不走 P8 行业场景，按通用产品软文生成。
    generic = (not audience) or (scene in ("", "无明确"))
    route = generic_route() if generic else resolve_scenario(audience, scene, note)
    strategy = {"product": product, "audience": audience or "无明确", "scene": scene or "无明确", "perspective": canonical_perspective(perspective), **platform_rules(platform), **route}

    # 只读工作区 知识库/，不再走远程。人群没对上画像时按通用处理，不追问。
    source = "知识库"
    try:
        pack = collect_local(route, strategy)
    except LocalError as exc:
        return _error("知识库不可用", str(exc), strategy)
    scenario_docs = pack["scenario_docs"]
    platform_doc = pack["platform_doc"]
    documents, images, nearby = pack["documents"], pack["images"], pack["nearby"]

    if not documents and nearby:
        names = "、".join(item["title"] for item in nearby[:6])
        return _error(
            "型号需要确认",
            f"没有找到与「{strategy['product']}」一致的资料，但找到相近型号：{names}。请改成完整型号后再生成。",
            strategy,
        )
    if not platform_doc["text"]:
        return _error(
            "没有找到平台模板",
            f"知识库里没有《{strategy['template_file']}》，因此不生成该平台成稿。",
            strategy,
        )
    if not documents:
        return _error(
            "没有找到该型号的产品事实",
            f"知识库里没有与「{strategy['product']}」一致的产品事实，因此不写参数。（后续可接入联网查官网补充）",
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
    compliance_issues = check_text(_article_text(article), source_text, strategy["platform"])
    style_issues = check_style(article, strategy["platform"], source_text)
    pending = [str(item) for item in draft.get("pending") or [] if str(item).strip()]
    # 反复重写直到核验通过或到上限：口水词、三词并列等 AI 腔要改到没有，残留才进待确认。
    attempts = 0
    while (compliance_issues or style_issues) and attempts < MAX_REWRITES:
        attempts += 1
        try:
            revised = _rewrite(strategy, scenario_docs, platform_doc, documents, images, article, compliance_issues + style_issues)
        except LlmError:
            pending.append("自动改写没有完成，下面的合规或 AI 味问题需要人工处理。")
            break
        article = _normalize_article(revised, images, strategy)
        compliance_issues = check_text(_article_text(article), source_text, strategy["platform"])
        style_issues = check_style(article, strategy["platform"], source_text)
        extra_pending = [str(item) for item in revised.get("pending") or [] if str(item).strip()]
        pending = list(dict.fromkeys(pending + extra_pending))

    for image in article["images"]:
        image["source_label"] = source
    verification = _verification(article, documents, images, compliance_issues, pending, nearby, strategy, style_issues)
    export_text = _export(strategy, scenario_docs, platform_doc, documents, article, verification)
    if route.get("generic"):
        message = f"未指定行业场景或人群，按通用产品软文生成。成稿遵循《{platform_doc['title']}》。来源：{source}。"
    else:
        message = f"已参考「{route.get('module_name') or route.get('module_id')}」客户画像，成稿遵循《{platform_doc['title']}》。来源：{source}。"
    return {
        "ok": True,
        "stage": "完成",
        "message": message,
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



def _write(strategy: dict, scenario_docs: list[dict], platform_doc: dict, documents: list[dict], images: list[dict], note: str) -> dict:
    return chat_json(SYSTEM_PROMPT, _user_prompt(strategy, scenario_docs, platform_doc, documents, images, note))


def _rewrite(strategy: dict, scenario_docs: list[dict], platform_doc: dict, documents: list[dict], images: list[dict], article: dict, issues: list[str]) -> dict:
    feedback = "\n".join(f"- {item}" for item in issues)
    user = _user_prompt(strategy, scenario_docs, platform_doc, documents, images, "")
    user += (
        "\n\n上一稿没有通过核验。请重新生成完整 JSON：合规问题必须删除，"
        "AI 腔问题要改写润色（换成具体说法、长短句交错、去掉套话和排比）。"
        "正文里的免责声明、元话术和来源归因（例如“资料没写/以官网为准/官方定位里写的是”）一律直接删除，不要改写保留；不确定的内容只放进 pending。"
        "但不得改动或杜撰 P1 事实、数字、型号、来源和结构，没有依据的句子不能保留。问题如下：\n"
        + feedback
        + "\n上一稿仅供改写参考：\n"
        + json.dumps(article, ensure_ascii=False)
    )
    return chat_json(SYSTEM_PROMPT, user)


def _exemplar_block(strategy: dict, note: str) -> str:
    exemplars = select_exemplars(strategy["platform"], strategy["audience"], strategy["scene"], note, perspective=strategy.get("perspective", ""))
    if not exemplars:
        return ""
    blocks = []
    for item in exemplars:
        good = f"好在哪：{item['good_points']}\n" if item["good_points"] else ""
        label = "·".join(x for x in (item["platform"] or "通用", item.get("perspective") or "", item.get("product") or "") if x)
        blocks.append(f"范文《{item['title']}》（{label}）\n{good}{item['body'][:1200]}")
    return (
        "参考范文（只学语气、结构和节奏，严禁照抄其句子，也不得借用范文里的任何产品信息；"
        "所有参数仍只来自下面的 P1 事实）：\n"
        + "\n\n".join(blocks)
        + "\n\n"
    )


def _user_prompt(strategy: dict, scenario_docs: list[dict], platform_doc: dict, documents: list[dict], images: list[dict], note: str) -> str:
    scenario_blocks = []
    for doc in scenario_docs:
        body = doc["text"] or ""
        if body:
            scenario_blocks.append(f"【{doc['role']}】{doc['title']}\n使用方式：{doc['use']}\n{body[:1800]}")
    fact_blocks = [f"[{index}] 标题：{doc['title']}\n摘录：{doc['text'][:3000]}" for index, doc in enumerate(documents, start=1)]
    image_lines = [
        f"{item['title']}｜画面：{item.get('theme') or '产品图'}｜已在本地知识库"
        for item in images
    ] or ["（本次没有该型号图片，images 输出空数组）"]
    revision = f"\n用户的临时修改要求：{note.strip()}" if note.strip() else ""
    exemplar_block = _exemplar_block(strategy, note)
    if scenario_blocks:
        opening = "成稿形态严格按平台模板，产品参数只来自产品事实，人群需求参考客户画像。"
        scenario_header = f"目标人群：{strategy['audience']}（下方有客户画像可参考）"
        scenario_section = "客户画像（理解人群的角色、任务和限制，画像没确认的门槛不要写成已满足）：\n" + chr(10).join(scenario_blocks)
    else:
        opening = "成稿形态严格按平台模板，产品参数只来自产品事实。"
        scenario_header = f"目标人群：{strategy['audience']}（知识库没有对应画像，请你按自己对这个人群的理解来写，不要编造未证实的使用结论）"
        scenario_section = (
            "写作要求：以产品本身的事实、卖点和适用性为主，结合平台模板和写作视角组织内容，"
            "按你对目标人群的合理理解切入，不要虚构具体的使用数据或结论。"
        )
    return f"""请为下面的任务写图文软文。{opening}

型号：{strategy['product']}
人群：{strategy['audience']}
营销场景：{strategy['scene']}
{scenario_header}
发布平台：{strategy['platform']}
写作视角：{strategy['perspective']}——{perspective_brief(strategy['perspective'])}
{revision}

{exemplar_block}P6/02 平台模板：
【{platform_doc['role']}】{platform_doc['title']}
使用方式：{platform_doc['use']}
{platform_doc['text'][:3500]}

{scenario_section}

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


def _verification(article, documents, images, issues, pending, nearby, strategy=None, style_issues=None) -> dict:
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
    ai_style = style_issues or ["通过：没有发现明显 AI 腔。"]
    pending_lines = pending or ["没有额外待确认项。"]
    return {
        "facts": fact_lines,
        "images": image_lines,
        "compliance": compliance,
        "ai_style": ai_style,
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
            f"- 写作视角：{strategy.get('perspective', '')}",
            f"- 参考画像：{strategy.get('module_name') or strategy.get('module_id') or '无（按人群理解）'}",
            f"- 发布平台：{strategy['platform']}",
            f"- 平台模板：{platform_doc['title']}",
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
            "- AI味：",
            *[f"  {line}" for line in verification.get("ai_style") or []],
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
