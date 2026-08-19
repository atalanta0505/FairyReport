# 任务合同 V2-T2 v1 — LLM 网关：平台 Key 池 + 计量 + 用量上限

- 状态：DRAFT（待产品负责人批准）
- 产品决定来源：`00-product-decision-v2.md`（D2 平台供 Key；§3 成本硬上限为强制配套项）
- 精确起始 SHA：`2477d1bf2d03b3740d98dc064f91806beae26dbf`
- 工作树门禁：`git status --short` 必须干净

## 1. 背景与目标

平台统一提供 LLM Key 且暂不收费，成本全部由产品负责人承担。本切片在后端建立统一 LLM 出口：客户端不再直连模型 API，一切调用经网关代理，逐次计量并受硬性上限保护。

## 2. 唯一主要行为变化

**登录用户可通过 `POST /api/llm/chat` 经后端网关调用平台 LLM（支持流式），调用被计量入库，并受"每用户每日 token 硬上限"约束。**

## 3. 明确不做

- 不做收费/配额商品化（只有技术性硬上限）
- 不做桌面端调用方（T7/T8 的事）
- 不做资料/写作/导出业务逻辑
- 不改 T1 认证行为（仅复用其 JWT 依赖注入）

## 4. 实现导航

- 现有基础：`backend/app/main.py`（挂新路由）、`backend/app/auth/security.py`（复用 JWT 校验依赖）、`backend/app/models.py`（加表）、`backend/app/config.py`（加配置）
- 新建 `backend/app/llm/`：
  - `router.py` — `POST /api/llm/chat`（JWT 保护；body：messages、可选 temperature/max_tokens/stream；stream=true 返回 SSE，透传上游 chunk；stream=false 返回 JSON）+ `GET /api/llm/usage`（返回当日已用 token 与上限）
  - `gateway.py` — httpx 调 OpenAI 兼容上游（不新增 openai 依赖）；Key 池轮询选择；上游超时/错误映射为 502/504 并保留上游错误摘要
  - `metering.py` — 计量：优先取上游 usage（流式用 stream_options.include_usage），无法取得时按字符数估算并标记 estimated；写入用量表
- 新增表 `usage_log`（user_id、日期(UTC)、prompt_tokens、completion_tokens、model、estimated 标志、时间戳）；当日上限检查 = 按 user_id+UTC 日聚合
- 配置（环境变量，参考 T1 风格）：`LLM_API_KEYS`（逗号分隔多 key）、`LLM_BASE_URL`（默认 https://api.deepseek.com/v1）、`LLM_MODEL_ALLOWLIST`（默认 deepseek-v4-flash）、`USER_DAILY_TOKEN_LIMIT`（默认 200000）、`LLM_TIMEOUT`（默认 120 秒）
- 请求的 model 不在白名单 → 422；超限 → 429（含当日已用量信息）

## 5. 允许修改

- `backend/**`（含修改 T1 已建文件：main.py/config.py/models.py 等）
- `docs/dev-flow/tasks/V2-T2/**`

## 6. 禁止修改

- 根目录现有 Streamlit 产品文件、steps/、components/、converters/、generic_knowledge/、根 requirements.txt、.opencode/、AGENTS.md
- T1 的既有测试不得删除或放宽断言（可增补）

## 7. 约束

- 不新增依赖（httpx/pytest 已在批准清单）；上游调用全部在测试中打桩（MockTransport 或 monkeypatch），不得真实调用模型 API
- Key 池中的 key 只从环境变量读取；任何日志/响应/测试不得出现真实 key；日志中 key 须脱敏（如前 4 位 + ***）
- 计量失败不得阻断响应（记录 estimated/失败标记）
- 流式响应：SSE 格式与 OpenAI 兼容（data: {chunk}\n\n，结束 data: [DONE]）

## 8. 验收标准

- [ ] 未带/无效 JWT 调 chat → 401
- [ ] 非流式调用：打桩上游返回 → 网关返回模型响应内容，usage_log 入库且数值与打桩 usage 一致
- [ ] 流式调用：打桩上游逐 chunk 返回 → SSE 透传且末尾含 usage 计量入库
- [ ] model 不在白名单 → 422
- [ ] 当日累计超过 USER_DAILY_TOKEN_LIMIT → 429；GET /api/llm/usage 数值一致
- [ ] Key 池含 2 个 key 时连续调用轮询使用（打桩断言 Authorization 头）
- [ ] 上游 5xx/超时 → 网关 502/504，不泄露 key
- [ ] `python -m pytest backend/tests -q` 全绿（含 T1 原 16 例）

## 9. Maker 快速测试（按顺序）

1. `python -m pytest backend/tests -q`
2. `python -c "from backend.app.main import app"`

## 10. Evidence Runner 分级验证计划

- 无昂贵步骤。真实上游联调（用产品负责人的真实 key）为日后人工项，不在本切片。

## 11. GUI / 人工验收项

- 无（纯 API 切片）。

## 12. 候选提交与完成说明要求

- 候选提交只含 backend/**；完成说明单独提交到 `docs/dev-flow/tasks/V2-T2/rounds/01/maker-completion.md`（按模板）
- 不 amend、不 rebase、不 push

## 13. 停止条件

- 基线或工作树不符；需要新依赖；必须越界修改；同一失败两次；
- SSE 透传在 FastAPI/httpx 组合上遇到无法在两次尝试内解决的障碍 → 报告（可降级为先非流式，流式转 T5 前补，但须先回报）。

## 14. 已知基线失败

- 无（T1 验收时 16 passed；任何新增失败属候选问题）。
