# 运行环境 — 腾讯云轻量服务器

- 登记日期：2026-08-19（只读侦察所得）

## 实例

| 项 | 值 |
|---|---|
| 公网 IP | 101.42.9.223（北京三区） |
| 实例 ID | lhins-i40u4w3o（名称 OpenClaw(Clawdbot)-mkbU） |
| 规格 | 2 核 / **2GB** 内存 / 50GB SSD（已用 20G）/ 4Mbps / 300GB 月流量 |
| 到期 | 2027-02-03 |
| 系统 | OpenCloudOS 9.4（内核 6.6.117，RPM 系，非 Ubuntu） |
| SSH | root + 公钥（id_ed25519_gitee 已加入 authorized_keys，已验证可登录；本机别名 `frl-server`） |
| Docker | **未安装**（部署切片前由产品负责人安装，dnf 方式） |

## 现状（非空闲服务器）

侦察时已有服务在运行（部署时不得触碰，端口须避开）：

- `openclaw-gateway`：127.0.0.1:18789/18791/37481
- `python3` 服务：**0.0.0.0:8000**（注意：uvicorn 默认端口即 8000，本服务内部端口改用 8010 并经 nginx 80/443 出口）
- `frps`：0.0.0.0:7000

## 资源风险（待产品决定）

- 内存 2GB，已用约 1GB，可用约 900MB + 8GB swap。FairyReport 栈（FastAPI+Postgres+Chroma+ONNX 嵌入）无法安全装入。
- 选项：① 升配至 ≥4GB（推荐，轻量控制台"升级配置"）；② 换/加服务器；③ 极限精简栈（SQLite 替 Postgres 等）并承担 OOM 风险。

## 部署约定（暂定）

- Docker Compose 部署（发行版无关）；内部端口 8010；nginx 反代 80/443；
- HTTPS 方案见产品决定 v2（O3：自签+客户端固定，或另行决定）；
- 安全组：22 已通；80/443 部署切片时放行。
