"""send-code 端点测试：发送成功（打桩断言）、重发间隔、每邮箱每日上限。"""
from datetime import timedelta

from sqlalchemy import select

from backend.app import db
from backend.app.config import settings
from backend.app.models import AuthCode


def test_send_code_success(client, mail_stub):
    """发送成功：打桩发信函数被调用，收到 6 位数字码，库中过期时间符合配置。"""
    resp = client.post("/api/auth/send-code", json={"email": "user@example.com"})
    assert resp.status_code == 200
    assert len(mail_stub) == 1
    to_addr, code = mail_stub[0]
    assert to_addr == "user@example.com"
    assert len(code) == 6 and code.isdigit()
    session = db.SessionLocal()
    row = session.execute(select(AuthCode).where(AuthCode.email == "user@example.com")).scalars().one()
    session.close()
    assert row.code == code
    assert row.expires_at - row.created_at == timedelta(minutes=settings.auth_code_expire_minutes)


def test_send_code_resend_within_interval_returns_429(client, mail_stub):
    """60 秒内重发返回 429，且不再次发信。"""
    email = "user@example.com"
    assert client.post("/api/auth/send-code", json={"email": email}).status_code == 200
    resp = client.post("/api/auth/send-code", json={"email": email})
    assert resp.status_code == 429
    assert len(mail_stub) == 1


def test_send_code_allowed_after_interval(client, mail_stub):
    """最新验证码创建时间回拨超过重发间隔后，允许再次发送。"""
    email = "user@example.com"
    assert client.post("/api/auth/send-code", json={"email": email}).status_code == 200
    session = db.SessionLocal()
    row = session.execute(select(AuthCode).where(AuthCode.email == email)).scalars().one()
    row.created_at = row.created_at - timedelta(seconds=settings.auth_code_resend_interval_seconds + 1)
    session.commit()
    session.close()
    resp = client.post("/api/auth/send-code", json={"email": email})
    assert resp.status_code == 200
    assert len(mail_stub) == 2


def test_send_code_daily_limit_returns_429(client, mail_stub, monkeypatch):
    """当日发信数达到上限后返回 429，且不再次发信。"""
    email = "limit@example.com"
    now = db.utcnow()
    monkeypatch.setattr("backend.app.auth.router.utcnow", lambda: now)
    session = db.SessionLocal()
    for i in range(settings.auth_code_daily_limit):
        session.add(AuthCode(
            email=email,
            code=f"{i % 10:06d}",
            created_at=now - timedelta(seconds=settings.auth_code_resend_interval_seconds + 30),
            expires_at=now + timedelta(minutes=settings.auth_code_expire_minutes),
        ))
    session.commit()
    session.close()
    resp = client.post("/api/auth/send-code", json={"email": email})
    assert resp.status_code == 429
    assert mail_stub == []
