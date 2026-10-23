"""把门店海报成稿排成 A4 竖版 PNG。纯本地排版，不调用任何外部模型。"""

from __future__ import annotations

import io
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1240, 1754
MARGIN = 96
RED = "#ED1C30"
INK = "#141414"
GRAY = "#5A5A5A"
CARD = "#FFFFFF"
BG = "#F2F3F5"

_FONT_DIR = Path("C:/Windows/Fonts")
_REGULAR_CANDIDATES = ("msyh.ttc", "simhei.ttf", "simsun.ttc", "Deng.ttf")
_BOLD_CANDIDATES = ("msyhbd.ttc", "msyh.ttc", "simhei.ttf", "Dengb.ttf")
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+\-/]*|\s+|.")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = _BOLD_CANDIDATES if bold else _REGULAR_CANDIDATES
    for name in names:
        path = _FONT_DIR / name
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int) -> list[str]:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return []
    tokens = _TOKEN_RE.findall(text)
    lines: list[str] = []
    current = ""
    index = 0
    while index < len(tokens):
        token = tokens[index]
        candidate = current + token
        if draw.textlength(candidate.rstrip(), font=font) <= max_width:
            current = candidate
            index += 1
            continue
        if current.strip():
            lines.append(current.strip())
            current = "" if token.isspace() else token
            index += 1
            if len(lines) >= max_lines:
                break
            continue
        # 单个词就超宽：按字符硬拆
        for char in token:
            if draw.textlength(current + char, font=font) <= max_width:
                current += char
            else:
                lines.append(current.strip())
                current = char
                if len(lines) >= max_lines:
                    break
        index += 1
        if len(lines) >= max_lines:
            break
    if current.strip() and len(lines) < max_lines:
        lines.append(current.strip())
    if index < len(tokens) and lines:
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > max_width:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


def _cover(path: str, width: int, height: int) -> Image.Image | None:
    file = Path(str(path or ""))
    if not file.is_file():
        return None
    try:
        image = Image.open(file).convert("RGB")
    except OSError:
        return None
    scale = max(width / image.width, height / image.height)
    size = (max(1, math.ceil(image.width * scale)), max(1, math.ceil(image.height * scale)))
    image = image.resize(size, Image.LANCZOS)
    left = (image.width - width) // 2
    top = (image.height - height) // 2
    return image.crop((left, top, left + width, top + height))


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    size = start
    while size > 20:
        font = _font(size, bold)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 2
    return _font(20, bold)


def render_poster(article: dict, state: dict | None = None) -> bytes:
    state = state or {}
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([44, 44, W - 44, H - 44], radius=34, fill=CARD)

    x = MARGIN
    right = W - MARGIN
    content_width = right - x
    y = 108

    brand_font = _font(30, True)
    tag_font = _font(23)
    draw.text((x, y), "懂你所需", font=brand_font, fill=RED)
    tag = "门店海报"
    draw.text((right - draw.textlength(tag, font=tag_font), y + 5), tag, font=tag_font, fill="#8A8A8A")
    y += 66

    title_font = _font(70, True)
    for line in _wrap(draw, article.get("title") or "门店海报", title_font, content_width, 3):
        draw.text((x, y), line, font=title_font, fill=INK)
        y += 90
    y += 8
    draw.rounded_rectangle([x, y, x + 110, y + 8], radius=4, fill=RED)
    y += 40

    lead_font = _font(32)
    lead_lines = _wrap(draw, article.get("lead") or "", lead_font, content_width, 3)
    for line in lead_lines:
        draw.text((x, y), line, font=lead_font, fill=GRAY)
        y += 48
    if lead_lines:
        y += 26

    images = article.get("images") or []
    candidates = state.get("candidates") or []
    image_path = ""
    for item in images:
        if str(item.get("path") or ""):
            image_path = str(item["path"])
            break
    if not image_path:
        for item in candidates:
            if str(item.get("path") or ""):
                image_path = str(item["path"])
                break

    image_height = 600
    drawn = _cover(image_path, content_width, image_height)
    if drawn is not None:
        mask = Image.new("L", (content_width, image_height), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, content_width, image_height], radius=22, fill=255)
        canvas.paste(drawn, (x, y), mask)
        y += image_height + 42
    else:
        # 没有可用配图时用型号色块占位，避免海报中段留出大片空白。
        panel_height = 420
        draw.rounded_rectangle([x, y, right, y + panel_height], radius=22, fill="#F4F5F7")
        draw.rounded_rectangle([x + 34, y + 40, x + 74, y + 48], radius=4, fill=RED)
        model = str((state.get("strategy") or {}).get("product") or "门店海报")
        model_font = _fit_font(draw, model, content_width - 68, 54)
        draw.text((x + 34, y + 78), model, font=model_font, fill=INK)
        scene = str((state.get("strategy") or {}).get("scene") or "")
        if scene:
            draw.text((x + 34, y + 162), scene, font=_font(30), fill=GRAY)
        y += panel_height + 42

    points = [str(item.get("point") or "").strip() for item in article.get("facts") or []]
    points = [item for item in points if item]
    if not points:
        points = [str(item).strip() for item in article.get("paragraphs") or [] if str(item).strip()]
    seen: set[str] = set()
    bullets: list[str] = []
    for item in points:
        if item in seen:
            continue
        seen.add(item)
        bullets.append(item)
        if len(bullets) == 3:
            break

    bullet_font = _font(31)
    for item in bullets:
        if y + 46 > H - 260:
            break
        draw.rounded_rectangle([x + 2, y + 13, x + 12, y + 23], radius=3, fill=RED)
        line = _wrap(draw, item, bullet_font, content_width - 34, 1)
        if line:
            draw.text((x + 32, y), line[0], font=bullet_font, fill="#252525")
        y += 52

    cta = str(article.get("cta") or "").strip()
    if cta:
        box_top = H - 288
        draw.rounded_rectangle([x, box_top, right, box_top + 92], radius=16, fill=RED)
        cta_font = _fit_font(draw, cta, content_width - 60, 38)
        width = draw.textlength(cta, font=cta_font)
        draw.text((x + (content_width - width) / 2, box_top + (92 - cta_font.size) / 2 - 5), cta, font=cta_font, fill="#FFFFFF")

    strategy = state.get("strategy") or {}
    footer = " · ".join(part for part in (strategy.get("product") or "", strategy.get("scene") or "") if part)
    if footer:
        footer_font = _font(23)
        draw.text((x, H - 158), footer, font=footer_font, fill="#9A9A9A")

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
