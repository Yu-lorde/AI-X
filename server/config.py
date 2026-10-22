from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = PROJECT_ROOT / "agent"
WEB_DIST = PROJECT_ROOT / "web" / "dist"
DATA_HOME = Path(__file__).resolve().parent / "data"
NODE_DIR = PROJECT_ROOT / ".tools" / "node"

COOKIE_NAME = "aix_visitor"
COOKIE_MAX_AGE = 365 * 24 * 3600


def detect_kb_root() -> Path | None:
    """找到含 P8-客户场景库 的本地知识库目录。"""
    candidates: list[Path] = []
    explicit = os.environ.get("AIX_KB_ROOT", "").strip()
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(PROJECT_ROOT / "华为PC知识库")
    for folder in sorted(PROJECT_ROOT.iterdir()):
        if folder.is_dir() and not folder.name.startswith(".") and folder not in candidates:
            candidates.append(folder)

    for base in candidates:
        if (base / "P8-客户场景库").is_dir():
            return base
        if base.is_dir():
            try:
                children = sorted(base.iterdir())
            except OSError:
                continue
            for child in children:
                if (child / "P8-客户场景库").is_dir():
                    return child
    return None
