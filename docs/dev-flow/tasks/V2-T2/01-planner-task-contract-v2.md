# 任务合同 V2-T2 v2 — LLM 网关：平台 Key 池 + 计量（无用量上限）

- 状态：READY_FOR_MAKER（范围变更已由产品负责人确认，v2 直接生效）
- 产品决定来源：`00-product-decision-v3.md`（D13 取消上限）；v1 合同保留作历史
- 精确起始 SHA：本合同提交后的 master HEAD（返工基线包含第 1 轮候选 `0d08654` 与完成说明 `6080405`）
- 工作树门禁：`git status --short` 必须干净

## 1. 背景

第 1 轮候选 `0d08654` 已实现网关+计量+上限。产品负责人决定暂不设置上限（D13）。本轮为窄返工：只移除上限执行逻辑，其余保留。

## 2. 唯一主要行为变化

**网关不再以任何用量上限拒绝调用（移除 429 限流与 USER_DAILY_TOKEN_LIMIT 配置）；计量与用量查询保留为纯可见性。**

## 3. 明确不做

- 不改 Key 池、SSE 透传、422/502/504 语义、脱敏、计量入库逻辑（除与上限耦合部分）
- 不做 v1 合同之外的任何新功能

## 4. 返工内容（基于第 1 轮代码）

- 移除：`USER_DAILY_TOKEN_LIMIT` 配置项、调用前的上限检查、429 分支、相关测试用例
- 保留：usage_log 计量入库、`GET /api/llm/usage`（返回当日已用 token；不再返回上限字段或将其语义改为"无上限"）
- 更新完成说明与测试命名，确保无"上限"残留语义

## 5. 允许修改 / 禁止修改

- 允许：`backend/**`、`docs/dev-flow/tasks/V2-T2/**`
- 禁止：同 v1 §6（根目录 Streamlit 产品文件、steps/、components/、converters/、generic_knowledge/、根 requirements.txt、.opencode/、AGENTS.md）

## 6. 验收标准

- [ ] 全量 `python -m pytest backend/tests -q` 全绿（T1 的 16 例 + T2 网关用例；原上限用例已移除而非跳过）
- [ ] 代码与配置中无 USER_DAILY_TOKEN_LIMIT / 429 上限残留（grep 可证）
- [ ] 非流式/流式计量入库行为不变（沿用 v1 §8 对应条目）
- [ ] 未带/无效 JWT → 401；白名单外 model → 422；上游故障 → 502/504 不泄露 key（沿用 v1）
- [ ] `python -c "from backend.app.main import app"` 通过

## 7. 快速测试 / 停止条件 / 候选要求

- 快速测试：`python -m pytest backend/tests -q` → 导入冒烟（同 v1 §9）
- 停止条件：同 v1 §13（基线不符 / 需新依赖 / 越界 / 同一失败两次）
- 候选提交只含 backend/**（消息："V2-T2 返工：移除用量上限（保留计量）"）；完成说明单独提交到 rounds/02/maker-completion.md；不 amend/rebase/push

## 8. 预算

约 1 小时（窄返工）。
