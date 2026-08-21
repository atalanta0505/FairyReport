# 致 Maker 的转发消息 V2-T8 v3

你是当前唯一可写 Maker。

工作目录：D:\Repo\FairyReport_lite
精确起始 SHA：本合同提交后的 master HEAD（开工前核实 `git rev-parse HEAD` 与 `git status --short` 干净）
有效合同：docs/dev-flow/tasks/V2-T8/01-planner-task-contract-v3.md（v3；v1/v2 作历史）

背景：B 级人工验证捕获首次运行时失败——应用启动 panic：PluginInitialization("shell", "Error deserializing 'plugins.shell' ... unknown field `scope`, expected `open`")。根因：tauri.conf.json 的 plugins.shell.scope 为 Tauri v1 语法；Tauri 2 中命令白名单 scope 必须在 capabilities 权限条目声明。

唯一主要变化：应用可正常启动（shell 插件初始化不再 panic）；python-uvicorn 白名单迁移到 capabilities（Tauri 2 语法），spawn/kill 语义不变。无其他变化。

实现导航：
- tauri.conf.json：删除 plugins.shell 配置块
- capabilities/default.json：把 "shell:default" 替换为显式权限对象，至少 shell:allow-spawn + shell:allow-kill，allow 条目 {"name":"python-uvicorn","cmd":"python","args":true}（字段是 cmd 不是 command；如运行时权限不足，按同一 scope 条目补 identifier）
- desktop/src/**、src-tauri/src/**、依赖、dist 一律不动

允许修改：
- desktop/src-tauri/tauri.conf.json、desktop/src-tauri/capabilities/default.json、docs/dev-flow/tasks/V2-T8/**

禁止修改：
- 上述以外一切（含 desktop/src/**、src-tauri/src/**、Cargo.*、package*.json、dist/**、.gitignore、engine/**、backend/**）

快速验证顺序（合同 v3 §7）：
1. `cargo check`（workdir=desktop/src-tauri）
2. `npx vitest run`（workdir=desktop）
3. `npx vue-tsc --noEmit`（workdir=desktop）
4. 启动实跑由产品负责人执行，你不得自行宣布启动成功

停止条件：
- 基线/工作树不符；越界；同一失败两次；按 Tauri 2 shell 插件文档两次尝试仍无法通过验证 → 停止报告（不擅自换插件/换壳）。

进度纪律：每阶段报告"已完成/当前在做/异常/是否仍在合同内"；超 3 分钟命令不执行，标记移交。

完成时：
1. 候选提交只含两个 JSON 文件；
2. 不 amend、不 rebase、不 push；
3. 完成说明写到 docs/dev-flow/tasks/V2-T8/rounds/03/maker-completion.md 并单独提交；
4. 冻结并交回。
