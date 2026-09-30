# ── FairyReport 云端 Web 部署 Dockerfile ──
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 环境变量配置
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8001 \
    ENGINE_DATA_DIR=/app/data

# 安装基础系统依赖（curl 用于健康检查）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 核心依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝核心计算引擎与模型资源
COPY engine/ engine/
COPY generic_knowledge/ generic_knowledge/
COPY pattern/ pattern/
COPY desktop/dist/ desktop/dist/
COPY data/fastembed_models/ data/fastembed_models/

# 创建持久化数据目录
RUN mkdir -p /app/data

# 暴露单端口服务（API + Web 界面一体化）
EXPOSE 8001

# 健康检查探针
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 启动服务
CMD ["python", "-m", "engine.app.main", "--host", "0.0.0.0", "--port", "8001"]
