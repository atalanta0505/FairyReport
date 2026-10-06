# Checker 验收报告 — V2-T50 v1

- **任务 ID**：V2-T50
- **合同版本**：v1（`docs/dev-flow/tasks/V2-T50/01-planner-task-contract-v1.md`）
- **待验收 SHA**：`cdd737b5f36d10743026f0f15059d5d2dcdc64eb`
- **基线 SHA**：`ef5a19236258cbb86ceb5c4b739f58fdafa1642c`
- **验收结论**：**PASS**
- **验收日期**：2026-10-06

## 0. 验收者身份与独立性声明（重要）

本轮验收由**独立上下文的 Checker 子代理**执行（不是 Maker 会话）。但必须如实记录两点局限：

1. **同模型**：该子代理继承会话默认模型 `deepseek-flash`，与 Maker 相同，未实现"跨模型降低相关性误差"；
2. **无只读护栏**：`docs/dev-flow/dsh-checker-subagent.md` 描述的 `checker` 实例（固定 `deepseek-v4-pro` + `toolFilter.deny=[write,edit]`）**尚未生效**（需重启 DSH）。

替代性约束：验收全程只使用只读命令；开始与结束各记录一次 `git rev-parse HEAD` 与 `git status --short`（含 `--untracked-files=all`），两次读数逐字节一致，工作树无残留。

因此本报告的证据等级为 **A 级（门禁可复现）+ C 级（源码审查）**，独立性为"独立上下文、同模型"。

## 1. 合同条款核验

| AC | 结论 | 独立证据 |
|---|---|---|
| AC1 脚本存在、返回 0 | PASS | `powershell -NoProfile -File scripts\verify.ps1` → exit 0（多次） |
| AC2 覆盖 5 项门禁且不重复 | PASS | 5 项与 README:171–188 一一对应；脚本用 `npx vite build` 而非 `npm run build`（后者=`vue-tsc --noEmit && vite build` 会重复类型检查），正合"不重复"要求 |
| AC3 结构化 JSON | PASS | 每条含 gate/label/command/workdir/status/exitCode/seconds/summary，另有 git/passed/selected |
| AC4 前后 git 状态 + worktreeStable | PASS | `headBefore=headAfter=cdd737b…`，`statusBefore=statusAfter=""`，`worktreeStable=true` |
| AC5 失败即停 + 非 0 退出 | PASS（实证） | 临时副本令 Vitest 使用非法标志：仅该门禁执行即停止、打印输出尾部、`status=FAIL`、exit 1；副本已删除 |
| AC6 `-Fast` / `-Only` | PASS（实证） | `-Fast` 4 项（跳过 build）；`-Only typecheck` 1 项；`-Only unit-desktop,typecheck`（`-File` 形式）2 项；未知 id 与选空均 exit 2 |
| AC7 三处文档修正 | PASS | AGENTS.md 测试事实与实测一致（172 pytest / 196 Vitest）；PROCESS.md 工件命名与磁盘逐一核对一致；子代理条款已更新 |
| AC8 纯 ASCII + PS 5.1/7 | PASS（5.1 实证，7 未实证） | 无 BOM、无非 ASCII 字节，在 Windows PowerShell 5.1 下多次成功执行；本机未安装 pwsh 7 |

## 2. 门禁证据（候选绑定）

`verify-report.json` 由被验收 SHA 上的干净工作树重新生成（`headBefore=headAfter=cdd737b…`，前后 `git status --short` 为空）：

```
unit-desktop   PASS   1.8s  Tests  196 passed (196)
typecheck      PASS   2s    no type errors
build          PASS   1.7s  built in 968ms
unit-engine    PASS   71s   172 passed, 2 warnings in 68.74s
rust-check     PASS   0.8s  Finished `dev` profile ... in 0.71s
RESULT: PASS        exit code 0
```

## 3. 两轮独立检查的问题闭环

第 1 轮（候选 `0a20a9a`）结论 PASS，提出 4 项非阻断缺陷：

| # | 第 1 轮意见 | 状态 |
|---|---|---|
| 1 | `-File` + `-Only a,b` 选 0 门禁却报 PASS（假绿） | **已修并实证**（`cdd737b`）：按逗号拆分、未知 id 与选空 exit 2 |
| 2 | 失败门禁摘要回落到 passSummary，出现"FAIL + all tests passed" | **已修并实证**：仅 exit 0 使用 passSummary |
| 3 | `verify-report.json` 未绑定候选 SHA | **已修**：本报告同提交的 JSON 绑定 `cdd737b` + 干净树 |
| 4 | 文档命名与模型选择条款不精确 | **已修**：命名按轮次后缀列全；第 14 行改为"默认手动选择 + preset 例外" |

第 2 轮（候选 `cdd737b`）结论 PASS，确认上述 3 项实证修复，另提出 2 项残余（见 §4）。

## 4. 阻断项与非阻断风险

- **阻断项**：无。
- **非阻断风险（转下一轮切片）**：
  1. **stderr 清洗不完整**：`Remove-NativeStderrNoise` 只覆盖 `CategoryInfo`/`FullyQualifiedErrorId`/`RemoteException`，PowerShell 指针帧（`At <path>:NNN char:NN`、`+ ~~~`）仍可能让失败摘要退化为装饰行。
  2. **PROCESS.md 角色表（第 10–12 行）**仍写无限定语的"产品负责人手动选择"，与第 14–15 行的 preset 例外有轻微张力；工件命名块未列出 T38 的 `04-checker-acceptance-report-v1.md`。
  3. **`-KeepGoing` 失败路径**未复测；**pwsh 7** 本机无法实证。
  4. **`README.md` 与 `templates/planner-task-contract.md:59`** 仍指向旧的 5 条散装命令 / `rounds/<NN>/`，不在本切片允许路径内。

## 5. Git 读数

- 验收对象：`cdd737b5f36d10743026f0f15059d5d2dcdc64eb`
- 开始：`git rev-parse HEAD` = `cdd737b…`；`git status --short` 空（`--untracked-files=all` 亦空）
- 结束：`git rev-parse HEAD` = `cdd737b…`；`git status --short` 空（`--untracked-files=all` 亦空）
- 本报告的提交**只新增证据与验收记录**，不含任何代码或合同改动，故被验收 SHA 保持 `cdd737b` 不变。

## 6. 发布建议

本切片无发布动作（纯开发流程基础设施）。若产品负责人决定推送，应推送 `cdd737b` 及其后的验收记录提交，并在推送前后比对远端 SHA。
