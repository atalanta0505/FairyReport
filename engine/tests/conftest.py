"""
测试夹具：确定性假嵌入 + tmp 数据目录 + FastAPI TestClient。

全部测试不下载真实模型、不联网、不污染用户数据目录。
"""
import os
import tempfile

# 在导入 engine 之前设定独立临时数据目录
_TMP_DIR = tempfile.mkdtemp(prefix="frl_engine_test_")
os.environ.setdefault("ENGINE_DATA_DIR", _TMP_DIR)

import gc  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from engine.app import db  # noqa: E402
from engine.app.config import settings  # noqa: E402
from engine.app.embedding import DeterministicStubEmbedder, set_embedder  # noqa: E402
from engine.app.generic.store import GenericStore  # noqa: E402
from engine.app.main import app  # noqa: E402
from engine.app.materials.vectorstore import ProjectVectorStore  # noqa: E402

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture(autouse=True)
def client(tmp_path):
    """每用例一个全新 tmp 数据目录 + DB 表重置 + 向量库缓存清理，返回 TestClient。

    用 per-test tmp 目录避免 chroma sqlite 锁导致跨用例残留向量（不依赖 rmtree 清锁）。
    """
    # 注入确定性假嵌入（不下载模型）
    set_embedder(DeterministicStubEmbedder())

    # 每用例独立数据目录：文件系统完全隔离
    settings.engine_data_dir = str(tmp_path)
    (tmp_path / "projects").mkdir(parents=True, exist_ok=True)

    # 重置 DB 表（DB 引擎为会话级，靠 drop/create 隔离）
    db.Base.metadata.drop_all(bind=db.engine)
    db.Base.metadata.create_all(bind=db.engine)

    # 清向量库缓存 + 释放上一用例可能的 sqlite 锁
    ProjectVectorStore._cache.clear()
    GenericStore.close()
    # 重置通用知识 HTTP 传输层（避免泄漏 MockTransport）
    from engine.app.generic.store import set_transport

    set_transport(None)
    gc.collect()

    with TestClient(app) as c:
        yield c

    # 用例后再次清理缓存
    ProjectVectorStore._cache.clear()
    GenericStore.close()
    set_transport(None)
    gc.collect()


def fixture_path(name: str) -> str:
    """返回 fixtures 目录下文件绝对路径。"""
    return os.path.join(FIXTURES_DIR, name)
