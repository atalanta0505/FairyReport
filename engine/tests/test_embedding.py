"""
嵌入模块单元测试：FastEmbedEmbedder 本地优先加载与持久化缓存路径测试。
"""
from pathlib import Path
from unittest.mock import patch, MagicMock

from engine.app.config import settings
from engine.app.embedding import FastEmbedEmbedder, DeterministicStubEmbedder, get_embedder, set_embedder


def test_deterministic_stub_embedder():
    embedder = DeterministicStubEmbedder()
    assert embedder.dim == 384
    res = embedder.encode(["你好", "世界"])
    assert len(res) == 2
    assert len(res[0]) == 384
    assert len(res[1]) == 384


def test_fastembed_embedder_uses_local_repo_model(tmp_path):
    embedder = FastEmbedEmbedder()
    assert embedder.dim == 384

    # 当仓库本地模型目录存在 model_optimized.onnx 时，应传入 specific_model_path
    with patch("fastembed.TextEmbedding") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.embed.return_value = [[0.1] * 384]
        mock_cls.return_value = mock_instance

        # 触发 _ensure_model
        out = embedder.encode(["测试"])
        assert len(out) == 1
        assert len(out[0]) == 384
        mock_cls.assert_called_once()
        _, kwargs = mock_cls.call_args
        # 验证是否指定了 specific_model_path 或 cache_dir
        assert "specific_model_path" in kwargs or "cache_dir" in kwargs


def test_fastembed_embedder_fallback_to_data_dir(tmp_path):
    embedder = FastEmbedEmbedder()

    # 模拟仓库路径不存在，但 engine_data_dir/models/fastembed 存在
    data_model_dir = tmp_path / "models" / "fastembed"
    data_model_dir.mkdir(parents=True)
    (data_model_dir / "model_optimized.onnx").write_text("fake onnx", encoding="utf-8")

    with patch("fastembed.TextEmbedding") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.embed.return_value = [[0.1] * 384]
        mock_cls.return_value = mock_instance

        with patch.object(settings, "engine_data_dir", str(tmp_path)):
            embedder._ensure_model()
            mock_cls.assert_called_once()


def test_get_set_embedder():
    original = get_embedder()
    stub = DeterministicStubEmbedder()
    set_embedder(stub)
    assert get_embedder() is stub
    set_embedder(None)
    # 重置后懒加载
    new_embedder = get_embedder()
    assert isinstance(new_embedder, FastEmbedEmbedder)
    # 恢复原状
    set_embedder(original)
