"""
LLM 客户端 — httpx 直连 OpenAI 兼容 chat/completions 及 Anthropic 原生 /v1/messages。

- Key 只从请求 llm_config 取，不落盘、日志脱敏
- 自动补全常见国内外云厂商缺失的 /v1（OpenAI、SiliconFlow、Moonshot、OpenRouter、DashScope、Gemini 等），
  同时保持 DeepSeek 与自定义测试桩 URL 原样不变
- 按厂商协议层自适应（OpenAI、Google Gemini、Anthropic Claude）自动过滤不兼容的采样惩罚参数，防止 400 报错
- 原生兼容 Anthropic Claude 官方接口（https://api.anthropic.com -> /v1/messages + x-api-key）
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
from urllib.parse import urlparse

import httpx

_logger = logging.getLogger(__name__)

MAX_RETRIES = 4  # 1 initial + 3 retries
RETRY_DELAYS = [2, 4, 8]  # 秒；测试可 monkeypatch 为 0
ANTHROPIC_DEFAULT_MAX_TOKENS = 8192
ANTHROPIC_VERSION = "2023-06-01"

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


def normalize_llm_base_url(raw_url: str) -> tuple[str, str]:
    """规范化国内外主流大模型 Base URL 并识别协议类型（'openai' | 'anthropic'）。

    仅对已知要求特定路径前缀的官方云域名做无损补全；
    DeepSeek 官方域名与任意本地/测试桩地址保持原样不改动。
    """
    cleaned = (raw_url or "").strip().rstrip("/")
    if not cleaned:
        return cleaned, "openai"

    parsed = urlparse(cleaned)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").rstrip("/")

    if host == "api.anthropic.com":
        if not path:
            cleaned = f"{cleaned}/v1"
        return cleaned, "anthropic"

    if host == "generativelanguage.googleapis.com":
        if not path:
            cleaned = f"{cleaned}/v1beta/openai"
        elif path == "/v1beta":
            cleaned = f"{cleaned}/openai"
        return cleaned, "openai"

    if host == "openrouter.ai":
        if not path:
            cleaned = f"{cleaned}/api/v1"
        elif path == "/api":
            cleaned = f"{cleaned}/v1"
        return cleaned, "openai"

    if host == "dashscope.aliyuncs.com":
        if not path:
            cleaned = f"{cleaned}/compatible-mode/v1"
        return cleaned, "openai"

    v1_hosts = {
        "api.openai.com",
        "api.siliconflow.cn",
        "api.siliconflow.com",
        "api.moonshot.cn",
        "api.moonshot.ai",
        "api.x.ai",
    }
    if host in v1_hosts and not path:
        cleaned = f"{cleaned}/v1"

    return cleaned, "openai"


def _is_openai_strict_model(model: str, base_url: str) -> bool:
    """判断是否为使用 max_completion_tokens 且不接收传统采样惩罚参数的 OpenAI 现代模型（如 GPT-5/GPT-6 等）。"""
    m = (model or "").strip().lower().split("/")[-1]
    host = (urlparse(base_url).hostname or "").lower()
    if host == "api.openai.com":
        return True
    return m.startswith(("gpt-5", "gpt-6", "o1", "o3", "o4"))


def _is_penalty_unsupported_model(model: str, base_url: str) -> bool:
    """判断上游厂商协议是否不支持 frequency_penalty / presence_penalty。"""
    m = (model or "").strip().lower().split("/")[-1]
    host = (urlparse(base_url).hostname or "").lower()
    if _is_openai_strict_model(m, base_url):
        return True
    if host == "generativelanguage.googleapis.com" or m.startswith("gemini-"):
        return True
    if "reasoner" in m or m.startswith("claude-"):
        return True
    return False


def _is_stream_options_unsupported(model: str, base_url: str) -> bool:
    """判断上游流式接口是否不兼容 stream_options: {include_usage: true}。"""
    m = (model or "").strip().lower().split("/")[-1]
    host = (urlparse(base_url).hostname or "").lower()
    return host == "generativelanguage.googleapis.com" or m.startswith("gemini-")


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
    """多厂商兼容大模型客户端（支持 OpenAI 兼容协议与 Anthropic 原生协议，用户自带 Key 不落盘）。"""

    def __init__(self, llm_config: dict) -> None:
        self.api_key = (llm_config.get("api_key") or "").strip()
        raw_base = (llm_config.get("base_url") or "").strip()
        self.model = (llm_config.get("model") or "").strip()
        if not self.api_key:
            raise LLMError(422, "llm_config.api_key 缺失")
        if not raw_base:
            raise LLMError(422, "llm_config.base_url 缺失")
        if not self.model:
            raise LLMError(422, "llm_config.model 缺失")
        self.base_url, self.provider = normalize_llm_base_url(raw_base)

    def _headers(self) -> dict:
        if self.provider == "anthropic":
            return {
                "x-api-key": self.api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            }
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _url(self) -> str:
        base = self.base_url.rstrip("/")
        if self.provider == "anthropic":
            return f"{base}/messages"
        return f"{base}/chat/completions"

    def _payload(
        self, messages, temperature, frequency_penalty, presence_penalty,
        top_p, max_tokens, stream=False,
    ) -> dict:
        if self.provider == "anthropic":
            sys_parts: list[str] = []
            anth_messages: list[dict] = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    if content:
                        sys_parts.append(str(content))
                else:
                    anth_messages.append({"role": role, "content": content})
            payload: dict = {
                "model": self.model,
                "messages": anth_messages or [{"role": "user", "content": ""}],
                "max_tokens": int(max_tokens) if max_tokens else ANTHROPIC_DEFAULT_MAX_TOKENS,
                "temperature": temperature,
            }
            if sys_parts:
                payload["system"] = "\n\n".join(sys_parts)
            if stream:
                payload["stream"] = True
            return payload

        is_openai_modern = _is_openai_strict_model(self.model, self.base_url)
        drop_penalties = _is_penalty_unsupported_model(self.model, self.base_url)

        payload = {
            "model": self.model,
            "messages": messages,
        }
        if not is_openai_modern:
            payload["temperature"] = temperature
            payload["top_p"] = top_p

        if not drop_penalties:
            payload["frequency_penalty"] = frequency_penalty
            payload["presence_penalty"] = presence_penalty

        if max_tokens:
            if is_openai_modern:
                payload["max_completion_tokens"] = max_tokens
            else:
                payload["max_tokens"] = max_tokens

        if stream:
            payload["stream"] = True
            if not _is_stream_options_unsupported(self.model, self.base_url):
                payload["stream_options"] = {"include_usage": True}
        return payload

    @staticmethod
    def _extract_non_stream_text(data: dict, provider: str) -> str:
        if provider == "anthropic":
            blocks = data.get("content") or []
            texts = [
                b.get("text", "")
                for b in blocks
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            return "".join(texts)
        return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""

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
            return self._extract_non_stream_text(data, self.provider)
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
            return self._extract_non_stream_text(data, self.provider)
        except LLMError:
            raise

    def chat_stream(
        self, messages, temperature: float = 0.2, callback=None,
        frequency_penalty: float = 0.0, presence_penalty: float = 0.0,
        top_p: float = 1.0, max_tokens: int = None,
    ) -> str:
        """流式：累积完整正文文本，callback(chunk) 实时推送。"""
        full = ""
        for chunk in self.chat_stream_iter(
            messages, temperature, frequency_penalty, presence_penalty, top_p, max_tokens
        ):
            if chunk.startswith('{"type": "thought"'):
                if callback:
                    callback(chunk)
                continue
            full += chunk
            if callback:
                callback(chunk)
        return full

    def chat_stream_iter(
        self, messages, temperature: float = 0.2,
        frequency_penalty: float = 0.0, presence_penalty: float = 0.0,
        top_p: float = 1.0, max_tokens: int = None,
    ) -> Iterator[str]:
        """流式 generator：yield 每个 thought/content chunk（str）。

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

                            if self.provider == "anthropic":
                                ev_type = obj.get("type")
                                if ev_type == "message_stop":
                                    return
                                if ev_type == "content_block_delta":
                                    delta = obj.get("delta") or {}
                                    d_type = delta.get("type")
                                    if d_type == "thinking_delta" and delta.get("thinking"):
                                        yielded = True
                                        yield json.dumps(
                                            {"type": "thought", "chunk": delta["thinking"]},
                                            ensure_ascii=False,
                                        )
                                    elif d_type == "text_delta" and delta.get("text"):
                                        yielded = True
                                        yield delta["text"]
                                continue

                            choices = obj.get("choices") or []
                            if not choices:
                                continue
                            delta = (choices[0] or {}).get("delta") or {}
                            reasoning_content = (
                                delta.get("reasoning_content")
                                or delta.get("reasoning")
                                or delta.get("thought")
                            )
                            if reasoning_content:
                                yielded = True
                                yield json.dumps(
                                    {"type": "thought", "chunk": reasoning_content},
                                    ensure_ascii=False,
                                )
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
