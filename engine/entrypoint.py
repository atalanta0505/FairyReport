"""
FairyReport Engine 入口脚本（为 PyInstaller 与独立启动提供顶层包装）
"""
import sys
from pathlib import Path

# 确保包含 engine 所在根目录
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from engine.app.main import main

if __name__ == "__main__":
    main()
