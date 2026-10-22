"""SQLite 历史作品存储。所有查询都带访客身份，避免不同访客互读、互改或互删。"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 1
BASE_DIR = Path(__file__).resolve().parent


def data_home() -> Path:
    """历史数据根目录，可用 AIX_HISTORY_HOME 指向云端持久磁盘。"""
    raw = os.environ.get("AIX_HISTORY_HOME", "").strip()
    return Path(raw).expanduser().resolve() if raw else BASE_DIR / "data"


def db_file() -> Path:
    return data_home() / "history.db"


def assets_dir() -> Path:
    return data_home() / "assets"


def visitor_secret() -> str:
    """图片访问令牌和访客标识的签名密钥，首次启动时生成并保存在数据目录。"""
    path = data_home() / "visitor_secret.key"
    if path.is_file():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = secrets.token_urlsafe(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return value


def _dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _load(value: str):
    return json.loads(value or "{}")


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS works (
            work_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            platform TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_works_owner_time
            ON works(owner_id, updated_at DESC);
        CREATE TABLE IF NOT EXISTS versions (
            version_id TEXT PRIMARY KEY,
            work_id TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            version_no INTEGER NOT NULL,
            source_version_no INTEGER,
            schema_version INTEGER NOT NULL,
            created_at REAL NOT NULL,
            fingerprint TEXT NOT NULL,
            inputs_json TEXT NOT NULL,
            article_json TEXT NOT NULL,
            state_json TEXT NOT NULL,
            sources_json TEXT NOT NULL,
            images_json TEXT NOT NULL,
            verification_json TEXT NOT NULL,
            UNIQUE(work_id, version_no),
            FOREIGN KEY(work_id) REFERENCES works(work_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_versions_owner_work
            ON versions(owner_id, work_id, version_no DESC);
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )


@contextmanager
def _connect():
    path = db_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _ensure_schema(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _payload_columns(payload: dict) -> tuple:
    return (
        _dump(payload.get("inputs") or {}),
        _dump(payload.get("article") or {}),
        _dump(payload.get("state") or {}),
        _dump(payload.get("sources") or {}),
        _dump(payload.get("images") or {}),
        _dump(payload.get("verification") or {}),
    )


def create_work(
    owner_id: str,
    title: str,
    platform: str,
    fingerprint: str,
    payload: dict,
    work_id: str | None = None,
) -> dict:
    """新建作品并写入 V1。work_id 由调用方先生成，便于同时准备图片目录。"""
    work_id = work_id or uuid.uuid4().hex
    version_id = uuid.uuid4().hex
    now = time.time()
    columns = _payload_columns(payload)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO works(work_id, owner_id, title, platform, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?)",
            (work_id, owner_id, title, platform, now, now),
        )
        conn.execute(
            """INSERT INTO versions(
                version_id, work_id, owner_id, version_no, source_version_no, schema_version,
                created_at, fingerprint, inputs_json, article_json, state_json,
                sources_json, images_json, verification_json
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (version_id, work_id, owner_id, 1, None, SCHEMA_VERSION, now, fingerprint, *columns),
        )
    return {"work_id": work_id, "version_id": version_id, "version_no": 1, "created_at": now}


