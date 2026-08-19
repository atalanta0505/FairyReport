# Maker 完成说明 — V2-T2 第 1 轮

## 合同与基线

- 有效合同：`tasks/V2-T2/01-planner-task-contract-v1.md`
- 起始 SHA：`c5988973a63ee93f3f9194428af9617adff1d873`（已核对一致：工作树干净，HEAD 与合同基线相符）

## 候选

- 候选 SHA：`0d086548e63f30ef0c38b062abb0fb17e65cd79b`
- 父提交：`c5988973a63ee93f3f9194428af9617adff1d873`
- 提交标题：V2-T2：LLM 网关+计量+每日硬上限（httpx 打桩测试）
- 精确修改文件：
  - `backend/app/config.py`：新增 LLM_API_KEYS / LLM_BASE_URL / LLM_MODEL_ALLOWLIST / USER_DAILY_TOKEN_LIMIT / LLM_TIMEOUT 配置及 Key 池、白名单解析属性
  - `backend/app/models.py`：新增 usage_log 表（user_id、UTC 日、prompt/completion tokens、model、estimated、时间戳）
  - `backend/app/auth/router.py`：`_current_user` 更名为 `current_user`（公开复用，行为不变）
  - `backend/app/main.py`：挂载 llm_router
  - `backend/app/llm/__init__.py`：新模块包
  - `backend/app/llm/schemas.py`：ChatRequest / ChatMessage（messages 非空、可选 temperature/max_tokens/stream）
  - `backend/app/llm/gateway.py`：httpx 调 OpenAI 兼容上游；Key 池轮询；5xx→502、超时→504；日志 Key 脱敏（前 4 位+***）；`_transport` 测试注入点
  - `backend/app/llm/metering.py`：上游 usage 优先（取不到按字符估算并标 estimated）；写 usage_log；失败仅记日志不阻断
  - `backend/app/llm/router.py`：POST /api/llm/chat（401/422/429/503 语义；stream=true SSE 透传 `data: {chunk}\n\n` + `data: [DONE]`，流式请求携带 stream_options.include_usage）+ GET /api/llm/usage
  - `backend/tests/conftest.py`：新增 LLM 打桩环境变量与 `llm_upstream`（httpx.MockTransport）夹具；原夹具未改动
  - `backend/tests/test_llm_chat.py`：新增 11 例（401×2、非流式计量、估算兜底、流式透传+计量、[DONE] 保底、流式 5xx、422、Key 轮询、502/504 不泄露 Key）
  - `backend/tests/test_llm_usage.py`：新增 3 例（usage 401、初始为 0、超限 429 与 usage 数值一致）

## 快速验证记录

| 命令 | 首次结果 | 修复后结果 |
|---|---|---|
| `python -m pytest backend/tests -q` | exit 0：30 passed, 1 warning（T1 原 16 例全数保持 + 新增 14 例） | 不适用 |
| `python -c "from backend.app.main import app"` | exit 0：导入成功（8 routes；以 DATABASE_URL=sqlite:// 运行避免生成 db 文件） | 不适用 |

首次失败记录：无。

## 未执行项（移交 Evidence Runner / 人工）

- 真实上游联调（使用产品负责人真实 Key）为日后人工项，不在本切片（合同 §10）。
- 生产环境多用户并发下的轮询/限流压测未做（本切片以单元级打桩覆盖语义）。

## 已知风险、未完成项与范围外发现

- 计量兜底估算公式为 `ceil(字符数/2)`（中英折中的粗略估计），仅在上游不返回 usage 时启用并标 `estimated=True`；如需更精确可在后续切片调整。
- 流式调用中若上游在首个 chunk 之后中途失败，SSE 连接将直接中断（HTTP 状态码已发出无法更改）；连接前故障（5xx/超时）已在首个 chunk 预取阶段映射为 502/504 JSON。
- 每日上限为调用前检查：单次调用本身不再二次扣减拦截，即"已用 >= 上限"才拒绝（与合同"当日累计超过上限 → 429"一致）。
- `backend/app/auth/router.py` 中 `_current_user` 更名为 `current_user` 属 T1 文件的纯改名增补（合同允许），T1 行为与断言未变。
- 范围外发现：pytest 输出存在 starlette 关于 httpx 弃用的第三方警告（`StarletteDeprecationWarning`），与本任务无关，仅报告不处理。

## 冻结声明

未 amend、未 rebase、未 push；候选已冻结，等待独立 Checker 对 `0d086548e63f30ef0c38b062abb0fb17e65cd79b` 验收。
