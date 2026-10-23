"""把四段式结果渲染成带图片的页面。图片来自已经下载的共享库文件。"""

import base64
import html
import re
from pathlib import Path
from urllib.parse import quote


def render_result(result: dict) -> str:
    if result.get("questions"):
        items = "".join(f"<li>{html.escape(item)}</li>" for item in result["questions"])
        return _card("先补充信息", f"<p>{html.escape(result.get('message') or '')}</p><ul>{items}</ul>")
    if not result.get("ok"):
        extra = []
        strategy = result.get("strategy") or {}
        if strategy.get("parent_title"):
            extra.append(
                f"已映射：P8《{html.escape(str(strategy.get('parent_title')))}》"
                f" / {html.escape(str(strategy.get('module_id', '')))} {html.escape(str(strategy.get('module_brief', '')))}"
            )
        docs = result.get("documents") or []
        if docs:
            extra.append("已检索到的资料：" + "、".join(html.escape(item["title"]) for item in docs))
        body = f"<p>{html.escape(result.get('detail') or '')}</p>"
        if extra:
            body += "<p>" + "<br>".join(extra) + "</p>"
        return _card(result.get("message") or "未能生成", body)

    strategy = result["strategy"]
    article = result["article"]
    verification = result["verification"]
    documents = result.get("documents") or []
    return "".join(
        [
            _section("一、场景判断", _scene(strategy)),
            _section("二、知识库依据", _sources(strategy, article, documents)),
            _section("三、图文软文", _article(article)),
            _section("四、核验结果", _checks(verification)),
        ]
    )


def _scene(strategy: dict) -> str:
    rows = [
        ("目标人群", strategy.get("audience")),
        ("使用场景", strategy.get("scene")),
        ("内容目标", strategy.get("module_brief") or strategy.get("module_id")),
        ("发布平台", strategy.get("platform")),
        ("P8 母文档", strategy.get("parent_title")),
        ("平台模板", strategy.get("template_query")),
    ]
    return _rows(rows)


def _sources(strategy: dict, article: dict, documents: list[dict]) -> str:
    facts = "".join(
        f"<li>{html.escape(item['point'])}<span>来源：{html.escape(item['source_title'])}</span></li>"
        for item in article.get("facts") or []
    ) or "<li>本次没有可回链的事实点。</li>"
    titles = "".join(f"<li>{html.escape(item['title'])}</li>" for item in documents) or "<li>无</li>"
    return (
        f"<p>产品型号：{html.escape(str(strategy.get('product') or ''))}</p>"
        f"<p class='label'>事实点</p><ul class='facts'>{facts}</ul>"
        f"<p class='label'>P1 资料</p><ul>{titles}</ul>"
    )


def _article(article: dict) -> str:
    paragraphs = article.get("paragraphs") or []
    slots = {index: [] for index in range(len(paragraphs) + 1)}
    loose = []
    for image in article.get("images") or []:
        slot = _slot(image.get("position") or "", len(paragraphs))
        if slot is None:
            loose.append(image)
        else:
            slots[slot].append(image)
    for index, image in enumerate(loose):
        slots[min(index + 1, len(paragraphs))].append(image)

    options = "；".join(html.escape(item) for item in article.get("title_options") or [])
    parts = []
    if options:
        parts.append(f"<p class='options'>标题备选：{options}</p>")
    parts.append(f"<h3>{html.escape(article.get('title') or '未命名')}</h3>")
    if article.get("lead"):
        parts.append(f"<p class='lead'>{html.escape(article['lead'])}</p>")
    parts.append(_images_html(slots[0]))
    for index, paragraph in enumerate(paragraphs, start=1):
        if str(paragraph).strip():
            parts.append(f"<p>{html.escape(paragraph)}</p>")
        parts.append(_images_html(slots[index]))
    if article.get("cta"):
        parts.append(f"<p class='cta'>行动引导：{html.escape(article['cta'])}</p>")
    tags = " ".join(f"#{html.escape(str(tag).lstrip('#'))}" for tag in article.get("tags") or [])
    if tags:
        parts.append(f"<p class='tags'>{tags}</p>")
    return "".join(parts)


def _checks(verification: dict) -> str:
    blocks = []
    for title, key in (("产品事实", "facts"), ("图片型号", "images"), ("合规", "compliance"), ("AI味", "ai_style"), ("待确认信息", "pending")):
        lines = "".join(f"<li>{html.escape(str(item))}</li>" for item in verification.get(key) or [])
        blocks.append(f"<p class='label'>{title}</p><ul>{lines}</ul>")
    return "".join(blocks)


