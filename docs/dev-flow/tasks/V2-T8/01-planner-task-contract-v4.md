# 任务合同 V2-T8 v4 — 范围增补：plugin-http 原生 HTTP 通路（第 4 轮验收基线）

- 状态：READY_FOR_MAKER（产品负责人 2026-08-21 "开工"指令批准；§7 增补依赖随批准生效）
- 变更说明：v3 第 3 轮 PASS 锁定 `b0c3b40d9355f74da29f9e2e5cb5f8178c0ddcd3`；B 级实跑捕获第二次运行时失败：登录报 `网络错误: Failed to fetch`。根因（协调者只读核查）：① 后端无 CORS（仓库无 CORSMiddleware，预检 OPTIONS 405），WebView 跨域 fetch 被浏览器拦截；② 打包版 `tauri://` 安全源 fetch `http://` 另有混合内容阻断。浏览器 fetch 通路不成立，改用 Tauri 官方 plugin-http（Rust 原生 fetch，不受 CORS/混合内容约束）。v1–v3 保留作历史。
- 产品决定来源：2026-08-21 产品负责人选定"plugin-http（推荐）"方案
- 精确起始 SHA：本合同提交后的 master HEAD
- 工作树门禁：`git status --short` 必须干净

## 1. 唯一主要变化

桌面端云端 API（send-code/register/login/me/pack manifest）与引擎健康轮询改走 @tauri-apps/plugin-http 原生 fetch，登录链路对真实服务器可用。**认证流程、状态持久化、引擎生命周期语义均不变。**

## 2. 明确不做

- 不改 backend/**（不加 CORS）、不做 HTTPS（发布前项）
- 不改认证/状态/引擎逻辑本身；不改 UI 结构
- 不引入 plugin-http 之外的依赖

## 3. 实现导航

- 依赖（随本合同批准）：npm `@tauri-apps/plugin-http`、crate `tauri-plugin-http`（major 均与 tauri 2 对齐）
- `src-tauri/src/lib.rs`：注册 `.plugin(tauri_plugin_http::init())`
- `src-tauri/capabilities/default.json`：增 `http:default` + fetch scope；scope 至少覆盖可配置云服务器地址（默认 http://101.42.9.223）与 `http://127.0.0.1` 任意端口（引擎健康）；URL 模式语法按 plugin-http v2 文档；若 MVP 暂用宽模式须在完成说明明示
- `src/lib/api.ts`：改用 `import { fetch } from '@tauri-apps/plugin-http'`（保持可测试性：模块可被 vi.mock；成功/401/网络错误分支测试保留并适配）
- `src/lib/engine.ts`：默认 fetcher 同改 plugin-http fetch（注入点保留，测试继续打桩）
- `npm run build` 重建 dist/（前端代码变化，保持快照一致）

## 4. 允许修改

- `desktop/**`（含 package*.json、Cargo.toml/Cargo.lock、src/**、src-tauri/**、capabilities、dist/**）
- `docs/dev-flow/tasks/V2-T8/**`

## 5. 禁止修改

- desktop/** 以外一切（engine/**、backend/**、根目录产品文件、.gitignore、generic_knowledge/**、.opencode/、AGENTS.md）

## 6. 验收标准

- [ ] diff 仅 desktop/** + docs
- [ ] 两个新依赖 major 与 tauri 2 对齐；无其他新依赖
- [ ] `npx vitest run` 全绿（api 成功/401/网络错误分支经 mock plugin-http 覆盖）
- [ ] `cargo check`、`npx vue-tsc --noEmit` 全绿
- [ ] B 级：产品负责人实跑 `npm run tauri dev` 登录成功（本轮关键运行时验证）+ 引擎灯绿 + 设置重启保留

## 7. 快速验证（按顺序）

1. `npx vitest run`（workdir=desktop）
2. `cargo check`（workdir=desktop/src-tauri）
3. `npx vue-tsc --noEmit`（workdir=desktop）

## 8. 停止条件

- 基线/工作树不符；越界；同一失败两次；
- 按 plugin-http v2 文档两次尝试仍无法通过编译/测试 → 停止报告（不擅自换方案）。

## 9. 候选提交与完成说明

- 候选只含 desktop/**
- 完成说明写到 `docs/dev-flow/tasks/V2-T8/rounds/04/maker-completion.md`，单独提交
- 不 amend、不 rebase、不 push

## 10. 已知基线失败

- B 级第二次失败：登录 `网络错误: Failed to fetch`（CORS/混合内容，原文见变更说明）。
