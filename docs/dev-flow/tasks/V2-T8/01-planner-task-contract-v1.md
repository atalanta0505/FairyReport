# 任务合同 V2-T8 v1 — Tauri 桌面壳 + 认证 UI + 引擎生命周期 + 设置

- 状态：ACCEPTED（第 1 轮 Checker PASS，锁定候选 a10e900605ace1d226a892ffe5d3237bd913439d；剩余 B 级人工项 3 项见 rounds/01/checker-report.md）— 合同已被 v2 增补取代（@tauri-apps/cli 窄修复），B 级人工验证改对 v2 候选执行
- 产品决定来源：`00-product-decision-v4.md` D18、`00-product-decision-v5.md` D21
- 精确起始 SHA：本合同提交后的 master HEAD
- 工作树门禁：`git status --short` 必须干净

## 1. 背景与目标

桌面端从零建立：Tauri 2 壳 + Vue 3 UI。本切片交付"能登录、能起引擎、能配置 Key"的最小可用壳；5 步主流程 UI 在 T9。

## 2. 唯一主要行为变化

**桌面应用启动后展示认证界面，可对云端完成注册/登录（JWT 本地保存）；登录后拉起本地引擎子进程并确认健康；设置页可配置并持久化 LLM Key/Base URL/模型。**

## 3. 明确不做

- 不做 5 步主流程 UI（T9）、不做打包/MSI/Portable（T10）
- 不做 keychain 加固（MVP 用本地状态文件+ACL，风险已记录，发布前加固）
- 不改 engine/**、backend/**（只消费其 HTTP 接口）

## 4. 实现导航

- 新建 `desktop/`（Tauri 2 + Vue 3 + TS + Pinia + Vite）：
  - `desktop/src/views/Login.vue` — 登录/注册双 tab（注册=邮箱+验证码+密码；验证码发送按钮带 60s 倒计时）
  - `desktop/src/views/Settings.vue` — LLM Key/Base URL/模型 + 服务器地址（默认 http://101.42.9.223）
  - `desktop/src/lib/api.ts` — 云端客户端（send-code/register/login/me/pack manifest）
  - `desktop/src/lib/engine.ts` — 引擎生命周期：选空闲端口 → 以子进程启动 `python -m uvicorn engine.app.main:app --host 127.0.0.1 --port <p>`（工作目录=仓库根，MVP 开发形态；T10 换打包引擎）→ 轮询 /health → 退出时 kill
  - `desktop/src/lib/state.ts` — token 与设置持久化到 %LOCALAPPDATA%/FairyReport/desktop-state.json（文件 ACL 限当前用户；密钥明文为 MVP 已知风险）
  - Rust 侧最小化：tauri 配置 + tauri-plugin-shell 白名单允许 python 子进程
- 主窗口路由：未登录→Login；已登录→占位 Home（T9 填充）+ Settings 入口
- 测试：vitest 单测（api.ts 打桩 fetch 的成功/401/网络错误分支；engine.ts 端口选择与健康轮询逻辑打桩 spawn）；`cargo check`；`vue-tsc --noEmit`
- B 级人工（产品负责人）：真实启动应用，用 13476526@qq.com 登录成功、引擎健康指示灯绿、设置重启后保留

## 5. 允许修改

- `desktop/**`（全部新建）
- `.gitignore`（node_modules/dist/target 等）
- `docs/dev-flow/tasks/V2-T8/**`

## 6. 禁止修改

- `engine/**`、`backend/**`、根目录产品文件、generic_knowledge/**、.opencode/、AGENTS.md

## 7. 工具链与依赖（人工安装，清单随合同批准）

- Node 20 LTS、Rust stable（rustup）、Visual Studio Build Tools 2022（C++ 桌面工作负载）、WebView2 运行时（Win10/11 一般自带）
- npm/cargo 依赖（tauri、vue、pinia、vite、vitest、typescript 及对应 crates）由安装命令拉取，执行归产品负责人

## 8. 验收标准

- [ ] `cargo check` 通过；`vue-tsc --noEmit` 通过；vitest 全绿
- [ ] 未登录强制进 Login；注册链路（send-code 倒计时）与登录链路对真实服务器可用（B 级人工）
- [ ] 登录后引擎子进程拉起、/health 绿；应用退出子进程随之结束（B 级）
- [ ] 设置持久化：重启后 Key/服务器地址保留（B 级）
- [ ] desktop-state.json 不含于仓库；ACL 限当前用户
- [ ] 101 回归不受影响（本切片不碰 engine/backend，抽查即可）

## 9. Maker 快速测试（按顺序）

1. cd desktop && npx vitest run
2. cargo check（desktop/src-tauri）
3. npx vue-tsc --noEmit

## 10. 停止条件

- 工具链人工项未决；基线/工作树不符；清单外依赖；越界；同一失败两次；
- Tauri 在 Windows 构建两次尝试无解 → 停止报告（不擅自换壳）。

## 11. 候选提交与完成说明

- 候选只含 desktop/**（及 .gitignore）；完成说明单独提交 rounds/01/maker-completion.md
- 不 amend、不 rebase、不 push

## 12. 已知基线失败

- 无。
