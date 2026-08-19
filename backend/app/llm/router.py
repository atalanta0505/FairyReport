"""
FairyReport Backend — LLM 网关端点（chat / usage）
"""
import itertools
import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..auth.router import current_user
from ..config import settings
from ..db import get_db
from . import gateway, metering
from .schemas import ChatRequest

llm_router = APIRouter(prefix="/api/llm", tags=["llm"])


def _prompt_len(messages: list[dict]) -> int:
    """请求消息内容总字符数（估算兜底用）。"""
    return sum(len(m.get("content") or "") for m in messages)


def _extract_content(data: dict) -> str:
    """从非流式上游响应提取助手回复文本。"""
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = (choices[0] or {}).get("message") or {}
    return message.get("content") or ""


def _sse_events(chunks: Iterator[str], *, user_id: int, model: str, prompt_len: int) -> Iterator[str]:
    """上游 chunk 转 SSE 文本（data: {chunk}\\n\\n，结束 data: [DONE]），结束后计量。"""
    usage = None
    completion_parts: list[str] = []
    for chunk in chunks:
        if chunk == "[DONE]":
            break
        yield f"data: {chunk}\n\n"
        try:
            obj = json.loads(chunk)
        except ValueError:
            continue
        if obj.get("usage"):
            usage = obj["usage"]
        for choice in obj.get("choices") or []:
            content = ((choice or {}).get("delta") or {}).get("content")
            if content:
                completion_parts.append(content)
    yield "data: [DONE]\n\n"
    metering.record_usage(
        user_id=user_id,
        model=model,
        usage=usage,
        prompt_len=prompt_len,
        completion_text="".join(completion_parts),
    )


@llm_router.post("/chat")
def chat(req: ChatRequest, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """经网关调用平台 LLM；stream=true 返回 SSE 透传，否则返回上游 JSON。"""
    user = current_user(authorization, db)
    allowlist = settings.llm_model_allowlist_items
    model = req.model or (allowlist[0] if allowlist else "")
    if not model or model not in allowlist:
        raise HTTPException(status_code=422, detail={"error": "model 不在白名单", "allowed": allowlist})
    day = metering.utc_today()
    used = metering.get_day_usage(db, user.id, day)
    limit = settings.user_daily_token_limit
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail={"error": "当日 token 用量已达上限", "date": day.isoformat(), "used_tokens": used, "limit": limit},
        )
    key = gateway.next_key()
    if key is None:
        raise HTTPException(status_code=503, detail="LLM Key 池未配置（LLM_API_KEYS）")
    messages = [m.model_dump() for m in req.messages]
    payload: dict = {"model": model, "messages": messages, "stream": req.stream}
    if req.temperature is not None:
        payload["temperature"] = req.temperature
    if req.max_tokens is not None:
        payload["max_tokens"] = req.max_tokens
    if req.stream:
        payload["stream_options"] = {"include_usage": True}
        upstream = gateway.chat_completion_stream(payload, key)
        try:
            first = next(upstream)
        except StopIteration:
            first = None
        except gateway.UpstreamError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail)
        chunks = itertools.chain([first], upstream) if first is not None else upstream
        events = _sse_events(chunks, user_id=user.id, model=model, prompt_len=_prompt_len(messages))
        return StreamingResponse(events, media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
    try:
        data = gateway.chat_completion(payload, key)
    except gateway.UpstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    metering.record_usage(
        user_id=user.id,
        model=model,
        usage=data.get("usage"),
        prompt_len=_prompt_len(messages),
        completion_text=_extract_content(data),
    )
    return data


@llm_router.get("/usage")
def usage(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """当前用户当日（UTC 日）已用 token 与上限。"""
    user = current_user(authorization, db)
    day = metering.utc_today()
    used = metering.get_day_usage(db, user.id, day)
    limit = settings.user_daily_token_limit
    return {
        "date": day.isoformat(),
        "used_tokens": used,
        "limit": limit,
        "remaining_tokens": max(0, limit - used),
    }
