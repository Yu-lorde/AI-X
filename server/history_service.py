"""历史作品的服务层：组装记录、保存版本、恢复编辑器状态、隔离访客资源。"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import shutil
from pathlib import Path

from .history_store import (
    assets_dir,
    data_home,
    append_version,
    create_work,
    decode_version,
    delete_work as store_delete_work,
    get_version,
    get_work as store_get_work,
    latest_version,
    list_works as store_list_works,
)

VISITOR_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")


def new_visitor_id() -> str:
    return secrets.token_urlsafe(32)


def valid_visitor_id(value: str | None) -> bool:
    return bool(value and VISITOR_RE.match(str(value)))


def article_fingerprint(article: dict, inputs: dict | None = None) -> str:
    """只比较发布内容与需求输入，不含绝对路径等本机信息。"""
    canonical = {
        "title": str(article.get("title") or ""),
        "title_options": list(article.get("title_options") or []),
        "lead": str(article.get("lead") or ""),
        "paragraphs": list(article.get("paragraphs") or []),
        "cta": str(article.get("cta") or ""),
        "tags": list(article.get("tags") or []),
        "facts": list(article.get("facts") or []),
        "images": [
            {
                "name": str(image.get("name") or ""),
                "position": str(image.get("position") or ""),
                "caption": str(image.get("caption") or ""),
                "source_label": str(image.get("source_label") or ""),
            }
            for image in article.get("images") or []
        ],
    }
    if inputs is not None:
        canonical["inputs"] = {
            key: str(inputs.get(key) or "")
            for key in ("product", "audience", "scene", "platform", "note")
        }
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def list_works(owner_id: str) -> list[dict]:
    if not valid_visitor_id(owner_id):
        return []
    return store_list_works(owner_id)


def get_work(owner_id: str, work_id: str) -> dict | None:
    if not valid_visitor_id(owner_id) or not work_id:
        return None
    return store_get_work(owner_id, work_id)


def load_work(owner_id: str, work_id: str, version_no: int | None = None) -> dict | None:
    """读取作品版本并恢复编辑器状态。不会写库，也不会触发模型或检索。"""
    if not valid_visitor_id(owner_id) or not work_id:
        return None
    work = get_work(owner_id, work_id)
    if work is None:
        return None
    if version_no is None:
        row = latest_version(owner_id, work_id)
    else:
        row = get_version(owner_id, work_id, int(version_no))
    if row is None:
        return None
    version = decode_version(row)
    state = _hydrate_state(version["state"])
    state["history"] = {
        "work_id": work_id,
        "version_no": version["version_no"],
        "source_version_no": version["source_version_no"],
        "fingerprint": version["fingerprint"],
        "schema_version": version["schema_version"],
        "created_at": version["created_at"],
    }
    return {
        "work": work,
        "version": version,
        "inputs": version["inputs"],
        "article": version["article"],
        "state": state,
        "sources": version["sources"],
        "verification": version["verification"],
        "images": version["images"],
    }


def save_new_work(owner_id: str, inputs: dict, article: dict, state: dict, sources: dict, verification: dict) -> dict:
    """完整文章生成成功后新建作品，自动写入 V1。"""
    if not valid_visitor_id(owner_id):
        raise ValueError("访客标识无效，无法保存历史")
    work_id = secrets.token_hex(16)
    stored_state = _persist_state(owner_id, work_id, state)
    payload = _payload(inputs, article, stored_state, sources, verification)
    fingerprint = article_fingerprint(article, inputs)
    title = str(article.get("title") or "未命名").strip() or "未命名"
    platform = str(inputs.get("platform") or "").strip()
    try:
        result = create_work(owner_id, title, platform, fingerprint, payload, work_id=work_id)
    except Exception:
        _remove_work_assets(owner_id, work_id)
        raise
    result["fingerprint"] = fingerprint
    result["title"] = title
    result["platform"] = platform
    return result


def save_version(
    owner_id: str,
    work_id: str,
    inputs: dict,
    article: dict,
    state: dict,
    sources: dict,
    verification: dict,
    source_version_no: int | None = None,
) -> dict:
    """把当前编辑框的最新内容保存为同一作品的下一个版本。"""
    if not valid_visitor_id(owner_id) or not work_id:
        raise ValueError("访客标识或作品无效")
    latest = latest_version(owner_id, work_id)
    if latest is None:
        raise PermissionError("作品不存在或不属于当前访客")
    fingerprint = article_fingerprint(article, inputs)
    if latest["fingerprint"] == fingerprint:
        return {
            "created": False,
            "version_no": int(latest["version_no"]),
            "fingerprint": fingerprint,
        }
    stored_state = _persist_state(owner_id, work_id, state)
    payload = _payload(inputs, article, stored_state, sources, verification)
    result = append_version(
        owner_id,
        work_id,
        fingerprint,
        payload,
        source_version_no=int(source_version_no) if source_version_no else None,
    )
    result["fingerprint"] = fingerprint
    return result


def delete_work(owner_id: str, work_id: str) -> bool:
    """先删数据库，成功后再清理该作品的图片目录。"""
    if not valid_visitor_id(owner_id) or not work_id:
        return False
    if not store_delete_work(owner_id, work_id):
        return False
    _remove_work_assets(owner_id, work_id)
    return True


def _payload(inputs: dict, article: dict, state: dict, sources: dict, verification: dict) -> dict:
    images = {
        "candidates": list(state.get("candidates") or []),
        "article": [
            {
                "name": image.get("name") or "",
                "position": image.get("position") or "",
                "caption": image.get("caption") or "",
            }
            for image in article.get("images") or []
        ],
    }
    return {
        "inputs": inputs,
        "article": article,
        "state": state,
        "sources": sources,
        "images": images,
        "verification": verification,
    }


def _safe_name(name: str) -> str:
    stem = Path(name or "image").name
    suffix = Path(stem).suffix.lower() or ".img"
    digest = hashlib.sha256(str(name or "image").encode("utf-8")).hexdigest()[:12]
    return f"{digest}{suffix}"


def _persist_state(owner_id: str, work_id: str, state: dict) -> dict:
    """复制本次允许留存的图片到受控目录，并在状态里写相对路径。"""
    folder = assets_dir() / owner_id / work_id
    folder.mkdir(parents=True, exist_ok=True)
    root = data_home().resolve()
    stored = json.loads(json.dumps(state or {}, ensure_ascii=False))
    candidates = []
    for item in stored.get("candidates") or []:
        name = str(item.get("name") or "")
        raw_path = str(item.get("path") or "")
        target_rel = ""
        missing = not bool(raw_path)
        if raw_path:
            source = Path(raw_path).expanduser()
            try:
                resolved = source.resolve()
            except OSError:
                resolved = source
            if _inside(resolved, folder):
                target_rel = resolved.relative_to(root).as_posix()
                missing = False
            elif resolved.is_file():
                dest = folder / _safe_name(name)
                try:
                    shutil.copy2(resolved, dest)
                    target_rel = dest.relative_to(root).as_posix()
                    missing = False
                except OSError:
                    missing = True
        candidates.append(
            {
                "name": name,
                "path": target_rel,
                "theme": str(item.get("theme") or ""),
                "missing": missing,
            }
        )
    stored["candidates"] = candidates
    stored.pop("embed_images", None)
    return stored


def _hydrate_state(state: dict) -> dict:
    restored = json.loads(json.dumps(state or {}, ensure_ascii=False))
    root = assets_dir().resolve()
    home = data_home().resolve()
    candidates = []
    missing_names = []
    for item in restored.get("candidates") or []:
        rel = str(item.get("path") or "")
        path = ""
        if rel:
            candidate = (home / rel).resolve()
            if _inside(candidate, root) and candidate.is_file():
                path = str(candidate)
        missing = not bool(path)
        if missing:
            missing_names.append(str(item.get("name") or ""))
        candidates.append(
            {
                "name": str(item.get("name") or ""),
                "path": path,
                "theme": str(item.get("theme") or ""),
                "missing": missing,
            }
        )
    restored["candidates"] = candidates
    restored["missing_images"] = missing_names
    restored["embed_images"] = True
    restored.setdefault("nearby_lines", [])
    return restored


def _inside(path: Path, folder: Path) -> bool:
    try:
        path.resolve().relative_to(folder.resolve())
        return True
    except (ValueError, OSError):
        return False


def _remove_work_assets(owner_id: str, work_id: str) -> None:
    folder = assets_dir() / owner_id / work_id
    if _inside(folder, assets_dir()) and folder.is_dir():
        shutil.rmtree(folder, ignore_errors=True)
