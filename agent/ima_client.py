"""通过官方 ima_api.cjs 调用知识库。参数由 Python 直接传给 node，不经过 PowerShell。"""

import hashlib
import json
import os
import subprocess
import urllib.request
from pathlib import Path

from config import DEFAULT_SKILL_SCRIPT, env

IMAGE_CACHE = Path(__file__).resolve().parent / "cache" / "images"


class ImaError(RuntimeError):
    pass


def script_path() -> Path:
    raw = env("IMA_SKILL_SCRIPT", DEFAULT_SKILL_SCRIPT)
    path = Path(raw)
    if not path.exists():
        raise ImaError(f"找不到 ima 调用脚本：{path}")
    return path


def call_api(api_path: str, body: dict) -> dict:
    script = script_path()
    payload = json.dumps(body, ensure_ascii=False)
    try:
        completed = subprocess.run(
            ["node", str(script), api_path, payload],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ImaError("没有找到 node。请先安装 Node.js 18 或更高版本。") from exc
    except subprocess.TimeoutExpired as exc:
        raise ImaError("ima 接口超时，请稍后重试。") from exc

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if completed.returncode != 0:
        message = _error_message(stderr) or stdout or "ima 调用失败"
        raise ImaError(message)
    if not stdout:
        raise ImaError(stderr or "ima 没有返回内容")
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ImaError(f"ima 返回的不是 JSON：{stdout[:180]}") from exc
    code = parsed.get("code", 0)
    if code not in (0, None):
        raise ImaError(parsed.get("msg") or f"ima 返回错误码 {code}")
    return parsed.get("data") or {}


def _error_message(stderr: str) -> str:
    if not stderr:
        return ""
    try:
        parsed = json.loads(stderr)
    except json.JSONDecodeError:
        return stderr
    return str(parsed.get("msg") or stderr)


def _items(data: dict, *keys: str) -> list:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def find_knowledge_base(name: str) -> dict:
    data = call_api(
        "openapi/wiki/v1/search_knowledge_base",
        {"query": name, "cursor": "", "limit": 20},
    )
    items = _items(data, "info_list")
    for item in items:
        title = item.get("kb_name") or item.get("name") or ""
        if name in title or title in name:
            kb_id = item.get("kb_id") or item.get("id") or ""
            if kb_id:
                return {"kb_id": kb_id, "kb_name": title}
    if items:
        first = items[0]
        kb_id = first.get("kb_id") or first.get("id") or ""
        title = first.get("kb_name") or first.get("name") or ""
        if kb_id:
            return {"kb_id": kb_id, "kb_name": title}
    raise ImaError(f"当前账号下没有找到知识库「{name}」。请确认已经用同一账号扫码加入。")


def list_knowledge(kb_id: str, folder_id: str = "") -> list[dict]:
    body = {"knowledge_base_id": kb_id, "cursor": "", "limit": 50}
    if folder_id:
        body["folder_id"] = folder_id
    data = call_api(
        "openapi/wiki/v1/get_knowledge_list",
        body,
    )
    found = []
    for item in _items(data, "knowledge_list", "info_list"):
        media_id = item.get("media_id") or ""
        title = item.get("title") or item.get("name") or ""
        if not media_id or not title:
            continue
        found.append(
            {
                "media_id": media_id,
                "title": title,
                "highlight": _plain(item.get("highlight_content") or ""),
                "media_type": item.get("media_type"),
            }
        )
    return found


def probe_connection(kb_name: str) -> str:
    """确认共享库可见，并实际打开一条资料。不返回密钥和知识库 ID。"""
    kb = find_knowledge_base(kb_name)
    hits = search_knowledge(kb["kb_id"], "MateBook D 14")
    method = "按「MateBook D 14」搜索"
    if not hits:
        hits = list_knowledge(kb["kb_id"])
        method = "搜索无结果，已改从目录读取"
    readable = [item for item in hits if item.get("media_type") != 99]
    if not readable:
        raise ImaError(f"已找到知识库「{kb['kb_name']}」，但结果里只有文件夹，没有可打开的资料。")
    readable.sort(key=lambda item: 0 if item.get("media_type") in (7, 13, 20) else 1)

    opened = None
    last_error = ""
    for item in readable[:8]:
        try:
            detail = read_media(item["media_id"])
        except ImaError as exc:
            last_error = str(exc)
            continue
        text = (detail.get("text") or item.get("highlight") or "").strip()
        opened = (item, detail, text)
        if text or detail.get("kind") == "image" or detail.get("url"):
            break
    if opened is None:
        raise ImaError(f"已找到知识库「{kb['kb_name']}」，但打开资料失败：{last_error}")

    item, detail, text = opened
    if text:
        excerpt = text[:180].replace("```", "'''")
        access = f"已读到内容，摘录如下：\n\n```text\n{excerpt}\n```"
    elif detail.get("kind") == "image" or detail.get("url"):
        access = "这条是图片或文件。接口已返回访问信息，说明内容可以打开。"
    else:
        access = "接口有返回，但这条没有可展示的正文。"
    return "\n".join(
        [
            "### 共享知识库已连通",
            f"- 知识库：{kb['kb_name']}",
            f"- 取数方式：{method}",
            f"- 抽查资料：{item['title']}",
            "",
            access,
        ]
    )


def search_knowledge(kb_id: str, query: str) -> list[dict]:
    data = call_api(
        "openapi/wiki/v1/search_knowledge",
        {"query": query, "cursor": "", "knowledge_base_id": kb_id},
    )
    found = []
    for item in _items(data, "info_list"):
        media_id = item.get("media_id") or ""
        title = item.get("title") or ""
        if not media_id or not title:
            continue
        found.append(
            {
                "media_id": media_id,
                "title": title,
                "highlight": _plain(item.get("highlight_content") or ""),
                "media_type": item.get("media_type"),
            }
        )
    return found


def read_media(media_id: str) -> dict:
    """读取原文或判定为图片。读不到原文时返回空文本，调用方改用检索摘要。"""
    info = call_api("openapi/wiki/v1/get_media_info", {"media_id": media_id})
    media_type = info.get("media_type")
    if media_type == 9:
        path = _cache_image(media_id, info)
        return {"kind": "image", "text": "", "path": path}
    if media_type == 11:
        notebook = (info.get("notebook_ext_info") or {}).get("notebook_id") or ""
        if not notebook:
            return {"kind": "note", "text": ""}
        note = call_api(
            "openapi/note/v1/get_doc_content",
            {"note_id": notebook, "target_content_format": 0},
        )
        return {"kind": "note", "text": note.get("content") or ""}

    url_info = info.get("url_info") or {}
    url = url_info.get("url") or ""
    if not url:
        return {"kind": "file", "text": ""}
    if media_type == 9 or _looks_like_image(url):
        return {"kind": "image", "text": "", "url": url}
    text = _download_text(url, url_info.get("headers") or {})
    return {"kind": "file", "text": text, "url": url}


def cached_image_path(media_id: str) -> str:
    digest = hashlib.sha256(media_id.encode()).hexdigest()[:16]
    if not IMAGE_CACHE.exists():
        return ""
    matches = [path for path in IMAGE_CACHE.glob(digest + ".*") if path.is_file() and path.stat().st_size > 1000]
    return str(matches[0]) if matches else ""


def _cache_image(media_id: str, info: dict) -> str:
    """把共享库图片下载到本机缓存。页面展示用本地文件，不把带签名的临时链接写进结果。"""
    url_info = info.get("url_info") or {}
    url = url_info.get("url") or ""
    if not url:
        return ""
    ext = ".png"
    for candidate in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        if candidate in url.lower().split("?")[0]:
            ext = candidate
            break
    IMAGE_CACHE.mkdir(parents=True, exist_ok=True)
    dest = IMAGE_CACHE / f"{hashlib.sha256(media_id.encode()).hexdigest()[:16]}{ext}"
    if dest.exists() and dest.stat().st_size > 1000:
        return str(dest)
    request = urllib.request.Request(url, headers={str(k): str(v) for k, v in (url_info.get("headers") or {}).items()})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read(8_000_000)
    except Exception:
        return ""
    if not data:
        return ""
    dest.write_bytes(data)
    return str(dest)


def _looks_like_image(name: str) -> bool:
    lowered = name.lower().split("?")[0]
    return lowered.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))


def _download_text(url: str, headers: dict) -> str:
    import urllib.request

    request = urllib.request.Request(url, headers={str(k): str(v) for k, v in headers.items()})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content_type = response.headers.get("Content-Type", "")
            if content_type.startswith("image/"):
                return ""
            raw = response.read(1_200_000)
    except Exception:
        return ""
    if url.lower().split("?")[0].endswith(".pdf") or raw.startswith(b"%PDF"):
        return ""
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return _plain(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    return ""


def _plain(text: str) -> str:
    import re

    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:6000]
