"""健康检查端点测试。"""


def test_health_returns_200(client):
    """GET /api/health 返回 200 与 ok 状态。"""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
