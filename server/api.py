"""HTTP 接口层：生成、预览、历史作品和知识库图片。"""

from __future__ import annotations

import mimetypes

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from config import DEFAULT_KB_NAME, credential_status, env, load_env_file
from editor import MAX_PARAS, pack_state
from ima_client import ImaError, probe_connection
from local_kb import KB_ROOT
from pipeline import run
from strategy import MARKETING_SCENES, PLATFORMS, PERSPECTIVES, PERSPECTIVE_DEFAULT
from parse_request import parse_request
from llm_client import LlmError
from pydantic import BaseModel, Field

from . import history_service
from .adapter import (
    compose_from_editor,
    editor_from,
    preview_payload,
    resolve_token,
    serialize_candidates,
    serialize_verification,
)
from .history_service import article_fingerprint, new_visitor_id, valid_visitor_id
from .history_store import db_file

router = APIRouter()


class GenerateIn(BaseModel):
    product: str = ""
    audience: str = ""
    scene: str = "开学季"
    platform: str = "小红书"
    note: str = ""
    perspective: str = PERSPECTIVE_DEFAULT


class EditorIn(BaseModel):
    title: str = ""
    options: str = ""
    lead: str = ""
    cta: str = ""
    tags: str = ""
    paragraphs: list[str] = Field(default_factory=list)
    picks: list[str] = Field(default_factory=list)
    captions: list[str] = Field(default_factory=list)
    cover: str = ""
    cover_caption: str = ""


class PreviewIn(BaseModel):
    editor: EditorIn


class SaveVersionIn(BaseModel):
    editor: EditorIn
    source_version_no: int | None = None


def _visitor(request: Request) -> str:
    token = getattr(request.state, "visitor", "")
    return token if valid_visitor_id(token) else new_visitor_id()


@router.get("/health")
def health() -> dict:
    return {"ok": True}


@router.get("/meta")
def meta(request: Request) -> dict:
    load_env_file()
    owner = _visitor(request)
    count = 0
    try:
        count = len(history_service.list_works(owner))
    except Exception:
        pass
    return {
        "scenes": MARKETING_SCENES,
        "platforms": list(PLATFORMS),
        "perspectives": list(PERSPECTIVES),
        "perspective_default": PERSPECTIVE_DEFAULT,
        "credentials": credential_status(),
        "kb": {"root": str(KB_ROOT), "exists": KB_ROOT.exists()},
        "history": {"db": str(db_file()), "count": count},
        "source_hint": "本地知识库" if KB_ROOT.exists() else "知识库未就绪",
    }


class ParseRequestIn(BaseModel):
    sentence: str = Field(min_length=1, max_length=6000)


@router.post("/parse-request")
def parse_sentence(payload: ParseRequestIn) -> dict:
    load_env_file()
    if not payload.sentence.strip():
        raise HTTPException(status_code=422, detail="请输入一句话需求。")
    if not credential_status()["llm_key"]:
        raise HTTPException(status_code=503, detail="未配置大模型密钥，请直接填写下方表单。")
    try:
        return {"inputs": parse_request(payload.sentence)}
    except LlmError:
        raise HTTPException(status_code=502, detail="需求解析失败，请重试或直接填写下方表单。")


@router.post("/generate")
def generate(payload: GenerateIn, request: Request) -> dict:
    owner = _visitor(request)
    inputs = payload.model_dump()
    try:
        result = run(inputs["product"], inputs["audience"], inputs["scene"], inputs["platform"], inputs["note"], inputs["perspective"])
    except Exception as exc:  # 业务异常统一回给前端，不返回堆栈
        return {"ok": False, "stage": "生成失败", "message": str(exc)[:300], "questions": [], "export_text": ""}

    if not result.get("ok"):
        return {
            "ok": False,
            "stage": result.get("stage") or "未能生成",
            "message": result.get("message") or "",
            "detail": result.get("detail") or "",
            "questions": result.get("questions") or [],
            "source": result.get("source") or "",
            "export_text": "",
        }

    state = pack_state(result)
    state["paragraph_count"] = len(state["paragraphs"])
    editor = editor_from(result["article"], state)
    article, verification, export_text = compose_from_editor(state, editor)
    sources = {
        "strategy": state.get("strategy") or {},
        "facts": article.get("facts") or [],
        "documents": state.get("documents") or [],
        "scenario_docs": state.get("scenario_docs") or [],
        "platform_doc": state.get("platform_doc") or {},
        "source": state.get("source") or result.get("source") or "",
    }

    warning = ""
    work_id = ""
    try:
        saved = history_service.save_new_work(owner, inputs, article, state, sources, verification)
        work_id = saved["work_id"]
    except Exception as exc:
        warning = f"成稿已生成，但历史保存失败：{str(exc)[:160]}"

    if not work_id:
        return {
            "ok": True,
            "work_id": "",
            "saved": False,
            "warning": warning,
            "message": result.get("message") or "",
            "source": result.get("source") or "",
            "inputs": inputs,
            "editor": editor,
            "preview": preview_payload(article, verification, export_text, article_fingerprint(article, inputs), state),
            "candidates": serialize_candidates(state),
            "missing_images": state.get("missing_images") or [],
            "versions": [],
            "meta": _meta_block(state),
        }

    data = _work_payload(owner, work_id)
    data.update(
        {
            "ok": True,
            "saved": True,
            "warning": warning,
            "message": result.get("message") or "",
            "source": result.get("source") or "",
        }
    )
    return data


