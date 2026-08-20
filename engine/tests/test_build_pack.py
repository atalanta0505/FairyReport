"""通用知识包构建脚本测试。"""
import hashlib
import json
import os
import zipfile

from engine.tools.build_generic_pack import build_pack

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
GENERIC_SOURCE = os.path.join(FIXTURES_DIR, "generic_source")


def test_build_stub_produces_complete_pack(tmp_path):
    """--stub 产出 zip+manifest，manifest 字段齐全，sha256 匹配。"""
    manifest = build_pack(str(tmp_path), source=GENERIC_SOURCE, stub=True)

    # manifest 字段齐全
    for k in ("version", "sha256", "built_at", "chunk_count", "templates"):
        assert manifest.get(k), f"manifest 缺字段或为空：{k}"
    assert manifest["chunk_count"] > 0
    assert manifest["templates"] == ["feasibility.json"]

    # 产出文件
    zip_path = os.path.join(str(tmp_path), "pack.zip")
    man_path = os.path.join(str(tmp_path), "manifest.json")
    assert os.path.exists(zip_path)
    assert os.path.exists(man_path)

    # zip 内含 manifest + templates + vector_db
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        assert "manifest.json" in names
        assert any(n.startswith("templates/") for n in names)
        assert any(n.startswith("vector_db/") for n in names)

    # 独立 manifest 的 sha256 == sha256(pack.zip)
    h = hashlib.sha256(open(zip_path, "rb").read()).hexdigest()
    assert h == manifest["sha256"]

    # 独立 manifest 文件内容与返回一致
    on_disk = json.loads(open(man_path, encoding="utf-8").read())
    assert on_disk == manifest


def test_build_version_is_deterministic(tmp_path):
    """同内容 → 同版本号（支撑幂等）。"""
    out1 = os.path.join(str(tmp_path), "a")
    out2 = os.path.join(str(tmp_path), "b")
    m1 = build_pack(out1, source=GENERIC_SOURCE, stub=True)
    m2 = build_pack(out2, source=GENERIC_SOURCE, stub=True)
    assert m1["version"] == m2["version"]
