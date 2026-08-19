# Checker 验收报告 — <TASK-ID> 第 <NN> 轮

- 状态：**PASS / FAIL / BLOCKED**
- 精确候选 SHA：<candidate-sha>
- 依据合同：`tasks/<TASK-ID>/01-planner-task-contract-v<N>.md`
- 基线 SHA：<base-sha>

## 独立检查边界

- 独立重跑：<命令与结果>
- 仅审查既有证据：<内容>
- 未重跑：<昂贵步骤及理由>

## 验收标准逐条核对

| 合同标准 | 证据等级(A/B/C/D) | 证据与结论 |
|---|---|---|
| <标准 1> | A | <pytest 输出摘要 / diff 位置> |

## 修改范围复核

- `git diff <base>..<candidate>` 是否严格落在允许路径内：是 / 否
- 是否触碰禁止路径：否 / <列出>

## 阻断项（仅 FAIL）

- 合同条目：<编号>
- 位置：<文件:行>
- 复现：<命令>
- 为什么阻断交付：<理由>

## 非阻断风险

- <已知限制及后续建议>

## 判定

- PASS：锁定 <candidate-sha>；剩余人工项：<列表>。
- FAIL：窄修复输入见 `checker-fix-task.md`（仅针对阻断项）。
- 两轮规则：若已是第二轮 FAIL —— **停止自动修复，交产品负责人再决策**。
