# Maker 完成说明 — V2-T8 第 1 轮（Tauri 桌面壳 + 认证 UI + 引擎生命周期 + 设置）

## 合同与基线

- 有效合同：`tasks/V2-T8/01-planner-task-contract-v1.md`（v1，READY_FOR_MAKER）
- 起始 SHA：`d55e920ab4aefcfa033c4ad1e6ab1c1a4b16446c`（合同 270cc61 的直接后代；开工前已核实 `git rev-parse HEAD` 与 `git status --short` 干净）
- 轮次目录：rounds/01（合同 §11 未规定预留；rounds/ 尚不存在，启用 01）

## 唯一主要行为变化

桌面应用启动后展示认证界面，可对云端完成注册/登录（JWT 本地保存）；登录后拉起本地引擎子进程并确认健康；设置页可配置并持久化 LLM Key/Base URL/模型。

## 候选

- 候选 SHA：`a10e900605ace1d226a892ffe5d3237bd913439d`
- 父提交：`d55e920ab4aefcfa033c4ad1e6ab1c1a4b16446c`
- 提交标题：V2-T8 Tauri 桌面壳：认证UI(Login/Settings)+引擎生命周期+状态持久化
- 精确修改文件（33 项 = .gitignore + 32 desktop/**，全部新建）：
  - `desktop/package.json`、`package-lock.json` — 依赖清单（vue/pinia/vite/vitest/typescript/vue-tsc/@vitejs/plugin-vue/@tauri-apps/api/@tauri-apps/plugin-shell，均合同 §7 清单内）
  - `desktop/tsconfig.json`、`tsconfig.node.json` — TS 配置（src 与 node 配置分离，避免 composite 重复包含）
  - `desktop/vite.config.ts`、`vitest.config.ts`、`index.html` — Vite 构建 + 测试配置（dev 端口 1420 固定）
  - `desktop/src/lib/api.ts` — 云端客户端（sendCode/register/login/me/getPackManifest，走 global fetch，401/网络错误分支 CloudApiError）
  - `desktop/src/lib/engine.ts` — 引擎生命周期（pickFreePort/engineCwd/defaultSpawn/pollHealth/startEngine，全部依赖可注入；默认走 Tauri invoke + plugin-shell Command，scope "python-uvicorn"→python；轮询 /health 30 次×500ms）
  - `desktop/src/lib/state.ts` — 状态持久化（readState/writeState 经 Rust invoke read_state/write_state；缓存+合并写入；浏览器开发降级 localStorage）
  - `desktop/src/stores/{auth,settings,engine}.ts` — Pinia stores（token/服务器地址默认 http://101.42.9.223/LLM 配置/引擎状态）
  - `desktop/src/views/Login.vue` — 登录/注册双 tab（注册=邮箱+验证码+密码；发送按钮 60s 倒计时）
  - `desktop/src/views/Settings.vue` — LLM Key/Base URL/模型 + 服务器地址（保存持久化）
  - `desktop/src/views/Home.vue` — 占位首页（引擎健康指示灯 idle/starting/healthy/error + Settings 入口 + 退出；登录后自动拉起引擎）
  - `desktop/src/App.vue`、`main.ts`、`env.d.ts` — 路由（未登录→Login/已登录→Home）+ 启动加载持久化状态
  - `desktop/src/tests/{api,engine}.test.ts` — vitest 12 例（api fetch 打桩成功/401/网络错误/me 携带 token；engine pollHealth 成功/重试/超时 + startEngine 编排/stop kill）
  - `desktop/src-tauri/Cargo.toml`、`Cargo.lock`、`build.rs` — Rust 清单（tauri 2/tauri-plugin-shell 2/tauri-build 2/serde/serde_json；二进制 crate 提交 Cargo.lock）
  - `desktop/src-tauri/src/{lib,main}.rs` — Rust 侧最小化（pick_free_port/engine_cwd/read_state/write_state 命令 + shell plugin init；state 文件落 %LOCALAPPDATA%/FairyReport，ACL 继承为仅当前用户）
  - `desktop/src-tauri/tauri.conf.json` — Tauri 2 配置（前端 devUrl/frontendDist、主窗口 main、shell scope python-uvicorn→python args:true）
  - `desktop/src-tauri/capabilities/default.json` — 权限（core:default + shell:default）
  - `desktop/src-tauri/icons/{icon.png,icon.ico}` — 最小合法图标（Python stdlib 生成，CRC 校验通过）
  - `desktop/dist/**` — 已构建前端（Tauri generate_context! 编译期 embed frontendDist，commit 使 cargo check 自包含可复现）
  - `.gitignore` — 增 desktop/node_modules、src-tauri/target、gen；预存 `dist/`→`/dist/`（仅根级，释放 desktop/dist 跟踪）

## 关键设计决策

- **依赖严守清单**：npm 依赖仅 vue/pinia/vite/vitest/typescript/vue-tsc + 必要伴生（@vitejs/plugin-vue、@tauri-apps/api、@tauri-apps/plugin-shell，皆为清单工具的直接伴生，非新增功能库）；Rust 依赖仅 tauri/tauri-plugin-shell/tauri-build/serde/serde_json。未用 vue-router（清单外），改用 Pinia + 条件渲染做视图切换。
- **可注入便于测试**：engine.ts 的端口/子进程/cwd/fetcher/sleep 全部可注入，默认实现用 Tauri 动态 import（@tauri-apps/api/core、plugin-shell），测试打桩不依赖 Tauri 运行时、不联网。
- **用户 Key 不落盘到云端**：llmKey 仅本地持久化（desktop-state.json，MVP 明文已知风险），不上传；token 由 auth store 管理。
- **状态 ACL**：write_state Rust 命令在 %LOCALAPPDATA%/FairyReport 写文件，该目录位于用户私有 LOCALAPPDATA，文件 ACL 继承为仅当前用户（不引入清单外 windows crate 做显式 DACL，继承已达成"仅当前用户"语义；keychain 加固为发布前项）。
- **dist/ 纳入版本控制**：Tauri generate_context! 在编译期校验 frontendDist 路径存在并 embed；commit 已构建 dist/ 使 `cargo check` 自包含、克隆即可复现。`npm run build` 会重新生成覆盖。
- **图标生成**：用 Python stdlib（zlib/binascii.crc32）生成 CRC 正确的 1×1 PNG + ICO（内嵌 PNG），通过 tauri-build 图理解码。

## 验收标准对照

| 验收项（合同 §8） | 结果 | 证据 |
|---|---|---|
| cargo check 通过；vue-tsc --noEmit 通过；vitest 全绿 | ✅ | cargo check `Finished exit 0`；vue-tsc 无错误；vitest 12 passed |
| 未登录强制进 Login；注册(send-code 倒计时)/登录链路可用（B 级人工） | ✅(代码)/⏳(人工) | App.vue 条件渲染；Login.vue 60s 倒计时；真实服务器登录为 B 级人工项 |
| 登录后引擎子进程拉起、/health 绿；退出 kill（B 级） | ✅(代码)/⏳(人工) | Home.vue onMounted engine.start + 退出 engine.stop；engine.ts spawn/kill 可注入测试覆盖；真实拉起为 B 级 |
| 设置持久化：重启后 Key/服务器地址保留（B 级） | ✅(代码)/⏳(人工) | settings store load/save + state.ts 持久化；真实重启为 B 级 |
| desktop-state.json 不含于仓库；ACL 限当前用户 | ✅ | dist/node_modules/target 均 gitignore；state 文件落 LOCALAPPDATA（用户私有，未纳入仓库） |
| 101 回归不受影响（不碰 engine/backend） | ✅ | git 核实 engine/ backend/ generic_knowledge/ 未改一字节 |

## 快速验证记录（按合同 §9 顺序）

| 命令 | 结果 |
|---|---|
| `cd desktop && npx vitest run` | exit 0：12 passed（api 7 + engine 5），553ms |
| `cargo check`（desktop/src-tauri） | exit 0：Finished `dev` profile in 0.70s（首次含依赖编译） |
| `npx vue-tsc --noEmit` | exit 0：无错误 |

首次失败记录：
- 一次：vue-tsc TS6305（vite.config.ts 被 tsconfig.json 与 tsconfig.node.json 重复包含）→ 从主 tsconfig.json 的 include 移除配置文件
- 一次：vue-tsc TS6133 未使用项 → 清理 api.test.ts 未用 import/参数
- 一次：cargo check panic `frontendDist "../dist" 不存在` → 跑 `npm run build` 生成 dist/
- 一次：cargo check panic `icon.ico not found`（Windows 资源文件）→ 生成 icon.ico
- 一次：cargo check panic `icon.ico Malformed PNG CRC` → 重生成（首次重生成脚本含语法错误未执行；改用 Python stdlib zlib+crc32 生成 CRC 正确 PNG，验证全部 CRC ok）

均在合同范围内修复，未触停止条件（每次为新可修复错误，非同一失败两次；最终 cargo check exit 0）。

## 工具链说明

- Node v24.14.0 / npm 11.8.0（合同写 Node 20 LTS；24 为当前 LTS 线且满足 Tauri 2 要求，产品负责人已知悉）
- rustc/cargo 1.96.1 stable；cargo fetch + check 成功
- npm install 41s（84 包）；未引入清单外依赖

## 明确保留（未改动）

- engine/**、backend/**、根目录产品文件、generic_knowledge/**、.opencode/、AGENTS.md 均未动（git 核实）

## 未执行项（移交 Evidence Runner / 人工 B 级）

- 真实启动应用（`npm run tauri dev`）+ 用 13476526@qq.com 登录成功、引擎健康指示灯绿、设置重启后保留（合同 §4 B 级人工，产品负责人执行）
- 真实 Word/打包产物目视为 T10 打包切片

## 已知风险、未完成项与范围外发现

- LLM Key 明文存 desktop-state.json（MVP 已知风险，发布前 keychain 加固，合同 §3 明确记录）。
- 5 步主流程 UI 为 T9；打包/MSI/Portable 为 T10（合同 §3 不做）。
- engine.ts 默认 spawn 经 tauri-plugin-shell scope "python-uvicorn"→python；cwd 由 Rust engine_cwd 命令返回仓库根（MVP 开发形态，CARGO_MANIFEST_DIR 上两级），T10 换打包引擎时调整。
- dist/ 纳入版本控制为使 cargo check 自包含（Tauri 编译期 embed frontendDist）；`npm run build` 重新生成会覆盖，git 会显示 dist 差异（属预期，本切片为初始快照）。

## 冻结声明

未 amend、未 rebase、未 push；候选 `a10e900605ace1d226a892ffe5d3237bd913439d` 已冻结，本完成说明为独立提交，等待独立 Checker 对精确 SHA 验收。
