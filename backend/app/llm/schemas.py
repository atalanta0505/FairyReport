"""
FairyReport Backend — LLM 网关 API 请求模型
"""
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """OpenAI 兼容聊天消息。"""

    role: str
    content: str


class ChatRequest(BaseModel):
    """/api/llm/chat 请求体；model 缺省取白名单首项。"""

    messages: list[ChatMessage] = Field(min_length=1)
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    stream: bool = False
