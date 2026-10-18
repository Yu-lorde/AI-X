"""把成稿拆成按位置编辑的字段，再组装回效果区使用的文章。"""

from render import _slot

NONE = "不配图"
MAX_PARAS = 6


def fit_paragraphs(paragraphs: list[str]) -> list[str]:
    items = [str(item).strip() for item in paragraphs if str(item).strip()]
    if not items:
        return [""]
    if len(items) <= MAX_PARAS:
        return items
    return items[: MAX_PARAS - 1] + ["\n\n".join(items[MAX_PARAS - 1 :])]


def slot_names(article: dict, count: int) -> list[str]:
    names = [NONE] * (count + 1)
    paragraphs = article.get("paragraphs") or []
    for image in article.get("images") or []:
        slot = _slot(image.get("position") or "", len(paragraphs))
        name = image.get("name") or ""
        if slot is None or not name or not (0 <= slot <= count) or names[slot] != NONE:
            continue
        names[slot] = name
    for image in article.get("images") or []:
        name = image.get("name") or ""
        if not name or name in names:
            continue
        for index, current in enumerate(names):
            if current == NONE:
                names[index] = name
                break
    return names


def pack_state(result: dict) -> dict:
    article = result.get("article") or {}
    paragraphs = fit_paragraphs(article.get("paragraphs") or [])
    candidates = []
    seen = set()
    for item in result.get("images") or []:
        name = item.get("title") or item.get("name") or ""
        path = item.get("path") or ""
        if not name or not path or name in seen:
            continue
        seen.add(name)
        candidates.append({"name": name, "path": path, "theme": item.get("theme") or "产品画面"})
    for image in article.get("images") or []:
        caption = str(image.get("caption") or "").strip()
        if not caption:
            continue
        for candidate in candidates:
            if candidate["name"] == image.get("name"):
                candidate["theme"] = caption
    verification = result.get("verification") or {}
    strategy = result.get("strategy") or {}
    platform_doc = result.get("platform_doc") or {}
    return {
        "ready": True,
        "candidates": candidates,
        "facts": article.get("facts") or [],
        "verification": verification,
        "nearby_lines": [line for line in verification.get("images") or [] if str(line).startswith("已排除")],
        "strategy": strategy,
        "paragraph_count": len(paragraphs),
        "use_tags": bool(strategy.get("use_tags")),
        "source": result.get("source") or "",
        "documents": [{"title": item.get("title") or ""} for item in result.get("documents") or []],
        "scenario_docs": [
            {"role": item.get("role") or "", "title": item.get("title") or ""}
            for item in result.get("scenario_docs") or []
        ],
        "platform_doc": {"title": platform_doc.get("title") or strategy.get("template_file") or ""},
        "paragraphs": paragraphs,
    }


def compose_article(title, options, lead, paragraphs, cta, tags, picks, captions, state) -> dict:
    by_name = {item["name"]: item for item in state.get("candidates") or []}
    positions = ["封面"] + [f"第{index}段之后" for index in range(1, len(paragraphs) + 1)]
    images = []
    for pick, position, caption in zip(picks, positions, captions):
        if not pick or pick == NONE:
            continue
        origin = by_name.get(pick)
        if origin is None:
            continue
        images.append(
            {
                "name": origin["name"],
                "source": origin["name"],
                "position": position,
                "caption": (caption or origin.get("theme") or "产品画面").strip(),
                "path": origin["path"],
                "theme": origin.get("theme") or "",
                "source_label": state.get("source") or "知识库",
                "use_file_url": True,
            }
        )
    option_lines = [line.strip() for line in str(options or "").splitlines() if line.strip()][:3]
    tag_list = []
    if state.get("use_tags"):
        raw = str(tags or "").replace("，", " ").replace(",", " ").replace("#", " ")
        tag_list = [item for item in raw.split() if item]
    return {
        "title": str(title or "").strip(),
        "title_options": option_lines,
        "lead": str(lead or "").strip(),
        "paragraphs": list(paragraphs),
        "cta": str(cta or "").strip(),
        "tags": tag_list,
        "images": images,
        "facts": state.get("facts") or [],
    }


def live_verification(state: dict, article: dict) -> dict:
    verification = dict(state.get("verification") or {})
    strategy = state.get("strategy") or {}
    product = strategy.get("product") or ""
    minimum = strategy.get("image_min") or 0
    from strategy import classify_title

    lines = []
    for image in article.get("images") or []:
        if classify_title(product, image.get("name") or "") == "exact":
            lines.append(f"通过：{image['name']}，插在{image['position']}")
        else:
            lines.append(f"待确认：{image['name']} 与型号 {product} 不一致")
    if not lines:
        lines.append("待确认：当前成稿没有配图。")
    elif minimum and len(lines) < minimum:
        lines.append(f"待确认：平台模板建议至少 {minimum} 张，当前选用 {len(article['images'])} 张。")
    lines.extend(state.get("nearby_lines") or [])
    verification["images"] = lines
    return verification


def intro_line(state: dict) -> str:
    strategy = state.get("strategy") or {}
    if not strategy:
        return ""
    return " · ".join(
        str(item)
        for item in (
            strategy.get("platform"),
            strategy.get("audience"),
            strategy.get("scene"),
            strategy.get("parent_title"),
            strategy.get("module_id"),
        )
        if item
    )


def caption_for(name: str, state: dict) -> str:
    if not name or name == NONE:
        return ""
    for item in state.get("candidates") or []:
        if item["name"] == name:
            return item.get("theme") or ""
    return ""
