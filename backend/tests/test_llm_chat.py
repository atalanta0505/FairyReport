"""POST /api/llm/chat 测试：鉴权、非流式/流式透传、白名单、Key 轮询、上游故障映射。"""
import json

from sqlalchemy import select

from backend.app import db
from backend.app.models import UsageLog

ALLOWED_MODEL = "deepseek-v4-flash"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _usage_rows() -> list[UsageLog]:
    session = db.SessionLocal()
    rows = session.execute(select(UsageLog).order_by(UsageLog.id)).scalars().all()
    session.close()
    return rows


def test_chat_without_token_returns_401(client, llm_upstream):
    """未带 JWT 调 chat 返回 401。"""
    llm_upstream.set_json({})
    resp = client.post("/api/llm/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert resp.status_code == 401
    assert llm_upstream.requests == []


def test_chat_with_invalid_token_returns_401(client, llm_upstream):
    """无效 JWT 调 chat 返回 401。"""
    llm_upstream.set_json({})
    resp = client.post(
        "/api/llm/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert resp.status_code == 401
    assert llm_upstream.requests == []


def test_chat_non_stream_returns_content_and_records_usage(
    client, mail_stub, register_user, login_token, llm_upstream
):
    """非流式：透传上游内容与请求参数，usage_log 数值与打桩 usage 一致。"""
    email = "llm-nonstream@example.com"
    register_user(email)
    token = login_token(email)
    llm_upstream.set_json({
        "id": "cmpl-1",
        "model": ALLOWED_MODEL,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello, world!"}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
    })
    resp = client.post(
        "/api/llm/chat",
        json={"messages": [{"role": "user", "content": "Say hello"}]},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "Hello, world!"
    sent = json.loads(llm_upstream.requests[0].content)
    assert sent["model"] == ALLOWED_MODEL
    assert sent["messages"] == [{"role": "user", "content": "Say hello"}]
    assert sent["stream"] is False
    assert llm_upstream.requests[0].headers["authorization"].startswith("Bearer sk-test-")
    rows = _usage_rows()
    assert len(rows) == 1
    assert rows[0].prompt_tokens == 11
    assert rows[0].completion_tokens == 7
    assert rows[0].model == ALLOWED_MODEL
    assert rows[0].estimated is False


def test_chat_non_stream_without_usage_estimates(
    client, mail_stub, register_user, login_token, llm_upstream
):
    """上游无 usage 时按字符估算并标 estimated。"""
    email = "llm-estimate@example.com"
    register_user(email)
    token = login_token(email)
    llm_upstream.set_json({"choices": [{"message": {"role": "assistant", "content": "0123456789"}}]})
    resp = client.post(
        "/api/llm/chat",
        json={"messages": [{"role": "user", "content": "Say hello"}]},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    rows = _usage_rows()
    assert len(rows) == 1
    assert rows[0].estimated is True
    assert rows[0].prompt_tokens == 5
    assert rows[0].completion_tokens == 5


def test_chat_stream_sse_passthrough_and_metering(
    client, mail_stub, register_user, login_token, llm_upstream
):
    """流式：SSE 逐 chunk 透传，末尾 usage 计量入库，请求携带 stream_options。"""
    email = "llm-stream@example.com"
    register_user(email)
    token = login_token(email)
    chunks = [
        json.dumps({"choices": [{"delta": {"content": "Hel"}}]}),
        json.dumps({"choices": [{"delta": {"content": "lo"}}]}),
        json.dumps({"choices": [], "usage": {"prompt_tokens": 6, "completion_tokens": 3, "total_tokens": 9}}),
    ]
    llm_upstream.set_sse(chunks)
    resp = client.post(
        "/api/llm/chat",
        json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = [e for e in resp.text.split("\n\n") if e.strip()]
    assert events[:-1] == [f"data: {chunk}" for chunk in chunks]
    assert events[-1] == "data: [DONE]"
    sent = json.loads(llm_upstream.requests[0].content)
    assert sent["stream"] is True
    assert sent["stream_options"] == {"include_usage": True}
    rows = _usage_rows()
    assert len(rows) == 1
    assert rows[0].prompt_tokens == 6
    assert rows[0].completion_tokens == 3
    assert rows[0].estimated is False


def test_chat_stream_appends_done_when_upstream_omits(
    client, mail_stub, register_user, login_token, llm_upstream
):
    """上游未发 [DONE] 时网关仍以保证的 SSE 结束标记收尾。"""
    email = "llm-stream-no-done@example.com"
    register_user(email)
    token = login_token(email)
    llm_upstream.set_sse([json.dumps({"choices": [{"delta": {"content": "x"}}]})], include_done=False)
    resp = client.post(
        "/api/llm/chat",
        json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.text.endswith("data: [DONE]\n\n")


def test_chat_stream_upstream_5xx_maps_to_502(
    client, mail_stub, register_user, login_token, llm_upstream
):
    """流式请求遇上游 5xx 时返回 502（未开始 SSE 输出）。"""
    email = "llm-stream-5xx@example.com"
    register_user(email)
    token = login_token(email)
    llm_upstream.set_status(503, "upstream busy")
    resp = client.post(
        "/api/llm/chat",
        json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
        headers=_auth(token),
    )
    assert resp.status_code == 502
    assert "upstream busy" in resp.text


def test_chat_model_not_in_allowlist_returns_422(
    client, mail_stub, register_user, login_token, llm_upstream
):
    """白名单外 model 返回 422，且不触达上游。"""
    email = "llm-allowlist@example.com"
    register_user(email)
    token = login_token(email)
    llm_upstream.set_json({})
    resp = client.post(
        "/api/llm/chat",
        json={"messages": [{"role": "user", "content": "hi"}], "model": "gpt-9-turbo"},
        headers=_auth(token),
    )
    assert resp.status_code == 422
    assert llm_upstream.requests == []


def test_chat_rotates_keys_round_robin(
    client, mail_stub, register_user, login_token, llm_upstream
):
    """Key 池含 2 个 key 时连续调用轮询使用（Authorization 头交替）。"""
    email = "llm-rotation@example.com"
    register_user(email)
    token = login_token(email)
    llm_upstream.set_json({
        "choices": [{"message": {"role": "assistant", "content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    })
    headers = []
    for _ in range(3):
        resp = client.post(
            "/api/llm/chat",
            json={"messages": [{"role": "user", "content": "ping"}]},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        headers.append(llm_upstream.requests[-1].headers["authorization"])
    assert headers[0] != headers[1]
    assert headers[0] == headers[2]
    assert set(headers) == {"Bearer sk-test-alpha-0001", "Bearer sk-test-beta-0002"}


def test_chat_upstream_5xx_maps_to_502_without_key_leak(
    client, mail_stub, register_user, login_token, llm_upstream
):
    """上游 5xx → 502 并保留错误摘要；响应不泄露 Key；失败不计入用量。"""
    email = "llm-5xx@example.com"
    register_user(email)
    token = login_token(email)
    llm_upstream.set_status(500, "internal meltdown")
    resp = client.post(
        "/api/llm/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers=_auth(token),
    )
    assert resp.status_code == 502
    assert "internal meltdown" in resp.text
    assert "sk-test-alpha-0001" not in resp.text
    assert "sk-test-beta-0002" not in resp.text
    assert _usage_rows() == []


def test_chat_upstream_timeout_maps_to_504_without_key_leak(
    client, mail_stub, register_user, login_token, llm_upstream
):
    """上游超时 → 504；响应不泄露 Key。"""
    email = "llm-timeout@example.com"
    register_user(email)
    token = login_token(email)
    llm_upstream.set_timeout()
    resp = client.post(
        "/api/llm/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers=_auth(token),
    )
    assert resp.status_code == 504
    assert "sk-test-alpha-0001" not in resp.text
    assert "sk-test-beta-0002" not in resp.text
    assert _usage_rows() == []
