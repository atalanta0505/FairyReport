# FairyReport_lite 开发流程（PMC）

基于《可移植的 AI 协作开发手册》裁剪的项目流程。核心：**以产品决定为输入，以版本化任务合同约束实现，以本地候选 SHA 冻结结果，以分级证据证明行为，以独立 Checker 作出判定，以产品负责人对精确 SHA 授权发布。**

## 角色与模型

| 角色 | 执行者 | LLM | 职责 | 禁止 |
|---|---|---|---|---|
| 产品负责人 | 用户 | — | 范围、优先级、风险、发布授权 | — |
| Planner | 主会话（本窗口） | qwen3.8-max | 只读侦察、切片、合同、协调 | 改产品代码、扩需求、宣布通过 |
| Maker | 独立会话：主代理切 maker | glm-5.2 | 唯一写入者，实现合同，产出冻结候选 | 改需求、push、amend、rebase |
| Checker | 独立会话：主代理切 checker | deepseek-v4-pro-0813 | 对精确 SHA 独立验收 | 改代码、改需求、相信 Maker 自述 |

三个角色使用三个不同家族的 LLM，降低相关性误差；Checker 与 Maker 模型隔离是刻意设计。
协调者为主会话；Maker/Checker 由产品负责人在独立会话执行（主代理切到对应角色、粘贴转发话术直接执行）。**不使用 @ 子代理委派**（该通道在本环境实测空返回）。

## 状态机

```text
DRAFT → READY_FOR_MAKER → MAKING → READY_FOR_CHECKER → ACCEPTED → PUSH_AUTHORIZED → PUSHED
失败循环：READY_FOR_CHECKER → CHANGES_REQUESTED → MAKING → READY_FOR_CHECKER
范围变化：任意未发布状态 → PRODUCT_DECISION_REQUIRED → 新合同版本 / 新修复轮次
```

## 六个硬门禁

1. **合同门**：没有版本化任务合同（`docs/dev-flow/tasks/<TASK-ID>/01-*`），不进入 Maker。
2. **候选门**：没有本地候选 SHA 和完成说明，不进入验证与 Checker。
3. **证据门**：没有逐项、可复核且候选绑定的证据，不得 ACCEPTED。
4. **冻结门**：代码、合同或验收标准变化后，旧验收立即失效。
5. **轮次门**：连续两轮 Checker 不通过，停止自动修复，交产品负责人再决策。
6. **发布门**：没有对精确已验收 SHA 的明确授权，不得推送。

## 证据等级

| 等级 | 证据 | 说明 |
|---|---|---|
| A | `python -m pytest` 自动化测试、可复现命令输出 | 高风险项首选 |
| B | Streamlit GUI 人工操作观察 | 无法自动化时使用，列入剩余人工项 |
| C | 源代码/配置检查 | 证明实现存在，不能单独证明运行正确 |
| D | Maker 自述 | 仅作线索，不作为验收结论 |

验证漏斗（前一级失败即停止）：目标单测 → 静态/模块检查 → 全量回归 → 构建/打包 → GUI/人工证据 → Checker 判定。

## 工件位置（只新增版本，不覆盖历史）

```text
docs/dev-flow/
  PROCESS.md                 本文件
  templates/                 合同 / 完成说明 / 验收报告模板
  tasks/<TASK-ID>/
    00-product-decision-v<N>.md      产品决定（可选）
    01-planner-task-contract-v<N>.md 任务合同
    02-planner-to-maker-message-v<N>.md Maker 转发消息
    rounds/<NN>/
      maker-completion.md    Maker 完成说明
      checker-report.md      Checker 验收报告
      checker-fix-task.md    FAIL 时的窄修复输入
```

## 项目特定适配

- **前置条件**：本流程依赖精确 Git SHA。仓库必须先 `git init` 并建立基线提交；未初始化时 Planner 应报告阻断。
- **测试现状**：仓库暂无 pytest 用例；每个涉及行为变化的切片，合同必须包含 Maker 先补最小目标测试（pytest + pytest-bdd）。
- **GUI 证据**：Streamlit 界面行为用 B 级证据（人工操作），在隔离数据目录（`FRL_DATA_DIR` 指向临时目录）下运行，避免污染真实项目数据。
- **凭据**：`.env` 中的 API Key 永不进入提交、报告或截图。
- **依赖**：安装/升级依赖前必须获产品负责人批准。
- **人工分工（V2 起）**：开发依赖的下载与安装、GUI 截图验证（B 级证据）由产品负责人承担；凭据类操作（如邮箱 SMTP 授权码）按 HUMAN_ACTION_REQUIRED 交接。Agent 不等待回复的时间计入工时。
- **运行模式（V2 起，T3 后修正）**：Planner+协调 = 主会话；Maker/Checker 由产品负责人在独立会话运行：Tab 把主代理切到 maker/checker（`mode: all`，自动绑定 glm-5.2 / deepseek-v4-pro-0813 与权限护栏），粘贴含精确 SHA 的转发话术直接执行；**禁止 @ 子代理委派**（实测空返回）。产品负责人回贴完成说明/验收报告。产品负责人未给出清晰指令词（如"T? 开工"）前，不启动任何实现。

## 每轮最小检查表

- Planner：基线已确认；单一主要行为；不做项与路径边界清晰；目标测试与停止条件齐备；转发话术可直接交付。
- Maker：起始 SHA 匹配；唯一写入者；只改允许范围；保留首次失败；候选 SHA + 完成说明齐备；已冻结。
- Checker：独立读取合同/diff/证据；未以 Maker 自述为结论；明确重跑与审查边界；FAIL 只给阻断项；PASS 锁定 SHA。
- 发布：授权针对精确 SHA；推送前后远端 SHA 精确比对；残余项已报告。
