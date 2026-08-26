"""
资料向量库 — 移植自根目录 kb.py（chromadb PersistentClient，每项目独立目录）。

upsert 以 source_id 为键构建稳定 ID，保证幂等；delete_by_source 按 source_id 删除。
"""
import gc
import hashlib
import logging
import os
import shutil
import time
from pathlib import Path

import chromadb

from ..config import settings

_logger = logging.getLogger(__name__)


def _sanitize_collection_name(name: str) -> str:
    """ChromaDB collection 名规则：3-512 字符、[a-zA-Z0-9._-]、首尾为字母数字。

    非 ASCII、过短或首尾非法的名称哈希为 proj_<md5>（恒满足规则）。
    """
    if (
        name.isascii()
        and 3 <= len(name) <= 512
        and all(c.isalnum() or c in "._-" for c in name)
        and name[0].isalnum()
        and name[-1].isalnum()
    ):
        return name
    return f"proj_{hashlib.md5(name.encode()).hexdigest()[:16]}"


class ProjectVectorStore:
    """单个项目的向量库（单例缓存，避免重复初始化）。"""

    _cache: dict[str, "ProjectVectorStore"] = {}

    @classmethod
    def get(cls, project_name: str, vector_dir) -> "ProjectVectorStore":
        """获取或创建某项目的向量库实例。"""
        key = project_name
        if key in cls._cache:
            return cls._cache[key]
        inst = cls(project_name, str(vector_dir))
        cls._cache[key] = inst
        return inst

    def __init__(self, project_name: str, vector_dir: str) -> None:
        self.project_name = project_name
        self.vector_dir = vector_dir
        self.client = chromadb.PersistentClient(path=vector_dir)
        self.collection = self.client.get_or_create_collection(
            _sanitize_collection_name(project_name)
        )

    def upsert(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        """upsert 幂等写入（source_id 为键构建稳定 ID）。

        chunks: [{"text", "source", "source_id", "doc_id", "index"}, ...]
        embeddings: 与 chunks 等长的向量列表。
        """
        if not chunks:
            return

        texts = [c["text"] for c in chunks]
        ids = []
        metadatas = []
        for i, c in enumerate(chunks):
            sid = c.get("source_id", c.get("source", "unknown"))
            ids.append(f"{sid}_{i}")
            metadatas.append(
                {
                    "source": c.get("source", ""),
                    "source_id": sid,
                    "doc_id": c.get("doc_id", -1),
                    "index": i,
                }
            )

        self.collection.upsert(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )

    def delete_by_source(self, source_id: str) -> None:
        """按 source_id 删除该项目所有向量。"""
        try:
            res = self.collection.get(where={"source_id": source_id})
            ids_to_delete = res.get("ids", [])
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
        except Exception as e:
            _logger.warning("Failed to delete chunks of source '%s': %s", source_id, e)

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception:
            return 0

    def close(self) -> None:
        """关闭客户端释放文件句柄。"""
        if hasattr(self, "client") and self.client is not None:
            try:
                if hasattr(self.client, "close"):
                    self.client.close()
            except Exception:
                pass
        if hasattr(self, "collection") and self.collection is not None:
            try:
                del self.collection
            except Exception:
                pass
            self.collection = None
        if hasattr(self, "client") and self.client is not None:
            try:
                del self.client
            except Exception:
                pass
            self.client = None

    @classmethod
    def close_project(cls, project_name: str) -> None:
        """关闭并清理某项目的缓存实例（释放 sqlite 文件锁）。"""
        if project_name in cls._cache:
            inst = cls._cache.pop(project_name)
            inst.close()
            gc.collect()


def safe_rmtree(path, ignore_errors: bool = True) -> None:
    """Windows 下 chroma 可能短暂持锁，检查路径存在性并重试 5 次退避删除。"""
    if path is None:
        return
    p = Path(path) if not isinstance(path, Path) else path
    if not p.exists():
        return
    for attempt in range(5):
        try:
            shutil.rmtree(p)
            return
        except Exception:
            if attempt == 4 and not ignore_errors:
                raise
            gc.collect()
            time.sleep(0.1)
    if ignore_errors:
        try:
            shutil.rmtree(p, ignore_errors=True)
        except Exception:
            pass


def remove_project_data(project_name: str) -> None:
    """删除项目的全部数据目录（files + vector）。"""
    ProjectVectorStore.close_project(project_name)
    pdir = settings.project_dir(project_name)
    safe_rmtree(pdir, ignore_errors=True)
