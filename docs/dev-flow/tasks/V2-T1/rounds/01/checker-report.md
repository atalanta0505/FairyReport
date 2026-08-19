# Checker 验收报告 — V2-T1 第 01 轮

- 状态：**PASS**
- 精确候选 SHA：`4f281bae7979936f6de0c4c30280f7edfb55b030`
- 依据合同：`tasks/V2-T1/01-planner-task-contract-v1.md`
- 基线 SHA：`24d47718c0d0899c58c42c2240b1658d78abf84f`

## 独立检查边界

- 独立重跑：
  - `git rev-parse HEAD` → `41096d1249a25ac35e3c5f959bf69f49d3b4c943`（完成说明提交，与交接一致）；`git rev-parse 4f281ba^` → `24d4771...`（候选父链正确）。
  - `python -m pytest backend/tests -q` → **16 passed, 1 warning in 1.99s**（唯一警告为 fastapi/starlette 库自身的 httpx 弃用提示，非候选代码问题）。
  - `python -c "from backend.app.main import app"` → 输出 `IMPORT_SMOKE_OK`。
  - `git diff --name-status 24d4771..4f281ba` → 20 个文件全部为 `A`（新增），全部位于 `backend/**`。
  - `git check-ignore -v backend/.env` → 命中 `.gitignore:51:.env`；`git ls-files backend/.env` 为空（未被提交）。
  - 凭据模式 grep（backend/ 内 `secret/password/auth_code = "≥12位值"`）→ 无命中。
- 仅审查既有证据：`docs/dev-flow/tasks/V2-T1/rounds/01/maker-completion.md`（仅作线索，逐条与事实比对）。
- 未重跑：Docker 镜像构建与 compose 实机部署（服务器未购买，合同 §10 定为 C 级审查证据）；真实 QQ SMTP 发信（合同 §11 人工项，且铁律禁止引入凭据）。

## 验收标准逐条核对

| 合同标准（§8） | 证据等级 | 证据与结论 |
|---|---|---|
| `POST /api/auth/send-code`：发码+打桩断言+限频；60 秒内重发 429 | A+C | A：`test_send_code.py` 4 用例全过（成功打桩断言/60 秒重发 429/间隔后可重发/每日上限 429），含于独立重跑 16 passed。C：`backend/app/auth/router.py:23-51`（6 位数字码 `secrets.randbelow`、重发间隔与每日上限判断）。 |
| `POST /api/auth/register`：创建用户；码错/过期 4xx；重复邮箱 4xx | A+C | A：`test_register.py` 4 用例全过（成功入库且密码非明文/码错 400/码过期 400/重复邮箱 409）。C：`router.py:54-73`（`expires_at > now` 过滤、409 唯一性检查、注册后清除该邮箱全部验证码）。 |
| `POST /api/auth/login`：邮箱+密码 → JWT；密码错误 401 | A+C | A：`test_login.py` 3 用例全过（成功返回含 sub/email/exp 的 bearer JWT/密码错 401/未注册邮箱 401）。C：`router.py:76-82`（统一 401 防用户枚举）、`security.py:16-28`（pbkdf2_hmac SHA-256 60 万轮+随机盐+`hmac.compare_digest` 常量时间比较，符合 §7 不引入 bcrypt/passlib）。 |
| `GET /api/users/me`：有效 JWT 返回用户信息；无效/过期 401 | A+C | A：`test_me.py` 4 用例全过（有效/缺头/无效/过期）。C：`router.py:85-108`（Bearer 解析、`PyJWTError` 捕获、sub 解析与用户存在性检查均 401）。 |
| `GET /api/health` 返回 200 | A+C | A：`test_health.py` 通过。C：`backend/app/main.py:19-22`。 |
| `python -m pytest backend/tests -q` 全绿 | A | Checker 独立重跑：`16 passed, 1 warning in 1.99s`；与 maker 自述"首次即绿"一致。测试无需 Docker/Postgres（conftest 强制 `DATABASE_URL=sqlite://` 内存库 + StaticPool）。 |
| Dockerfile 与 docker-compose.yml 存在且经审查 | C | 两文件存在。Dockerfile：python:3.14-slim、安装 backend/requirements.txt、uvicorn 8000，合理。compose：api+postgres:16、pg_isready healthcheck、pgdata 卷、端口 8000，合理。实机部署待服务器（合同 §10）。 |
| 依赖清单 = 合同批准的 8 项 | C | `backend/requirements.txt` 恰为 fastapi/uvicorn/SQLAlchemy/psycopg[binary]/pydantic-settings/PyJWT/pytest/httpx 共 8 项（带版本锁定），无清单外依赖，未触碰根 requirements.txt。 |

