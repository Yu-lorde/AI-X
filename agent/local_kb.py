"""ima 不可用时，从本地华为 PC 知识库读取同样的场景文档、平台模板、产品事实和图片。"""

import csv
from pathlib import Path

from strategy import classify_title

KB_ROOT = Path(__file__).resolve().parent.parent / "华为PC知识库" / "华为PC全板块深度知识库_v7"
P8 = KB_ROOT / "P8-客户场景库"
P6_TEMPLATES = KB_ROOT / "P6-营销素材库" / "02-平台模板"
P1 = KB_ROOT / "P1-产品参数库"
CHILD_FILES = {
    "客户画像": "客户画像.md",
    "问题清单": "问题清单.md",
    "方案输出模板": "方案输出模板.md",
    "验收清单": "验收清单.md",
    "完整参考案例": "完整参考案例.md",
}


class LocalError(RuntimeError):
    pass


def collect(route: dict, strategy: dict) -> dict:
    if not KB_ROOT.exists():
        raise LocalError(f"找不到本地知识库：{KB_ROOT}")
    scenario_docs = _scenario_docs(route)
    platform_doc = _platform_doc(strategy)
    documents, images, nearby = _product_pack(strategy["product"])
    return {
        "scenario_docs": scenario_docs,
        "platform_doc": platform_doc,
        "documents": documents,
        "images": images,
        "nearby": nearby,
        "source": "本地知识库",
    }


def _scenario_docs(route: dict) -> list[dict]:
    parent = _find_markdown(P8, f"{route['parent_title']}.md")
    docs = [
        {
            "role": "母文档",
            "use": "先按母文档的角色、任务链、证据边界和模块导航执行。",
            "title": parent.name if parent else route["parent_title"],
            "text": _read(parent, 2500),
        }
    ]
    folder = P8 / "12-行业场景" / route["module_id"]
    for child in route["children"]:
        path = folder / CHILD_FILES[child["role"]]
        docs.append(
            {
                "role": child["role"],
                "use": child["use"],
                "title": str(path.relative_to(KB_ROOT)) if path.exists() else child["query"],
                "text": _read(path, 2500),
            }
        )
    return docs


def _platform_doc(strategy: dict) -> dict:
    path = P6_TEMPLATES / f"{strategy['template_file']}.md"
    if not path.exists():
        path = _find_markdown(P6_TEMPLATES, f"{strategy['template_query']}.md") or path
    return {
        "role": "平台模板",
        "use": "成稿的篇幅、结构、图文节奏和发布前检查以这份 P6/02 模板为准。",
        "title": path.name if path.exists() else strategy["template_query"],
        "text": _read(path, 4000),
    }


def _product_pack(product: str) -> tuple[list[dict], list[dict], list[dict]]:
    documents = []
    images = []
    nearby = []
    if not P1.exists():
        return documents, images, nearby
    for fact in P1.rglob("产品事实.md"):
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
