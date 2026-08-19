# 任务合同 V2-T1 v1 — 后端骨架 + 邮箱注册/登录

- 状态：DRAFT（待产品负责人批准）
- 产品决定来源：`docs/dev-flow/tasks/V2-DESKTOP/00-product-decision-v2.md`（D1/D4/D8/D9）
- 精确起始 SHA：`bd07bbdd135b175eacd58c1bef3e3007fc17cbd9`
- 工作树门禁：`git status --short` 必须干净

## 1. 背景与目标

V2 桌面正式版的云端后端从零建立。本切片交付可运行的 FastAPI 服务骨架与账号认证 API，为后续资料/写作/导出 API 提供宿主。

## 2. 唯一主要行为变化

**用户可通过邮箱验证码注册、并以邮箱+密码登录，服务端签发 JWT。**（API 级行为，以自动化测试证明）

## 3. 明确不做

- 不做任何前端/桌面端（desktop/ 目录本切片不创建）
- 不部署到腾讯云（服务器未购买）；只交付 docker-compose 文件供日后部署
- 不做资料、写作、导出、generic KB、LLM 网关等后续切片内容
- 不做收费/配额/订阅
- 不改动现有 Streamlit 应用的任何文件

## 4. 实现导航

- 新建 `backend/` 目录（FastAPI 应用），建议结构：
  - `backend/app/main.py`（应用入口、路由挂载、健康检查 `/api/health`）
  - `backend/app/config.py`（pydantic-settings，读 backend/.env）
  - `backend/app/db.py`（SQLAlchemy 引擎/会话）
  - `backend/app/models.py`（User 表：id/email/密码哈希/created_at 等）
  - `backend/app/auth/`（send-code / register / login / me；验证码生成、过期、限频；JWT 签发校验）
  - `backend/app/smtp.py`（QQ SMTP 发信封装，stdlib smtplib 放线程执行）
- 测试：`backend/tests/`（pytest + fastapi TestClient；SQLite 内存库；SMTP 打桩）
- 部署件：`backend/Dockerfile`、`backend/docker-compose.yml`（api + postgres:16）
- 参考现有代码风格：`config.py`（.env 覆盖模式）、`llm.py`（重试封装风格）

## 5. 允许修改

- `backend/**`（全部新建）
- `.gitignore`（如需为 backend 增补条目）
- `docs/dev-flow/tasks/V2-T1/**`（完成说明）

## 6. 禁止修改

- 根目录现有产品文件：`app.py`、`config.py`、`llm.py`、`pipeline.py`、`kb.py`、`outline.py`、`writer.py`、`exporter.py`、`project_store.py`、`ref_manager.py`、`hint_store.py`、`utils.py`、`web_search.py`
- `steps/`、`components/`、`converters/`、`generic_knowledge/`
- 根目录 `requirements.txt`（后端依赖独立为 `backend/requirements.txt`）

## 7. 约束

- Python 3.14 兼容；依赖最小化，仅限合同所列清单（见 §8 批准清单）
- 密码用 stdlib `hashlib.pbkdf2_hmac` + 盐哈希，不引入 bcrypt/passlib
- 验证码：6 位数字，10 分钟过期，同邮箱重发间隔 ≥60 秒，每邮箱每日上限可配置（默认 10）
- JWT 过期时间可配置（默认 7 天）；密钥从环境变量读取
- QQ SMTP 凭据（账号/授权码）只从环境变量读取；`backend/.env` 必须被 gitignore；任何测试不得真实发信（打桩）
- 测试必须可在无 Docker、无 Postgres 环境运行（SQLite 内存库）

## 8. 验收标准

- [ ] `POST /api/auth/send-code`：向邮箱发送验证码（测试中打桩断言调用与限频逻辑）；60 秒内重发返回 429
- [ ] `POST /api/auth/register`：邮箱+验证码+密码 → 创建用户；验证码错误/过期返回 4xx；重复邮箱返回 4xx
- [ ] `POST /api/auth/login`：邮箱+密码 → JWT；密码错误 401
- [ ] `GET /api/users/me`：携带有效 JWT 返回用户信息；无效/过期 401
- [ ] `GET /api/health` 返回 200
- [ ] `python -m pytest backend/tests -q` 全绿（首次运行即绿，保留输出）
- [ ] `backend/Dockerfile` 与 `docker-compose.yml` 存在且内容经 Checker 审查（C 级证据；实机部署待服务器）
- [ ] 依赖清单 = fastapi、uvicorn、sqlalchemy、psycopg[binary]、pydantic-settings、PyJWT、pytest、httpx（随合同批准一并批准；超出即触发停止条件）

## 9. Maker 快速测试（按顺序）

1. `python -m pytest backend/tests -q`
2. `python -c "from backend.app.main import app"`（导入冒烟，于仓库根执行）

## 10. Evidence Runner 分级验证计划

- 本切片无昂贵步骤；compose 文件留待服务器就位后的部署切片实测。

## 11. GUI / 人工验收项

- 无（纯 API 切片）。真实 QQ 邮箱发信联调为后续人工项（需产品负责人提供 SMTP 授权码，HUMAN_ACTION_REQUIRED 另行交接）。

## 12. 候选提交与完成说明要求

- 本地候选提交，记录精确 SHA；不 amend、不 rebase、不 push
- 完成说明按 `docs/dev-flow/templates/maker-completion.md` 写入 `docs/dev-flow/tasks/V2-T1/rounds/01/maker-completion.md`

## 13. 停止条件

- 基线或工作树与合同不符
- 需要清单外依赖、或需改动禁止路径
- 同一实现或目标测试失败两次
- Python 3.14 与某依赖不兼容且无干净替代（报告后由 Planner 决定）

## 14. 已知基线失败

- 无（仓库当前无任何测试；本切片测试全部为新增，任何失败都属候选问题）
