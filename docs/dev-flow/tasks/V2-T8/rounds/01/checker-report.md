# Checker 验收报告 — V2-T8 第 1 轮

- 状态：**PASS**
- 精确候选 SHA：a10e900605ace1d226a892ffe5d3237bd913439d
- 依据合同：`tasks/V2-T8/01-planner-task-contract-v1.md`
- 基线 SHA：d55e920ab4aefcfa033c4ad1e6ab1c1a4b16446c

## 独立检查边界

- 独立重跑（本轮全部自行执行，未采信 Maker 自述）：
  - `npx vitest run`（workdir=desktop）→ exit 0：**12 passed**（api 7 + engine 5），597ms
  - `cargo check`（workdir=desktop/src-tauri）→ exit 0：`Finished dev profile`（0.30s，二次确认）
  - `npx vue-tsc --noEmit`（workdir=desktop）→ exit 0：无类型错误
- 代码级审查（A 级）：父链、diff 范围、依赖清单逐一对账、.gitignore、state.ts/Rust write_state、路由/倒计时/引擎生命周期行为、测试覆盖。
- B 级人工项（产品负责人执行并回贴）：真实启动应用（`npm run tauri dev`）登录/引擎健康/设置重启保留，未在本会话执行，列为剩余人工项。

## 验收标准逐条核对

