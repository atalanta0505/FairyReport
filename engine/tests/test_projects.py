"""项目路由测试：创建/列出/删除。"""
import os

from unittest.mock import patch

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


def test_open_project_folder(client):
    client.post("/projects", json={"name": "folder_proj"})
    with patch("os.startfile", create=True) as mock_startfile:
        resp = client.post("/projects/folder_proj/open-folder")
        assert resp.status_code == 200
        data = resp.json()
        assert "path" in data
        assert str(settings.files_dir("folder_proj").resolve()) == data["path"]
        if os.name == "nt":
            mock_startfile.assert_called_once()


def test_open_nonexistent_project_folder_returns_404(client):
    resp = client.post("/projects/nope/open-folder")
    assert resp.status_code == 404


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


def test_delete_project_cleans_materials_chunks_and_allows_clean_recreation(client):
    """
    删除项目时级联彻底清理 materials 数据表记录与磁盘分块向量索引；
    重建同名项目时资料列表与向量库完全干净，通用知识包不受影响。
    """
    from engine.app.materials.vectorstore import ProjectVectorStore
    from engine.tests.conftest import fixture_path

    # 1. 创建项目并摄取资料
    name = "clean_recreate_proj"
    resp = client.post("/projects", json={"name": name})
    assert resp.status_code == 201

    ingest_resp = client.post(
        f"/projects/{name}/materials/ingest",
        json={"file_paths": [fixture_path("sample.md"), fixture_path("sample.txt")]},
    )
    assert ingest_resp.status_code == 200
    assert len(ingest_resp.json()) == 2
    assert ingest_resp.json()[0]["chunk_count"] > 0

    # 保存大纲与章节以确保有附加持久化文件
    client.post(
        f"/projects/{name}/outline",
        json={
            "report_type": "可行性研究报告",
            "outline_md": "# 第一章 概述",
            "chapters": [{"seq": 1, "title": "第一章 概述"}],
        },
    )
    client.post(
        f"/projects/{name}/chapters/1",
        json={"text": "第一章正文内容"},
    )

    # 验证资料与向量已存在
    mats = client.get(f"/projects/{name}/materials").json()
    assert len(mats) == 2

    store = ProjectVectorStore.get(name, settings.vector_dir(name))
    assert store.count() > 0

    pdir = settings.project_dir(name)
    assert pdir.exists()
    assert settings.files_dir(name).exists()
    assert (pdir / "outline.json").exists()
    assert (pdir / "chapters.json").exists()

    # 检查通用知识包状态（作为基线比较）
    generic_status_before = client.get("/generic/status").json()

    # 2. 删除项目
    del_resp = client.delete(f"/projects/{name}")
    assert del_resp.status_code == 204

    # 验证磁盘目录已被彻底清理
    assert not pdir.exists()

    # 验证通用知识包状态未受影响
    generic_status_after = client.get("/generic/status").json()
    assert generic_status_before == generic_status_after

    # 3. 重新创建同名项目
    recreate_resp = client.post("/projects", json={"name": name})
    assert recreate_resp.status_code == 201

    # 验证新项目的资料列表为空、分块为 0、大纲与章节重置
    mats_new = client.get(f"/projects/{name}/materials").json()
    assert mats_new == []

    store_new = ProjectVectorStore.get(name, settings.vector_dir(name))
    assert store_new.count() == 0

    outline_new = client.get(f"/projects/{name}/outline").json()
    assert outline_new["outline_md"] == ""
    assert outline_new["chapters"] == []

    chapters_new = client.get(f"/projects/{name}/chapters").json()
    assert chapters_new["chapters"] == {}

