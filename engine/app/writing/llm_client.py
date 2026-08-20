"""
LLM 客户端 — httpx 直连 OpenAI 兼容 chat/completions。

- Key 只从请求 llm_config 取，不落盘、日志脱敏
- 非流式 chat() 与流式 chat_stream()（SSE 透传，generator）
- 1+3 指数退避重试（上游 5xx/429/超时/连接错误）；4xx 非 429 不重试
- 上游 5xx/连接错误 → 502；超时 → 504
- HTTP 传输层可注入（测试用 MockTransport，不联网）
"""
from __future__ import annotations

import json
import logging
import time
from typing import Iterator

import httpx

_logger = logging.getLogger(__name__)

MAX_RETRIES = 4  # 1 initial + 3 retries
RETRY_DELAYS = [2, 4, 8]  # 秒；测试可 monkeypatch 为 0

# ── 可注入 HTTP 传输层（测试用 MockTransport 替换）──
_transport: httpx.BaseTransport | None = None


def set_transport(transport: httpx.BaseTransport | None) -> None:
    global _transport
    _transport = transport


def get_transport() -> httpx.BaseTransport | None:
    return _transport


class LLMError(Exception):
    """LLM 调用失败（已映射为 HTTP 状态码）。"""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def mask_key(key: str) -> str:
    """脱敏 API Key：保留前 2 与后 4 字符。"""
    if not key:
        return "(empty)"
    if len(key) <= 6:
        return key[:2] + "***"
    return f"{key[:2]}***{key[-4:]}"


def _is_retryable_status(status: int) -> bool:
    return status >= 500 or status == 429


def _map_error(e: Exception) -> LLMError:
    """将 httpx/openai 兼容上游异常映射为 LLMError。"""
    if isinstance(e, httpx.TimeoutException):
        return LLMError(504, f"上游超时：{type(e).__name__}")
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if _is_retryable_status(status):
            return LLMError(502, f"上游返回 {status}")
        return LLMError(status, f"上游返回 {status}")
    # 其余 RequestError（ConnectError 等）
    return LLMError(502, f"无法连接上游：{type(e).__name__}")


def _retry(fn):
    """1+3 指数退避重试包装；仅对可重试错误（5xx/429/超时/连接错误）重试。"""

    def wrapper(*args, **kwargs):
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                return fn(*args, **kwargs)
            except httpx.HTTPStatusError as e:
                last_error = e
                if not _is_retryable_status(e.response.status_code):
                    raise _map_error(e)  # 4xx 非 429：不重试
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
            except (httpx.TimeoutException, httpx.RequestError) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
        raise _map_error(last_error)  # type: ignore[arg-type]

    return wrapper


class LLMClient:
    """OpenAI 兼容 chat/completions 客户端（用户自带 Key，不存储）。"""

    def __init__(self, llm_config: dict) -> None:
        self.api_key = (llm_config.get("api_key") or "").strip()
        self.base_url = (llm_config.get("base_url") or "").strip()
        self.model = (llm_config.get("model") or "").strip()
        if not self.api_key:
            raise LLMError(422, "llm_config.api_key 缺失")
        if not self.base_url:
            raise LLMError(422, "llm_config.base_url 缺失")
        if not self.model:
            raise LLMError(422, "llm_config.model 缺失")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _url(self) -> str:
        base = self.base_url.rstrip("/")
        return f"{base}/chat/completions"

    def _payload(
        self, messages, temperature, frequency_penalty, presence_penalty,
        top_p, max_tokens, stream=False,
    ) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "top_p": top_p,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if stream:
            payload["stream"] = True
            payload["stream_options"] = {"include_usage": True}
        return payload

    @_retry
    def _post_json(self, payload: dict) -> dict:
        with httpx.Client(transport=_transport, timeout=120.0) as client:
            resp = client.post(self._url(), json=payload, headers=self._headers())
            if resp.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"upstream {resp.status_code}", request=resp.request, response=resp
                )
            return resp.json()

    def chat(
        self, prompt: str, system_prompt: str = "", temperature: float = 0.2,
        frequency_penalty: float = 0.0, presence_penalty: float = 0.0,
        top_p: float = 1.0, max_tokens: int = None,
    ) -> str:
        """非流式：返回完整文本。"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        try:
            data = self._post_json(
                self._payload(
                    messages, temperature, frequency_penalty, presence_penalty,
                    top_p, max_tokens, stream=False,
                )
            )
            return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        except LLMError:
            raise

    def chat_messages(
        self, messages, temperature: float = 0.2, max_tokens: int = None,
    ) -> str:
        """非流式：直接接受 messages 列表。"""
        try:
            data = self._post_json(
                self._payload(
                    messages, temperature, 0.0, 0.0, 1.0, max_tokens, stream=False,
                )
            )
            return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        except LLMError:
            raise

    def chat_stream(
        self, messages, temperature: float = 0.2, callback=None,
        frequency_penalty: float = 0.0, presence_penalty: float = 0.0,
        top_p: float = 1.0, max_tokens: int = None,
    ) -> str:
        """流式：累积完整文本，callback(chunk) 实时推送。"""
        full = ""
        for chunk in self.chat_stream_iter(
            messages, temperature, frequency_penalty, presence_penalty, top_p, max_tokens
        ):
            full += chunk
            if callback:
                callback(chunk)
        return full

    def chat_stream_iter(
        self, messages, temperature: float = 0.2,
        frequency_penalty: float = 0.0, presence_penalty: float = 0.0,
        top_p: float = 1.0, max_tokens: int = None,
    ) -> Iterator[str]:
        """流式 generator：yield 每个 content chunk（str）。

        连接/首响应阶段重试 1+3；一旦 yield 开始后不再重试，错误转为 LLMError。
        """
        payload = self._payload(
            messages, temperature, frequency_penalty, presence_penalty,
            top_p, max_tokens, stream=True,
        )
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            yielded = False
            try:
                with httpx.Client(transport=_transport, timeout=120.0) as client:
                    with client.stream(
                        "POST", self._url(), json=payload, headers=self._headers()
                    ) as resp:
                        if resp.status_code >= 400:
                            resp.read()
                            raise httpx.HTTPStatusError(
                                f"upstream {resp.status_code}",
                                request=resp.request, response=resp,
                            )
                        for line in resp.iter_lines():
                            if not line or not line.startswith("data: "):
                                continue
                            data_str = line[len("data: "):]
                            if data_str.strip() == "[DONE]":
                                return
                            try:
                                obj = json.loads(data_str)
                            except (ValueError, json.JSONDecodeError):
                                continue
                            choices = obj.get("choices") or []
                            if not choices:
                                continue
                            delta = (choices[0] or {}).get("delta") or {}
                            content = delta.get("content")
                            if content:
                                yielded = True
                                yield content
                        return  # 流正常结束
            except httpx.HTTPStatusError as e:
                if yielded:
                    raise _map_error(e)  # 已输出，不重试
                last_error = e
                if not _is_retryable_status(e.response.status_code):
                    raise _map_error(e)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
            except (httpx.TimeoutException, httpx.RequestError) as e:
                if yielded:
                    raise _map_error(e)
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
        raise _map_error(last_error)  # type: ignore[arg-type]
