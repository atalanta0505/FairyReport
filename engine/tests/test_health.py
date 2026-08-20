"""健康检查与配置测试。"""
from engine.app.config import settings


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_config_binds_localhost_only(client):
    """应用配置仅绑定 127.0.0.1。"""
    assert settings.host == "127.0.0.1"
    assert client.get("/health").json()["host"] == "127.0.0.1"
