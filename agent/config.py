import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"

DEFAULT_SKILL_SCRIPT = r"C:\Users\ROG\Downloads\ima-skills-1.1.10\ima-skill\ima_api.cjs"
DEFAULT_KB_NAME = "任德耀新建华为PC知识库"
DEFAULT_LLM_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_LLM_MODEL = "deepseek-chat"


def load_env_file() -> None:
    """Load agent/.env without overriding variables already set in the shell."""
    if not ENV_PATH.exists():
        return
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def credential_status() -> dict:
    return {
        "ima_id": bool(env("IMA_OPENAPI_CLIENTID") or env("IMA_CLIENT_ID")),
        "ima_key": bool(env("IMA_OPENAPI_APIKEY") or env("IMA_API_KEY")),
        "llm_key": bool(env("LLM_API_KEY")),
    }
