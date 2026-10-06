# Maker 完成说明 — V2-T50 v1.2

- 状态：READY_FOR_CHECKER
- 合同：`docs/dev-flow/tasks/V2-T50/01-planner-task-contract-v1.md`（v1，未变更——本文件记录的全部改动都在 AC1–AC8 之内，属"让实现真正满足既有验收标准"，不是范围扩张）
- 基线 SHA：`ef5a19236258cbb86ceb5c4b739f58fdafa1642c`
- 候选 SHA：本文件最后修订所在提交（由 Checker 用 `git rev-parse HEAD` 读取）
- 授权来源：产品负责人会话指令"上述①②③你都可以自己执行吗？我给你全部所需的授权"（2026-10-06）

## 1. 变更清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `scripts/verify.ps1` | 新增 | 5 项全量门禁的唯一入口，输出表格 + JSON + 前后 git 状态 |
| `AGENTS.md` | 修改 | 测试规模基线改为事实；新增"全量门禁"一条 |
| `docs/dev-flow/PROCESS.md` | 修改 | 修正 3 处过期条款（子代理禁令、测试现状、工件命名），A 级证据指向门禁脚本，模型选择条款与新机制对齐 |
| `docs/dev-flow/tasks/V2-T50/01-planner-task-contract-v1.md` | 新增 | 本切片合同 |
| `docs/dev-flow/tasks/V2-T50/verify-report.json` | 新增 | 门禁证据（候选绑定版本随验收提交一并入库，见 §3） |
| `docs/dev-flow/dsh-checker-subagent.md` | 新增 | §7 的 DSH preset 注入说明（配置本身在仓库外） |

未触碰 `engine/**`、`desktop/**`、`.github/**`、依赖清单与 `.env*`。

## 2. 逐条验收标准与证据

| AC | 结论 | 证据 |
|---|---|---|
| AC1 脚本存在且返回 0 | 通过 | 多次全量运行 exit 0，其中按文档命令形式 `powershell -NoProfile -File scripts\verify.ps1` 执行 |
| AC2 覆盖 5 项门禁且不重复 | 通过 | 5 条命令互不重复（构建用 `npx vite build`，类型检查单独一条） |
| AC3 结构化 JSON | 通过 | 每条含 gate/label/command/workdir/status/exitCode/seconds/summary（+ git 区块、passed、selected） |
| AC4 前后 git 状态 + worktreeStable | 通过 | JSON `git.worktreeStable`，实测多次运行恒为 true |
| AC5 失败即停 + 非 0 退出 | 通过（**实证**） | 临时副本把 Vitest 参数改为非法标志后运行：仅该门禁执行即停止、打印输出尾部、`status=FAIL`、exit 1；`-KeepGoing` 时跑完再 exit 1。临时副本已删除，工作树无残留 |
| AC6 `-Fast` / `-Only` | 通过（**实证**） | `-Fast` 跳过 build（4 项）；`-Only typecheck` 恰 1 项；`-Only unit-desktop,typecheck`（`-File` 形式）恰 2 项 |
| AC7 三处文档修正 | 通过 | AGENTS.md / PROCESS.md 对应行已更新，且按第 1 轮 Checker 意见进一步精确化 |
| AC8 纯 ASCII + 5.1/7 兼容 | 通过 | 本机无 `pwsh`（仅 Windows PowerShell 5.1），脚本全程在该版本下执行成功 |

## 3. 门禁证据（A 级）

开发期一次全量运行（HEAD `0a20a9a` 的加固前版本）：

```
GATE           STATUS  SECONDS  SUMMARY
unit-desktop   PASS        1.8  Tests  196 passed (196)
typecheck      PASS        2    no type errors
build          PASS        1.7  built in 934ms
unit-engine    PASS       84.1  172 passed, 2 warnings in 82.15s
rust-check     PASS        0.8  Finished `dev` profile ... in 0.73s
worktreeStable: True
RESULT: PASS
```