| 合同标准 | 证据等级(A/B/C/D) | 证据与结论 |
|---|---|---|
| §8.1 cargo check / vue-tsc --noEmit / vitest 全绿 | A | 独立重跑全部通过（见上）。 |
| §8.2 未登录强制进 Login；注册(send-code 倒计时)/登录链路 | A(代码)/B(人工) | `App.vue`：`<Login v-else-if="!auth.isLoggedIn" /> <Home v-else />`；`Login.vue`：`countdown=ref(0)` + `setInterval` 60s 倒计时 + `canSendCode` 禁用逻辑；api.ts 打桩分支测试（成功/401/网络错误）覆盖。真实服务器链路为 B 级人工。 |
| §8.3 登录后引擎子进程拉起、/health 绿、退出 kill | A(代码)/B(人工) | `engine.ts`：`defaultSpawn` 经 `@tauri-apps/plugin-shell` Command（scope `python-uvicorn`→python，`tauri.conf.json` args:true）、`pollHealth` 30×500ms、`stop()` kill；`engine.test.ts` 5 例覆盖 pollHealth 成功/重试/超时 + startEngine 编排/stop kill。真实拉起为 B 级人工。 |
| §8.4 设置持久化重启保留 | A(代码)/B(人工) | `state.ts` readState/writeState 经 Rust invoke read_state/write_state（浏览器降级 localStorage）；settings store 保存到 `desktop-state.json`。真实重启为 B 级人工。 |
| §8.5 desktop-state.json 不含于仓库；ACL 限当前用户 | A(不在仓)/C(ACL) | `git ls-files` 无任何 `desktop-state.json`/state.json；`lib.rs:8-11` 落 `%LOCALAPPDATA%/FairyReport`，ACL 依赖 LOCALAPPDATA 用户私有目录继承（未引入显式 DACL，符合 §3 MVP 风险记录；keychain 加固为发布前项）。 |
| §8.6 101 回归不受影响（不碰 engine/backend） | A | `git diff d55e920..a10e900` 无任何 engine/**、backend/**、generic_knowledge/** 改动。 |

## 依赖清单逐一对账（合同 §7）

- `desktop/package.json`：
  - dependencies：`vue`、`pinia`、`@tauri-apps/api`、`@tauri-apps/plugin-shell`
  - devDependencies：`vite`、`vitest`、`typescript`、`vue-tsc`、`@vitejs/plugin-vue`
  - 均为 §7 清单或直接伴生（`@tauri-apps/plugin-shell`=引擎子进程 shell 能力；`@tauri-apps/api`=Tauri 2 前端 API；`@vitejs/plugin-vue`=Vite+Vue 官方插件；`vue-tsc`=§9 要求的类型检查工具）。**无清单外功能库**（无 axios/vue-router/UI 框架）。
- `desktop/src-tauri/Cargo.toml`：dependencies `tauri`(2)、`tauri-plugin-shell`(2)、`serde`、`serde_json`；build-dependencies `tauri-build`(2)。均在 §7 内。
- `Cargo.lock` 已提交（二进制 crate 惯例）。npm 用 package-lock.json 已提交。

## 修改范围复核

- `git diff --name-status d55e920..a10e900`：`.gitignore`(M) + 32 项 `desktop/**`(A)，全部落在允许路径（§5）。
- 禁止路径零改动：engine/**、backend/**、generic_knowledge/**、根产品文件、.opencode/、AGENTS.md 均无 diff。
- 父链：`git log --oneline d55e920..a10e900` 仅 a10e900 一个提交；`a10e900^ == d55e920`。完成说明 `7e95e6b` 及后续流程文档提交不属候选范围。
- `git status --short` 干净；`git branch -vv` master 无 upstream（未 push）。

## 重点项审查

- **.gitignore `dist/` → `/dist/`**：根锚定后不再忽略 `desktop/dist/`，使已构建前端可纳入版本控制（Tauri `generate_context!` 编译期校验并 embed frontendDist，`cargo check` 需 dist 存在）；已验证仓库内除 `desktop/dist` 外无其他被意外解除忽略的 dist/ 目录（engine/backend 无 dist）。`desktop/dist/` 4 个跟踪文件为合法 Vite 构建产物（index.html + assets/*.js + assets/*.css）。增补 `desktop/node_modules/`、`src-tauri/target/`、`src-tauri/gen/` 合理。此项成立。
- **state.ts / Rust write_state LOCALAPPDATA+ACL**：`lib.rs:47-52` `state_dir()=%LOCALAPPDATA%/FairyReport`，`create_dir_all` + `fs::write` 写 `desktop-state.json`；ACL 依赖 LOCALAPPDATA 用户私有目录的继承语义（C 级，未显式 DACL），与合同 §3"MVP 用本地状态文件+ACL、发布前加固"一致。`state.ts` 文档字符串明确记录该语义与明文 Key 风险。
- **engine 子进程安全边界**：tauri.conf.json shell scope 仅允许 `python-uvicorn`→`python`、args:true；端口经 `pick_free_port` 绑定 127.0.0.1:0 取系统分配端口，子进程 host 固定 127.0.0.1。

## 阻断项（仅 FAIL）

无。

## 非阻断风险

- LLM Key 明文存 `desktop-state.json`（MVP 已知风险，合同 §3 记录；发布前 keychain 加固）。
- ACL 为 LOCALAPPDATA 继承语义而非显式 DACL（C 级）；极端环境若 LOCALAPPDATA 权限被放宽则不满足"仅当前用户"，发布前加固。
- `engine.ts` 默认 spawn 的 cwd 为仓库根（`engine_cwd` = CARGO_MANIFEST_DIR 上两级），MVP 开发形态，T10 打包换引擎时需调整。
- dist/ 纳入版本控制后 `npm run build` 会覆盖导致 git 差异（初始快照，属预期）。
- Node v24.14.0 而非合同字面 Node 20 LTS（24 为当前 LTS 线，产品负责人已知悉，非阻断）。

## B 级剩余人工项（产品负责人执行并回贴）

1. 真实启动 `npm run tauri dev`，用 `13476526@qq.com` 登录成功。
2. 引擎健康指示灯绿（子进程拉起 + /health 200）。
3. 设置 Key/服务器地址保存后重启应用，确认保留。

## 判定

- **PASS**：锁定 `a10e900605ace1d226a892ffe5d3237bd913439d` 为 V2-T8 代码候选。剩余 B 级人工项 3 项（上列），由产品负责人回贴观察后并入验收记录。