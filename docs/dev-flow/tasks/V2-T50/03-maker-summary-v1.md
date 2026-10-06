# Maker 完成说明 — V2-T50 v1.1

- 状态：READY_FOR_CHECKER
- 合同：`docs/dev-flow/tasks/V2-T50/01-planner-task-contract-v1.md`（v1）
- 基线 SHA：`ef5a19236258cbb86ceb5c4b739f58fdafa1642c`
- 候选 SHA：本文件最后修订所在提交（由 Checker 用 `git rev-parse HEAD` 读取）
- 授权来源：产品负责人会话指令"上述①②③你都可以自己执行吗？我给你全部所需的授权"（2026-10-06）

## 1. 变更清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `scripts/verify.ps1` | 新增 | 5 项全量门禁的唯一入口，输出表格 + JSON + 前后 git 状态 |
| `AGENTS.md` | 修改 | 测试规模基线改为事实；新增"全量门禁"一条 |
| `docs/dev-flow/PROCESS.md` | 修改 | 修正 3 处过期条款（子代理禁令、测试现状、工件命名），并把 A 级证据指向门禁脚本 |
| `docs/dev-flow/tasks/V2-T50/01-planner-task-contract-v1.md` | 新增 | 本切片合同 |
| `docs/dev-flow/tasks/V2-T50/verify-report.json` | 新增 | 本轮门禁证据（机器可读） |
| `docs/dev-flow/dsh-checker-subagent.md` | 新增 | §7 的 DSH preset 注入说明（配置本身在仓库外） |

未触碰 `engine/**`、`desktop/**`、`.github/**`、依赖清单与 `.env*`。

## 2. 逐条验收标准与证据

| AC | 结论 | 证据 |
|---|---|---|
| AC1 脚本存在且返回 0 | 通过 | 三次全量运行 exit code 0，其中一次严格按文档命令形式（`powershell -NoProfile -File scripts\verify.ps1`）执行 |
| AC2 覆盖 5 项门禁且不重复 | 通过 | 5 条命令互不重复（构建用 `npx vite build`，类型检查单独一条） |
| AC3 结构化 JSON | 通过 | `verify-report.json`：每条含 gate/label/command/workdir/status/exitCode/seconds/summary |
| AC4 前后 git 状态 + worktreeStable | 通过 | JSON `git.worktreeStable = true`（HEAD 前后一致） |
| AC5 失败即停 + 非 0 退出 | 通过（C 级代码审查） | 未指定 `-KeepGoing` 时 `break` 并打印失败门禁输出尾部；本切片无红灯门禁可实证 |
| AC6 `-Fast` / `-Only` | 通过 | `-Only unit-desktop,typecheck` 实测只跑 2 项、exit 0 |
| AC7 三处文档修正 | 通过 | AGENTS.md、PROCESS.md 对应行已更新 |
| AC8 纯 ASCII + 5.1/7 兼容 | 通过 | 本机**没有 pwsh**（只有 Windows PowerShell 5.1），脚本按文档命令形式在该版本下执行成功 |

## 3. 门禁证据（A 级，绑定提交 `6bbc9ca`）

```
GATE           STATUS  SECONDS  SUMMARY
unit-desktop   PASS        1.8  Tests  196 passed (196)
typecheck      PASS        2    no type errors
build          PASS        1.7  built in 941ms
unit-engine    PASS       70.2  172 passed, 2 warnings in 68.39s
rust-check     PASS        0.8  Finished `dev` profile ... in 0.69s
worktreeStable: True  (HEAD 6bbc9caf1eb24a866f4f35042d43d221891a733b)
RESULT: PASS
```

完整机器可读结果见 `verify-report.json`。

## 4. 未做项与残余人工项

1. **`README.md` 未改**：README:171–188 仍罗列 5 条散装命令。它不在本合同 §5 的允许路径内，按"不做项与路径边界清晰"原则留给后续切片（建议补一行：`一条命令跑完全部 5 项：powershell -NoProfile -File scripts\verify.ps1`）。
2. **`-KeepGoing` 的失败路径未被实证**：本切片无红灯门禁可触发，只有 C 级代码审查证据。
3. **HUMAN_ACTION_REQUIRED（产品负责人）**：重启 DSH 桌面端，确认新会话出现 `checker` 工具；preset 注入已通过 YAML 解析与结构断言，但运行时组装未验证。
4. **`checker` 首次实跑**：留给下一个切片作为其验收者。

## 5. 停止条件复盘

无触发：基线 SHA 与工作树在开始前均已核验；未越界修改、未安装依赖、未 push。

## 6. 自检声明

- 唯一写入者：本轮仅本会话写入上述文件；
- 未 amend / 未 rebase / 未 push；
- `.env` 未被读取、打印或写入任何工件；
- 未跟踪文件未清理、未暂存（提交只含本合同 §5 与 §7 允许的路径）。

## 7. 修订记录

- **v1**（提交 `6bbc9ca`）：按合同 v1 落地，文档命令形式写作 `pwsh -File scripts/verify.ps1`。
- **v1.1**（本提交）：自查发现本机并无 `pwsh`（`Get-Command pwsh` 为空；实际为 Windows PowerShell 5.1，`C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe`）。已把脚本头、AGENTS.md、PROCESS.md、合同中的命令统一改为 `powershell -NoProfile -File scripts\verify.ps1`，并**按该形式重跑全部 5 项门禁**、刷新 `verify-report.json`。这与本轮要修的"文档与事实脱钩"属同一类缺陷，故在本切片内一并修正，不留给下游。
