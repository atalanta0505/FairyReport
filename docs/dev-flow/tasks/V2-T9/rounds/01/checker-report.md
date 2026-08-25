# Checker 验收报告 — V2-T9 第 1 轮

- 状态：**PASS**
- 精确候选 SHA：`6736512931bf00855b4c4122021c9e296a7bab49`
- 依据合同：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v1.md`
- 基线 SHA：`8b7a6474d6cd978bc204ca018708fe431f7c69db`

---

## 1. 独立检查边界与重跑证据

所有 A 级快速验证命令均由 Checker 独立在当前工作树下重新执行，未盲目采信 Maker 自述：

- **Vitest 单元测试**：`npx vitest run`（workdir=`desktop`）
  - 结果：exit code 0，**28 passed**（3 个测试文件，总计 28 项测试用例，耗时 832ms）。
  - 套件详情：
    - `src/tests/api.test.ts` (7 tests)
    - `src/tests/engine.test.ts` (5 tests)
    - `src/tests/project.test.ts` (16 tests，本切片新增)
  - 覆盖项：引擎 API 项目 CRUD、资料摄取与删除、通用知识包检测与更新、网络异常与 409 错误透传；Pinia store 步骤切换、项目切换与自选、资料响应式列表更新、通用包状态维护等。
- **Rust 编译与插件检查**：`cargo check`（workdir=`desktop/src-tauri`）
  - 结果：exit code 0，`Finished dev profile [unoptimized + debuginfo] target(s) in 0.67s`，无编译错误或警告。
- **TypeScript 类型检查**：`npx vue-tsc --noEmit`（workdir=`desktop`）
  - 结果：exit code 0，无任何类型报错。
- **前端生产构建验证**：`npm run build`（workdir=`desktop`）
  - 结果：exit code 0，53 modules transformed，生产环境打包成功。
  - 构建后工作树核对：`git status` 干净，产物哈希与候选提交记录完全一致。

---

## 2. 验收标准逐条核对（合同 §7）

| 合同验收标准 | 证据等级 (A/B/C/D) | 证据与核验结论 |
|---|---|---|
| §7.1 代码边界：diff 严格限制在 `desktop/**` | A | `git diff --name-status 8b7a647..6736512` 显示仅修改/新增 `desktop/**`（包含 package*.json, Cargo.*, capabilities/default.json, src-tauri/src/lib.rs, src/components/**, src/lib/**, src/stores/**, src/tests/**, src/views/**, dist/**），未触碰 `engine/**`、`backend/**` 或根目录。 |
| §7.2 依赖规范：仅新增 `@tauri-apps/plugin-dialog`（major=2 对齐），无其他未批准依赖 | A | `desktop/package.json` 新增 `@tauri-apps/plugin-dialog: ^2.2.0`（锁定 2.7.2）；`desktop/src-tauri/Cargo.toml` 新增 `tauri-plugin-dialog = "2"`（锁定 2.7.2）；Tauri 2 官方体系版本对齐。 |
| §7.3 A 级验证：vitest 全绿（原12项+新增16项全部通过） | A | 独立重跑通过：28 项用例全部通过（100% 通过率）。 |
| §7.3 A 级验证：`cargo check` 全绿（插件注册编译无误） | A | 独立重跑通过：exit code 0，插件初始化与 tauri-codegen 正常。 |
| §7.3 A 级验证：`npx vue-tsc --noEmit` 全绿 | A | 独立重跑通过：exit code 0，严格类型检查通过。 |
| §7.3 A 级验证：`npm run build` 构建成功且 dist 产物一致 | A | 独立重跑通过：exit code 0，打包生成物与提交完全一致。 |
| §7.4 B 级实跑：5 步向导、项目 CRUD、文件对话框选取与摄取、通用包一键同步 | ⏳ | B 级人工项，由产品负责人实机执行并验收。 |

---

## 3. 代码级重点审查

1. **原生文件对话框插件与权限（`tauri-plugin-dialog`）**：
   - `desktop/src-tauri/src/lib.rs`：在 `tauri::Builder::default()` 链式调用中正确注册 `.plugin(tauri_plugin_dialog::init())`。
   - `desktop/src-tauri/capabilities/default.json`：在 `permissions` 数组中追加 `"dialog:default"`，符合 Tauri 2 最小权限规范。
   - 依赖版本 `2.7.2` 与 `tauri 2` 核心完全兼容。
2. **本地引擎客户端封装（`desktop/src/lib/engineApi.ts`）**：
   - 统一采用 `@tauri-apps/plugin-http` 的 `pluginFetch`，绕开浏览器同源沙箱限制。
   - 完整实现了 `/projects`（GET / POST / DELETE）、`/projects/{name}/materials`（GET / DELETE）、`/projects/{name}/materials/ingest`（POST）、`/generic/status`（GET）、`/generic/update`（POST）等本地引擎 API。
   - 统一使用 `EngineApiError` 对 HTTP 4xx/5xx 与网络异常（status=0）进行结构化封装，解析后端返回的 `detail` 错误信息。
3. **状态管理（`desktop/src/stores/project.ts`）**：
   - 基于 Pinia 管理主流程当前步骤（`currentStep` 1~5 边界限制）、活动项目（`currentProject`）、资料列表（`materials`）、通用包状态（`genericStatus`）与各类加载中状态（`loadingProjects`, `loadingMaterials`, `ingesting`, `updatingGeneric`）。
   - 包含项目创建自动选中、项目删除自动清理级联资料、资料摄取与删除自动刷新等响应式流转。
4. **向导导航与 Step 1 UI 组件（`Home.vue` & `Step1Project.vue`）**：
   - `Home.vue`：顶部导航栏实现 5 步向导指示器（1.项目与资料 -> 2.模板与大纲 -> 3.章节写作 -> 4.审阅修改 -> 5.成果导出），状态高亮与步骤跳转联动，步骤 2~5 提供结构清晰的占位组件与流转操作；支持与设置页面无缝切换。
   - `Step1Project.vue`：
     - 项目管理：支持下拉切换、内联新建项目、删除确认提示；
     - 通用知识包：状态卡片显示已安装版本/未就绪警告，支持「一键同步通用知识包」；
     - 资料上传与列表：提供文件拖拽 Dropzone 与「选择文件」原生对话框（过滤 `.docx, .xlsx, .csv, .md, .txt`），摄取过程呈现分块向量化加载动画，表格实时展示扩展名 Badge、分块数、文件大小及删除操作；
     - 流转守卫：当前未选择项目时禁用「下一步」与文件选择操作。
5. **测试覆盖（`desktop/src/tests/project.test.ts`）**：
   - 16 项测试用例全部采用 Vitest + mock `@tauri-apps/plugin-http`，覆盖了正常流程、409 重复命名、网络断开、跨步骤越界及资料增删。

---

## 4. 修改范围复核

- **基线 SHA**：`8b7a6474d6cd978bc204ca018708fe431f7c69db`
- **候选 SHA**：`6736512931bf00855b4c4122021c9e296a7bab49`
- **父链验证**：`git rev-parse 6736512^` 返回 `8b7a6474d6cd978bc204ca018708fe431f7c69db`，提交链条单一连续。
- **文件范围**：无任何越界修改，严格遵循合同 §5 与 §6 约束。
- **工作树状态**：干净。

---

## 5. 阻断项（仅 FAIL）

无。

---

## 6. 非阻断风险与后续切片说明

1. **Step 2 ~ Step 5 业务功能占位**：
   - 当前向导步骤 2（模板与大纲）、步骤 3（章节写作）、步骤 4（审阅修改）、步骤 5（成果导出）为占位卡片，将在后续任务切片（S2/S3/S4）中逐步落地。
2. **拖拽上传在纯 Web 环境下的沙箱限制**：
   - 在 Tauri 桌面环境下，拖拽的 `File` 对象含有 native `path` 属性可直接获取本地路径并调用 `/materials/ingest`；在纯 Web/浏览器预览下浏览器出于沙箱安全无法获取物理路径。UI 已在未获取到路径时给出明确指引，引导点击「选择文件」使用原生对话框。

---

## 7. B 级待执行人工项（产品负责人）

1. **启动与向导界面**：在 `desktop/` 目录运行 `npm run tauri dev`，确认顶部呈现 5 步向导流程条及 Step 1 界面。
2. **项目创建与切换**：
   - 点击「新建项目」，输入项目名称（如 `水库安全鉴定项目A`）并确认创建；
   - 验证下拉框自动选中新项目，尝试在多个项目间切换。
3. **通用知识包一键同步**：
   - 观察通用知识包卡片状态（若未安装显示黄色警告）；
   - 点击「一键同步通用知识包」，验证从云端下载并解压安装，安装成功后状态变更为绿色「已就绪」并展示版本号。
4. **原生文件选取与资料摄取**：
   - 点击「选择文件」按钮，确认弹出 Windows 原生文件选择对话框且默认过滤 `.docx, .xlsx, .csv, .md, .txt`；
   - 选取一份工程底稿测试文件，观察加载条提示「文件解析与分块向量化入库中」；
   - 摄取完成后核对资料列表表格：文件名、文件类型 Badge、分块数、文件大小与摄取时间是否正确展示。
5. **资料与项目删除及步骤流转**：
   - 点击资料右侧「删除」按钮，确认二次确认弹窗与删除成功反馈；
   - 点击底部的「下一步：模板与大纲 &rarr;」，验证成功流转至 Step 2 占位视图，且顶部步骤 1 变为绿色完成态、步骤 2 高亮激活。

---

## 8. 判定

- **PASS**：批准候选 SHA `6736512931bf00855b4c4122021c9e296a7bab49`，各项 A 级指标全绿，架构与代码质量优秀，进入产品负责人 B 级人工验收。
