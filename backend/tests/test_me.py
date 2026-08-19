"""/api/users/me 端点测试：有效 JWT 返回用户信息；缺失/无效/过期 401。"""
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from sqlalchemy import select

from backend.app import db
from backend.app.config import settings
from backend.app.models import User


def test_me_with_valid_token(client, mail_stub, register_user, login_token):
    """有效 JWT 返回当前用户信息。"""
    email = "me@example.com"
    register_user(email)
    token = login_token(email)
    resp = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == email
    assert isinstance(body["id"], int)
    assert body["created_at"]


def test_me_without_header_returns_401(client):
    """未携带 Authorization 头返回 401。"""
    assert client.get("/api/users/me").status_code == 401


def test_me_with_invalid_token_returns_401(client):
    """无效 JWT 返回 401。"""
    resp = client.get("/api/users/me", headers={"Authorization": "Bearer not-a-valid-token"})
    assert resp.status_code == 401


def test_me_with_expired_token_returns_401(client, mail_stub, register_user):
    """过期 JWT 返回 401。"""
    email = "expired-token@example.com"
    register_user(email)
    session = db.SessionLocal()
    user = session.execute(select(User).where(User.email == email)).scalars().one()
    session.close()
    token = pyjwt.encode(
        {"sub": str(user.id), "email": email, "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    resp = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
