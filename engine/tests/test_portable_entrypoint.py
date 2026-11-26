"""
便携模式数据目录解析与入口分发（FastAPI / MCP Server）单元测试。
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

from engine.app.config import _default_engine_data_dir
from engine.entrypoint import dispatch


def test_default_engine_data_dir_prefers_env(monkeypatch, tmp_path: Path):
    custom_dir = tmp_path / "custom_data"
    monkeypatch.setenv("ENGINE_DATA_DIR", str(custom_dir))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "fairyreport-engine.exe"))
    (tmp_path / ".portable").write_text("", encoding="utf-8")

    assert _default_engine_data_dir() == str(custom_dir)


def test_default_engine_data_dir_frozen_portable_mode(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("ENGINE_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    portable_dir = tmp_path / "portable_bundle"
    portable_dir.mkdir()
    (portable_dir / ".portable").write_text("", encoding="utf-8")
    fake_exe = portable_dir / "fairyreport-engine.exe"
    fake_exe.write_text("", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))

    assert Path(_default_engine_data_dir()) == portable_dir / "data"


def test_default_engine_data_dir_frozen_without_portable_falls_back(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("ENGINE_DATA_DIR", raising=False)
    local_app = tmp_path / "localappdata"
    monkeypatch.setenv("LOCALAPPDATA", str(local_app))
    non_portable_dir = tmp_path / "installed_dir"
    non_portable_dir.mkdir()
    fake_exe = non_portable_dir / "fairyreport-engine.exe"
    fake_exe.write_text("", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))

    assert Path(_default_engine_data_dir()) == local_app / "FairyReport"


def test_entrypoint_dispatch_routes_to_mcp_and_strips_flag(monkeypatch):
    captured: dict[str, list[str]] = {}

    fake_mcp = types.ModuleType("engine.mcp_server")

    def _fake_mcp_main():
        captured["argv"] = list(sys.argv)

    fake_mcp.main = _fake_mcp_main  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "engine.mcp_server", fake_mcp)
    monkeypatch.setattr(sys, "argv", ["fairyreport-engine.exe"])

    dispatch(["--mcp", "--transport", "streamable-http", "--port", "8002"])

    assert captured["argv"] == [
        "fairyreport-engine.exe",
        "--transport",
        "streamable-http",
        "--port",
        "8002",
    ]


def test_entrypoint_dispatch_routes_to_fastapi_engine_by_default(monkeypatch):
    captured: dict[str, list[str]] = {}

    fake_main = types.ModuleType("engine.app.main")

    def _fake_engine_main():
        captured["argv"] = list(sys.argv)

    fake_main.main = _fake_engine_main  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "engine.app.main", fake_main)
    monkeypatch.setattr(sys, "argv", ["fairyreport-engine.exe"])

    dispatch(["--port", "8001"])

    assert captured["argv"] == ["fairyreport-engine.exe", "--port", "8001"]
