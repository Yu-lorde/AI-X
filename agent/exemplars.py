"""Few-shot 范文库：按平台/人群/场景检索最匹配的范文，作为风格示例注入 prompt。

范文只用于学习语气、结构和节奏，不提供任何产品事实（事实只来自 P1）。
每篇范文是一个带 frontmatter 的 md 文件，字段见 范文库/README.md。
"""

import re
from pathlib import Path

from config import env

DEFAULT_EXEMPLAR_ROOT = Path(__file__).resolve().parent.parent / "范文库"


def exemplar_root() -> Path:
    raw = env("EXEMPLAR_ROOT")
    return Path(raw) if raw else DEFAULT_EXEMPLAR_ROOT


def load_exemplars() -> list[dict]:
    root = exemplar_root()
    if not root.exists():
        return []
    items = []
    for path in sorted(root.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        meta, body = _parse(path.read_text(encoding="utf-8"))
        if not body.strip():
            continue
        items.append(
            {
                "title": path.stem,
                "platform": meta.get("platform", ""),
                "audience": meta.get("audience", ""),
                "scene": meta.get("scene", ""),
                "perspective": meta.get("perspective", ""),
                "product": meta.get("product", ""),
                "tags": meta.get("tags", []),
                "good_points": meta.get("good_points", ""),
                "body": body.strip(),
            }
        )
    return items


def select_exemplars(platform: str, audience: str, scene: str, note: str = "", limit: int = 2, perspective: str = "") -> list[dict]:
    """平台是硬门槛，再按视角、场景、人群和标签打分排序，取前 limit 篇。"""
    text = f"{audience} {note}"
    scored = []
    for item in load_exemplars():
        # 不同平台的范文会教错成稿形态。范文未写平台视为通用，可用于任何平台。
        if item["platform"] and platform and item["platform"] != platform:
            continue
        score = 0
        if item["platform"] and item["platform"] == platform:
            score += 3
        if item["perspective"] and perspective and item["perspective"] == perspective:
            score += 3
        if item["scene"] and item["scene"] == scene:
            score += 2
        if item["audience"] and item["audience"] in text:
            score += 2
        score += sum(1 for tag in item["tags"] if tag and tag in text)
        if score <= 0:
            continue
        scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def _parse(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    meta = {}
    for line in parts[1].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if key == "tags":
            value = value.strip("[]")
            meta[key] = [token.strip().strip('"').strip("'") for token in re.split(r"[，,、]", value) if token.strip()]
        else:
            meta[key] = value.strip('"').strip("'")
    return meta, parts[2]
