"""
测试夹具：SQLite 内存库 + FastAPI TestClient + SMTP/LLM 上游打桩。

全部测试不依赖网络、Docker、Postgres，不真实发信，不真实调用模型 API。
"""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-jwt-secret-0123456789abcdef"
os.environ["LLM_API_KEYS"] = "sk-test-alpha-0001,sk-test-beta-0002"
os.environ["LLM_BASE_URL"] = "https://llm.stub.invalid/v1"

import httpx
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


class LLMUpstreamStub:
    """上游 LLM API 打桩（httpx.MockTransport handler）；记录收到的全部请求。"""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self._handler = None

    def set_json(self, body: dict, status_code: int = 200) -> None:
        """打桩返回 JSON 响应。"""
        self._handler = lambda request: httpx.Response(status_code, json=body)

    def set_sse(self, chunks: list[str], include_done: bool = True) -> None:
        """打桩返回 SSE 流；chunks 为 data: 后的载荷，默认末尾补 data: [DONE]。"""
        events = [f"data: {chunk}\n\n" for chunk in chunks]
        if include_done:
            events.append("data: [DONE]\n\n")
        body = "".join(events)
        self._handler = lambda request: httpx.Response(
            200, text=body, headers={"Content-Type": "text/event-stream"}
        )

    def set_status(self, status_code: int, text: str = "") -> None:
        """打桩返回指定状态码与文本体。"""
        self._handler = lambda request: httpx.Response(status_code, text=text)

    def set_timeout(self) -> None:
        """打桩模拟上游超时。"""
        def _raise(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("stub upstream timeout", request=request)
        self._handler = _raise

    def handle(self, request: httpx.Request) -> httpx.Response:
        """MockTransport 入口：记录请求后交由已设置的 handler。"""
        self.requests.append(request)
        assert self._handler is not None, "测试未设置上游打桩响应"
        return self._handler(request)


@pytest.fixture()
def llm_upstream(monkeypatch):
    """以 MockTransport 替换网关传输层；用例不得真实访问上游。"""
    stub = LLMUpstreamStub()
    monkeypatch.setattr("backend.app.llm.gateway._transport", httpx.MockTransport(stub.handle))
    return stub
