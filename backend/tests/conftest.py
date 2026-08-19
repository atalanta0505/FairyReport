"""
测试夹具：SQLite 内存库 + FastAPI TestClient + SMTP 打桩。

全部测试不依赖网络、Docker、Postgres，不真实发信。
"""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-jwt-secret-0123456789abcdef"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app import db
from backend.app.main import app
from backend.app.models import AuthCode


@pytest.fixture()
def client():
    """每用例一个干净内存库的 TestClient。"""
    db.Base.metadata.drop_all(bind=db.engine)
    db.Base.metadata.create_all(bind=db.engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def mail_stub(monkeypatch):
    """以记录器替换 smtp.send_code_email，保证测试绝不真实发信；返回已发送 (邮箱, 码) 列表。"""
    sent = []

    def _stub(to_addr: str, code: str) -> None:
        sent.append((to_addr, code))

    monkeypatch.setattr("backend.app.smtp.send_code_email", _stub)
    return sent


@pytest.fixture()
def send_code(client):
    """调用 send-code 并返回实际写库的验证码。"""
    def _send(email: str) -> str:
        resp = client.post("/api/auth/send-code", json={"email": email})
        assert resp.status_code == 200
        session = db.SessionLocal()
        row = session.execute(
            select(AuthCode).where(AuthCode.email == email).order_by(AuthCode.id.desc())
        ).scalars().first()
        session.close()
        assert row is not None
        return row.code
    return _send


@pytest.fixture()
def register_user(client, send_code):
    """走通 发码 → 注册 全流程。"""
    def _register(email: str, password: str = "test-password-1") -> None:
        code = send_code(email)
        resp = client.post("/api/auth/register", json={"email": email, "code": code, "password": password})
        assert resp.status_code in (200, 201)
    return _register


@pytest.fixture()
def login_token(client):
    """登录并返回 JWT。"""
    def _login(email: str, password: str = "test-password-1") -> str:
        resp = client.post("/api/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200
        return resp.json()["access_token"]
    return _login
