"""
双源 RAG 检索 — 项目库（engine materials vectorstore）+ 已安装通用包（generic collection）。

引用格式与根目录 kb.py 一致：项目资料【源:filename】、通用知识 [Z]。
嵌入走可注入接口（engine.app.embedding.get_embedder）。
"""
import logging

from ..config import settings
from ..embedding import get_embedder
from ..generic.store import GenericStore
from ..materials.vectorstore import ProjectVectorStore
from .prompts import RAG_RESULTS_PER_SOURCE

_logger = logging.getLogger(__name__)


def query_rag(
    project_name: str,
    query_text: str,
    n_results: int = None,
    include_generic: bool = True,
) -> str:
    """双源 RAG 检索，返回格式化字符串。

    项目库 → 【源:filename】: doc
    通用库 → [Z]: doc
    无结果 → "（无相关参考资料）"
    """
    if n_results is None:
        n_results = RAG_RESULTS_PER_SOURCE

    results: list[str] = []
    emb = None

    # ── 项目库 ──
    try:
        if project_name and settings.vector_dir(project_name).exists():
            store = ProjectVectorStore.get(
                project_name, settings.vector_dir(project_name)
            )
            if store.count() > 0:
                emb = get_embedder().encode([query_text])[0]
                res = store.collection.query(query_embeddings=[emb], n_results=n_results)
                docs = (res.get("documents") or [[]])[0]
                metas = (res.get("metadatas") or [[]])[0]
                for doc, meta in zip(docs, metas):
                    meta = meta or {}
                    source = meta.get("source", "未知")
                    results.append(f"【源:{source}】: {doc}")
    except Exception as e:
        _logger.warning("项目库检索失败: %s", e)

    # ── 通用库（已安装才检索）──
    if include_generic:
        try:
            gen_col = GenericStore._get_collection()
            if gen_col and gen_col.count() > 0:
                if emb is None:
                    emb = get_embedder().encode([query_text])[0]
                res = gen_col.query(query_embeddings=[emb], n_results=n_results)
                docs = (res.get("documents") or [[]])[0]
                for doc in docs:
                    results.append(f"[Z]: {doc}")
        except Exception as e:
            _logger.warning("通用库检索失败: %s", e)

    return "\n\n---\n\n".join(results) if results else "（无相关参考资料）"
