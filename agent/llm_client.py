import json
import re
import urllib.error
import urllib.request

from config import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL, env


class LlmError(RuntimeError):
    pass


def chat_json(system: str, user: str) -> dict:
    api_key = env("LLM_API_KEY")
    if not api_key:
        raise LlmError("还没有配置 LLM_API_KEY。检索可以先做，生成软文需要一个公开大模型密钥。")
    base = env("LLM_BASE_URL", DEFAULT_LLM_BASE_URL).rstrip("/")
    model = env("LLM_MODEL", DEFAULT_LLM_MODEL)
    url = base + "/chat/completions" if base.endswith("/v1") else base + "/v1/chat/completions"
    request_body = {
        "model": model,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    data = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise LlmError(f"大模型接口返回 {exc.code}：{detail}") from exc
    except urllib.error.URLError as exc:
        raise LlmError(f"无法连接大模型接口：{exc.reason}") from exc
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmError("大模型没有返回正文。") from exc
    return _parse_json(content)


def _parse_json(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise LlmError("大模型没有返回可解析的 JSON。")
        return json.loads(match.group(0))