### 合同 §7 约束补充核对（C 级）

- 验证码 6 位数字/10 分钟过期/60 秒重发间隔/每日上限默认 10 且可配置：`backend/app/config.py:25-27` + `schemas.py:43-48`。✓
- JWT 过期可配置默认 7 天、密钥从环境变量读取：`config.py:20-22`、`security.py:31-45`。✓
- QQ SMTP 凭据只从环境变量/.env 读取：`config.py:30-33` 默认空串；`smtp.py:29-30` 缺失即抛错；仓库内无硬编码凭据。✓
- `backend/.env` 被 gitignore（`.gitignore:51`）且未提交；`*.db` 亦被忽略（`.gitignore:48`）。✓
- 测试不真实发信：`conftest.py:29-38` `mail_stub` 以 monkeypatch 替换 `smtp.send_code_email`，全部发码用例均使用该夹具。✓

## 修改范围复核

- `git diff 24d4771..4f281ba` 是否严格落在允许路径内：**是**（20 个文件全部 `A` 且位于 `backend/**`，784 行新增、0 行删除/修改）。
- 是否触碰禁止路径：**否**（根目录现有 .py、steps/、components/、converters/、generic_knowledge/、根 requirements.txt、.opencode/ 均未出现在 diff 中；`.gitignore` 亦未修改，现有 `.env`/`*.db` 规则已覆盖需要，与 maker 说明一致）。

## 安全审查（C 级）

- 仓库内无真实凭据：凭据模式 grep 无命中；SMTP 账号/授权码默认空串；测试 JWT 密钥为显式测试值。✓
- 生产密钥注入：compose 中 `JWT_SECRET: ${JWT_SECRET:?请在部署环境设置 JWT_SECRET}` 强制注入。✓
- `backend/.env` 未被提交（`git ls-files` 为空，check-ignore 命中）。✓
- 测试无真实发信（smtp 被打桩，见上）。✓

## 完成说明核对

`maker-completion.md` 与事实一致：候选/父 SHA 正确；20 个文件清单与 diff 完全吻合；"首次运行即绿、修复后 16 passed"与独立重跑结果（16 passed, 1 warning）一致；未执行项（Docker 实测、真实发信）与合同 §10/§11 一致；冻结声明（未 amend/rebase/push）与 git 历史相符。

## 阻断项（仅 FAIL）

- 无。

## 非阻断风险

- `config.py` 的 `jwt_secret` 带开发默认值（保证无环境变量的导入冒烟可通过）；生产已经 compose `${JWT_SECRET:?}` 强制覆盖，建议部署切片再评估是否移除默认值。
- SMTP 为后台守护线程发送：凭据缺失/失败仅打日志，send-code 仍返回 200（码已入库）。本切片有意简化，真实发信联调时需验证可达性与错误可观测性。
- 每日发信上限按 UTC 日界计算，UTC+8 用户的日界在北京时间 08:00；如产品要求本地日界为后续调整项。
- compose 中 `POSTGRES_PASSWORD` 带默认值 `fairyreport`（`${POSTGRES_PASSWORD:-fairyreport}`）；与 JWT_SECRET 的强制注入不一致，建议部署切片同样改为 `:?` 强制。
- fastapi TestClient 存在一条库自身的 httpx 弃用警告，非候选代码问题，未处理（换依赖超出批准清单）。

## 判定

- **PASS**：锁定候选 SHA `4f281bae7979936f6de0c4c30280f7edfb55b030`。
- 剩余人工项：
  1. 真实 QQ 邮箱发信联调（需产品负责人提供 SMTP 授权码，HUMAN_ACTION_REQUIRED 另行交接，不得经 Agent 传递凭据）。
  2. Docker 镜像构建与 compose 实机部署验证（服务器购买后的部署切片）。
- 两轮规则：本轮为第 1 轮，PASS，无需进入修复轮。
