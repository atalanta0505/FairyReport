# 任务合同 V2-T7 v1 — 认证服务部署上云（跑通模式）

- 状态：DRAFT（待产品负责人批准）
- 产品决定来源：`00-product-decision-v4.md` D19、O3；`docs/dev-flow/infra.md`
- 精确起始 SHA：本合同提交后的 master HEAD
- 工作树门禁：`git status --short` 必须干净
- 性质：运维+轻代码切片；服务器操作由协调者经 SSH（frl-server）执行，非 Maker 会话

## 1. 背景与目标

把 T1 认证服务 + T4 知识包下发部署到 101.42.9.223，桌面端（T8）可对其完成真实注册/登录与知识包下载。本切片为"跑通模式"：HTTP、单节点、SQLite。

## 2. 唯一主要行为变化

**公网可访问认证与知识包服务：/api/health、注册/登录（真实 QQ 邮件验证码）、/api/pack/*（JWT 门控）经 http://101.42.9.223 可用。**

## 3. 明确不做

- 不做 HTTPS（O3：发布前自签+客户端固定；本轮 HTTP 为已知悉临时风险）
- 不做自动更新/监控/备份脚本（备份列发布前；本轮仅人工知晓数据在服务器卷内）
- 不触碰现有服务（openclaw-gateway、:8000 python、frps:7000）

## 4. 实现导航

- `backend/docker-compose.yml` 重构：移除 postgres 服务；api 服务环境变量 DATABASE_URL=sqlite:////data/frl.db（卷挂载 ./data）；JWT_SECRET 与 QQ SMTP 变量经 .env（服务器本地，不入仓库）；nginx 服务 80→api:8010；api 内部端口 8010（避开现有 :8000）
- `backend/Dockerfile` 保持/微调（python:3.12-slim 基础，装 backend/requirements.txt）
- 真实知识包：协调者在本机执行 `python -m engine.tools.build_generic_pack --out <dir>`（首次自动下载 fastembed 模型，需征询）→ scp pack.zip+manifest.json 至服务器 PACK_DIR（compose 卷挂载 ./pack）
- 部署：scp backend/ → 服务器；docker compose up -d --build；健康检查
- E2E：协调者 curl 注册流程；验证码由产品负责人读邮箱口述（一次性测试码，可经聊天）

## 5. 允许修改

- `backend/**`（compose/Dockerfile/config 部署适配；不改 T1 业务逻辑与测试）
- `docs/dev-flow/tasks/V2-T7/**`
- 服务器侧文件（不入仓库）

## 6. 禁止修改

- engine/**、根目录产品文件、generic_knowledge/**、根 requirements.txt、.opencode/、AGENTS.md
- 服务器现有服务与端口（7000/8000/18789-91）

## 7. 人工项（产品负责人）

1. 安装 Docker（dnf，OpenCloudOS）并确认 `docker --version`
2. 安全组放行 80
3. 经腾讯云控制台/自行 SSH 在服务器写入 backend/.env：QQ_SMTP_USER、QQ_SMTP_AUTH_CODE、JWT_SECRET（协调者提供生成命令与占位模板，**值不经聊天**）
4. 注册 E2E 时读测试邮箱验证码口述给协调者

## 8. 验收标准

- [ ] `curl http://101.42.9.223/api/health` → 200
- [ ] 真实注册：send-code → 邮箱收码 → register → login 拿 JWT → /api/users/me 200
- [ ] 带 JWT `GET /api/pack/manifest` 200 且与本机 manifest 一致；download 200 且 sha256 一致
- [ ] 无 JWT → pack 401
- [ ] 服务器 `free -h` 可用内存 > 300MB；现有服务端口仍在（ss -tlnp 比对）
- [ ] backend 101 测试本地仍全绿（部署适配不破坏单测）

## 9. 快速验证（协调者执行）

1. ssh frl-server "ss -tlnp | grep -E ':80|:8010'" 与 docker compose ps
2. 本机 curl 三连（health/register/login/pack）

## 10. 停止条件

- Docker 安装失败（人工项未决）；端口冲突；构建两次失败；OOM 或现有服务受影响 → 停止报告

## 11. 候选提交要求

- 仓库内变更（compose/Dockerfile 等）单独候选提交；服务器操作记录写入 rounds/01/maker-completion.md（本切片"Maker"=协调者，说明中注明）；Checker 仍独立验收（SSH 只读核查+curl）
- 不 amend、不 rebase；推送需另行许可
