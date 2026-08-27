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


def test_scan_empty_files_dir_returns_empty_list(client):
    """files 目录为空时，scan 返回空列表。"""
    name = _make_project(client)
    resp = client.post(f"/projects/{name}/materials/scan")
    assert resp.status_code == 200
    assert resp.json() == []


def test_scan_ingests_files_in_files_dir(client):
    """直接放入 files 目录的文件被 scan 正确摄取分块并入库。"""
    name = _make_project(client)
    fdir = settings.files_dir(name)

    # 模拟用户手工拷入 2 份文件
    import shutil
    shutil.copy2(fixture_path("sample.md"), os.path.join(fdir, "local_sample.md"))
    shutil.copy2(fixture_path("sample.txt"), os.path.join(fdir, "local_notes.txt"))
    # 拷入不支持的文件（应被忽略）
    with open(os.path.join(fdir, "ignored.exe"), "w") as f:
        f.write("binary")

    resp = client.post(f"/projects/{name}/materials/scan")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    sources = sorted(r["source_id"] for r in results)
    assert sources == ["local_notes.txt", "local_sample.md"]
    assert all(r["status"] == "ok" and r["chunk_count"] > 0 for r in results)

    # 验证 DB 与向量库
    mats = client.get(f"/projects/{name}/materials").json()
    assert len(mats) == 2
    store = ProjectVectorStore.get(name, settings.vector_dir(name))
    assert store.count() > 0


def test_scan_unknown_project_returns_404(client):
    resp = client.post("/projects/missing_proj/materials/scan")
    assert resp.status_code == 404


def test_ingest_exception_returns_error_result_and_rolls_back(client, monkeypatch):
    """当转换或向量化入库过程中发生异常时，接口返回 status='error' 并回滚，而不是 500。"""
    name = _make_project(client)
    path = fixture_path("sample.md")

    # 模拟 embedder.encode 抛出异常
    from engine.app.embedding import DeterministicStubEmbedder

    def mock_encode(self, texts):
        raise RuntimeError("ONNX runtime error: model corrupted")

    monkeypatch.setattr(DeterministicStubEmbedder, "encode", mock_encode)

    resp = client.post(
        f"/projects/{name}/materials/ingest",
        json={"file_paths": [path]},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert "摄取失败: ONNX runtime error: model corrupted" in results[0]["error"]

    # 验证 DB 中没有残留脏记录
    mats = client.get(f"/projects/{name}/materials").json()
    assert len(mats) == 0


def test_ingest_empty_file_returns_error_result(client, tmp_path):
    """空文件摄取返回 status='error' 且 chunk_count=0。"""
    name = _make_project(client)
    empty_f = tmp_path / "empty.txt"
    empty_f.write_text("   \n\t  ", encoding="utf-8")

    resp = client.post(
        f"/projects/{name}/materials/ingest",
        json={"file_paths": [str(empty_f)]},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert "内容为空" in results[0]["error"]


