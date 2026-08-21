# 任务合同 V2-T8 v3 — 范围增补：shell scope 配置修复（第 3 轮验收基线）

- 状态：READY_FOR_CHECKER（第 3 轮；候选 b0c3b40d9355f74da29f9e2e5cb5f8178c0ddcd3，完成说明 ba06e72）
- 批准记录：产品负责人 2026-08-21 以"请执行"指令启动第 3 轮，视为批准本合同（状态字段补记于第 3 轮交付后）
- 变更说明：v2 第 2 轮 PASS 锁定 `fa541fd83e8189a40c543159351a33945643b904`；B 级人工验证捕获首次运行时失败（A 级静态检查不可见，运行时反序列化错误）：

  ```text
  thread 'main' panicked at src\lib.rs:65:10:
  error while running FairyReport desktop application:
  PluginInitialization("shell", "Error deserializing 'plugins.shell' within your
  Tauri configuration: unknown field `scope`, expected `open`")
  ```

  根因：`tauri.conf.json` 的 `plugins.shell.scope` 是 Tauri v1 语法；Tauri 2 的 shell 插件配置仅接受 `open` 字段，命令白名单 scope 必须在 capabilities 权限条目中声明。v3 将该窄修复合法化；其余条款不变，v1/v2 保留作历史。
- 产品决定来源：产品负责人 2026-08-21 "请执行"指令（批准本合同并启动第 3 轮）
- 精确起始 SHA：本合同提交后的 master HEAD
- 工作树门禁：`git status --short` 必须干净

## 1. 唯一主要变化

应用可正常启动：shell 插件初始化不再 panic；`python-uvicorn` 命令白名单从 `tauri.conf.json` 迁移到 capabilities 声明（Tauri 2 语法），引擎子进程 spawn/kill 权限语义不变。**无任何其他行为变化。**

## 2. 明确不做

- 不改 `desktop/src/**` 前端源码（engine.ts 的 `Command.create("python-uvicorn", ...)` 保持不变）
- 不改 `src-tauri/src/*.rs` 命令实现、Cargo.toml/Cargo.lock、package.json/lock
- 不重建 dist/、不引入任何依赖

## 3. 实现导航

- `desktop/src-tauri/tauri.conf.json`：删除 `plugins.shell` 配置块（该节在 Tauri 2 仅支持 `open` 字段）
- `desktop/src-tauri/capabilities/default.json`：把 `"shell:default"` 替换为显式权限对象，scope 条目字段按 tauri-plugin-shell v2 文档（注意是 `cmd` 不是 `command`），示例结构：

  ```json
  {
    "identifier": "shell:allow-spawn",
    "allow": [{ "name": "python-uvicorn", "cmd": "python", "args": true }]
  }
  ```

  至少覆盖 `shell:allow-spawn` 与 `shell:allow-kill`（engine.ts 用 spawn + kill）；如运行时仍报权限不足，按同一 scope 条目补对应 identifier。

## 4. 允许修改

- `desktop/src-tauri/tauri.conf.json`、`desktop/src-tauri/capabilities/default.json`
- `docs/dev-flow/tasks/V2-T8/**`

## 5. 禁止修改

- 上述以外一切文件（含 desktop/src/**、src-tauri/src/**、Cargo.*、package*.json、dist/**、.gitignore、engine/**、backend/**）

## 6. 验收标准

- [ ] `git diff <起始SHA>..<候选SHA>` 仅上述两个 JSON 文件
- [ ] `cargo check`（desktop/src-tauri）、`npx vitest run`、`npx vue-tsc --noEmit` 仍全绿
- [ ] `npm run tauri dev` 启动无 panic、Login 页出现（产品负责人实跑，B 级证据并入第 3 轮记录）
- [ ] scope 名称保持 `python-uvicorn`，引擎 spawn/kill 语义不变

## 7. 快速验证（按顺序）

1. `cargo check`（workdir=desktop/src-tauri）
2. `npx vitest run`（workdir=desktop）
3. `npx vue-tsc --noEmit`（workdir=desktop）
4. `npm run tauri dev` 启动验证（产品负责人执行；Maker 侧可用 `cargo build` 替代确认编译通过，但不得自行宣布启动成功）

## 8. 停止条件

- 基线/工作树不符；越界；同一失败两次；
- 按 Tauri 2 shell 插件文档两次尝试仍无法启动 → 停止报告（不擅自换插件/换壳）。

## 9. 候选提交与完成说明

- 候选只含两个 JSON 文件
- 完成说明写到 `docs/dev-flow/tasks/V2-T8/rounds/03/maker-completion.md`，单独提交
- 不 amend、不 rebase、不 push

## 10. 已知基线失败

- B 级首次失败：`npm run tauri dev` 启动 panic（原文见变更说明）。修复前不得重复实跑超过两次。
