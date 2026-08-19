# Checker 验收报告 — V2-T2 第 02 轮（返工）

- 状态：**PASS**
- 精确候选 SHA：`5575ca88f7865e1465da800ee1f4112963c9290f`
- 依据合同：`tasks/V2-T2/01-planner-task-contract-v2.md`（v1 上限相关条目已由产品决定 v3 / D13 取消，不作为验收依据）
- 基线 SHA：`331381a9f4f20da0779d40d3efa2cb54d17dbfdd`

## 独立检查边界

- 独立重跑：
  - `git rev-parse HEAD` → `c6d79b4aff894dd0f4d5452e124f9268be25f7c2`（完成说明提交）；`git status --short` 干净。
  - `git log --oneline 331381a..HEAD` → 恰 2 条：`5575ca8 V2-T2 返工：移除用量上限（保留计量）`、`c6d79b4 V2-T2 第2轮 Maker 完成说明`；`git show` 确认候选父提交恰为基线 `331381a`，完成说明提交父为候选、仅含 `rounds/02/maker-completion.md`（+60 行）。
  - `python -m pytest backend/tests -q` → **30 passed, 1 warning in 6.36s**（唯一警告为 starlette 对 httpx 的第三方弃用提示，非候选代码问题）。
  - `pytest --collect-only -q` → 30 例收集、0 skip：T1 16 例（health 1 + login 3 + me 4 + register 4 + send_code 4）+ T2 14 例（llm_chat 11 + llm_usage 3）；原上限用例 `test_daily_limit_enforced_and_usage_consistent` 已删除（非 skip），替换为 `test_usage_accumulates_and_never_blocks`。
  - `python -c "from backend.app.main import app"`（以 `DATABASE_URL=sqlite://` 环境守卫运行，避免在仓库生成 db 文件；冒烟后 `git status --short` 仍干净）→ `import OK, routes: 8`。
  - `git diff --name-status 331381a..5575ca8` → 6 个文件全部 `M` 且位于 `backend/**`（+19/−37，删除为主的窄返工）。
  - 残留 grep（`backend/**`）：`USER_DAILY_TOKEN_LIMIT|user_daily_token_limit|用量已达上限|硬上限|token 上限` → **0 命中**；`remaining_tokens` → 仅 2 处且均为测试中 `assert "remaining_tokens" not in body` 的负向断言（test_llm_usage.py:23,47）；`429` → 仅 T1 邮箱验证码限频（auth/router.py:33,41 与 test_send_code.py，合同保留项）及 test_llm_usage.py:29 docstring 中"无 429"的负向描述。LLM 网关无 429 上限分支残留。
- 仅审查既有证据：`rounds/02/maker-completion.md`（仅作线索，逐条与事实比对，见"完成说明核对"）。
- 未重跑：真实上游 LLM 联调（需产品负责人真实 Key，合同外人工项，铁律禁止经 Agent 传递凭据）；生产多用户并发压测（本切片以单元级打桩覆盖语义）。

## 验收标准逐条核对（合同 v2 §6）

| 合同标准 | 证据等级 | 证据与结论 |
|---|---|---|
| 全量 `python -m pytest backend/tests -q` 全绿（T1 16 例 + T2 网关用例；原上限用例已移除而非跳过） | A | Checker 独立重跑 `30 passed, 1 warning in 6.36s`；collect-only 确认 30 例 0 skip，上限用例已删除并由 `test_usage_accumulates_and_never_blocks`（连续 3 次调用均 200、usage 累计 180、无上限字段）替换。 |
| 代码与配置中无 USER_DAILY_TOKEN_LIMIT / 429 上限残留（grep 可证） | A | 上方残留 grep 结果：配置项/上限文案 0 命中；`429` 仅存于 T1 邮箱限频（保留项）与负向 docstring。diff 证实 `config.py` 删除 `user_daily_token_limit`、`router.py` 删除调用前上限检查与 429 分支。 |
| 非流式/流式计量入库行为不变（沿用 v1 §8） | C+A | C：`metering.py` 仅 docstring 改动（diff 可证），`record_usage` 上游 usage 优先、估算兜底标 `estimated`、失败不阻断逻辑完整（metering.py:34-71）；`router.py` 非流式（:96-102）与 SSE 结束后（:54-60）计量调用保留。A：`test_chat_non_stream_returns_content_and_records_usage`、`test_chat_non_stream_without_usage_estimates`、`test_chat_stream_sse_passthrough_and_metering`、`test_usage_accumulates_and_never_blocks` 全部通过。 |
| 未带/无效 JWT → 401；白名单外 model → 422；上游故障 → 502/504 不泄露 key（沿用 v1） | C+A | C：diff 未触碰 401（`current_user`）、422 白名单（router.py:69-70）、503 Key 池未配置（:72-73）、`UpstreamError` 502/504 映射（gateway.py:75-91,114-119）；`mask_key` 脱敏仍在（gateway.py:30-32,67）。A：`test_chat_without_token_returns_401`、`test_chat_with_invalid_token_returns_401`、`test_chat_model_not_in_allowlist_returns_422`、`test_chat_upstream_5xx_maps_to_502_without_key_leak`、`test_chat_upstream_timeout_maps_to_504_without_key_leak`、`test_chat_stream_upstream_5xx_maps_to_502` 全部通过。 |
| `python -c "from backend.app.main import app"` 通过 | A | Checker 独立重跑：`import OK, routes: 8`（环境守卫 `DATABASE_URL=sqlite://`，冒烟后工作树仍干净）。 |

