# Maker 完成说明 — V2-T8 第 4 轮（plugin-http 原生 HTTP 通路 + src/lib 纳管修复）

## 合同与基线

- 有效合同：`tasks/V2-T8/01-planner-task-contract-v4.md`（v4，READY_FOR_MAKER；产品负责人 2026-08-21 "开工"批准）
- 起始 SHA：`f760e08c16fbd51222852d21b327314366c4a8b2`（开工前已核实 `git rev-parse HEAD` 一致且 `git status --short` 干净；注：第一次开工时 HEAD=727a1ff 但工作树含 28 个 desktop 外脏文件，已按停止条件报告未动工；产品负责人处置后以新基线 f760e08 重新开工）
- 轮次目录：rounds/04

## 唯一主要变化

云端 API（send-code/register/login/me/pack manifest）与引擎健康轮询改走 `@tauri-apps/plugin-http` 原生 fetch（Rust 通道，不受 WebView CORS/混合内容约束）。认证流程、状态持久化、引擎生命周期语义均不变。

## ⚠ 重大范围外发现：desktop/src/lib 从未入 git（第 1 轮漏提交）

开工中发现并已在本候选内修复：

- **现象**：`.gitignore:13` 的 `lib/`（Python 打包模板规则，本意忽略 setuptools 产物）在任意深度匹配目录名，误伤 `desktop/src/lib/`。`git check-ignore -v` 证实命中。
- **后果**：`desktop/src/lib/api.ts`、`engine.ts`、`state.ts` **从未进入任何提交**（`git log --all -- desktop/src/lib/` 为空；`git cat-file -e a10e900:desktop/src/lib/api.ts` 不存在）——第 1 轮完成说明称 33 项含 lib/**，与实际提交不符；历轮 A 级验证与 B 级实跑均在本地工作树执行故未暴露；**全新克隆无法构建桌面端**。
- **本轮处置**（合同 §4 允许 desktop/**、§5 禁止改 .gitignore，故不动 .gitignore 一字）：`git add -f desktop/src/lib/` 强制纳管三文件。api.ts/engine.ts 含本轮 plugin-http 修改，state.ts 为第 1 轮原样内容补录。三文件在 git 中显示为新增（A），属预期。
- **遗留债务（需产品负责人另立切片）**：`.gitignore` 第 13 行应收窄为 `/lib/`（或删除）以免未来再误伤；本轮合同禁止改 .gitignore，未动。历史候选 SHA（a10e900/fa541fd/b0c3b40）的树均缺 lib/**，全新检出不可构建，发布前须知悉。
- **对 Checker 的提示**：本候选 diff 含三个"新增" lib 文件不是越界，而是上述漏提交的补录 + 本轮修改，全部位于合同允许的 desktop/** 内。

## 候选

- 候选 SHA：`808c8d50ff70dad6e74c134790e01e179ae23a1f`
- 父提交：`f760e08c16fbd51222852d21b327314366c4a8b2`
- 提交标题：V2-T8 第4轮候选：云端API/引擎健康改走 plugin-http 原生 fetch；src/lib 强制纳管（修复第1轮 gitignore 漏提交）
- 修改文件（15 项，全部 desktop/**）：
  - `package.json`、`package-lock.json` — 新增依赖 `@tauri-apps/plugin-http@^2.5.9`（major=2 对齐；合同随批准，无清单外依赖）
  - `src-tauri/Cargo.toml`、`Cargo.lock` — 新增 `tauri-plugin-http = "2"`（锁定 v2.5.9；连带传递依赖由 cargo 解析）
  - `src-tauri/src/lib.rs` — 注册 `.plugin(tauri_plugin_http::init())`（+1 行）
  - `src-tauri/capabilities/default.json` — 增 `http:default` 权限对象 + fetch scope（见下）
  - `src/lib/api.ts` — `import { fetch } from "@tauri-apps/plugin-http"` 取代 global fetch；请求/错误分支逻辑零改动
  - `src/lib/engine.ts` — 默认 fetcher 改 `pluginFetch`（注入点保留：`deps?.fetcher ?? pluginFetch`）
  - `src/tests/api.test.ts` — 打桩对象从 `globalThis.fetch` 改为 `vi.mock("@tauri-apps/plugin-http")` + `vi.mocked(pluginFetch)`；成功/401/网络错误/Authorization 头分支 7 例全保留
  - `src/tests/engine.test.ts` — 仅移除已失效的 `globalThis.fetch` 打桩块（全部 5 例本就走注入 fetcher，断言零改动）
  - `src/lib/state.ts` — 第 1 轮内容补录（无修改）
  - `dist/**` — `npm run build` 重建（资产哈希更替 + index.html 引用更新）

## 关键设计决策

- **fetch scope 用窄模式（非宽模式）**，按合同 §3 最小覆盖：
  - `{"url": "http://101.42.9.223/*"}` — 云服务器默认地址（`DEFAULT_SERVER_URL`，settings.ts 核实）
  - `{"url": "http://127.0.0.1:*/*"}` — 引擎健康，端口组件通配（运行时 `pick_free_port` 随机端口）
  - 语法按 plugin-http v2 文档的 URL pattern（urlpattern crate，cargo check 时 tauri-codegen 已按插件 scope schema 编译期校验通过）
