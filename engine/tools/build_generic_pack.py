"""
通用知识包构建脚本 — 读 generic_knowledge/ → 分块 → 嵌入 → 打 zip + sha256。

包格式 v1：zip 内含 manifest.json + templates/ + vector_db/（chroma 持久化目录，collection=generic_kb）。

CLI：
    python -m engine.tools.build_generic_pack --out <dir> [--stub] [--source <dir>]

默认 --source 为仓库根目录下 generic_knowledge/（只读源）。
--stub 使用确定性假向量（不下载模型、不联网）；默认走真实 fastembed。
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import chromadb

# 仓库根目录（engine/tools/build_generic_pack.py 上两级）
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SOURCE = _REPO_ROOT / "generic_knowledge"

# 引擎分块与嵌入（独立自洽，相对导入）
import sys  # noqa: E402

sys.path.insert(0, str(_REPO_ROOT))

from engine.app.materials.chunking import chunk_text  # noqa: E402
from engine.app.embedding import (  # noqa: E402
    DeterministicStubEmbedder,
    FastEmbedEmbedder,
)

GENERIC_COLLECTION = "generic_kb"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _collect_literature(source_dir: Path) -> list[Path]:
    """收集源目录下的 .md 文献（不递归进 templates/）。"""
    return sorted(p for p in source_dir.iterdir() if p.suffix == ".md" and p.is_file())


def _collect_templates(source_dir: Path) -> list[Path]:
    """收集 templates/ 下模板 JSON。"""
    tdir = source_dir / "templates"
    if not tdir.is_dir():
        return []
    return sorted(p for p in tdir.iterdir() if p.suffix == ".json" and p.is_file())


def _build_chunks(literature: list[Path]) -> list[dict]:
    """对文献分块，返回 chunk 列表（含 source/source_id/doc_id/index）。"""
    all_chunks: list[dict] = []
    for doc_id, fpath in enumerate(literature, start=1):
        text = fpath.read_text(encoding="utf-8")
        chunks = chunk_text(
            text, source_name=fpath.name, source_id=fpath.name, doc_id=doc_id
        )
        for i, c in enumerate(chunks):
            c["index"] = i
        all_chunks.extend(chunks)
    return all_chunks


def _write_vector_db(vector_dir: Path, chunks: list[dict], embedder) -> None:
    """写入 chroma 持久化目录（collection=generic_kb）。"""
    vector_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(vector_dir))
    col = client.get_or_create_collection(GENERIC_COLLECTION)
    if chunks:
        texts = [c["text"] for c in chunks]
        embeddings = embedder.encode(texts)
        ids = [f"{c['source_id']}_{c['index']}" for c in chunks]
        metadatas = [
            {
                "source": c.get("source", ""),
                "source_id": c.get("source_id", ""),
                "doc_id": c.get("doc_id", -1),
                "index": c.get("index", i),
            }
            for i, c in enumerate(chunks)
        ]
        col.upsert(embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids)
    # 释放 client 以便后续打包（chroma sqlite 文件锁）
    try:
        del col
    except Exception:
        pass
    try:
        del client
    except Exception:
        pass
    gc.collect()


def _add_dir_to_zip(zf, src_dir: Path, arcname_prefix: str) -> None:
    """将目录递归加入 zip，arc 路径以 prefix 为根。"""
    for root, _dirs, files in os.walk(str(src_dir)):
        for f in sorted(files):
            full = os.path.join(root, f)
            rel = os.path.join(arcname_prefix, os.path.relpath(full, str(src_dir)))
            zf.write(full, rel.replace(os.sep, "/"))


def _content_version(chunks: list[dict], template_names: list[str]) -> str:
    """基于内容的确定性版本号（同内容→同版本，支撑幂等）。"""
    chunk_texts = sorted(c["text"] for c in chunks)
    payload = json.dumps(
        {"chunks": chunk_texts, "templates": sorted(template_names)},
        ensure_ascii=False,
        sort_keys=True,
    )
    return "v-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def build_pack(out_dir: str, source: str = None, stub: bool = False) -> dict:
    """构建知识包，输出 pack.zip 与 manifest.json 到 out_dir，返回 manifest。"""
    source_dir = Path(source) if source else _DEFAULT_SOURCE
    if not source_dir.is_dir():
        raise FileNotFoundError(f"源目录不存在：{source_dir}")

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. 收集文献与模板
    literature = _collect_literature(source_dir)
    templates = _collect_templates(source_dir)
    template_names = [t.name for t in templates]

    # 2. 分块
    chunks = _build_chunks(literature)

    # 3. 嵌入器
    embedder = DeterministicStubEmbedder() if stub else FastEmbedEmbedder()

    # 4. 写 chroma 到临时目录
    work = Path(tempfile.mkdtemp(prefix="frl_build_"))
    try:
        vector_dir = work / "vector_db"
        _write_vector_db(vector_dir, chunks, embedder)

        templates_dir = work / "templates"
        templates_dir.mkdir(exist_ok=True)
        for t in templates:
            shutil.copy2(t, templates_dir / t.name)

        # 5. manifest（sha256 暂为占位，zip 成形后填独立 manifest）
        version = _content_version(chunks, template_names)
        manifest = {
            "version": version,
            "sha256": "",  # 占位；权威值写入独立 manifest.json
            "built_at": _utcnow_iso(),
            "chunk_count": len(chunks),
            "templates": template_names,
        }

        # 6. 打 zip（manifest.json + templates/ + vector_db/）
        zip_path = out_path / "pack.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
            _add_dir_to_zip(zf, templates_dir, "templates")
            _add_dir_to_zip(zf, vector_dir, "vector_db")

        # 7. 计算 zip sha256，回填独立 manifest
        h = _file_sha256(zip_path)
        manifest["sha256"] = h
        (out_path / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return manifest
    finally:
        shutil.rmtree(work, ignore_errors=True)
        gc.collect()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="构建通用知识包")
    parser.add_argument("--out", required=True, help="输出目录")
    parser.add_argument("--source", default=None, help="源目录（默认 generic_knowledge/）")
    parser.add_argument("--stub", action="store_true", help="使用确定性假向量（不下载模型）")
    args = parser.parse_args()

    manifest = build_pack(args.out, source=args.source, stub=args.stub)
    print(f"pack.zip + manifest.json -> {args.out}")
    print(f"version={manifest['version']} sha256={manifest['sha256'][:16]}... chunks={manifest['chunk_count']} templates={len(manifest['templates'])}")


if __name__ == "__main__":
    main()
