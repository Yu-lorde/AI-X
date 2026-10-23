"""从工作区的 知识库/ 读取所有要用的文档：产品事实、客户画像、精简平台模板。

只读本地，不再走远程。场景只参考客户画像；没有对应画像时返回空，让模型按理解写。
"""

import csv
from pathlib import Path

from strategy import classify_title

KB_ROOT = Path(__file__).resolve().parent.parent / "知识库"
PRODUCTS = KB_ROOT / "产品"
PORTRAITS = KB_ROOT / "画像"
TEMPLATES = KB_ROOT / "平台模板"


class LocalError(RuntimeError):
    pass


def collect(route: dict, strategy: dict) -> dict:
    if not KB_ROOT.exists():
        raise LocalError(f"找不到知识库目录：{KB_ROOT}")
    scenario_docs = _scenario_docs(route)
    platform_doc = _platform_doc(strategy)
    documents, images, nearby = _product_pack(strategy["product"])
    return {
        "scenario_docs": scenario_docs,
        "platform_doc": platform_doc,
        "documents": documents,
        "images": images,
        "nearby": nearby,
        "source": "知识库",
    }


def _scenario_docs(route: dict) -> list[dict]:
    """只取客户画像。通用模式或没有对应画像时返回空。"""
    if route.get("generic") or not route.get("module_id"):
        return []
    path = PORTRAITS / f"{route['module_id']}.md"
    if not path.is_file():
        return []
    return [
        {
            "role": "客户画像",
            "use": "核对角色、任务和组织限制。画像里的空项不能被写成已经确认的需求。",
            "title": path.name,
            "text": _read(path, 2500),
        }
    ]


def _platform_doc(strategy: dict) -> dict:
    path = TEMPLATES / f"{strategy['template_file']}.md"
    if not path.is_file():
        path = _find_markdown(TEMPLATES, f"{strategy['template_query']}.md") or path
    return {
        "role": "平台模板",
        "use": "成稿的写作流程、篇幅、图文节奏、标题数和交付字段以这份模板为准。",
        "title": path.name if path.is_file() else strategy["template_file"],
        "text": _read(path, 4000),
    }


def _product_pack(product: str) -> tuple[list[dict], list[dict], list[dict]]:
    documents = []
    images = []
    nearby = []
    if not PRODUCTS.exists():
        return documents, images, nearby
    for fact in PRODUCTS.rglob("产品事实.md"):
        folder = fact.parent.name
        kind = classify_title(product, folder)
        if kind == "nearby":
            nearby.append({"title": folder})
            continue
        if kind != "exact":
            continue
        documents.append(
            {
                "title": f"{folder}/产品事实.md",
                "media_id": "",
                "text": _read(fact, 4000),
                "kind": "file",
            }
        )
        image_dir = fact.parent / "images"
        if not image_dir.exists():
            continue
        captions = _image_captions(fact.parent / "图片索引.csv")
        for file in sorted(image_dir.iterdir()):
            if file.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                continue
            if classify_title(product, file.name) != "exact":
                continue
            images.append(
                {
                    "title": file.name,
                    "media_id": "",
                    "text": "",
                    "kind": "image",
                    "path": str(file),
                    "theme": captions.get(file.name) or file.stem,
                }
            )
    return documents[:3], images[:8], nearby


def _image_captions(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        return {
            (row.get("文件名") or "").strip(): (row.get("官网图片说明") or "").strip()
            for row in rows
            if (row.get("文件名") or "").strip()
        }


def _find_markdown(root: Path, name: str) -> Path | None:
    if not root.exists():
        return None
    matches = [path for path in root.rglob(name) if path.is_file()]
    return matches[0] if matches else None


def _read(path: Path | None, limit: int) -> str:
    if path is None or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")[:limit].strip()