def _slot(position: str, paragraph_count: int) -> int | None:
    if any(word in position for word in ("标题", "导语", "开头", "封面", "首图")):
        return 0
    if any(word in position for word in ("结尾", "引导", "文末")):
        return paragraph_count
    digits = re.findall(r"\d+", position)
    if not digits:
        return None
    index = int(digits[0])
    if paragraph_count == 0:
        return 0
    return min(max(index, 1), paragraph_count)


def _images_html(images: list[dict]) -> str:
    blocks = []
    for image in images:
        src = _image_src(image)
        caption = image.get("caption") or image.get("theme") or "产品画面"
        meta = (
            f"{html.escape(caption)}"
            f"<span>文件：{html.escape(image.get('name') or '')} · 位置：{html.escape(image.get('position') or '')} · 来源：{html.escape(image.get('source_label') or '知识库')}</span>"
        )
        if src:
            blocks.append(f"<figure><img src='{src}' alt='{html.escape(caption)}'><figcaption>{meta}</figcaption></figure>")
        else:
            blocks.append(f"<figure><figcaption>{meta}</figcaption></figure>")
    return "".join(blocks)


def _image_src(image: dict) -> str:
    path = image.get("path") or ""
    if image.get("use_file_url") and path and Path(path).is_file():
        return "/gradio_api/file=" + quote(Path(path).resolve().as_posix(), safe="/:")
    return _data_uri(path)


def _data_uri(path: str) -> str:
    file = Path(path)
    if not file.is_file():
        return ""
    kind = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
    mime = kind.get(file.suffix.lower(), "image/png")
    encoded = base64.b64encode(file.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _rows(rows: list[tuple]) -> str:
    return "".join(
        f"<p><b>{html.escape(label)}</b> {html.escape(str(value or '未填写'))}</p>" for label, value in rows
    )


def _section(title: str, body: str) -> str:
    return f"<section class='copy-section'><h2>{html.escape(title)}</h2>{body}</section>"


def render_effect(article: dict | None, intro: str = "", notice: str = "") -> str:
    if notice:
        return _card("效果区", f"<p>{html.escape(notice)}</p>")
    if not article:
        return _card("效果区", "<p>生成后，这里按成稿顺序显示标题、正文和图片。编辑区一改，这里马上跟着变。</p>")
    intro_html = f"<p class='scene-line'>{html.escape(intro)}</p>" if intro else ""
    return f"<section class='copy-section effect-sheet'><h2>效果区</h2>{intro_html}{_article(article)}</section>"


def render_sources(strategy: dict | None, article: dict | None, documents: list[dict] | None, scenario_docs: list[dict] | None, source: str = "") -> str:
    if not strategy:
        body = "<p>生成后在这里列出产品型号、事实点和资料标题。</p>"
        return _section("二、知识库依据", body)
    facts = "".join(
        f"<li>{html.escape(item['point'])}<span>来源：{html.escape(item['source_title'])}</span></li>"
        for item in (article or {}).get("facts") or []
    ) or "<li>本次没有可回链的事实点。</li>"
    titles = []
    for item in scenario_docs or []:
        if item.get("title"):
            titles.append(f"<li>[P8/{html.escape(str(item.get('role') or ''))}] {html.escape(item['title'])}</li>")
    for item in documents or []:
        titles.append(f"<li>[P1] {html.escape(item['title'])}</li>")
    title_html = "".join(titles) or "<li>无</li>"
    source_line = f"<p>资料来源：{html.escape(source)}</p>" if source else ""
    body = (
        f"<p>产品型号：{html.escape(str(strategy.get('product') or ''))}</p>"
        f"{source_line}"
        f"<p class='label'>事实点</p><ul class='facts'>{facts}</ul>"
        f"<p class='label'>资料标题</p><ul>{title_html}</ul>"
    )
    return _section("二、知识库依据", body)


def render_checks(verification: dict | None) -> str:
    if not verification:
        body = "<p>生成后在这里列出产品事实、图片型号、合规和待确认信息。</p>"
        return _section("四、核验结果", body)
    return _section("四、核验结果", _checks(verification))


def _card(title: str, body: str) -> str:
    return f"<section class='copy-section notice'><h2>{html.escape(title)}</h2>{body}</section>"
