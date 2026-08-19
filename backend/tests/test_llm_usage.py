"""GET /api/llm/usage 与每日 token 硬上限测试。"""
from backend.app.config import settings


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_usage_requires_auth(client):
    """未带 JWT 查询用量返回 401。"""
    assert client.get("/api/llm/usage").status_code == 401


def test_usage_reports_zero_initially(client, mail_stub, register_user, login_token):
    """无调用时当日已用为 0，上限取配置值。"""
    email = "llm-usage-zero@example.com"
    register_user(email)
    token = login_token(email)
    resp = client.get("/api/llm/usage", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["used_tokens"] == 0
    assert body["limit"] == settings.user_daily_token_limit
    assert body["remaining_tokens"] == settings.user_daily_token_limit


def test_daily_limit_enforced_and_usage_consistent(
    client, mail_stub, register_user, login_token, llm_upstream, monkeypatch
):
    """超当日上限 → 429（含用量信息），且与 /api/llm/usage 数值一致。"""
    email = "llm-limit@example.com"
    register_user(email)
    token = login_token(email)
    monkeypatch.setattr(settings, "user_daily_token_limit", 50)
    llm_upstream.set_json({
        "choices": [{"message": {"role": "assistant", "content": "long answer"}}],
        "usage": {"prompt_tokens": 35, "completion_tokens": 25, "total_tokens": 60},
    })
    payload = {"messages": [{"role": "user", "content": "q"}]}
    first = client.post("/api/llm/chat", json=payload, headers=_auth(token))
    assert first.status_code == 200
    blocked = client.post("/api/llm/chat", json=payload, headers=_auth(token))
    assert blocked.status_code == 429
    detail = blocked.json()["detail"]
    assert detail["used_tokens"] == 60
    assert detail["limit"] == 50
    assert len(llm_upstream.requests) == 1
    usage_resp = client.get("/api/llm/usage", headers=_auth(token))
    assert usage_resp.status_code == 200
    body = usage_resp.json()
    assert body["used_tokens"] == 60
    assert body["limit"] == 50
    assert body["remaining_tokens"] == 0
