# ── FairyReport Cloud Backend Engine Dockerfile ──
FROM python:3.11-slim

# 设置 Python 环境
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_ENDPOINT=https://hf-mirror.com \
    ENGINE_DATA_DIR=/app/data \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

# 换国内源加速 apt（适配 Debian 12/13）
RUN sed -i 's|deb.debian.org|mirrors.tencentyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.tencentyun.com|g' /etc/apt/sources.list 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# 安装系统工具（含 curl 用于 Docker 健康探针）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖清单，利用 Docker 分层缓存机制加速构建
COPY requirements-engine.txt .
RUN pip install --no-cache-dir -i https://mirrors.tencentyun.com/pypi/simple/ -r requirements-engine.txt || \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements-engine.txt

# 复制代码与只读资源库
COPY engine/ /app/engine/
COPY generic_knowledge/ /app/generic_knowledge/

# 创建持久化数据挂载目录
RUN mkdir -p /app/data

EXPOSE 8000

# 健康检查探针
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动引擎服务
CMD ["uvicorn", "engine.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
