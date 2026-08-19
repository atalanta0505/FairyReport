"""
FairyReport Backend — LLM 调用计量（上游 usage 优先，字符估算兜底）
"""
import math
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import UsageLog


def utc_today() -> date:
    """当前 UTC 日期（用量统计聚合键）。"""
    return datetime.now(timezone.utc).date()


def estimate_tokens(char_count: int) -> int:
    """按字符数粗略估算 token 数（上游 usage 不可用时的兜底）。"""
    return math.ceil(char_count / 2)


def get_day_usage(db: Session, user_id: int, day: date) -> int:
    """用户指定 UTC 日已用 token 总数（prompt + completion）。"""
    total = db.scalar(
        select(func.coalesce(func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens), 0)).where(
            UsageLog.user_id == user_id, UsageLog.day == day
        )
    )
    return int(total or 0)


def record_usage(
    *,
    user_id: int,
    model: str,
    usage: dict | None,
    prompt_len: int = 0,
    completion_text: str = "",
) -> UsageLog | None:
    """写入一条计量记录（独立会话）；优先上游 usage，取不到则估算并标 estimated；失败不抛异常。"""
    session = SessionLocal()
    try:
        prompt_tokens = int((usage or {}).get("prompt_tokens") or 0)
        completion_tokens = int((usage or {}).get("completion_tokens") or 0)
        estimated = False
        if prompt_tokens + completion_tokens <= 0:
            prompt_tokens = estimate_tokens(prompt_len)
            completion_tokens = estimate_tokens(len(completion_text))
            estimated = True
        row = UsageLog(
            user_id=user_id,
            day=utc_today(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            estimated=estimated,
        )
        session.add(row)
        session.commit()
        return row
    except Exception as exc:
        print(f"[metering] 计量写入失败（不阻断响应）: {exc}")
        try:
            session.rollback()
        except Exception:
            pass
        return None
    finally:
        session.close()
