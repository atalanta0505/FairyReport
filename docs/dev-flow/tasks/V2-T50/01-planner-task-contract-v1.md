# Planner 任务合同 — V2-T50 v1

- 状态：READY_FOR_MAKER
- 产品决定来源：产品负责人在会话中下达"上述①②③你都可以自己执行"并给出全部所需授权（2026-10-06）；本切片只落其中的 ②③，① 的 DSH preset 注入见 §7，单独执行且不进入本仓库提交。
- 精确起始 SHA：`ef5a19236258cbb86ceb5c4b739f58fdafa1642c`
- 工作树门禁：`git status --short` 干净（已核验）

## 1. 背景与目标

PMC 流程的第 3 条硬门禁（证据门）目前靠人肉维持：README 第 171–188 行列了 5 条散装命令，Maker 与 Checker 各自贴一遍、各自抄一遍数字进文档，产物是一段段自然语言。同时有 3 处流程条款已与仓库事实脱钩（详见 §4），会误导后续 Agent。

本切片把门禁固化为一**条**可复现命令，并修正这 3 处条款。不改变任何产品运行时行为。

## 2. 唯一主要行为变化

仓库新增一条门禁入口 `scripts/verify.ps1`：顺序执行 5 项门禁，输出统一的表格与 JSON 结果，并在执行前后各记录一次 git 状态。

## 3. 明确不做

- 不修改 `engine/`、`desktop/` 下任何产品代码、测试代码或构建配置；
- 不新增依赖，不改 `requirements.txt`、`desktop/package.json`、`desktop/src-tauri/Cargo.toml`；
- 不改 `.github/workflows/release.yml`（CI 门禁是另一个切片）；
- 不改 `docs/dev-flow/templates/` 下的模板结构；
- 不 push、不 amend、不 rebase。

## 4. 交付物与验收标准

三项交付物，逐条对应验收标准：

- [ ] **AC1** `scripts/verify.ps1` 存在，且 `pwsh -File scripts/verify.ps1` 在干净工作树上返回 exit code 0；
- [ ] **AC2** 脚本覆盖 5 项全量门禁，且与 README:171–188 逐项一致：Vitest、vue-tsc、Vite 构建、Pytest、cargo check（构建项不与类型检查重复执行）；
- [ ] **AC3** 脚本输出结构化 JSON，每条包含 `gate/label/command/workdir/exitCode/seconds/summary`，Maker 与 Checker 可直接粘贴同一份结构，无需再各自抄数字；
- [ ] **AC4** 脚本在开始与结束各记录一次 `git rev-parse HEAD` 与 `git status --short`，并给出 `worktreeStable` 布尔值——这是 Checker 子代理"只读"的自证机制（配合 §7 的 `toolFilter`）；
- [ ] **AC5** 任一门禁失败时立即停止（默认），打印失败门禁的输出尾部，整体 exit code 非 0；
- [ ] **AC6** `-Fast` 可跳过前端生产构建；`-Only <id>` 可只跑指定门禁（用于快速回归）；
- [ ] **AC7** `AGENTS.md` 与 `docs/dev-flow/PROCESS.md` 中的 3 处过期条款已修正：
  1. "本仓库当前没有测试用例"（AGENTS.md:22、PROCESS.md:64）→ 改为按当前事实描述，并要求行为变化切片补最小目标测试；
  2. "禁止 @ 子代理委派（实测空返回）"（PROCESS.md:15、:70）→ 改为当前 DSH 已支持，并给出角色隔离的推荐用法；
  3. 工件命名漂移（PROCESS.md:55–58）→ 补齐 V2-T36 起实际使用的 `03-maker-summary / 04-checker-acceptance-report` 命名。
- [ ] **AC8** 脚本自身为纯 ASCII（Windows PowerShell 5.1 读取无 BOM UTF-8 会乱码），且在 PowerShell 5.1 与 pwsh 7 下均可运行。

## 5. 允许修改

- `scripts/verify.ps1`（新增）
- `AGENTS.md`
- `docs/dev-flow/PROCESS.md`
- `docs/dev-flow/tasks/V2-T50/**`（本切片的合同与完成说明）

## 6. 禁止修改

- 其余全部路径；尤其是 `engine/**`、`desktop/**`、`.github/**`、`requirements.txt`、`.env*`。

## 7. 附：Checker 子代理 preset 注入（不在本切片提交范围）

在 DSH profile patch 中为 `preset-ptc` / `preset-standard` 注入一个专用 `checker` 委派实例：`agentOptions` 固定 `deepseek-v4-pro`（与 Maker 的 `deepseek-flash` 强制不同）、`persona` 只读验收、`toolFilter.deny=[write,edit]`、`maxDepth=0`。该配置位于 `%USERPROFILE%\.dsh\profiles\desktop\cordis.patch.yml`，属产品负责人的 DSH 环境配置，**不进入本仓库**；仓库内仅保留一份可复核副本 `docs/dev-flow/dsh-checker-subagent.md`。

## 8. Maker 快速测试（按顺序）

1. `pwsh -File scripts/verify.ps1 -Only unit-desktop,typecheck`（脚本自身可跑通）
2. `pwsh -File scripts/verify.ps1`（全量 5 项，作为本切片的 A 级证据）
3. `git status --short`（确认脚本前后工作树一致）

## 9. Evidence Runner 分级验证计划

- A 级：`pwsh -File scripts/verify.ps1` 全量输出（本切片自举：脚本自己证明门禁）；
- C 级：脚本源码与 README 门禁清单逐项比对；
- 无 B 级 GUI 项：本切片不触及运行界面；残余人工项为"重启 DSH 后 `checker` 工具出现"（§7，由产品负责人确认）。

## 10. 候选提交与完成说明要求

- 本地候选提交，记录精确 SHA；不 amend、不 rebase、不 push；
- 完成说明写入 `docs/dev-flow/tasks/V2-T50/03-maker-summary-v1.md`。

## 11. 停止条件

- 起始 SHA 或工作树不符；需要修改禁止路径；需要安装依赖；同一失败两次；需要 GUI/凭据/产品决定。
