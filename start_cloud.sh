#!/usr/bin/env bash
# ── FairyReport 云端服务启动脚本 (Linux / macOS) ──
set -e

PORT=${PORT:-8001}
HOST=${HOST:-0.0.0.0}
DATA_DIR=${ENGINE_DATA_DIR:-./data}

export HOST
export PORT
export ENGINE_DATA_DIR="$DATA_DIR"

echo "=================================================="
echo "  FairyReport 云端服务启动中..."
echo "  主机: $HOST"
echo "  端口: $PORT"
echo "  数据目录: $ENGINE_DATA_DIR"
echo "=================================================="

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "错误：未检测到 python3，请先安装 Python 3.10+"
    exit 1
fi

# 启动一体化 FastAPI 引擎（自动托管 API 与前端 Web）
python3 -m engine.app.main --host "$HOST" --port "$PORT"
