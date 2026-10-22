"""在导入 agent 模块前准备好路径、Node 和本地知识库目录。"""

from __future__ import annotations

import os
import sys

from .config import AGENT_DIR, NODE_DIR, detect_kb_root


def boot() -> None:
    agent = str(AGENT_DIR)
    if agent not in sys.path:
        sys.path.insert(0, agent)

    if NODE_DIR.is_dir():
        node = str(NODE_DIR)
        parts = os.environ.get("PATH", "").split(os.pathsep)
        if node not in parts:
            os.environ["PATH"] = node + os.pathsep + os.environ.get("PATH", "")

    if not os.environ.get("AIX_KB_ROOT"):
        kb_root = detect_kb_root()
        if kb_root is not None:
            os.environ["AIX_KB_ROOT"] = str(kb_root)
