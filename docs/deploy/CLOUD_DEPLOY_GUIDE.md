# FairyReport 云端服务快速部署手册 🚀

> **面向系统运维人员与部署工程师的标准化指引**  
> 本手册指导如何在合伙公司的云服务器（Linux 4核8G 推荐配置）上快速部署 FairyReport 核心后端引擎，并配合 Windows 桌面客户端实现协同作业。

---

## 1. 架构与运行逻辑说明

```
┌──────────────────────────────────────┐       ┌─────────────────────────────────────────────────────────┐
│     Windows 客户端 (咨询师工作机)    │       │                 云服务器 (4核 8G)                       │
│                                      │       │                                                         │
│  ┌────────────────────────────────┐  │       │  ┌───────────────────────────────────────────────────┐  │
│  │   FairyReport 桌面端 (.exe)    │  │       │  │             Docker 容器 (fairyreport-engine)      │  │
│  │                                │  │ HTTP  │  │                                                   │  │
│  │  - 本地富文本编辑画布          │──┼───────┼─▶│  - FastAPI 异步核心引擎 (Port: 8000)             │  │
│  │  - 步骤流转导航                │  │ (API) │  │  - ChromaDB 嵌入式向量数据库                      │  │
│  │  - 客户端不占算力、轻量免配环境│  │       │  │  - FastEmbed 轻量向量化 (ONNX Runtime)            │  │
│  └────────────────────────────────┘  │       │  │  - 智能 Word / Markdown 成果导出构建器            │  │
│                                      │       │  └─────────────────────────┬─────────────────────────┘  │
└──────────────────────────────────────┘       │                            │                            │
                                               │                            ▼                            │
                                               │                 ┌────────────────────┐                  │
                                               │                 │ 宿主机挂载目录     │                  │
                                               │                 │ ./data (项目底稿、 │                  │
                                               │                 │ 向量索引、终稿成果)│                  │
                                               │                 └────────────────────┘                  │
                                               └─────────────────────────────────────────────────────────┘
```

- **客户端（极度轻量）**：桌面安装包仅 ~10MB，无需在每位咨询师电脑上配置复杂 Python/Torch 环境；
- **云端服务（集中管控）**：AI 检索、底稿解析、报告导出集中运行；大模型 API Key 统一保管在云端，安全防泄密；
- **数据持久化**：项目底稿与向量库挂载在宿主机 `./data` 目录，容器升级、重启数据零丢失。

---

## 2. 云服务器准备工作

### 2.1 端口与网络防火墙（安全组）
在阿里云 / 腾讯云 / 华为云的安全组规则中，放行以下端口入方向：
- **TCP 8000**：FairyReport 后端引擎默认服务端口（来源 IP 可根据需要限制为公司公网 IP 或 0.0.0.0/0 全放行）。

### 2.2 确认 Docker 与 Docker Compose
在云服务器终端执行命令检查环境：
```bash
docker -v
docker compose version
```
> **若未安装 Docker**（Ubuntu / Debian 极速安装命令）：
> ```bash
> curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
> systemctl enable --now docker
> ```

---

## 3. 一键部署流程（3 步走）

### 第一步：获取部署代码
将仓库克隆或将交付代码压缩包上传至云服务器解压：
```bash
cd /opt
# 克隆仓库（或解压上传的代码包）
git clone https://github.com/atalanta0505/FairyReport.git fairyreport
cd fairyreport
```

### 第二步：配置环境变量
复制环境配置文件模板并填入您的 `DEEPSEEK_API_KEY`：
```bash
cp .env.example .env
nano .env  # 或使用 vim .env
```
修改 `.env` 对应行：
```ini
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
*(按 `Ctrl+O` 回车保存，`Ctrl+X` 退出)*

### 第三步：启动容器服务
在项目根目录下执行：
```bash
docker compose up -d --build
```
> 系统将自动完成镜像构建、依赖拉取并后台启动。全程大约需要 2~3 分钟。

---

## 4. 验证服务运行状态

### 4.1 查看容器状态
```bash
docker ps
```
若显示 `fairyreport-engine` 且状态为 `Up (healthy)` 即代表成功启动。

### 4.2 本地与公网健康检查
在服务器本地执行：
```bash
curl http://127.0.0.1:8000/health
```
正常响应：
```json
{"status": "ok", "host": "0.0.0.0"}
```
在您的办公电脑浏览器打开：
`http://<云服务器公网IP>:8000/health`
若正常返回 JSON，说明安全组放行成功，外部可正常连通！

---

## 5. 客户端（桌面软件）连接使用指引

1. 启动安装好的 **FairyReport 桌面端**；
2. 点击右上角 **「设置」**（或在引导页）；
3. 将 **引擎服务地址（Base URL）** 填入云服务器地址：
   `http://<云服务器公网IP>:8000`
4. 状态指示灯变为绿色 **「引擎就绪」**；
5. 即可开启多名团队成员协同编写工程报告！

---

## 6. 常用运维管理命令

- **查看实时运行日志**：
  ```bash
  docker logs -f fairyreport-engine
  ```
- **重启服务**：
  ```bash
  docker compose restart
  ```
- **停止服务**：
  ```bash
  docker compose down
  ```
- **版本更新（拉取新代码后重建）**：
  ```bash
  git pull
  docker compose up -d --build
  ```
- **数据备份**：
  所有项目文件、底稿与数据库均保存在项目根目录下的 `./data` 文件夹内，只需定期打包备份该文件夹即可完成整库全量灾备：
  ```bash
  tar -czvf fairyreport_data_backup_$(date +%Y%m%d).tar.gz data/
  ```

---

## 7. （可选进阶）配置 Nginx 与 HTTPS 域名代理

若合伙公司已有备案域名并希望使用 HTTPS 加密传输，可配置 Nginx 反向代理：

```nginx
server {
    listen 80;
    server_name report.yourcompany.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name report.yourcompany.com;

    ssl_certificate     /etc/nginx/ssl/your_cert.pem;
    ssl_certificate_key /etc/nginx/ssl/your_key.key;

    # 客户端上传大文件底稿支持 (支持高达 200MB 的 PDF/Word 底稿)
    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        
        # 支持 SSE 流式打字与大模型思考流长连接
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 延长长文本深度思考与撰写超时时间（10分钟）
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}
```
配置完成后，桌面客户端的 Base URL 直接填写 `https://report.yourcompany.com` 即可。
