# 致 Maker 的转发消息 V2-T1 v1

你是当前唯一可写 Maker。

工作目录：D:\Repo\FairyReport_lite
精确起始 SHA：bd07bbdd135b175eacd58c1bef3e3007fc17cbd9
有效合同：docs/dev-flow/tasks/V2-T1/01-planner-task-contract-v1.md

唯一主要行为：用户可通过邮箱验证码注册、以邮箱+密码登录，服务端签发 JWT（API 级，测试证明）。

实现导航：
- 新建 backend/（FastAPI）：app/main.py、app/config.py、app/db.py、app/models.py、app/auth/、app/smtp.py
- 测试 backend/tests/（TestClient + SQLite 内存库 + SMTP 打桩）
- 部署件 backend/Dockerfile、backend/docker-compose.yml（api + postgres:16）
- 风格参考现有 config.py 的 .env 覆盖模式

允许修改：
- backend/**（新建）、.gitignore（如需）、docs/dev-flow/tasks/V2-T1/**

禁止修改：
- 根目录全部现有 .py 产品文件、steps/、components/、converters/、generic_knowledge/、根 requirements.txt

快速验证顺序：
1. python -m pytest backend/tests -q
2. python -c "from backend.app.main import app"

停止条件：
- 基线或工作树不符；
- 必须越界修改或需要清单外依赖（fastapi/uvicorn/sqlalchemy/psycopg[binary]/pydantic-settings/PyJWT/pytest/httpx 之外）；
- 同一实现或目标测试失败两次；
- 需要真实发信、凭据、GUI 或产品决定。

完成时：
1. 只提交允许范围；
2. 创建本地候选提交；
3. 不 amend、不 rebase、不 push；
4. 按模板写完成说明到 docs/dev-flow/tasks/V2-T1/rounds/01/maker-completion.md，报告 SHA、diff、首次测试结果、风险和未完成项；
5. 冻结工作树并交回。
