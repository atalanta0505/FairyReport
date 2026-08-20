"""通用知识包下发端点测试（JWT 保护 / 401 / 404 / 200）。"""
import json
import os
import zipfile

from backend.app import db
from backend.app.auth import security
from backend.app.config import settings
from backend.app.models import User


def _make_token(client) -> str:
    """直接建用户并签发 JWT（不走邮箱流程，专注 pack 端点）。"""
    session = db.SessionLocal()
    ph, salt = security.hash_password("pack-pw")
    u = User(email="pack@test.com", password_hash=ph, salt=salt)
    session.add(u)
    session.commit()
    session.refresh(u)
    uid = u.id
    session.close()
    return security.create_access_token(uid, "pack@test.com")


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _put_stub_pack(pack_dir: str) -> dict:
    """在 PACK_DIR 放置打桩 manifest.json 与 pack.zip。"""
    os.makedirs(pack_dir, exist_ok=True)
    manifest = {
        "version": "v-test",
        "sha256": "abc123",
        "built_at": "2026-01-01T00:00:00+00:00",
        "chunk_count": 3,
        "templates": ["t.json"],
    }
    with open(os.path.join(pack_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    with zipfile.ZipFile(os.path.join(pack_dir, "pack.zip"), "w") as z:
        z.writestr("manifest.json", json.dumps(manifest))
        z.writestr("vector_db/dummy", "")
    return manifest


def test_manifest_no_jwt_401(client):
    assert client.get("/api/pack/manifest").status_code == 401


def test_download_no_jwt_401(client):
    assert client.get("/api/pack/download").status_code == 401


def test_invalid_jwt_401(client, tmp_path):
    settings.pack_dir = str(tmp_path)
    resp = client.get(
        "/api/pack/manifest", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert resp.status_code == 401


def test_manifest_missing_404(client, tmp_path):
    settings.pack_dir = str(tmp_path)  # 空目录，无文件
    token = _make_token(client)
    assert client.get("/api/pack/manifest", headers=_auth(token)).status_code == 404


def test_download_missing_404(client, tmp_path):
    settings.pack_dir = str(tmp_path)
    token = _make_token(client)
    assert client.get("/api/pack/download", headers=_auth(token)).status_code == 404


def test_manifest_200(client, tmp_path):
    settings.pack_dir = str(tmp_path)
    manifest = _put_stub_pack(str(tmp_path))
    token = _make_token(client)
    resp = client.get("/api/pack/manifest", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["version"] == manifest["version"]


def test_download_200(client, tmp_path):
    settings.pack_dir = str(tmp_path)
    _put_stub_pack(str(tmp_path))
    token = _make_token(client)
    resp = client.get("/api/pack/download", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.content) > 0
