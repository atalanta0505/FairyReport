"""ChromaDB stores for project materials and optional local shared sources."""
import logging
import os
import hashlib

# ⚠️ Must be set BEFORE importing sentence_transformers, otherwise hf-mirror does not take effect
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

import chromadb
from sentence_transformers import SentenceTransformer
from config import (
    GENERIC_DB_DIR, EMBED_MODEL_NAME,
    RAG_RESULTS_PER_SOURCE,
    RERANK_ENABLED, RERANK_MODEL, RERANK_BASE_URL,
)

_logger = logging.getLogger(__name__)


def _sanitize_project_name(name: str) -> str:
    """ChromaDB collection names only allow [a-zA-Z0-9._-]; Chinese project names are hashed."""
    if name.isascii() and all(c.isalnum() or c in "._-" for c in name):
        return name
    return f"proj_{hashlib.md5(name.encode()).hexdigest()[:16]}"


class KnowledgeBase:
    # ── Module-level cache: avoid reloading the embedding model on every initialization ──
    _embedder = None
    _instance_cache: dict[str, 'KnowledgeBase'] = {}

    @classmethod
    def _get_embedder(cls):
        if cls._embedder is None:
            try:
                cls._embedder = SentenceTransformer(
                    EMBED_MODEL_NAME,
                    local_files_only=True,
                )
            except OSError:
                # Model not cached locally; download via mirror (HuggingFace unavailable in mainland China)
                cls._embedder = SentenceTransformer(EMBED_MODEL_NAME)
        return cls._embedder

    @classmethod
    def get_instance(cls, project_name: str, project_db_path: str):
        """Get or create a KB instance (singleton pattern).

        If the cache already has an instance for this project, return it directly
        without re-initializing.
        """
        if project_name in cls._instance_cache:
            return cls._instance_cache[project_name]
        instance = cls(project_name, project_db_path)
        cls._instance_cache[project_name] = instance
        return instance

    def close(self):
        """Close the ChromaDB client, release the SQLite file lock."""
        try:
            del self.project_collection
        except Exception as e:
            _logger.debug("Releasing project_collection when closing KB failed: %s", e)
        try:
            del self.generic_collection
        except Exception as e:
            _logger.debug("Releasing generic_collection when closing KB failed: %s", e)
        try:
            del self.client
        except Exception as e:
            _logger.debug("Releasing client when closing KB failed: %s", e)

    @classmethod
    def close_instance(cls, project_name: str):
        """Close and clean up the KB cache for the given project.

        Note: .close() must be called on the instance first to release the file lock;
        this method only clears the reference cache on the Python side.
        """
        if project_name in cls._instance_cache:
            del cls._instance_cache[project_name]
            import gc
            gc.collect()

    def __init__(self, project_name: str, project_db_path: str):
        self.project_name = project_name
        self.client = chromadb.PersistentClient(path=project_db_path)

        # Use the cached embedding model (no network access)
        self.embedder = self._get_embedder()

        # Collection name: Chinese project names need to be converted to ASCII
        collection_name = _sanitize_project_name(project_name)

        # ── Project collection ──
        self.project_collection = self.client.get_or_create_collection(
            collection_name
        )

        # ── Generic collection (read-only) ──
        self.generic_collection = self._load_generic_collection()

    # ── Load generic store ──
    @staticmethod
    def _load_generic_collection():
        if not GENERIC_DB_DIR.exists():
            return None
        try:
            generic_client = chromadb.PersistentClient(path=str(GENERIC_DB_DIR))
            return generic_client.get_collection("generic_kb")
        except Exception as e:
            _logger.warning("Failed to load generic knowledge base: %s", e)
            return None

    # ── Ingest (project materials) ──
    def ingest_project(self, chunks: list):
        """
        chunks: [{"text": "...", "source": "filename.docx", "source_id": "subdir/filename.docx", "doc_id": 1}, ...]

        Uses source_id for unique chroma IDs to prevent collisions between files with same basename
        in different subdirectories. Uses upsert for idempotent re-ingestion.
        """
        if not chunks:
            return

        texts = [c["text"] for c in chunks]
        embeddings = self.embedder.encode(texts, show_progress_bar=True).tolist()

        # Build stable unique IDs using source_id (or fall back to source for old data)
        ids = []
        metadatas = []
        for i, c in enumerate(chunks):
            sid = c.get("source_id", c.get("source", "unknown"))
            ids.append(f"proj_{sid}_{i}")
            metadatas.append({
                "source": c["source"],
                "source_id": sid,
                "doc_id": c.get("doc_id", -1),
                "index": i
            })

        # Use upsert to be idempotent — safe to re-ingest same chunks
        self.project_collection.upsert(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )

    # ── Rerank (optional, using SiliconFlow BGE Reranker) ──
    def _rerank(self, query: str, documents: list, top_n: int) -> list:
        """Rerank retrieval results, return top_n items with relevance_score > 0."""
        import requests
        import json

        api_key = os.getenv("SILICONFLOW_API_KEY")
        if not api_key:
            return documents[:top_n]

        try:
            payload = {
                "model": RERANK_MODEL,
                "query": query,
                "documents": documents,
                "top_n": top_n,
            }
            resp = requests.post(
                RERANK_BASE_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                # Sort by relevance_score, filter score == 0
                ordered = sorted(
                    [r for r in results if r.get("relevance_score", 0) > 0],
                    key=lambda x: x.get("relevance_score", 0),
                    reverse=True,
                )
                return [documents[r["index"]] for r in ordered]
        except Exception as e:
            _logger.warning("Rerank request failed: %s", e)

        return documents[:top_n]

    # ── Delete chunks from project store by source ──
    def delete_by_source(self, source_name: str, match_by_source_id: bool = True):
        """Delete all chunks of the given source from the project collection.

        Args:
            source_name: source identifier to match.
            match_by_source_id: if True, match against source_id metadata field;
                if False, fall back to matching against source (basename) for legacy data.
        """
        if self.project_collection.count() == 0:
            return
        try:
            all_data = self.project_collection.get()
            ids_to_delete = []
            for i, meta in enumerate(all_data.get("metadatas", [])):
                if not meta:
                    continue
                if match_by_source_id:
                    matched = (meta.get("source_id") == source_name or
                              (not meta.get("source_id") and meta.get("source") == source_name))
                else:
                    matched = (meta.get("source") == source_name)
                if matched:
                    ids_to_delete.append(all_data["ids"][i])
            if ids_to_delete:
                self.project_collection.delete(ids=ids_to_delete)
        except Exception as e:
            _logger.warning("Failed to delete chunks of source '%s': %s", source_name, e)

    # ── Dual-source retrieval ──
    def query(self, query_text: str, n_results: int = None,
              include_generic: bool = True):
        """Return formatted retrieval result string.

        Project and local shared material use the 【源:filename】 format.
        If RERANK_ENABLED=True, the retrieval results are reranked.

        Args:
            include_generic: whether to also search the optional local shared knowledge base.
        """
        if n_results is None:
            n_results = RAG_RESULTS_PER_SOURCE

        query_emb = self.embedder.encode([query_text]).tolist()
        results = []

        # Project store -> 【源:filename】 format
        if self.project_collection.count() > 0:
            try:
                proj_res = self.project_collection.query(
                    query_embeddings=query_emb,
                    n_results=n_results,
                )
                proj_docs = list(proj_res["documents"][0])
                proj_metas = list(proj_res["metadatas"][0])

                # Rerank (optional)
                if RERANK_ENABLED:
                    proj_docs = self._rerank(query_text, proj_docs, n_results)
                    # Simply match back to metadata (order changed after rerank)
                    # Match by document text
                    doc_to_meta = {}
                    for i, doc in enumerate(proj_res["documents"][0]):
                        doc_to_meta[doc] = proj_metas[i]
                    proj_metas = [doc_to_meta.get(d, {}) for d in proj_docs]

                for doc, meta in zip(proj_docs, proj_metas):
                    source_name = meta.get("source", "未知")
                    citation = f"【源:{source_name}】"
                    results.append(f"{citation}: {doc}")
            except Exception as e:
                _logger.warning("Project store retrieval failed: %s", e)

        # Optional local shared store. Sources remain attributable by filename.
        if include_generic and self.generic_collection and self.generic_collection.count() > 0:
            try:
                gen_res = self.generic_collection.query(
                    query_embeddings=query_emb,
                    n_results=n_results,
                )
                gen_docs = list(gen_res["documents"][0])
                gen_metas = list(gen_res["metadatas"][0])

                # Rerank (optional)
                if RERANK_ENABLED:
                    gen_docs = self._rerank(query_text, gen_docs, n_results)
                    doc_to_meta = {}
                    for i, doc in enumerate(gen_res["documents"][0]):
                        doc_to_meta[doc] = gen_metas[i]
                    gen_metas = [doc_to_meta.get(d, {}) for d in gen_docs]

                for doc, meta in zip(gen_docs, gen_metas):
                    source_name = meta.get("source", "本地共享资料")
                    results.append(f"【源:{source_name}】: {doc}")
            except Exception as e:
                _logger.warning("Generic store retrieval failed: %s", e)

        return "\n\n---\n\n".join(results) if results else "（无相关参考资料）"
