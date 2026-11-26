"""
FairyReport Engine 入口脚本（为 PyInstaller 与独立启动提供顶层包装）。

同一可执行文件支持双运行模式：
  - 桌面端 FastAPI 后端引擎（默认）：
      fairyreport-engine.exe [--host 127.0.0.1] [--port 8001]
  - 零 Python 环境 MCP Server 模式（传入 --mcp）：
      fairyreport-engine.exe --mcp
      fairyreport-engine.exe --mcp --transport streamable-http --port 8002
"""
import sys
from pathlib import Path

# 确保包含 engine 所在根目录
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


def dispatch(argv: list[str] | None = None) -> None:
    """根据启动参数懒加载并分发至 MCP Server 或 FastAPI 后端引擎。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--mcp" in args:
        args.remove("--mcp")
        sys.argv = [sys.argv[0], *args]
        from engine.mcp_server import main as mcp_main

        mcp_main()
        return

    if argv is not None:
        sys.argv = [sys.argv[0], *args]
    from engine.app.main import main as engine_main

    engine_main()


if __name__ == "__main__":
    dispatch()
