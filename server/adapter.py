"""把 agent 的成稿结果转换成前端可直接使用的结构。"""

from __future__ import annotations

import base64
import hashlib
import hmac
from pathlib import Path

from editor import MAX_PARAS, NONE, caption_for, compose_article, intro_line, live_verification, slot_names
from local_kb import KB_ROOT
from pipeline import _export

from .config import AGENT_DIR, DATA_HOME
from .history_store import visitor_secret

ALLOWED_ROOTS = [KB_ROOT, AGENT_DIR / "cache", DATA_HOME / "assets"]

_VERIFICATION_KEYS = ("facts", "images", "compliance", "pending")


def image_token(path: str) -> str:
    raw = str(Path(path).resolve())
    digest = hmac.new(visitor_secret().encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()[:20]
    body = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{body}.{digest}"


def image_url(path: str) -> str:
    if not path:
        return ""
    file = Path(path)
    if not file.is_file():
        return ""
    return "/api/images/" + image_token(str(file))


def resolve_token(token: str) -> Path | None:
    body, _, digest = str(token or "").partition(".")
    if not body or not digest:
        return None
    try:
        padded = body + "=" * (-len(body) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    expected = hmac.new(visitor_secret().encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()[:20]
    if not hmac.compare_digest(expected, digest):
        return None
    path = Path(raw)
    try:
        resolved = path.resolve()
    except OSError:
        return None
    if not resolved.is_file():
        return None
    for root in ALLOWED_ROOTS:
        try:
            resolved.relative_to(root.resolve())
            return resolved
        except (ValueError, OSError):
            continue
    return None


def serialize_candidates(state: dict) -> list[dict]:
    items = []
    for item in state.get("candidates") or []:
        name = str(item.get("name") or "")
        url = image_url(str(item.get("path") or ""))
        items.append(
            {
                "name": name,
                "theme": str(item.get("theme") or ""),
                "url": url,
                "missing": bool(item.get("missing")) or not bool(url),
            }
        )
    return items


def serialize_article(article: dict) -> dict:
    images = []
    for image in article.get("images") or []:
        url = image_url(str(image.get("path") or ""))
        images.append(
            {
                "name": str(image.get("name") or ""),
                "position": str(image.get("position") or ""),
                "caption": str(image.get("caption") or ""),
                "source_label": str(image.get("source_label") or ""),
                "url": url,
                "missing": not bool(url),
            }
        )
    return {
        "title": str(article.get("title") or ""),
        "title_options": list(article.get("title_options") or []),
        "lead": str(article.get("lead") or ""),
        "paragraphs": list(article.get("paragraphs") or []),
        "cta": str(article.get("cta") or ""),
        "tags": list(article.get("tags") or []),
        "facts": list(article.get("facts") or []),
        "images": images,
    }


def serialize_verification(verification: dict | None) -> dict:
    data = verification or {}
    return {key: [str(item) for item in data.get(key) or []] for key in _VERIFICATION_KEYS}


def editor_from(article: dict, state: dict) -> dict:
    paragraphs = [str(item) for item in article.get("paragraphs") or []][:MAX_PARAS]
    if not paragraphs:
        paragraphs = [str(item) for item in state.get("paragraphs") or []][:MAX_PARAS] or [""]
    count = len(paragraphs)
    names = slot_names({**article, "paragraphs": paragraphs}, count)
    captions = [caption_for(name, state) for name in names]
    return {
        "title": str(article.get("title") or ""),
        "options": "\n".join(article.get("title_options") or []),
        "lead": str(article.get("lead") or ""),
        "cta": str(article.get("cta") or ""),
        "tags": " ".join(article.get("tags") or []),
        "paragraphs": paragraphs,
        "picks": ["" if name == NONE else name for name in names[1:]],
        "captions": captions[1:],
        "cover": "" if names[0] == NONE else names[0],
        "cover_caption": captions[0],
    }


def compose_from_editor(state: dict, editor: dict) -> tuple[dict, dict, str]:
    paragraphs = [str(item) for item in editor.get("paragraphs") or []][:MAX_PARAS] or [""]
    count = len(paragraphs)
    picks = [str(item) for item in editor.get("picks") or []][:count]
    captions = [str(item) for item in editor.get("captions") or []][:count]
    picks = ["" if item == NONE else item for item in picks] + [""] * (count - len(picks))
    captions = captions + [""] * (count - len(captions))
    picks = [str(editor.get("cover") or "")] + picks
    captions = [str(editor.get("cover_caption") or "")] + captions
    article = compose_article(
        editor.get("title") or "",
        editor.get("options") or "",
        editor.get("lead") or "",
        paragraphs,
        editor.get("cta") or "",
        editor.get("tags") or "",
        picks,
        captions,
        state,
    )
    verification = live_verification(state, article)
    export_text = _export(
        state.get("strategy") or {},
        state.get("scenario_docs") or [],
        state.get("platform_doc") or {},
        state.get("documents") or [],
        article,
        verification,
    )
    return article, verification, export_text


def preview_payload(article: dict, verification: dict, export_text: str, fingerprint: str, state: dict) -> dict:
    return {
        "article": serialize_article(article),
        "verification": serialize_verification(verification),
        "export_text": export_text,
        "fingerprint": fingerprint,
        "intro": intro_line(state),
    }