### 合同 v2 §2/§3/§4 窄返工边界补充核对（C 级）

- 唯一主要行为变化成立：`chat()` 不再有任何用量检查（router.py:63-103 从 JWT 校验直达白名单→Key 池→上游）；`GET /api/llm/usage` 只返回 `date` 与 `used_tokens`，无上限语义（router.py:106-115）。✓
- "只删不增"核实：完整 diff 逐行审查，产品代码改动仅为删除上限配置/检查/429 分支/上限字段与相应 docstring 措辞更新；测试侧除删除上限用例外仅新增证明新行为的 `test_usage_accumulates_and_never_blocks`（合同 §4 要求的最小目标测试）。✓
- Key 池轮询（`next_key`，gateway.py:35-44）、SSE 透传与 `[DONE]` 保底（router.py:35-60）、`stream_options.include_usage`（router.py:81）、脱敏、计量入库均未被返工触碰（不在 diff 中）。✓

## 修改范围复核

- `git diff 331381a..5575ca8` 是否严格落在允许路径内：**是**（6 个文件全部 `M` 且位于 `backend/**`：config.py、llm/__init__.py、llm/metering.py、llm/router.py、models.py、tests/test_llm_usage.py）。
- 是否触碰禁止路径：**否**（根目录 Streamlit 产品文件、steps/、components/、converters/、generic_knowledge/、根 requirements.txt、.opencode/、AGENTS.md 均未出现在 diff 中）。
- 候选提交只含 backend/**，完成说明单独提交（c6d79b4 仅含 maker-completion.md）；候选提交消息与合同 §7 规定一致。✓

## 安全审查（C 级）

- 完整 diff 逐行审查：无任何真实凭据/密钥入库；`llm_api_keys` 等敏感项默认空串、仅从环境变量/.env 读取（config.py:36-40）。✓
- 日志脱敏仍在：`mask_key`（前 4 位 + ***）用于全部上游失败日志（gateway.py:67），`UpstreamError.detail` 不含 Key，并有 `test_chat_upstream_5xx_maps_to_502_without_key_leak` / `..._504_without_key_leak` 守护。✓

## 完成说明核对

`maker-completion.md` 与事实一致：候选/父 SHA 正确；6 个修改文件清单与 diff 完全吻合；"30 passed（T1 16 + T2 14）"与独立重跑一致；"8 routes"与独立冒烟一致；grep 残留结论与独立 grep 一致；未执行项（真实上游联调、并发压测）如实披露；冻结声明（未 amend/rebase/push）与 git 历史相符（候选父提交即基线，无历史改写痕迹）。

## 阻断项（仅 FAIL）

- 无。

## 非阻断风险

- `GET /api/llm/usage` 响应字段收窄（移除 `limit`/`remaining_tokens`）：backend 为 V2 新建、当前无前端消费，无兼容性破坏；如后续前端需展示用量，需另行约定字段（maker 已披露，Checker 确认）。
- 计量兜底估算 `ceil(字符数/2)` 沿用第 1 轮，本轮未改，精度为粗略估算（有意简化）。
- starlette 关于 httpx 弃用的第三方警告（1 warning）：非候选代码问题，换依赖超出批准清单，未处理。
- 真实上游联调与多用户并发压测未做（单元级打桩覆盖语义），见剩余人工项。

## 判定

- **PASS**：锁定候选 SHA `5575ca88f7865e1465da800ee1f4112963c9290f`。
- 剩余人工项：
  1. 真实上游 LLM 联调（需产品负责人提供真实 Key；HUMAN_ACTION_REQUIRED 另行交接，不得经 Agent 传递凭据）。
  2. 生产环境多用户并发压测（部署切片）。
- 两轮规则：本轮为第 2 轮（返工轮），PASS，无需触发两轮规则评估。
