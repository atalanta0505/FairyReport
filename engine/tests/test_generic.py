"""通用知识下载/安装/检索测试（--stub 建包 + MockTransport 假下发，不联网）。"""
import httpx
import pytest

from engine.app.config import settings
from engine.app.generic.store import GenericStore, set_transport
from engine.tools.build_generic_pack import build_pack

FIXTURES_DIR = __import__("os").path.join(__import__("os").path.dirname(__file__), "fixtures")
GENERIC_SOURCE = __import__("os").path.join(FIXTURES_DIR, "generic_source")
SERVER_URL = "http://pack.stub"


class PackServerStub:
    """假下发服务器：按 manifest.sha256 服务 manifest + zip（可篡改 zip）。"""

    def __init__(self, manifest: dict, zip_bytes: bytes) -> None:
        self.manifest = manifest
        self.zip_bytes = zip_bytes
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/api/pack/manifest":
            return httpx.Response(200, json=self.manifest)
        if request.url.path == "/api/pack/download":
            return httpx.Response(
                200, content=self.zip_bytes, headers={"content-type": "application/zip"}
            )
        return httpx.Response(404, text="not found")


def _build_and_serve(tmp_path, corrupt: bool = False) -> tuple[PackServerStub, dict]:
    """构建 --stub 包并注入 MockTransport 下发；corrupt=True 篡改 zip。"""
    out = tmp_path / "pack_out"
    manifest = build_pack(str(out), source=GENERIC_SOURCE, stub=True)
    zip_bytes = (out / "pack.zip").read_bytes()
    if corrupt:
        b = bytearray(zip_bytes)
        b[len(b) // 2] ^= 0xFF  # 翻转中间字节
        zip_bytes = bytes(b)
    stub = PackServerStub(manifest, zip_bytes)
    set_transport(httpx.MockTransport(stub.handle))
    return stub, manifest


def _update(client, token: str = "dummy-jwt"):
    return client.post(
        "/generic/update", json={"server_url": SERVER_URL, "token": token}
    )


def test_update_install_status_query(client, tmp_path):
    """正常安装 → status 显示版本 → query 返回段落。"""
    stub, manifest = _build_and_serve(tmp_path)

    resp = _update(client)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "installed"
    assert resp.json()["version"] == manifest["version"]

    s = client.get("/generic/status").json()
    assert s["installed"] is True
    assert s["version"] == manifest["version"]

    q = client.get("/generic/query", params={"text": "可行性研究", "n": 5})
    assert q.status_code == 200, q.text
    assert len(q.json()["results"]) > 0
    # 段落结构
    r0 = q.json()["results"][0]
    assert "text" in r0 and "source" in r0


def test_not_installed_query_404(client):
    """未安装 query → 404 明确语义。"""
    resp = client.get("/generic/query", params={"text": "x"})
    assert resp.status_code == 404
    assert "未安装" in resp.json()["detail"]


def test_tamper_rejected_no_half_install(client, tmp_path):
    """sha256 篡改 → 拒绝且不标记已装、不留半装。"""
    stub, manifest = _build_and_serve(tmp_path, corrupt=True)

    resp = _update(client)
    assert resp.status_code == 422
    assert "sha256" in resp.json()["detail"]

    # 不标记已装
    assert client.get("/generic/status").json()["installed"] is False
    # 不留半装：versions 目录不存在或为空
    versions = (
        __import__("pathlib").Path(settings.engine_data_dir)
        / "generic"
        / "versions"
    )
    assert not versions.exists() or not any(versions.iterdir())


def test_update_idempotent(client, tmp_path):
    """重复 update 同版本 → 幂等（不重下）。"""
    stub, manifest = _build_and_serve(tmp_path)

    r1 = _update(client)
    assert r1.json()["status"] == "installed"

    stub.requests.clear()
    r2 = _update(client)
    assert r2.status_code == 200
    assert r2.json()["status"] == "already_installed"

    # 幂等：第二次未发起 download（只查 manifest）
    downloads = [r for r in stub.requests if r.url.path == "/api/pack/download"]
    assert len(downloads) == 0


def test_server_401_forwarded(client):
    """服务器 401 → 引擎转发 401。"""
    set_transport(httpx.MockTransport(lambda req: httpx.Response(401, text="unauthorized")))
    resp = _update(client, token="bad")
    assert resp.status_code == 401


def test_server_404_forwarded(client):
    """服务器 404（无包）→ 引擎转发 404。"""
    set_transport(httpx.MockTransport(lambda req: httpx.Response(404, text="no pack")))
    resp = _update(client)
    assert resp.status_code == 404


def test_status_not_installed_initially(client):
    """初始状态未安装。"""
    assert client.get("/generic/status").json() == {"installed": False}



def test_server_connect_timeout_graceful(client):
    """服务器连接超时 → 转换为清晰的 504 错误提示。"""
    def raise_timeout(req):
        raise httpx.ConnectTimeout("Connect timeout", request=req)

    set_transport(httpx.MockTransport(raise_timeout))
    resp = _update(client)
    assert resp.status_code == 504
    assert "超时" in resp.json()["detail"]


@pytest.fixture(autouse=True)
def _reset_generic_state():
    """每用例前后清 GenericStore 缓存与传输层（client fixture 已重置目录）。"""
    yield
    GenericStore.close()
    set_transport(None)
