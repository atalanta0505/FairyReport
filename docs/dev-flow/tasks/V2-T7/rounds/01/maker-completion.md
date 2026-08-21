# Maker 完成说明 — V2-T7 第 1 轮（运维切片，协调者代行 Maker）

## 合同与基线

- 有效合同：`docs/dev-flow/tasks/V2-T7/01-planner-task-contract-v1.md`（v2 增补见 01-planner-task-contract-v2.md）
- 起始 SHA：`21b04dc`；仓库侧候选范围：`5da16c0` → `f774f39` → `0dab11d`

## 候选

- 仓库候选 SHA：`0dab11d`（3 提交：部署适配 / fastembed 前缀修复 / pip 镜像）
- 提交标题见 git log；修改文件：backend/docker-compose.yml、backend/Dockerfile、backend/nginx/nginx.conf、engine/app/config.py、engine/app/embedding.py（后两者经产品负责人窄修复指令，v2 合同合法化）

## 服务器侧操作（不入仓库）

- /opt/frl/backend（scp 上传，含 nginx/、pack/、.env 由产品负责人经控制台写入）
- Docker Engine 29.7.2 + compose 5.5.0（产品负责人安装）；daemon.json 配置腾讯内网镜像加速
- `docker compose up -d --build` 起 api+nginx；防火墙 TCP:80 放行（产品负责人操作）

## 快速验证记录

| 项 | 结果 |
|---|---|
| python -m pytest engine/tests backend/tests -q | 101 passed（两次） |
| 公网 /api/health | 200 {"status":"ok"} |
| 真实注册 E2E（QQ 邮箱验证码 841675） | REGISTER/LOGIN/ME 全过 |
| pack manifest/download（JWT） | version=v-e91b59bddd4f；sha256 b3464203…29fe 与本地一致 |
| pack 无 JWT | 401 |
| 服务器内存 | available 770–793Mi > 300MB |
| 现有服务 | :7000/:8000/:18789 均在 |

首次失败记录：fastembed 真实建包报"模型不受支持"（新版需完整 ID）→ 窄修复（产品负责人批准）后成功；docker daemon.json 首次写入因 shell 转义损坏 → 管道重写修复。

## 未执行项（移交）

- HTTPS（O3，发布前）；备份脚本；Word 目视（T9）；真实 LLM 联调（T8/T9）

## 已知风险

- HTTP 明文为产品负责人已知悉的临时风险（跑通模式）
- 测试账号 13476526@qq.com 密码已告知产品负责人，由其处置

## 冻结声明

仓库侧未 amend、未 rebase、未 push；服务器侧配置稳定运行，等待 Checker。
