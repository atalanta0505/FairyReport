# Checker 验收报告 — V2-T8 第 3 轮

- 状态：**PASS**
- 精确候选 SHA：b0c3b40d9355f74da29f9e2e5cb5f8178c0ddcd3
- 依据合同：`tasks/V2-T8/01-planner-task-contract-v3.md`（v3；v1/v2 及前两轮报告作历史）
- 基线 SHA：97b3945200c86c43fa931bca8f7f4163da26edf3

## 独立检查边界

- 独立重跑（本轮全部自行执行，未采信 Maker 自述）：
  - `cargo check`（workdir=desktop/src-tauri）→ exit 0：`Finished dev profile`（0.41s）
  - `npx vitest run`（workdir=desktop）→ exit 0：**12 passed**（api 7 + engine 5），681ms
  - `npx vue-tsc --noEmit`（workdir=desktop）→ exit 0：无类型错误
  - 两个 JSON 配置文件 Python `json.load` 解析通过（语法有效）
- 代码级审查（A 级）：diff 逐行核对、tauri.conf.json 全文确认无 plugins.shell 残留、capabilities scope 语法核对、engine.ts spawn/kill 语义核对、零改动面核实。
- B 级人工项：`npm run tauri dev` 实跑（启动无 panic、Login 页出现）——按合同 v3 §7.4 由产品负责人执行，Checker 不代为宣布启动成功，列为待执行人工项。

## 验收标准逐条核对（合同 v3 §6）

| 合同标准 | 证据等级(A/B/C/D) | 证据与结论 |
|---|---|---|
| §6.1 diff 仅两个 JSON 文件 | A | `git diff --name-status 97b3945..b0c3b40` 恰为 `desktop/src-tauri/tauri.conf.json`(M) + `desktop/src-tauri/capabilities/default.json`(M)；无其他文件。 |
| §6.2 cargo check / vitest / vue-tsc 全绿 | A | 本轮独立重跑三项全部通过（见上）。 |
| §6.3 `npm run tauri dev` 启动无 panic、Login 页出现 | ⏳ | B 级，产品负责人实跑（待执行，见判定）。 |
| §6.4 scope 名称保持 `python-uvicorn`，spawn/kill 语义不变 | A | capabilities scope 条目 `{"name":"python-uvicorn","cmd":"python","args":true}`；`engine.ts:45-46` `Command.create("python-uvicorn", args, { cwd })` + `cmd.spawn()`、`:49/:97` `child.kill()`；`git diff 97b3945..b0c3b40 -- desktop/src/` 为空（前端零改动）。 |

## 重点审查

- **tauri.conf.json 无 plugins.shell 残留**：diff 显示 `-11` 行完整删除 `plugins.shell.scope` 块；候选后全文确认文件中已无任何 `plugins` 键——Tauri 2 仅接受该节 `open` 字段，删除即消除 panic 根因（`unknown field 'scope', expected 'open'` 反序列化错误）。
- **capabilities 使用 Tauri 2 语法**：
  - `"shell:default"` 字符串替换为显式权限对象：`{"identifier":"shell:allow-spawn","allow":[{"name":"python-uvicorn","cmd":"python","args":true}]}`——字段为 `cmd`（非 v1 的 `command`），与 tauri-plugin-shell v2 ShellScopeEntry schema 一致；`args:true` 放行任意参数（与 v1 配置 `args:true` 等价语义）。
  - 追加 `"shell:allow-kill"`，覆盖 `child.kill()`；kill 按已 spawn 子进程 pid 追踪，无需 scope 条目。
  - `core:default` 保留；`windows:["main"]` 不变。
- **零改动面**：name-status 仅两文件；desktop/src/**（含 engine.ts）、src-tauri/src/*.rs、Cargo.toml/Cargo.lock、package*.json、dist/** 全部零改动（diff 验证）；引擎 spawn/kill 语义不变。
- **编译期配置校验**：`cargo check` 通过意味着 `tauri.conf.json` 经 `generate_context!` 反序列化成功，候选配置对 Tauri 2 schema 有效。

## 修改范围复核

- 父链：`git log --oneline 97b3945..b0c3b40` 仅 b0c3b40 一个提交；`b0c3b40^ == 97b3945`。
- 候选后 `ba06e72`（完成说明）与流程文档提交（HEAD=47b68c0）不属候选范围。
- `git status --short` 干净。

## 阻断项（仅 FAIL）

无。

## 非阻断风险

- 运行时 capabilities 权限解析的最终确认（spawn/kill 实际放行）依赖 `npm run tauri dev` 实跑——该验证属 B 级人工项，本轮 A 级静态与编译检查已覆盖配置正确性。
- 若运行时仍报权限不足（如 kill 需单独 scope 条目），按合同 v3 §3 末条以同一 scope 条目补对应 identifier（不构成本轮阻断）。

## B 级待执行人工项（产品负责人）

1. `npm run tauri dev` 启动：窗口出现、无 panic、Login 页渲染（本项即第 3 轮修复的运行时验证）。
2. 用 `13476526@qq.com` 登录成功。
3. 引擎健康指示灯绿（子进程 spawn + /health 200）；应用退出子进程结束（kill 权限实际生效）。

## 判定

- **PASS**：锁定 `b0c3b40d9355f74da29f9e2e5cb5f8178c0ddcd3` 为 V2-T8 第 3 轮候选。B 级实跑由产品负责人执行并回贴观察；启动成功与否不影响本轮 A 级验收结论，但为发布前必需证据。