# Maker 完成说明 — V2-T2 第 2 轮（窄返工）

## 合同与基线

- 有效合同：`tasks/V2-T2/01-planner-task-contract-v2.md`（产品决定 v3：D13 取消上限）
- 起始 SHA：`331381a9f4f20da0779d40d3efa2cb54d17dbfdd`（已核对一致：`git status --short` 干净，HEAD 与合同基线相符）
- 返工基线含第 1 轮候选 `0d08654` 与完成说明 `6080405`

## 唯一主要行为变化

网关不再以任何用量上限拒绝调用：移除调用前上限检查与 429 分支、移除 `USER_DAILY_TOKEN_LIMIT` 配置；计量（usage_log 入库，含 estimated 标记）与 `GET /api/llm/usage` 保留为纯可见性（只返回 `date` 与 `used_tokens`，不再含 `limit` / `remaining_tokens` 字段）。

## 候选

- 候选 SHA：`5575ca88f7865e1465da800ee1f4112963c9290f`
- 父提交：`331381a9f4f20da0779d40d3efa2cb54d17dbfdd`
- 提交标题：V2-T2 返工：移除用量上限（保留计量）
- 精确修改文件：
  - `backend/app/config.py`：删除 `user_daily_token_limit` 配置项（其余配置未动）
  - `backend/app/llm/router.py`：`chat()` 删除调用前上限检查与 429 分支；`usage()` 不再返回 `limit` / `remaining_tokens`，docstring 更新为纯可见性
  - `backend/app/models.py`：`UsageLog` docstring 去除"硬上限"表述（改为用量可见性统计）
  - `backend/app/llm/metering.py`：`utc_today` docstring 去除"每日上限"表述（改为用量统计聚合键）
  - `backend/app/llm/__init__.py`：模块 docstring 去除"每日硬上限"表述
  - `backend/tests/test_llm_usage.py`：删除上限用例 `test_daily_limit_enforced_and_usage_consistent`（删除而非 skip）；`test_usage_reports_zero_initially` 改为断言无上限字段；新增 `test_usage_accumulates_and_never_blocks`（连续 3 次调用均 200 不被拒、usage 累计 180、无上限字段）作为证明新行为的最小目标测试

## 明确保留（未改动）

- Key 池轮询（`gateway.next_key`）、SSE 透传与 `[DONE]` 保底、stream_options.include_usage
- 401（未带/无效 JWT）、422（白名单外 model）、502/504（上游故障，不泄露 Key）、503（Key 池未配置）语义
- Key 脱敏（`mask_key`）、计量入库逻辑（上游 usage 优先，估算兜底并标 `estimated`，失败不阻断）
- T1 全部行为与邮箱验证码 429 限频（属 T1 范围，与 LLM 用量上限无关）

## 快速验证记录

| 命令 | 首次结果 | 修复后结果 |
|---|---|---|
| `python -m pytest backend/tests -q` | exit 0：30 passed, 1 warning（T1 原 16 例全数保持 + T2 网关 14 例，其中上限用例已被累计无阻断用例替换） | 不适用 |
| `python -c "from backend.app.main import app"` | exit 0：导入成功（8 routes；以 DATABASE_URL=sqlite:// 运行避免生成 db 文件） | 不适用 |

首次失败记录：无。

## grep 残留检查

- `USER_DAILY_TOKEN_LIMIT|user_daily_token_limit|用量已达上限|token 上限|硬上限` 于 `backend/**`：0 命中
- `429` 于 `backend/**`：仅存于 `backend/app/auth/router.py` 与 `backend/tests/test_send_code.py`（T1 邮箱验证码限频，合同保留项），以及 `test_llm_usage.py` docstring 中"无 429"的负向描述；LLM 网关与测试中无 429 上限分支残留

## 未执行项（移交 Evidence Runner / 人工）

- 真实上游联调（使用产品负责人真实 Key）为日后人工项，不在本切片。
- 生产环境多用户并发压测未做（本切片以单元级打桩覆盖语义）。

## 已知风险、未完成项与范围外发现

- `GET /api/llm/usage` 响应体字段收窄（移除 `limit` / `remaining_tokens`）：当前无任何已上线前端消费该端点（backend 为 V2 新建），故无兼容性破坏；如后续前端需要展示"无上限"，需另行约定字段。
- 计量兜底估算公式 `ceil(字符数/2)` 沿用第 1 轮，未改动。
- 范围外发现：pytest 输出存在 starlette 关于 httpx 弃用的第三方警告（`StarletteDeprecationWarning`），与本任务无关，仅报告不处理。

## 冻结声明

未 amend、未 rebase、未 push；候选已冻结，等待独立 Checker 对 `5575ca88f7865e1465da800ee1f4112963c9290f` 验收。
