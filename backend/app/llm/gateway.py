"""
FairyReport Backend — LLM 上游网关（httpx，OpenAI 兼容）

Key 池轮询选择；上游 5xx → 502、超时 → 504；Key 只来自 settings，日志一律脱敏。
"""
import threading
from collections.abc import Iterator

import httpx

from ..config import settings

_transport: httpx.BaseTransport | None = None

_key_index = 0
_key_lock = threading.Lock()

_ERROR_SUMMARY_LIMIT = 200


class UpstreamError(Exception):
    """上游故障映射异常：status_code 为网关对外响应码（502/504），detail 不含 Key。"""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def mask_key(key: str) -> str:
    """Key 脱敏（前 4 位 + ***），仅用于日志。"""
    return f"{key[:4]}***" if key else "***"


def next_key() -> str | None:
    """轮询返回 Key 池下一个 Key；池为空返回 None。"""
    global _key_index
    keys = settings.llm_key_list
    if not keys:
        return None
    with _key_lock:
        key = keys[_key_index % len(keys)]
        _key_index += 1
    return key


def _url() -> str:
    return settings.llm_base_url.rstrip("/") + "/chat/completions"


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}", "Accept": "application/json"}


def _client() -> httpx.Client:
    kwargs: dict = {"timeout": httpx.Timeout(settings.llm_timeout)}
    if _transport is not None:
        kwargs["transport"] = _transport
    return httpx.Client(**kwargs)


def _summary(text: str) -> str:
    return (text or "").strip()[:_ERROR_SUMMARY_LIMIT]


def _log_failure(key: str, message: str) -> None:
    print(f"[llm] 上游调用失败 (key={mask_key(key)}): {message}")


def chat_completion(payload: dict, key: str) -> dict:
    """非流式调用上游 /chat/completions，返回响应 JSON。"""
    try:
        with _client() as client:
            resp = client.post(_url(), json=payload, headers=_headers(key))
    except httpx.TimeoutException as exc:
        _log_failure(key, "请求超时")
        raise UpstreamError(504, "LLM 上游请求超时") from exc
    except httpx.HTTPError as exc:
        _log_failure(key, f"连接错误 {type(exc).__name__}")
        raise UpstreamError(502, f"LLM 上游连接错误: {type(exc).__name__}") from exc
    if resp.status_code >= 500:
        _log_failure(key, f"HTTP {resp.status_code}")
        raise UpstreamError(502, f"LLM 上游服务错误 (HTTP {resp.status_code}): {_summary(resp.text)}")
    if resp.status_code >= 400:
        _log_failure(key, f"HTTP {resp.status_code}")
        raise UpstreamError(502, f"LLM 上游拒绝请求 (HTTP {resp.status_code}): {_summary(resp.text)}")
    try:
        return resp.json()
    except ValueError as exc:
        _log_failure(key, "响应非合法 JSON")
        raise UpstreamError(502, "LLM 上游响应不是合法 JSON") from exc


def chat_completion_stream(payload: dict, key: str) -> Iterator[str]:
    """流式调用上游，逐条产出 SSE data: 后的载荷（含 [DONE]）。"""
    try:
        with _client() as client:
            with client.stream("POST", _url(), json=payload, headers=_headers(key)) as resp:
                if resp.status_code >= 500:
                    body = _summary(resp.read().decode("utf-8", errors="replace"))
                    _log_failure(key, f"HTTP {resp.status_code}")
                    raise UpstreamError(502, f"LLM 上游服务错误 (HTTP {resp.status_code}): {body}")
                if resp.status_code >= 400:
                    body = _summary(resp.read().decode("utf-8", errors="replace"))
                    _log_failure(key, f"HTTP {resp.status_code}")
                    raise UpstreamError(502, f"LLM 上游拒绝请求 (HTTP {resp.status_code}): {body}")
                for line in resp.iter_lines():
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    chunk = line[len("data:"):].strip()
                    if chunk:
                        yield chunk
    except httpx.TimeoutException as exc:
        _log_failure(key, "流式请求超时")
        raise UpstreamError(504, "LLM 上游请求超时") from exc
    except httpx.HTTPError as exc:
        _log_failure(key, f"流式连接错误 {type(exc).__name__}")
        raise UpstreamError(502, f"LLM 上游连接错误: {type(exc).__name__}") from exc
