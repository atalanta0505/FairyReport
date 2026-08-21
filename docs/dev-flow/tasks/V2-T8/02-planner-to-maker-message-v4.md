# 致 Maker 的转发消息 V2-T8 v4

你是当前唯一可写 Maker。

工作目录：D:\Repo\FairyReport_lite
精确起始 SHA：本合同提交后的 master HEAD（开工前核实 `git rev-parse HEAD` 与 `git status --short` 干净）
有效合同：docs/dev-flow/tasks/V2-T8/01-planner-task-contract-v4.md（v4；v1–v3 作历史）

背景：B 级实跑登录报 `网络错误: Failed to fetch`。根因：后端无 CORS（预检 405）+ 打包版 tauri:// 安全源 fetch http:// 混合内容阻断；浏览器 fetch 通路不成立。改用 Tauri 官方 plugin-http 原生 fetch。

唯一主要变化：云端 API 与引擎健康轮询改走 @tauri-apps/plugin-http fetch；认证/状态/引擎语义不变。

实现导航：
- npm install @tauri-apps/plugin-http；Cargo 增 tauri-plugin-http（major 与 tauri 2 对齐，随合同批准）
- lib.rs 注册 tauri_plugin_http::init()
- capabilities/default.json 增 http:default + fetch scope（覆盖云服务器默认 http://101.42.9.223 与 127.0.0.1 任意端口；模式语法按 plugin-http v2 文档；宽模式须在完成说明明示）
- api.ts 改 import { fetch } from '@tauri-apps/plugin-http'（保持可 mock；成功/401/网络错误分支测试保留适配）
- engine.ts 默认 fetcher 同改（注入点保留，测试继续打桩）
- npm run build 重建 dist/

允许修改：
- desktop/**、docs/dev-flow/tasks/V2-T8/**

禁止修改：
- desktop/** 以外一切（engine/**、backend/**、根目录产品文件、.gitignore、generic_knowledge/**、.opencode/、AGENTS.md）

快速验证顺序（合同 v4 §7）：
1. `npx vitest run`（workdir=desktop）
2. `cargo check`（workdir=desktop/src-tauri）
3. `npx vue-tsc --noEmit`（workdir=desktop）

停止条件：
- 基线/工作树不符；越界；同一失败两次；按 plugin-http v2 文档两次尝试仍无法通过编译/测试 → 停止报告（不擅自换方案）。

进度纪律：每阶段报告"已完成/当前在做/异常/是否仍在合同内"；超 3 分钟命令不执行，标记移交。

完成时：
1. 候选提交只含 desktop/**；
2. 不 amend、不 rebase、不 push；
3. 完成说明写到 docs/dev-flow/tasks/V2-T8/rounds/04/maker-completion.md 并单独提交；
4. 冻结并交回。