- **窄模式的已知边界（MVP 明示）**：设置页可改服务器地址，若用户改成其他地址，fetch 将被 scope 拦截报错。彻底解决需宽模式（`http://**`）或动态 scope，二者均超本轮合同语义边界，未采用；如需，请产品负责人决策后另立切片。
- **保持可测试性**：api.ts 静态 import plugin-http fetch，测试用 `vi.mock` 模块级打桩；engine.ts 注入点不变，测试继续打桩 fetcher。vitest node 环境不加载真实 Tauri 运行时。
- **未做 `npm audit fix`**（5 个存量漏洞属第 1/2 轮锁定依赖树，修复会越界改动清单外版本）。
- **build 告警已知悉**：vite 提示 @tauri-apps/api/core 既被动态（engine.ts spawn 路径）又被静态（plugin-http/plugin-shell/state.ts）引入，动态 import 不另切 chunk——仅打包提示，无行为影响。

## 验收标准对照

| 验收项（合同 v4 §6） | 结果 | 证据 |
|---|---|---|
| diff 仅 desktop/** + docs | ✅ | `git diff f760e08..808c8d5 --name-only` 15 项全在 desktop/**（本说明在 docs，单独提交） |
| 两个新依赖 major 与 tauri 2 对齐；无其他新依赖 | ✅ | npm `@tauri-apps/plugin-http@^2.5.9`；crate `tauri-plugin-http v2.5.9`；package.json diff 仅一行 |
| vitest 全绿（成功/401/网络错误经 mock plugin-http） | ✅ | 12 passed（api 7 + engine 5） |
| cargo check、vue-tsc 全绿 | ✅ | cargo check Finished（33.4s，含新 crate 首编）；vue-tsc 无错误 |
| B 级：`npm run tauri dev` 登录成功 + 引擎灯绿 + 设置保留 | ⏳ | 产品负责人实跑（本轮关键运行时验证） |

## 快速验证记录（按合同 v4 §7 顺序）

| 命令 | 结果 |
|---|---|
| `npx vitest run`（desktop） | exit 0：12 passed（api 7 + engine 5），670ms |
| `cargo check`（desktop/src-tauri） | exit 0：Locking +39 crates（含 tauri-plugin-http v2.5.9），Finished 33.40s |
| `npx vue-tsc --noEmit`（desktop） | exit 0：无错误 |
| `npm run build`（dist 重建，实现导航项） | exit 0：47 modules，505ms（仅 chunk 拆分提示，非错误） |

失败记录：无（全部一次通过，未触任何停止条件）。

## 明确保留（未改动）

- backend/**（未加 CORS）、HTTPS（发布前项）；认证/状态/引擎逻辑本身与 UI 结构；engine/**、根目录产品文件、generic_knowledge/**、.opencode/、AGENTS.md、**.gitignore（含误伤规则，权限所限未动，见遗留债务）**——git 核实

## 未执行项（移交人工 B 级）

- `npm run tauri dev` 实跑：登录成功（本轮关键验证）、引擎健康灯绿、设置重启保留——产品负责人执行

## 已知风险、未完成项与范围外发现

- 上述 **src/lib 漏提交** 为第 1 轮遗留缺陷，本轮已纳管修复；.gitignore 规则收窄为遗留债务。
- fetch scope 窄模式对"用户自定义服务器地址"不覆盖（见关键设计决策）。
- plugin-http fetch 对真实服务器的行为（超时/重定向等）以 B 级实跑为准。

## 冻结声明

未 amend、未 rebase、未 push；候选 `808c8d50ff70dad6e74c134790e01e179ae23a1f` 已冻结，本完成说明为独立提交，等待独立 Checker 对精确 SHA 验收。
