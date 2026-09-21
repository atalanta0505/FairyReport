"""
FairyReport 本地引擎 — 嵌入封装（可注入/可打桩）。

默认实现走 fastembed（sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2，dim=384）。
测试通过 set_embedder() 注入确定性假向量，不下载模型、不联网。
"""
from __future__ import annotations

import hashlib
import os
from typing import Protocol

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


class Embedder(Protocol):
    """嵌入器协议。"""

    dim: int

    def encode(self, texts: list[str]) -> list[list[float]]:
        """返回与 texts 等长的向量列表（每向量 dim 维）。"""
        ...


class FastEmbedEmbedder:
    """fastembed 真实嵌入器（懒加载，首次 encode 时才加载模型）。"""

    dim = 384

    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2") -> None:
        self._model_name = model_name
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from pathlib import Path
            from fastembed import TextEmbedding
            from .config import settings

            import sys

            specific_path = None

            # 0. 优先检测 PyInstaller 打包内置目录或同级目录
            if getattr(sys, "frozen", False):
                bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
                candidates = [
                    bundle_dir / "fastembed_models",
                    bundle_dir / "data" / "fastembed_models",
                    Path(sys.executable).parent / "data" / "fastembed_models",
                    Path(sys.executable).parent / "fastembed_models",
                ]
                for candidate in candidates:
                    if candidate.exists() and (candidate / "model_optimized.onnx").exists():
                        specific_path = str(candidate)
                        break

            # 1. 优先使用仓库内预置或下载好的模型（100% 离线，毫秒级就绪）
            if not specific_path:
                repo_model_dir = Path(__file__).resolve().parent.parent.parent / "data" / "fastembed_models"
                data_model_dir = Path(settings.engine_data_dir) / "models" / "fastembed"

                if repo_model_dir.exists() and (repo_model_dir / "model_optimized.onnx").exists():
                    specific_path = str(repo_model_dir)
                elif data_model_dir.exists() and (data_model_dir / "model_optimized.onnx").exists():
                    specific_path = str(data_model_dir)

            if specific_path:
                self._model = TextEmbedding(model_name=self._model_name, specific_model_path=specific_path)
            else:
                cache_dir = str(Path(settings.engine_data_dir) / "models")
                self._model = TextEmbedding(model_name=self._model_name, cache_dir=cache_dir)

    def encode(self, texts: list[str]) -> list[list[float]]:
        self._ensure_model()
        return [list(map(float, e)) for e in self._model.embed(texts)]


class DeterministicStubEmbedder:
    """确定性假嵌入器：基于文本 SHA-256 生成固定 384 维向量，不联网。"""

    dim = 384

    def encode(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()  # 32 bytes
            base = [(b - 128) / 128.0 for b in h]  # 32 values in [-1, 1]
            vec = (base * (self.dim // 32 + 1))[: self.dim]  # 扩展到 384 维
            out.append(vec)
        return out


# ── 默认嵌入器（懒加载），可被测试替换 ──
_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    """获取当前嵌入器（默认 FastEmbed，测试可替换）。"""
    global _embedder
    if _embedder is None:
        _embedder = FastEmbedEmbedder()
    return _embedder


def set_embedder(embedder: Embedder | None) -> None:
    """注入/重置嵌入器（测试用）。传 None 恢复懒加载默认。"""
    global _embedder
    _embedder = embedder
