# Maker 完成说明 — V2-T8 第 3 轮（shell scope 迁移到 capabilities，修复启动 panic）

## 合同与基线

- 有效合同：`tasks/V2-T8/01-planner-task-contract-v3.md`（v3，转发消息 v3 声明有效；v1/v2 作历史）
- 起始 SHA：`97b3945200c86c43fa931bca8f7f4163da26edf3`（合同 v3 提交；开工前已核实 `git rev-parse HEAD` 一致且 `git status --short` 干净）
- 轮次目录：rounds/03
- 备注：合同 v3 文本内"状态"字段仍标 DRAFT（待批准），但致 Maker 转发消息 v3 已声明 v3 为有效合同且产品负责人以"请执行"指令启动，据此开工。

## 唯一主要变化

修复首次运行时启动 panic（`PluginInitialization("shell", "Error deserializing 'plugins.shell' ... unknown field 'scope', expected 'open'")`）：
- `tauri.conf.json` 删除 `plugins.shell` 配置块（该节在 Tauri 2 仅支持 `open`，v1 的 `scope` 字段不被接受）
- `capabilities/default.json` 将 `"shell:default"` 替换为显式权限：`shell:allow-spawn`（scope 条目 `{"name":"python-uvicorn","cmd":"python","args":true}`）+ `shell:allow-kill`

引擎子进程 spawn/kill 语义不变：`engine.ts` 的 `Command.create("python-uvicorn", ...)` 与 `child.kill()` 保持不变（desktop/src/** 未动）。

## 候选

- 候选 SHA：`b0c3b40d9355f74da29f9e2e5cb5f8178c0ddcd3`
- 父提交：`97b3945200c86c43fa931bca8f7f4163da26edf3`
- 提交标题：V2-T8 第3轮候选：shell scope 迁移到 capabilities（Tauri 2 语法，修复启动 panic）
- 精确修改文件（2 项，合同 §4 允许范围内）：
  - `desktop/src-tauri/tauri.conf.json` — 删除 `plugins.shell` 块（-11 行）
  - `desktop/src-tauri/capabilities/default.json` — `"shell:default"` → `shell:allow-spawn`（带 scope）+ `shell:allow-kill`

## 关键设计决策

- 严格按合同 §3 实现导航：删 `plugins.shell` 块；capabilities 用显式权限对象。scope 条目字段用 `cmd`（非 v1 的 `command`），与 tauri-plugin-shell 2.3.5 的 `ShellScopeEntry` schema 一致（`name`+`cmd` 必填，`args` 布尔放行任意参数）。
- `kill` 无需 scope 条目：tauri-plugin-shell 2.3.5 的 `kill` 命令按已 spawn 子进程 pid 追踪，`shell:allow-kill` 权限即足够（据构建产物 acl-manifests.json 中 `allow-kill` 定义确认）。
- 未引入任何依赖、未重建 dist/、未改任何 src 源码（engine.ts / lib.rs / Cargo.* / package*.json 均未动）。

## 验收标准对照

| 验收项（合同 v3 §6） | 结果 | 证据 |
|---|---|---|
| diff 仅两 JSON 文件 | ✅ | `git diff 97b3945..b0c3b40 --name-only` 恰为该两文件 |
| cargo check / vitest / vue-tsc 全绿 | ✅ | cargo check exit 0；vitest 12 passed；vue-tsc 无错误 |
| `npm run tauri dev` 启动无 panic | ⏳ | 产品负责人实跑（B 级），Maker 不自宣启动成功 |
| scope 名称保持 `python-uvicorn`，spawn/kill 语义不变 | ✅ | capabilities scope 条目 `name=python-uvicorn`；engine.ts 未改 |

## 快速验证记录（按合同 v3 §7 顺序）

| 命令 | 结果 |
|---|---|
| `cargo check`（desktop/src-tauri） | exit 0：Compiling fairyreport-desktop + Finished 2.92s |
| `npx vitest run`（desktop） | exit 0：12 passed（engine 5 + api 7），621ms |
| `npx vue-tsc --noEmit`（desktop） | exit 0：无错误 |

第 4 项（`npm run tauri dev` 实跑）按合同由产品负责人执行，Maker 侧未执行、未宣布启动成功。

失败记录：无（三项 A 级验证一次通过，未触任何停止条件）。

## 明确保留（未改动）

- desktop/src/**（含 engine.ts）、src-tauri/src/**、Cargo.toml/Cargo.lock、package*.json、dist/**、.gitignore、engine/**、backend/**、generic_knowledge/**、.opencode/、AGENTS.md 均未动（git 核实）

## 未执行项（移交人工 B 级）

- `npm run tauri dev` 启动验证（Login 页出现、无 panic）——产品负责人执行，B 级证据并入第 3 轮记录

## 冻结声明

未 amend、未 rebase、未 push；候选 `b0c3b40d9355f74da29f9e2e5cb5f8178c0ddcd3` 已冻结，本完成说明为独立提交，等待独立 Checker 对精确 SHA 验收。
