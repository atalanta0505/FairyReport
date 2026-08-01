"""
LLM Client — DeepSeek / OpenAI compatible API wrapper
- Streaming output
- .env auto-fallback
- Auto-retry (1 initial + 3 retries, exponential backoff 2s/4s/8s, 4 calls total)
"""
import os
import re
import time
from openai import OpenAI
from config import DEFAULT_MODEL, DEFAULT_BASE_URL

MAX_RETRIES = 4  # 1 initial + 3 retries
RETRY_DELAYS = [2, 4, 8]  # seconds


def _retry_api_call(fn, *args, **kwargs):
    """Generic exponential backoff retry wrapper."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                time.sleep(delay)
    raise last_error


class LLMClient:
    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        self.model = model or DEFAULT_MODEL
        self.base_url = base_url or DEFAULT_BASE_URL
        # Priority: parameter > environment variable > .env (already loaded by config.py)
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        # Allow creation without a key so the app can start; actual calls will raise a clear error.
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _ensure_client(self):
        """Raise a clear error if the API key is missing when an LLM call is attempted."""
        if not self.api_key or not self.client:
            raise ValueError(
                "未配置 DeepSeek API Key，无法调用模型。"
                "请进入侧边栏 ⚙️ Settings 配置 API Key、Base URL 和模型。"
            )

    # ── Streaming output (accepts messages list) ──
    def chat_stream(self, messages: list, temperature: float = 0.2, callback=None,
                    max_tokens: int = None, frequency_penalty: float = 0.0,
                    presence_penalty: float = 0.0, top_p: float = 1.0):
        """
        Streaming chat. callback(chunk_text) is invoked per chunk for real-time UI updates.
        Returns the complete response text.
        max_tokens: maximum output token count, for hard word-count control.
        """
        self._ensure_client()

        def _do_chat():
            kwargs = dict(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                top_p=top_p,
            )
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            kwargs["stream_options"] = {"include_usage": True}
            response = self.client.chat.completions.create(**kwargs)
            full_text = ""
            completion_tokens = 0
            for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_text += delta.content
                    if callback:
                        callback(delta.content)
                # The last chunk carries usage info
                if chunk.usage and chunk.usage.completion_tokens:
                    completion_tokens = chunk.usage.completion_tokens
            # Log: actual output token usage vs Chinese character count
            if isinstance(completion_tokens, int) and completion_tokens > 0:
                chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', full_text))
                import sys
                print(f"[LLM] completion_tokens={completion_tokens}, chinese_chars={chinese_chars}, "
                      f"ratio={completion_tokens/chinese_chars:.2f} tok/char, "
                      f"total_chars={len(full_text)}", file=sys.stderr, flush=True)
            return full_text

        return _retry_api_call(_do_chat)

    # ── Non-streaming (accepts prompt + system_prompt strings) ──
    def chat(self, prompt: str, system_prompt: str = "", temperature: float = 0.2,
             max_tokens: int = None, frequency_penalty: float = 0.0,
             presence_penalty: float = 0.0, top_p: float = 1.0) -> str:
        self._ensure_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        def _do_chat():
            kwargs = dict(model=self.model, messages=messages, temperature=temperature,
                          frequency_penalty=frequency_penalty,
                          presence_penalty=presence_penalty,
                          top_p=top_p)
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            resp = self.client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""

        return _retry_api_call(_do_chat)

    # ── Non-streaming (directly accepts messages list) ──
    def chat_messages(self, messages: list, temperature: float = 0.2,
                      max_tokens: int = None) -> str:
        """Complete conversation request that directly accepts a messages list.

        Args:
            messages: [{"role": "system"|"user"|"assistant", "content": "..."}, ...]
            temperature: LLM temperature parameter

        Returns:
            Complete response text
        """
        self._ensure_client()
        def _do_chat():
            kwargs = dict(model=self.model, messages=messages, temperature=temperature)
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            resp = self.client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""

        return _retry_api_call(_do_chat)
