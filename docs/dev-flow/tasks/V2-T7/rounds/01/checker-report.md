# Checker 验收报告 — V2-T7 第 1 轮

- 状态：**FAIL**
- 精确候选 SHA：0dab11da3c1aefd7d7cecef7669cc65737061084
- 依据合同：`tasks/V2-T7/01-planner-task-contract-v1.md`
- 基线 SHA：21b04dc2f0d3c42e9737d6a067f8f9700f456e97

## 独立检查边界

- 独立重跑（Windows PowerShell 5.1，HEAD=0dab11d）：
  - `python -m pytest engine/tests backend/tests -q` → exit 0：**101 passed, 2 warnings**（回归全绿）
- 服务器只读核查（SSH frl-server，全程只读，未改任何服务器文件）：
  - `docker compose ps` → 两容器 Up：`backend-api-1`（Up 20 hours）、`backend-nginx-1`（Up 20 hours, 0.0.0.0:80->80）
  - `free -h` → available **793Mi**（>300MB）
  - `ss -tlnp` → 现有服务仍在：`:7000`(frps)、`:8000`(python3)、`:18789`(openclaw-gatewa)；另新增 `:80`(docker-proxy)
  - `/opt/frl/backend/.env` 存在，键为三（仅 `cut -d= -f1` 取键名，不打印值）：`JWT_SECRET`、`SMTP_USER`、`SMTP_AUTH_CODE`
- 公网黑盒（自执行 curl）：
  - `curl http://101.42.9.223/api/health` → **HTTP/1.1 200** `{"status":"ok"}`
  - 无 JWT `GET /api/pack/manifest` → **HTTP/1.1 401** `{"detail":"未提供认证凭据"}`
  - `POST /api/auth/login`（email=13476526@qq.com）→ 200，取得 access_token
  - 带 JWT `GET /api/pack/manifest` → **200**，`version=v-e91b59bddd4f`、manifest.sha256=`b3464203…ffb29fe`
  - 带 JWT `GET /api/pack/download` → **200**, size=4013820，实测 sha256=`b3464203fd80f050f7f19852e4961a967e6047abfaa63be4288fe66d0ffb29fe`（与 manifest 及预期值一致）
- 未独立验证：真实注册 send-code→邮箱收码→register→login 全链路（需邮箱验证码，验证步骤仅提供 login 账号），§8.2 的注册全流程本次未覆盖。

## 验收标准逐条核对

| 合同标准 | 证据等级(A/B/C/D) | 证据与结论 |
|---|---|---|
| §8.1 `curl /api/health` → 200 | A | 自执行 200 `{"status":"ok"}`。 |
| §8.2 真实注册 send-code→收码→register→login→me | B | 本次仅验证 login 200（有既有测试账号）；send-code/register/邮箱验证码全流程未独立重跑（产品负责人邮箱依赖），不构成本次阻断的新问题，但需人工补验。 |
| §8.3 带 JWT manifest 200 且与本机一致；download 200 且 sha256 一致 | A | manifest 200、version 精确匹配；download 200、sha256 精确匹配预期值。 |
| §8.4 无 JWT → pack 401 | A | 自执行 401。 |
| §8.5 `free -h` >300MB；现有端口仍在 | A | available 793Mi；:7000/:8000/:18789 均在。 |
| §8.6 backend 101 测试本地仍全绿 | A | 自跑 `pytest` 101 passed。 |

## 修改范围复核

- `git diff 21b04dc..0dab11d` 是否严格落在允许路径内：**否**。
  - 允许：`backend/Dockerfile`、`backend/docker-compose.yml`、`backend/nginx/nginx.conf`（3 项，属 backend/**）。
  - 越界：**`engine/app/config.py`、`engine/app/embedding.py`**（提交 `f774f39`，fastembed 模型 ID `paraphrase-multilingual-MiniLM-L12-v2` → `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`）。
- 是否触碰禁止路径：**是** — 合同 §6 明确「禁止修改 engine/**」。
- 父链/提交关系：`git log --oneline 21b04dc..0dab11d` 共 3 提交 `5da16c0`（backend 部署）→ `f774f39`（engine fastembed）→ `0dab11d`（backend Dockerfile）；`0dab11d^ == f774f39`。
- `git status --short` 干净；`git branch -vv` 显示 master 无 upstream（未推送）。

## 阻断项（仅 FAIL）

### 阻断项 1：越界修改 engine/**（合同 §6 违反）

- 合同条目：§5（允许修改仅 backend/** 与 docs/dev-flow/tasks/V2-T7/**）、§6（禁止修改 engine/**）。
- 位置：`engine/app/config.py:35`、`engine/app/embedding.py:28`（提交 `f774f39`）。
- 复现：`git show f774f39 --stat` → `engine/app/config.py | 2 +-`、`engine/app/embedding.py | 4 ++--`；`git diff --name-only 21b04dc..0dab11d` 含 engine/app/config.py、engine/app/embedding.py。
- 为什么阻断交付：本切片为「部署运维切片」，合同明文禁止改动 engine/（§6），并设「越界」为停止条件（§10）。fastembed 模型 ID 补前缀虽为真实建包所需，但属 T3（引擎）产物的行为变更，应在受控合同/返工内处理，而非混入部署候选；混入使验收范围不可控，且违反"候选只含允许路径"的门禁。备份/真实建包即便因此修复，也不应在本切片越界提交。

## 非阻断风险

- `backend/Dockerfile` 基础镜像为 `python:3.14-slim`，与合同 §4 导航「python:3.12-slim 基础」不一致（§4 属"保持/微调"指引，非硬性禁止，故非阻断；建议确认 3.14 与后端依赖兼容性由本地 pytest 已间接佐证）。
- docker-compose 环境变量名用 `SMTP_USER`/`SMTP_AUTH_CODE`（合同 §7 措辞为 QQ_SMTP_USER/QQ_SMTP_AUTH_CODE），仅为命名差异，服务器 .env 三键名与 compose 引用一致，不影响功能。
- `docs/dev-flow/tasks/V2-T7/rounds/01/maker-completion.md` 尚未提交（合同 §11 要求服务器操作记录写入），当前 rounds/ 目录仅合同文件；建议 Maker/协调者补齐完成说明。
- 本轮为 HTTP 明文（合同 §3 已知悉的临时风险，非本轮问题）；HTTPS 留待发布前自签+客户端固定。

## 判定

- **FAIL**：仅因阻断项 1（越界修改 engine/**，合同 §6 违反）。窄修复输入：将 `f774f39` 的 engine 改动移出 T7 候选范围（回退至 `5da16c0` 或另行受控返工处理，fastembed 修复如需则走返工合同），候选仅保留 backend/** 与 rounds/01/maker-completion.md；修复后重新验收。