"""资料摄取/列出/删除测试。"""
import os

from engine.app.config import settings
from engine.app.materials.vectorstore import ProjectVectorStore
from engine.tests.conftest import fixture_path

ALL_FIXTURES = ["sample.csv", "sample.docx", "sample.md", "sample.txt", "sample.xlsx"]


def _make_project(client, name="p1"):
    r = client.post("/projects", json={"name": name})
    assert r.status_code == 201
    return name


def test_ingest_each_format_produces_chunks(client):
    """五格式各有用例：ingest 后 chunk_count > 0。"""
    name = _make_project(client)
    for fname in ALL_FIXTURES:
        resp = client.post(
            f"/projects/{name}/materials/ingest",
            json={"file_paths": [fixture_path(fname)]},
        )
        assert resp.status_code == 200, f"{fname}: {resp.text}"
        result = resp.json()[0]
        assert result["status"] == "ok", f"{fname} failed: {result}"
        assert result["chunk_count"] > 0, f"{fname} no chunks"
        assert result["ext"] == os.path.splitext(fname)[1]


def test_ingest_md_creates_chunks_and_file(client):
    """ingest .md 本地路径 → chunk_count>0，文件已拷贝。"""
    name = _make_project(client)
    resp = client.post(
        f"/projects/{name}/materials/ingest",
        json={"file_paths": [fixture_path("sample.md")]},
    )
    assert resp.status_code == 200
    r = resp.json()[0]
    assert r["chunk_count"] > 0
    assert os.path.exists(os.path.join(settings.files_dir(name), "sample.md"))


def test_reingest_same_source_upsert_no_accumulation(client):
    """同源重复 ingest → upsert 覆盖不累积。"""
    name = _make_project(client)
    path = fixture_path("sample.md")
    url = f"/projects/{name}/materials/ingest"

    r1 = client.post(url, json={"file_paths": [path]}).json()[0]
    r2 = client.post(url, json={"file_paths": [path]}).json()[0]

    assert r1["chunk_count"] == r2["chunk_count"]
    assert r1["chunk_count"] > 0

    # 向量数量不累积
    store = ProjectVectorStore.get(name, settings.vector_dir(name))
    assert store.count() == r2["chunk_count"]
    # 资料记录仍为 1 条
    mats = client.get(f"/projects/{name}/materials").json()
    assert len(mats) == 1
    assert mats[0]["chunk_count"] == r2["chunk_count"]


def test_delete_material_removes_file_and_vectors(client):
    """按 source 删除 → 文件+向量同删。"""
    name = _make_project(client)
    path = fixture_path("sample.md")
    client.post(
        f"/projects/{name}/materials/ingest",
        json={"file_paths": [path]},
    )

    store = ProjectVectorStore.get(name, settings.vector_dir(name))
    assert store.count() > 0
    copied = os.path.join(settings.files_dir(name), "sample.md")
    assert os.path.exists(copied)

    resp = client.delete(f"/projects/{name}/materials/sample.md")
    assert resp.status_code == 204

    # 文件已删
    assert not os.path.exists(copied)
    # 向量已删
    assert store.count() == 0
    # 资料记录已删
    mats = client.get(f"/projects/{name}/materials").json()
    assert mats == []


def test_list_materials(client):
    name = _make_project(client)
    client.post(
        f"/projects/{name}/materials/ingest",
        json={"file_paths": [fixture_path("sample.md"), fixture_path("sample.txt")]},
    )
    resp = client.get(f"/projects/{name}/materials")
    assert resp.status_code == 200
    ids = sorted(m["source_id"] for m in resp.json())
    assert ids == ["sample.md", "sample.txt"]


def test_ingest_nonexistent_path_returns_4xx(client):
    name = _make_project(client)
    resp = client.post(
        f"/projects/{name}/materials/ingest",
        json={"file_paths": [fixture_path("does_not_exist.md")]},
    )
    assert 400 <= resp.status_code < 500


def test_ingest_unsupported_extension_returns_4xx(client, tmp_path):
    name = _make_project(client)
    bad = tmp_path / "bad.pdf"
    bad.write_text("not really a pdf", encoding="utf-8")
    resp = client.post(
        f"/projects/{name}/materials/ingest",
        json={"file_paths": [str(bad)]},
    )
    assert 400 <= resp.status_code < 500


def test_ingest_unknown_project_returns_404(client):
    resp = client.post(
        "/projects/missing/materials/ingest",
        json={"file_paths": [fixture_path("sample.md")]},
    )
    assert resp.status_code == 404


def test_delete_nonexistent_material_returns_404(client):
    name = _make_project(client)
    resp = client.delete(f"/projects/{name}/materials/nope.md")
    assert resp.status_code == 404