@router.get("/works")
def works(request: Request) -> dict:
    owner = _visitor(request)
    try:
        items = history_service.list_works(owner)
    except Exception as exc:
        return {"works": [], "error": str(exc)[:160]}
    return {"works": items}


@router.get("/works/{work_id}")
def work_detail(work_id: str, request: Request, version: int | None = None) -> dict:
    data = _work_payload(_visitor(request), work_id, version)
    if data is None:
        raise HTTPException(status_code=404, detail="没有找到该作品或该版本")
    return data


@router.post("/works/{work_id}/preview")
def work_preview(work_id: str, payload: PreviewIn, request: Request) -> dict:
    owner = _visitor(request)
    loaded = history_service.load_work(owner, work_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="没有找到该作品")
    state = loaded["state"]
    article, verification, export_text = compose_from_editor(state, payload.editor.model_dump())
    fingerprint = article_fingerprint(article, loaded["inputs"])
    return preview_payload(article, verification, export_text, fingerprint, state)


@router.post("/works/{work_id}/versions")
def save_version(work_id: str, payload: SaveVersionIn, request: Request) -> dict:
    owner = _visitor(request)
    loaded = history_service.load_work(owner, work_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="没有找到该作品")
    state = loaded["state"]
    inputs = loaded["inputs"]
    article, verification, export_text = compose_from_editor(state, payload.editor.model_dump())
    sources = loaded["sources"] or {}
    try:
        saved = history_service.save_version(
            owner,
            work_id,
            inputs,
            article,
            state,
            sources,
            verification,
            source_version_no=payload.source_version_no,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    data = _work_payload(owner, work_id)
    if data is None:
        raise HTTPException(status_code=404, detail="没有找到该作品")
    data.update(
        {
            "created": bool(saved.get("created")),
            "saved_version_no": int(saved.get("version_no") or data["version_no"]),
            "message": "已保存新版本" if saved.get("created") else "内容与最新版本一致，无需保存",
            "export_text": export_text,
        }
    )
    return data


@router.delete("/works/{work_id}")
def delete_work(work_id: str, request: Request) -> dict:
    deleted = history_service.delete_work(_visitor(request), work_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="作品不存在或不属于当前访客")
    return {"ok": True}


@router.get("/images/{token}")
def image(token: str) -> FileResponse:
    path = resolve_token(token)
    if path is None:
        raise HTTPException(status_code=404, detail="图片不存在")
    media_type = mimetypes.guess_type(path.name)[0] or "image/png"
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "private, max-age=86400"})


@router.post("/test-kb")
def test_kb() -> dict:
    load_env_file()
    status = credential_status()
    if not (status["ima_id"] and status["ima_key"]):
        report = "没有检测到 ima 凭证，生成时会改读本地「华为PC知识库」。"
        if not KB_ROOT.exists():
            report += f" 当前本地知识库路径不存在：{KB_ROOT}"
        return {"report": report, "credentials": status}
    try:
        report = probe_connection(env("IMA_KB_NAME", DEFAULT_KB_NAME))
    except ImaError as exc:
        report = f"连接失败：{exc}。生成时会改读本地知识库。"
    return {"report": report, "credentials": status}


def _meta_block(state: dict) -> dict:
    strategy = state.get("strategy") or {}
    return {
        "use_tags": bool(state.get("use_tags")),
        "source": state.get("source") or "",
        "documents": state.get("documents") or [],
        "scenario_docs": state.get("scenario_docs") or [],
        "platform_title": (state.get("platform_doc") or {}).get("title") or "",
        "paragraph_count": len(state.get("paragraphs") or []),
        "strategy": {
            key: strategy.get(key)
            for key in ("product", "audience", "scene", "platform", "parent_title", "module_id", "module_brief", "template_query")
            if strategy.get(key)
        },
    }


def _work_payload(owner: str, work_id: str, version_no: int | None = None) -> dict | None:
    loaded = history_service.load_work(owner, work_id, version_no)
    if loaded is None:
        return None
    state = loaded["state"]
    editor = editor_from(loaded["article"], state)
    article, verification, export_text = compose_from_editor(state, editor)
    fingerprint = article_fingerprint(article, loaded["inputs"])
    saved = loaded["version"]
    return {
        "ok": True,
        "work_id": work_id,
        "version_no": saved["version_no"],
        "saved_version_no": saved["version_no"],
        "fingerprint": fingerprint,
        "saved_fingerprint": saved["fingerprint"],
        "title": loaded["work"].get("title") or "",
        "platform": loaded["work"].get("platform") or "",
        "inputs": loaded["inputs"],
        "editor": editor,
        "preview": preview_payload(article, verification, export_text, fingerprint, state),
        "candidates": serialize_candidates(state),
        "missing_images": state.get("missing_images") or [],
        "versions": loaded["work"].get("versions") or [],
        "meta": _meta_block(state),
        "saved_at": saved["created_at"],
        "updated_at": loaded["work"].get("updated_at") or saved["created_at"],
    }
