"""
通用知识包本地管理 — 下载/校验/原子安装/检索。

引擎凭服务器 URL+JWT 下载通用知识包（sha256 校验、原子安装），安装后可本地检索。
嵌入走可注入接口（engine.app.embedding.get_embedder），测试用确定性假向量不联网。
"""
from __future__ import annotations

import gc
import hashlib
import io
import json
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import chromadb
import httpx

from ..config import settings
from ..embedding import get_embedder
from ..materials.vectorstore import safe_rmtree

GENERIC_COLLECTION = "generic_kb"

# ── 可注入 HTTP 传输层（测试用 MockTransport 替换，不联网）──
_transport: httpx.BaseTransport | None = None


def set_transport(transport: httpx.BaseTransport | None) -> None:
    """注入/重置 HTTP 传输层（测试用）。传 None 恢复默认。"""
    global _transport
    _transport = transport


def get_transport() -> httpx.BaseTransport | None:
    return _transport


# ── 异常 ──
class GenericError(Exception):
    """通用知识模块基类异常。"""


class GenericNotInstalled(GenericError):
    """未安装时检索。"""


class GenericTamperError(GenericError):
    """sha256 校验失败（篡改/损坏）。"""


class GenericServerError(GenericError):
    """与服务器交互失败。"""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


# ── HTTP 下发 ──
def _fetch_manifest(server_url: str, token: str) -> dict:
    try:
        timeout = httpx.Timeout(30.0, connect=15.0)
        with httpx.Client(transport=_transport, timeout=timeout) as c:
            r = c.get(
                f"{server_url.rstrip('/')}/api/pack/manifest",
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        raise GenericServerError(
            e.response.status_code,
            f"manifest 请求失败：{e.response.status_code}",
        )
    except httpx.ConnectTimeout:
        raise GenericServerError(504, f"连接服务器超时（{server_url}），请检查网络连接或服务器地址")
    except httpx.RequestError as e:
        err_str = str(e)
        if "10060" in err_str or "timed out" in err_str.lower():
            raise GenericServerError(504, f"连接服务器超时（{server_url}），请检查网络连接或防火墙")
        raise GenericServerError(502, f"无法连接服务器：{e}")


def _download_pack(server_url: str, token: str) -> bytes:
    try:
        timeout = httpx.Timeout(120.0, connect=15.0)
        with httpx.Client(transport=_transport, timeout=timeout) as c:
            r = c.get(
                f"{server_url.rstrip('/')}/api/pack/download",
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            return r.content
    except httpx.HTTPStatusError as e:
        raise GenericServerError(
            e.response.status_code,
            f"download 请求失败：{e.response.status_code}",
        )
    except httpx.ConnectTimeout:
        raise GenericServerError(504, f"下载知识包连接超时（{server_url}）")
    except httpx.RequestError as e:
        err_str = str(e)
        if "10060" in err_str or "timed out" in err_str.lower():
            raise GenericServerError(504, f"连接服务器超时（{server_url}）")
        raise GenericServerError(502, f"无法连接服务器：{e}")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class GenericStore:
    """通用知识包本地存储与检索（模块级单例）。"""

    _collection = None
    _client = None
    _loaded_version: str | None = None

    # ── 路径 ──
    @staticmethod
    def _generic_dir() -> Path:
        return Path(settings.engine_data_dir) / "generic"

    @staticmethod
    def _versions_dir() -> Path:
        return GenericStore._generic_dir() / "versions"

    @staticmethod
    def _state_path() -> Path:
        return GenericStore._generic_dir() / "state.json"

    @staticmethod
    def _version_dir(version: str) -> Path:
        return GenericStore._versions_dir() / version

    @staticmethod
    def _vector_dir(version: str) -> Path:
        return GenericStore._version_dir(version) / "vector_db"

    # ── 状态读写 ──
    @staticmethod
    def _read_state() -> dict | None:
        p = GenericStore._state_path()
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _write_state(state: dict) -> None:
        p = GenericStore._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def _install_from_zip_bytes(cls, zip_bytes: bytes, version: str) -> dict:
        """从 zip 字节解压并原子安装通用知识包。"""
        cls.close()
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            versions_dir = cls._versions_dir()
            versions_dir.mkdir(parents=True, exist_ok=True)
            final_dir = cls._version_dir(version)
            tmp_dir = cls._versions_dir() / f"{version}.tmp"
            safe_rmtree(tmp_dir, ignore_errors=True)
            tmp_dir.mkdir(parents=True, exist_ok=True)
            try:
                zf.extractall(tmp_dir)
                if final_dir.exists():
                    safe_rmtree(final_dir, ignore_errors=True)
                os.replace(tmp_dir, final_dir)
                for child in versions_dir.iterdir():
                    if child.is_dir() and child != final_dir and not child.name.endswith(".tmp"):
                        safe_rmtree(child, ignore_errors=True)
                cls._write_state(
                    {"version": version, "installed_at": _utcnow_iso()}
                )
            except Exception:
                safe_rmtree(tmp_dir, ignore_errors=True)
                raise
        return {"status": "installed", "version": version}

    # ── 对外 API ──
    @classmethod
    def status(cls) -> dict:
        """已装版本/未装。未装时返回 installed: False。"""
        state = cls._read_state()
        if not state:
            return {"installed": False}
        return {
            "installed": True,
            "version": state.get("version"),
            "installed_at": state.get("installed_at"),
        }

    @classmethod
    def close(cls) -> None:
        """释放已加载的 collection/client（释放 sqlite 锁）。"""
        if cls._collection is not None:
            try:
                del cls._collection
            except Exception:
                pass
            cls._collection = None
        if cls._client is not None:
            try:
                del cls._client
            except Exception:
                pass
            cls._client = None
        cls._loaded_version = None
        gc.collect()

    @classmethod
    def _get_collection(cls):
        """加载（如未加载）并返回 generic_kb collection；未装返回 None。"""
        state = cls._read_state()
        if not state:
            return None
        version = state.get("version")
        vdir = cls._vector_dir(version)
        if not vdir.exists():
            return None
        if cls._collection is not None and cls._loaded_version == version:
            return cls._collection
        cls.close()
        client = chromadb.PersistentClient(path=str(vdir))
        cls._client = client
        cls._collection = client.get_or_create_collection(GENERIC_COLLECTION)
        cls._loaded_version = version
        return cls._collection

    @classmethod
    def query(cls, text: str, n: int = 5) -> list[dict]:
        """对已装 generic_kb 本地检索，返回段落列表。"""
        col = cls._get_collection()
        if col is None:
            raise GenericNotInstalled("通用知识未安装")
        emb = get_embedder().encode([text])[0]
        res = col.query(query_embeddings=[emb], n_results=max(1, n))
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        out: list[dict] = []
        for doc, meta in zip(docs, metas):
            meta = meta or {}
            out.append(
                {
                    "text": doc,
                    "source": meta.get("source", ""),
                    "source_id": meta.get("source_id", ""),
                }
            )
        return out

    @classmethod
    def update(cls, server_url: str, token: str) -> dict:
        """拉 manifest → 下载 → sha256 校验 → 原子解压切换 → 加载。

        校验失败 → 抛 GenericTamperError 且不标记已装、不留半装。
        同版本重复 → 幂等（不重下）。
        """
        # 先关已加载 collection，释放锁（替换前）
        cls.close()

        manifest = _fetch_manifest(server_url, token)
        version = manifest.get("version")
        expected_sha = manifest.get("sha256")
        if not version or not expected_sha:
            raise GenericServerError(502, "manifest 字段缺失")

        # 幂等：同版本已装则不重下
        state = cls._read_state()
        if state and state.get("version") == version and cls._version_dir(version).exists():
            return {"status": "already_installed", "version": version}

        # 下载
        zip_bytes = _download_pack(server_url, token)

        # sha256 校验（篡改/损坏 → 拒绝，不留半装）
        actual = hashlib.sha256(zip_bytes).hexdigest()
        if actual != expected_sha:
            raise GenericTamperError(
                f"sha256 校验失败：期望 {expected_sha[:16]}… 实际 {actual[:16]}…"
            )

        # 原子解压切换与安装
        return cls._install_from_zip_bytes(zip_bytes, version=version)

    @classmethod
    def reset(cls) -> None:
        """清空全部通用知识状态与目录（测试/重置用）。"""
        cls.close()
        safe_rmtree(cls._generic_dir(), ignore_errors=True)
