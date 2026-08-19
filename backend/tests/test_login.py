"""login 端点测试：成功返回 JWT、密码错误 401。"""
import jwt as pyjwt


def test_login_success_returns_jwt(client, mail_stub, register_user):
    """注册后以正确密码登录：返回含 sub/email/exp 的 JWT。"""
    email = "user@example.com"
    register_user(email, "test-password-1")
    resp = client.post("/api/auth/login", json={"email": email, "password": "test-password-1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    payload = pyjwt.decode(body["access_token"], options={"verify_signature": False})
    assert payload["email"] == email
    assert payload["sub"]
    assert "exp" in payload


def test_login_wrong_password_returns_401(client, mail_stub, register_user):
    """密码错误返回 401。"""
    email = "user@example.com"
    register_user(email, "test-password-1")
    resp = client.post("/api/auth/login", json={"email": email, "password": "wrong-password-1"})
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client):
    """未注册邮箱登录返回 401。"""
    resp = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "whatever-123"})
    assert resp.status_code == 401
