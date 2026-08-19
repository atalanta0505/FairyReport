"""GET /api/llm/usage 测试（纯可见性：只报当日已用 token，无上限语义）。"""


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_usage_requires_auth(client):
    """未带 JWT 查询用量返回 401。"""
    assert client.get("/api/llm/usage").status_code == 401


def test_usage_reports_zero_initially(client, mail_stub, register_user, login_token):
    """无调用时当日已用为 0，且响应不含上限字段。"""
    email = "llm-usage-zero@example.com"
    register_user(email)
    token = login_token(email)
    resp = client.get("/api/llm/usage", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["used_tokens"] == 0
    assert "limit" not in body
    assert "remaining_tokens" not in body


def test_usage_accumulates_and_never_blocks(
    client, mail_stub, register_user, login_token, llm_upstream
):
    """连续调用不因用量被拒（无 429），usage 持续累计且不含上限字段。"""
    email = "llm-usage-accumulate@example.com"
    register_user(email)
    token = login_token(email)
    llm_upstream.set_json({
        "choices": [{"message": {"role": "assistant", "content": "long answer"}}],
        "usage": {"prompt_tokens": 35, "completion_tokens": 25, "total_tokens": 60},
    })
    payload = {"messages": [{"role": "user", "content": "q"}]}
    for _ in range(3):
        resp = client.post("/api/llm/chat", json=payload, headers=_auth(token))
        assert resp.status_code == 200
    assert len(llm_upstream.requests) == 3
    usage_resp = client.get("/api/llm/usage", headers=_auth(token))
    assert usage_resp.status_code == 200
    body = usage_resp.json()
    assert body["used_tokens"] == 180
    assert "limit" not in body
    assert "remaining_tokens" not in body
