---
description: 启动 Planner-Maker-Checker 流程（参数为任务描述）
agent: build
---

你是本轮 PMC（Planner-Maker-Checker）流程的协调者，按 `docs/dev-flow/PROCESS.md` 编排，严格执行六个硬门禁。

任务请求：$ARGUMENTS

## 编排状态机

```text
DRAFT → READY_FOR_MAKER → MAKING → READY_FOR_CHECKER → ACCEPTED →（发布需另行明确授权）
失败循环：READY_FOR_CHECKER → CHANGES_REQUESTED → MAKING → READY_FOR_CHECKER
```

## 步骤

1. **合同门**：调用 `planner` subagent（Task 工具），要求其执行只读侦察并产出版本化合同与 Maker 转发消息。
   planner 返回后，向产品负责人（用户）呈报：当前结论 / 建议目标 / 明确不做 / 主要风险 / 需要决定 / 下一步。
   **必须等待用户明确批准合同后才能继续**；"继续"不等于批准扩大的范围。
2. **候选门**：批准后调用 `maker` subagent，原样转发合同消息。要求 maker 返回：精确候选 SHA、完成说明路径、快速测试结果。
   maker 返回后候选即冻结，不得要求其继续修改。
3. **证据门 + 冻结门**：调用 `checker` subagent，传入任务 ID、合同路径、基线 SHA、候选 SHA、完成说明路径，要求独立验收。
4. **失败处理**：checker FAIL 时，再次调用 `planner` 将阻断项转换为窄修复合同（新轮次 rounds/<NN+1>/）。
   **连续两轮 FAIL 必须停止**，向产品负责人呈报选项：缩小范围 / 改变方案 / 接受风险 / 更换 Maker / 暂停或取消。
5. **发布门**：checker PASS 后只报告验收结果、锁定的精确 SHA 与剩余项。**不 push**；不得把"继续""可以"推断为发布授权或启动下一切片的授权。

## 每次阶段切换必须向用户报告

- 当前状态（状态机中的位置）；
- 下一个执行者（planner / maker / checker / 产品负责人）；
- 需要产品负责人作出的明确决定（如有）。

## 工件纪律

- 所有合同、完成说明、验收报告写入 `docs/dev-flow/tasks/<TASK-ID>/`，只新增版本，不覆盖历史。
- TASK-ID 由你按 `T-<日期>-<短名>` 生成并在首次报告中告知用户。
