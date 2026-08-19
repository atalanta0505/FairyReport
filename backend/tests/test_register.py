"""register 端点测试：成功创建、验证码错误/过期、重复邮箱。"""
from datetime import timedelta

from sqlalchemy import select

from backend.app import db
from backend.app.models import AuthCode, User


def test_register_success(client, mail_stub, send_code):
    """有效验证码注册成功：用户入库，密码以哈希+盐存储。"""
    email = "new@example.com"
    code = send_code(email)
    resp = client.post("/api/auth/register", json={"email": email, "code": code, "password": "test-password-1"})
    assert resp.status_code in (200, 201)
    session = db.SessionLocal()
    user = session.execute(select(User).where(User.email == email)).scalars().one()
    session.close()
    assert user.salt and user.password_hash
    assert user.password_hash != "test-password-1"
    assert user.created_at is not None


def test_register_wrong_code_returns_4xx(client, mail_stub, send_code):
    """验证码错误返回 4xx，且不创建用户。"""
    email = "new@example.com"
    code = send_code(email)
    wrong = "000000" if code != "000000" else "000001"
    resp = client.post("/api/auth/register", json={"email": email, "code": wrong, "password": "test-password-1"})
    assert 400 <= resp.status_code < 500
    session = db.SessionLocal()
    assert session.execute(select(User).where(User.email == email)).first() is None
    session.close()


def test_register_expired_code_returns_4xx(client, mail_stub, send_code):
    """验证码过期返回 4xx，且不创建用户。"""
    email = "expired@example.com"
    code = send_code(email)
    session = db.SessionLocal()
    row = session.execute(select(AuthCode).where(AuthCode.email == email)).scalars().one()
    row.expires_at = db.utcnow() - timedelta(seconds=1)
    session.commit()
    session.close()
    resp = client.post("/api/auth/register", json={"email": email, "code": code, "password": "test-password-1"})
    assert 400 <= resp.status_code < 500
    session = db.SessionLocal()
    assert session.execute(select(User).where(User.email == email)).first() is None
    session.close()


def test_register_duplicate_email_returns_4xx(client, mail_stub, register_user):
    """重复邮箱注册返回 4xx，且不产生第二个用户。"""
    email = "dup@example.com"
    register_user(email)
    session = db.SessionLocal()
    session.add(AuthCode(
        email=email,
        code="123456",
        created_at=db.utcnow(),
        expires_at=db.utcnow() + timedelta(minutes=10),
    ))
    session.commit()
    session.close()
    resp = client.post("/api/auth/register", json={"email": email, "code": "123456", "password": "test-password-2"})
    assert 400 <= resp.status_code < 500
    session = db.SessionLocal()
    users = session.execute(select(User).where(User.email == email)).scalars().all()
    session.close()
    assert len(users) == 1
