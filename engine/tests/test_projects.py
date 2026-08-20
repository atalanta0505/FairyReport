"""项目路由测试：创建/列出/删除。"""
import os

from engine.app.config import settings


def test_create_project(client):
    resp = client.post("/projects", json={"name": "demo"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "demo"
    # 目录已创建
    assert settings.files_dir("demo").exists()
    assert settings.vector_dir("demo").exists()


def test_create_duplicate_returns_409(client):
    client.post("/projects", json={"name": "demo"})
    resp = client.post("/projects", json={"name": "demo"})
    assert resp.status_code == 409


def test_list_projects(client):
    client.post("/projects", json={"name": "a"})
    client.post("/projects", json={"name": "b"})
    resp = client.get("/projects")
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert names == ["a", "b"]


def test_delete_project_removes_dirs(client):
    client.post("/projects", json={"name": "gone"})
    pdir = settings.project_dir("gone")
    assert pdir.exists()
    resp = client.delete("/projects/gone")
    assert resp.status_code == 204
    assert not pdir.exists()
    # 列表中已无
    assert all(p["name"] != "gone" for p in client.get("/projects").json())


def test_delete_nonexistent_returns_404(client):
    resp = client.delete("/projects/nope")
    assert resp.status_code == 404
