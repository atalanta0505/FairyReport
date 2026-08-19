# 致 Maker 的转发消息 V2-T2 v1

你是当前唯一可写 Maker。

工作目录：D:\Repo\FairyReport_lite
精确起始 SHA：2477d1bf2d03b3740d98dc064f91806beae26dbf
有效合同：docs/dev-flow/tasks/V2-T2/01-planner-task-contract-v1.md

唯一主要行为：登录用户可经 POST /api/llm/chat 通过后端网关调用平台 LLM（支持 SSE 流式），调用计量入库，受每用户每日 token 硬上限约束。

实现导航：
- 新建 backend/app/llm/（router.py / gateway.py / metering.py）
- 复用 backend/app/auth/security.py 的 JWT 依赖；backend/app/models.py 增 usage_log 表；config.py 增配置
- 上游用 httpx（不新增依赖），测试全部打桩（MockTransport/monkeypatch）
- 配置：LLM_API_KEYS（逗号分隔）/ LLM_BASE_URL / LLM_MODEL_ALLOWLIST（默认 deepseek-v4-flash）/ USER_DAILY_TOKEN_LIMIT（默认 200000）/ LLM_TIMEOUT
- 语义：白名单外 model → 422；超限 → 429；上游故障 → 502/504 且不泄露 key；日志 key 脱敏

允许修改：
- backend/**（含 T1 文件的增补；T1 既有测试不得删除或放宽）
- docs/dev-flow/tasks/V2-T2/**

禁止修改：
- 根目录现有 Streamlit 产品文件、steps/、components/、converters/、generic_knowledge/、根 requirements.txt、.opencode/、AGENTS.md

快速验证顺序：
1. python -m pytest backend/tests -q
2. python -c "from backend.app.main import app"

停止条件：
- 基线或工作树不符；需要新依赖；必须越界修改；同一失败两次；
- SSE 透传两次尝试仍受阻 → 停止并报告（可提议降级方案，由 Planner 决定）。

完成时：
1. 只提交 backend/**；
2. 创建本地候选提交；
3. 不 amend、不 rebase、不 push；
4. 按模板写完成说明到 docs/dev-flow/tasks/V2-T2/rounds/01/maker-completion.md；
5. 冻结工作树并交回。