def append_version(
    owner_id: str,
    work_id: str,
    fingerprint: str,
    payload: dict,
    source_version_no: int | None = None,
) -> dict:
    """追加版本；内容与最新版一致时不写入。"""
    columns = _payload_columns(payload)
    now = time.time()
    title = str((payload.get("article") or {}).get("title") or "").strip()
    platform = str((payload.get("inputs") or {}).get("platform") or "").strip()
    with _connect() as conn:
        work = conn.execute(
            "SELECT work_id FROM works WHERE work_id = ? AND owner_id = ?",
            (work_id, owner_id),
        ).fetchone()
        if work is None:
            raise PermissionError("作品不存在或不属于当前访客")
        latest = conn.execute(
            "SELECT version_no, fingerprint FROM versions WHERE work_id = ? AND owner_id = ? ORDER BY version_no DESC LIMIT 1",
            (work_id, owner_id),
        ).fetchone()
        if latest is None:
            raise PermissionError("作品没有可用版本")
        if latest["fingerprint"] == fingerprint:
            return {"created": False, "version_no": int(latest["version_no"]), "fingerprint": fingerprint}
        version_no = int(latest["version_no"]) + 1
        version_id = uuid.uuid4().hex
        conn.execute(
            """INSERT INTO versions(
                version_id, work_id, owner_id, version_no, source_version_no, schema_version,
                created_at, fingerprint, inputs_json, article_json, state_json,
                sources_json, images_json, verification_json
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                version_id,
                work_id,
                owner_id,
                version_no,
                source_version_no,
                SCHEMA_VERSION,
                now,
                fingerprint,
                *columns,
            ),
        )
        conn.execute(
            "UPDATE works SET title = ?, platform = ?, updated_at = ? WHERE work_id = ? AND owner_id = ?",
            (title or "未命名", platform, now, work_id, owner_id),
        )
    return {"created": True, "version_id": version_id, "version_no": version_no, "created_at": now}


def list_works(owner_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT w.work_id, w.title, w.platform, w.created_at, w.updated_at,
                      (SELECT COUNT(*) FROM versions v WHERE v.work_id = w.work_id AND v.owner_id = w.owner_id) AS version_count,
                      (SELECT MAX(v.version_no) FROM versions v WHERE v.work_id = w.work_id AND v.owner_id = w.owner_id) AS latest_no
               FROM works w
               WHERE w.owner_id = ?
               ORDER BY w.updated_at DESC""",
            (owner_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_work(owner_id: str, work_id: str) -> dict | None:
    with _connect() as conn:
        work = conn.execute(
            "SELECT work_id, title, platform, created_at, updated_at FROM works WHERE work_id = ? AND owner_id = ?",
            (work_id, owner_id),
        ).fetchone()
        if work is None:
            return None
        versions = conn.execute(
            """SELECT version_id, version_no, source_version_no, created_at, fingerprint
               FROM versions WHERE work_id = ? AND owner_id = ?
               ORDER BY version_no DESC""",
            (work_id, owner_id),
        ).fetchall()
    result = dict(work)
    result["versions"] = [dict(row) for row in versions]
    return result


def latest_version(owner_id: str, work_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            """SELECT * FROM versions WHERE work_id = ? AND owner_id = ?
               ORDER BY version_no DESC LIMIT 1""",
            (work_id, owner_id),
        ).fetchone()
    return dict(row) if row else None


def get_version(owner_id: str, work_id: str, version_no: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            """SELECT * FROM versions WHERE work_id = ? AND owner_id = ? AND version_no = ?""",
            (work_id, owner_id, int(version_no)),
        ).fetchone()
    return dict(row) if row else None


def delete_work(owner_id: str, work_id: str) -> bool:
    with _connect() as conn:
        owned = conn.execute(
            "SELECT work_id FROM works WHERE work_id = ? AND owner_id = ?",
            (work_id, owner_id),
        ).fetchone()
        if owned is None:
            return False
        conn.execute("DELETE FROM versions WHERE work_id = ? AND owner_id = ?", (work_id, owner_id))
        conn.execute("DELETE FROM works WHERE work_id = ? AND owner_id = ?", (work_id, owner_id))
    return True


def decode_version(row: dict) -> dict:
    """把数据库行还原成服务层可直接使用的结构。"""
    return {
        "version_id": row["version_id"],
        "version_no": int(row["version_no"]),
        "source_version_no": row["source_version_no"],
        "schema_version": int(row["schema_version"]),
        "created_at": float(row["created_at"]),
        "fingerprint": row["fingerprint"],
        "inputs": _load(row["inputs_json"]),
        "article": _load(row["article_json"]),
        "state": _load(row["state_json"]),
        "sources": _load(row["sources_json"]),
        "images": _load(row["images_json"]),
        "verification": _load(row["verification_json"]),
    }
