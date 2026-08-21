# 致 Maker 的转发消息 V2-T8 v1

你是当前唯一可写 Maker。

工作目录：D:\Repo\FairyReport_lite
精确起始 SHA：本转发消息提交后的 master HEAD（合同提交 270cc61 的直接后代，仅新增本任务文档；开工前核实 `git rev-parse HEAD` 与 `git status --short` 干净）
有效合同：docs/dev-flow/tasks/V2-T8/01-planner-task-contract-v1.md

唯一主要行为：桌面应用启动后展示认证界面，可对云端完成注册/登录（JWT 本地保存）；登录后拉起本地引擎子进程并确认健康；设置页可配置并持久化 LLM Key/Base URL/模型。

实现导航（合同 §4）：
- 新建 desktop/（Tauri 2 + Vue 3 + TS + Pinia + Vite）
- desktop/src/views/Login.vue — 登录/注册双 tab（注册=邮箱+验证码+密码；验证码发送按钮带 60s 倒计时）
- desktop/src/views/Settings.vue — LLM Key/Base URL/模型 + 服务器地址（默认 http://101.42.9.223）
- desktop/src/lib/api.ts — 云端客户端（send-code/register/login/me/pack manifest）
- desktop/src/lib/engine.ts — 选空闲端口 → 子进程 `python -m uvicorn engine.app.main:app --host 127.0.0.1 --port <p>`（工作目录=仓库根，MVP 开发形态）→ 轮询 /health → 退出时 kill
- desktop/src/lib/state.ts — token 与设置持久化到 %LOCALAPPDATA%/FairyReport/desktop-state.json（文件 ACL 限当前用户；密钥明文为 MVP 已知风险）
- Rust 侧最小化：tauri 配置 + tauri-plugin-shell 白名单允许 python 子进程
- 主窗口路由：未登录→Login；已登录→占位 Home（T9 填充）+ Settings 入口
- 测试：vitest 单测（api.ts 打桩 fetch 的成功/401/网络错误分支；engine.ts 端口选择与健康轮询逻辑打桩 spawn）

允许修改：
- desktop/**（全部新建）、.gitignore（node_modules/dist/target 等）、docs/dev-flow/tasks/V2-T8/**

禁止修改：
- engine/**、backend/**、根目录产品文件、generic_knowledge/**、.opencode/、AGENTS.md

工具链现状（开工前已探测）：
- Node v24.14.0 / npm 11.8.0（合同写 Node 20 LTS；24 为当前 LTS 线且满足 Tauri 2 要求，产品负责人已知悉）、rustc/cargo 1.96.1 stable；desktop/ 尚不存在
- 脚手架与 npm install / cargo fetch 仅限合同 §7 清单内依赖（清单随合同批准）；清单外依赖一律停止上报

快速验证顺序（合同 §9）：
1. cd desktop && npx vitest run
2. cargo check（desktop/src-tauri）
3. npx vue-tsc --noEmit

停止条件：
- 基线/工作树不符；清单外依赖；越界；同一失败两次；Tauri 在 Windows 构建两次尝试无解 → 停止报告（不擅自换壳）。

进度纪律：每阶段报告"已完成/当前在做/异常/是否仍在合同内"；超 3 分钟命令不执行，标记移交。

完成时：
1. 候选提交只含 desktop/**（及 .gitignore）；
2. 不 amend、不 rebase、不 push；
3. 完成说明写到 docs/dev-flow/tasks/V2-T8/rounds/01/maker-completion.md 并单独提交；
4. 冻结并交回。
