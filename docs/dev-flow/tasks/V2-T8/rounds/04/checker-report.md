# Checker 验收报告 — V2-T8 第 4 轮

- 状态：**PASS**
- 精确候选 SHA：`808c8d50ff70dad6e74c134790e01e179ae23a1f`
- 依据合同：`tasks/V2-T8/01-planner-task-contract-v4.md`（v4；v1–v3 及前三轮报告作历史）
- 基线 SHA：`f760e08c16fbd51222852d21b327314366c4a8b2`

## 独立检查边界与重跑证据

所有 A 级快速验证命令均由 Checker 独立在干净工作树下重新执行，未盲目采信 Maker 自述：

- **Vitest 单元测试**：`npx vitest run`（workdir=`desktop`）
  - 结果：exit 0，**12 passed**（`api.test.ts` 7 例 + `engine.test.ts` 5 例），耗时 784ms。
  - 覆盖项：API sendCode 成功/网络错误（CloudApiError status=0）、login 成功/401 错误、register 成功、me/manifest 携带 Bearer token 请求头；引擎健康轮询重试与超时。
- **Rust 编译与插件检查**：`cargo check`（workdir=`desktop/src-tauri`）
  - 结果：exit 0，`Finished dev profile [unoptimized + debuginfo] target(s) in 8.67s`，无编译错误或警告。
- **TypeScript 类型检查**：`npx vue-tsc --noEmit`（workdir=`desktop`）
  - 结果：exit 0，无任何类型错误。
- **前端生产构建验证**：`npm run build`（workdir=`desktop`）
  - 结果：exit 0，47 modules transformed，耗时 523ms。构建后工作树对比无未跟踪或未同步差异，dist 产物与提交严格一致。

## 验收标准逐条核对（合同 v4 §6）

| 合同标准 | 证据等级 (A/B/C/D) | 证据与结论 |
|---|---|---|
| §6.1 diff 仅 `desktop/**` + docs | A | `git diff --name-status f760e08..808c8d5` 恰好 15 项文件，全部位于 `desktop/**`（含 package*.json、Cargo.*、src-tauri/**、src/**、dist/**）；docs 修改为独立流程提交。 |
| §6.2 两个新依赖 major 与 tauri 2 对齐；无其他新依赖 | A | npm `@tauri-apps/plugin-http@^2.5.9`；crate `tauri-plugin-http = "2"`（Cargo.lock 锁定 v2.5.9）；无任何清单外新增依赖。 |
| §6.3 `npx vitest run` 全绿（api 成功/401/网络错误分支经 mock plugin-http 覆盖） | A | 独立执行通过（12 passed，见重跑记录）；`vi.mock("@tauri-apps/plugin-http")` 完整覆盖 API 分支。 |
| §6.4 `cargo check`、`npx vue-tsc --noEmit` 全绿 | A | 独立重跑全部 exit 0，编译期配置与类型全绿。 |
| §6.5 B 级：产品负责人实跑 `npm run tauri dev` 登录成功 + 引擎灯绿 + 设置重启保留 | ⏳ | B 级人工项，移交产品负责人执行。 |

## 重点审查

1. **`plugin-http` 原生 HTTP 通路注册与权限配置**：
   - `desktop/src-tauri/src/lib.rs`：在 `tauri::Builder::default()` 中正确注册 `.plugin(tauri_plugin_http::init())`。
   - `desktop/src-tauri/capabilities/default.json`：配置了 `http:default` 权限对象，使用窄模式 allow scope：
     - `{"url": "http://101.42.9.223/*"}`：覆盖默认云端服务器地址。
     - `{"url": "http://127.0.0.1:*/*"}`：覆盖本地引擎健康轮询（通配任意端口）。
     - 符合 Tauri 2 capabilities URL pattern schema，`cargo check` 阶段经 `tauri-codegen` 校验有效。
2. **前端调用改造与测试打桩**：
   - `desktop/src/lib/api.ts`：将 global `fetch` 改为静态引入 `import { fetch } from "@tauri-apps/plugin-http"`。请求异常统一封装为 `CloudApiError(0, ...)`，401/4xx/5xx 错误解析与透传逻辑保持完整。
   - `desktop/src/lib/engine.ts`：健康轮询默认 fetcher 切换为 `pluginFetch`，同时保持 `deps?.fetcher` 依赖注入点，单元测试打桩零污染。
   - `desktop/src/tests/api.test.ts`：采用 `vi.mock("@tauri-apps/plugin-http")` 模拟原生 fetch，完整覆盖成功、401、网络错误等 7 项关键用例。
3. **`desktop/src/lib/` 纳管与 `.gitignore` 漏提交修复**：
   - **根因核验**：根目录 `.gitignore:13` 中存在无根路径限定的 `lib/` 规则，导致任意深度匹配，静默忽略了 `desktop/src/lib/` 目录。
   - **合规处置**：Maker 在本候选通过 `git add -f` 强制将 `api.ts`、`engine.ts`、`state.ts` 纳入版本控制，同时严格遵守合同 §5 禁止修改 `.gitignore` 的边界约束。
   - **文件完整性**：候选 commit 中完整包含了上述 3 个文件，修复了全新 clone 无法构建的前序历史缺陷。

## 修改范围复核

- 基线 SHA：`f760e08c16fbd51222852d21b327314366c4a8b2`
- 候选 SHA：`808c8d50ff70dad6e74c134790e01e179ae23a1f`
- 父链验证：`git rev-parse 808c8d5^` 返回 `f760e08c16fbd51222852d21b327314366c4a8b2`，链条正确单一。
- 修改文件范围：15 项变动全部在 `desktop/**` 范围内，未越界触碰任何禁止修改目录或根目录文件。
- 工作树状态：`git status --short` 干净。

## 阻断项（仅 FAIL）

无。

## 非阻断风险与遗留债务

1. **`.gitignore` 泛匹配规则债务**：
   - 根目录 `.gitignore` 第 13 行的 `lib/` 仍处于生效状态，后续若在其他子项目新增 `lib/` 目录仍可能被静默忽略。
   - **处置建议**：建议产品负责人后续单独设立工程维护切片，将规则收窄为 `/lib/`。
2. **fetch scope 窄模式范围边界**：
   - 当前 capabilities 中配置了默认云服务器 `http://101.42.9.223/*`。若用户在设置页将服务器地址修改为其他自定义 IP 或域名，fetch 请求将被 Tauri scope 拦截报错。
   - 此设计符合本轮 MVP 最小权限原则与合同导航要求，若后续需支持动态配置任意服务器地址，可在后续任务评估宽模式 scope（`http://*/*` / `https://*/*`）或运行时动态权限申请。

## B 级待执行人工项（产品负责人）

1. **桌面端启动验证**：在 `desktop/` 目录运行 `npm run tauri dev`，确认窗口正常加载且无 panic。
2. **真实登录与云端通信验证**：
   - 在登录界面使用 `13476526@qq.com` 获取验证码并登录。
   - 验证基于 `@tauri-apps/plugin-http` 的原生 HTTP 通路能够正常与真实后端 `http://101.42.9.223` 建立通信，彻底解决前序由 WebView 引起的 `Failed to fetch` 跨域与混合内容阻断问题。
3. **引擎健康与状态持久化**：
   - 确认主界面引擎健康指示灯变绿（端口分配、子进程拉起及 `/health` 轮询正常）。
   - 退出并重启应用，确认本地存储配置保持不变。

## 判定

- **PASS**：锁定 `808c8d50ff70dad6e74c134790e01e179ae23a1f` 为 V2-T8 第 4 轮候选提交。
