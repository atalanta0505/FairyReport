# Maker 完成说明 — V2-T1 第 1 轮

## 合同与基线

- 有效合同：`tasks/V2-T1/01-planner-task-contract-v1.md`
- 起始 SHA：`bd07bbdd135b175eacd58c1bef3e3007fc17cbd9`（已核对一致；其上 24d4771 仅含本合同治理文件，候选基于 24d4771 构建，验收 diff 基线 = 24d4771）

## 候选

- 候选 SHA：`4f281bae7979936f6de0c4c30280f7edfb55b030`
- 父提交：`24d47718c0d0899c58c42c2240b1658d78abf84f`
- 提交标题：V2-T1：后端骨架+邮箱注册/登录（FastAPI/JWT/QQ SMTP 打桩测试）
- 精确修改文件（全部新增，20 个，未触碰任何现有文件；.gitignore 经核实无需修改）：
  - `backend/__init__.py`：后端包标记
  - `backend/app/__init__.py`：应用包标记
  - `backend/app/main.py`：FastAPI 入口，挂载 auth/users 路由，`GET /api/health`，导入时建表
  - `backend/app/config.py`：pydantic-settings 配置（DATABASE_URL/JWT/验证码限频/QQ SMTP，环境变量 > backend/.env > 默认值）
  - `backend/app/db.py`：SQLAlchemy 同步引擎/会话（SQLite 内存库用 StaticPool），`utcnow()`、`get_db()`
  - `backend/app/models.py`：User（email 唯一、密码哈希、盐、created_at）+ AuthCode（email、码、过期时间、创建时间）
  - `backend/app/smtp.py`：QQ SMTP 封装（stdlib smtplib，守护线程执行；凭据只从配置读取）
  - `backend/app/auth/__init__.py`：认证包标记
  - `backend/app/auth/security.py`：pbkdf2_hmac(SHA-256, 60 万轮) + 随机盐；PyJWT 签发/校验（sub/exp，默认 7 天）
  - `backend/app/auth/schemas.py`：请求/响应模型（邮箱/验证码/密码基础校验）
  - `backend/app/auth/router.py`：send-code（429 限频）/ register（400 码错、409 重复邮箱）/ login（401）/ me（401）
  - `backend/tests/conftest.py`：SQLite 内存库 + TestClient + SMTP 打桩夹具（强制覆盖 DATABASE_URL/JWT_SECRET）
  - `backend/tests/test_health.py`：health 200
  - `backend/tests/test_send_code.py`：发送成功（打桩断言）、60 秒重发 429、间隔后可重发、每日上限 429
  - `backend/tests/test_register.py`：成功创建、码错误 4xx、码过期 4xx、重复邮箱 4xx
  - `backend/tests/test_login.py`：成功返回 JWT、密码错误 401、未注册邮箱 401
  - `backend/tests/test_me.py`：有效 JWT 返回用户信息、缺头/无效/过期 401
  - `backend/requirements.txt`：合同批准的 8 个依赖（锁定为本机已验证版本）
  - `backend/Dockerfile`：python:3.14-slim + uvicorn（供日后部署，本切片未实测）
  - `backend/docker-compose.yml`：api + postgres:16，环境变量注入（供日后部署，本切片未实测）

## 快速验证记录

| 命令 | 首次结果 | 修复后结果 |
|---|---|---|
| `python -m pytest backend/tests -q` | 16 passed, 0 failed（1.94s；6 warnings） | 加长测试用 JWT 密钥至 32 字节消除 InsecureKeyLengthWarning 后：16 passed, 0 failed（2.03s；余 1 条 fastapi 库自身的 httpx 弃用提示） |
| `python -c "from backend.app.main import app"` | 成功（IMPORT_SMOKE_OK） | 不适用 |

首次失败记录：无（pytest 首次运行即全绿）。说明：首次运行无失败，仅 PyJWT 对 15 字节测试密钥的 InsecureKeyLengthWarning；属测试夹具密钥长度问题，改长密钥后消除，非行为修复。冒烟测试产生的默认 SQLite 文件 `backend_dev.db`（被 `*.db` 规则忽略）已删除。

## 未执行项（移交 Evidence Runner / 人工）

- `backend/Dockerfile` / `docker-compose.yml` 实机构建与部署（服务器未购买；合同 §10 定为 C 级审查证据）
- 真实 QQ 邮箱发信联调（需产品负责人提供 SMTP 授权码，HUMAN_ACTION_REQUIRED，合同 §11）

## 已知风险、未完成项与范围外发现

- `backend/app/config.py` 的 `jwt_secret` 带开发默认值（保证无环境变量的导入冒烟可通过）；生产必须经环境变量注入强密钥，docker-compose 已用 `${JWT_SECRET:?...}` 强制要求。
- SMTP 发送为后台守护线程：凭据缺失/发送失败仅打印日志，send-code 仍返回 200（码已入库）。属本切片有意的简化，生产联调时需关注。
- 每邮箱每日发信上限按 UTC 日界计算（`utcnow` 取日始）；对 UTC+8 用户日界在北京时间 08:00。如需本地日界为后续调整项。
- 依赖版本锁定为本机已验证版本（fastapi 0.140.7 等）；fastapi TestClient 有一条来自库自身的 httpx/httpx2 弃用警告，不影响行为，未处理（换依赖超出批准清单）。
- 范围外发现（只报告不处理）：仓库根存在未跟踪的 `desktop.ini`（已被 .gitignore 覆盖）；根项目仍无任何测试用例（与合同 §14 基线一致）。

## 冻结声明

未 amend、未 rebase、未 push；候选已冻结，等待独立 Checker 对 `4f281bae7979936f6de0c4c30280f7edfb55b030` 验收。