**候选绑定证据**：`verify-report.json` 只有在候选提交产生之后运行才能绑定候选 SHA。本轮把它与 Checker 验收报告放在同一个收尾提交里入库，其中 `git.headBefore == git.headAfter ==` 被验收的候选 SHA、`statusBefore/statusAfter` 均为空。第 1 轮 Checker 已指出前一版 JSON 绑定的是 `6bbc9ca` + 脏树，该缺陷即由此修正。

## 4. 第 1 轮独立检查意见与处置

第 1 轮由**独立上下文**的 Checker 子代理（同模型，机制尚未生效）验收 `0a20a9a`，结论 **PASS**，同时给出 4 项非阻断缺陷。处置如下：

| # | 意见 | 处置 |
|---|---|---|
| 1 | `-File` + `-Only a,b` 只选中 0 个门禁，却报 PASS/exit 0（**假绿**） | 已修：`-Only` 按逗号拆分；未知门禁 id 报错 exit 2；选空报错 exit 2。已实测三种情形 |
| 2 | 失败门禁的 summary 回落到 passSummary，出现"FAIL + all tests passed"自相矛盾文本 | 已修：仅在 exit code 0 时使用 passSummary；失败时用输出中的真实摘要/末行。已实测 |
| 3 | `verify-report.json` 绑定 `6bbc9ca` + 脏树，未绑定候选 SHA | 已修：见 §3，候选绑定版本随验收提交入库 |
| 4 | 文档细节：`现行（V2-T36 起）`不精确；PROCESS.md 第 14 行"一律手动选择"与第 15/72 行"由 preset 固定"存在张力 | 已修：命名说明改为按轮次实际后缀逐一列出；第 14 行改为"默认手动选择"，并说明 preset 固定模型的情形 |

另采纳其"stderr 装饰污染 summary"的观察（5.1 下 `2>&1` 会把原生 stderr 包装成 PowerShell 错误记录），新增 `Remove-NativeStderrNoise` 清洗后再提取摘要。

## 5. 未做项与残余人工项

1. **`README.md` 未改**：README:171–188 仍罗列 5 条散装命令；不在合同 §5 允许路径内，留给后续切片（建议补一行：`一条命令跑完全部 5 项：powershell -NoProfile -File scripts\verify.ps1`）。
2. **`templates/planner-task-contract.md:59`** 仍指向 `rounds/<NN>/`；合同 §3 明确"不改模板"，故留作后续切片。
3. **pwsh 7 路径未实证**：本机未安装 pwsh，仅有 Windows PowerShell 5.1。
4. **HUMAN_ACTION_REQUIRED（产品负责人）**：重启 DSH 桌面端，确认新会话出现 `checker` 工具；preset 注入已通过 YAML 解析与结构断言，运行时组装未验证。
5. **`checker` 首次实跑**：留给下一个切片作为其验收者。

## 6. 停止条件复盘

无触发：基线 SHA 与工作树在开始前均已核验；未越界修改、未安装依赖、未 push。

## 7. 自检声明

- 唯一写入者：本轮仅本会话写入上述文件；
- 未 amend / 未 rebase / 未 push；
- `.env` 未被读取、打印或写入任何工件；
- 未跟踪文件未清理、未暂存（提交只含合同 §5 与 §7 允许的路径；自检用的临时脚本已删除，`git status` 可证）。

## 8. 修订记录

- **v1**（提交 `6bbc9ca`）：按合同 v1 落地，文档命令形式写作 `pwsh -File scripts/verify.ps1`。
- **v1.1**（提交 `0a20a9a`）：本机无 `pwsh`（实测 `Get-Command pwsh` 为空，实为 Windows PowerShell 5.1），已把脚本头、AGENTS.md、PROCESS.md、合同统一改为 `powershell -NoProfile -File scripts\verify.ps1` 并按该形式重跑门禁。
- **v1.2**（本提交）：按第 1 轮独立检查意见加固脚本（假绿、FAIL 摘要、stderr 噪声）并精确化 PROCESS.md 两处措辞；候选绑定证据与验收报告随后一并入库。
