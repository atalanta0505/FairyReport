# 任务合同 V2-T9 v1 — 桌面主流程 UI（第 1 切片：向导框架 + 项目与资料管理 + 通用知识包同步）

- 状态：READY_FOR_MAKER（2026-08-25 产品负责人批准）
- 依据：`docs/dev-flow/tasks/V2-DESKTOP/00-product-decision-v4.md`（D14/D15/D18 架构 C 桌面主流程定案）
- 精确起始 SHA：`813b28f1677319cf0ff6e5df195ea3dd572486aa`（已推送远端 master）
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

在桌面端实现 5 步主流程向导导航骨架，并完整落地 **Step 1: 项目与资料管理** 与 **通用知识包状态检测与同步**：
1. **向导导航框架**：在 `Home.vue` 中构建标准 5 步向导流程条（1.项目与资料 -> 2.模板与大纲 -> 3.章节写作 -> 4.审阅修改 -> 5.成果导出），支持步骤间切换与状态感知。
2. **项目管理**：支持项目列表获取、创建新项目、切换当前活动项目、删除项目（对接引擎 `/projects` CRUD API）。
3. **资料管理**：支持通过原生文件选择对话框（`@tauri-apps/plugin-dialog`）或文件拖拽选择待摄取文件（.docx/.xlsx/.csv/.md/.txt），调用引擎 `/projects/{name}/materials/ingest` 执行解析-分块-向量化入库，实时展示资料列表（文件名、类型、分块数、大小、时间）与删除资料功能。
4. **通用知识包管理**：挂载检测 `/generic/status`，若未安装显示“通用知识包未就绪”提示并提供“一键同步”按钮（调用 `/generic/update` 传入 serverUrl 与 token）。

---

## 2. 依赖引入（随本合同批准请求）

为提供原生文件选择对话框体验，本切片引入官方 Tauri 2 对齐依赖：
- **npm 依赖**：`@tauri-apps/plugin-dialog@^2.2.0`（用于前端 `open()` 弹窗选择文件）
- **Rust crate**：`tauri-plugin-dialog = "2"`（锁定 v2.x，注册进 `src-tauri/src/lib.rs`）
- **Capabilities 权限**：`src-tauri/capabilities/default.json` 增加 `"dialog:default"`

---

## 3. 明确不做（本切片非目标）

- 不做 Step 2 ~ Step 5 的具体业务功能（大纲生成、写作流式、审阅、Docx 导出分别留在 S2/S3/S4）。
- 不改动 `engine/**` 后端接口与数据库模型（复用现有已验收 API）。
- 不引入富文本/Markdown 重量级编辑器（保留至 S2/S3）。

---

## 4. 实现导航

- **依赖与 Rust 配置**：
  - `desktop/package.json`：新增 `@tauri-apps/plugin-dialog`
  - `desktop/src-tauri/Cargo.toml`：新增 `tauri-plugin-dialog = "2"`
  - `desktop/src-tauri/src/lib.rs`：注册 `.plugin(tauri_plugin_dialog::init())`
  - `desktop/src-tauri/capabilities/default.json`：追加 `"dialog:default"`
- **引擎 API 客户端**：
  - `desktop/src/lib/engineApi.ts`：封装 `/projects`、`/projects/{name}/materials`、`/generic` 的 HTTP 请求（使用已验收的 `@tauri-apps/plugin-http` 原生 fetch 或 engine.ts 内部通信通路）。
- **状态管理**：
  - `desktop/src/stores/project.ts`：管理当前活动项目、项目列表、当前项目资料列表、通用包状态、向导当前步骤。
- **UI 组件**：
  - `desktop/src/views/Home.vue`：重构为主流程向导布局（顶部 Step 1~5 步骤指示器，主体根据当前 step 渲染对应组件）。
  - `desktop/src/components/Step1Project.vue`：
    - 顶部：项目切换下拉框 + “新建项目”弹窗/输入框 + “删除项目”；
    - 中部：通用知识包状态卡片（已安装版本 / 未安装状态 + “一键下载安装”按钮与加载态）；
    - 下部：资料上传卡片（“选择文件”按钮 + 支持 docx/xlsx/csv/md/txt + 拖拽上传区域）+ 资料列表表格（展示 source_id, ext, chunk_count, size, created_at, 操作栏删除按钮）；
    - 底部：“下一步：模板与大纲”按钮（当前有选中项目时点亮）。
- **测试**：
  - `desktop/src/tests/project.test.ts`：单元测试覆盖项目增删选、资料摄取与删除、通用包状态逻辑。

---

## 5. 允许修改

- `desktop/**`（package*.json, Cargo.*, src/**, src-tauri/**, dist/**）
- `docs/dev-flow/tasks/V2-T9/**`

---

## 6. 禁止修改

- `engine/**`、`backend/**`、根目录产品文件、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 7. 验收标准

- [ ] **代码边界**：diff 严格限制在 `desktop/**` 与 `docs/dev-flow/tasks/V2-T9/**`。
- [ ] **依赖规范**：仅新增 `@tauri-apps/plugin-dialog`（major=2 对齐），无其他未经批准依赖。
- [ ] **A 级验证**：
  - `npx vitest run`（`desktop/`）全绿（原有 12 项测试 + 本切片新增测试全部通过）。
  - `cargo check`（`desktop/src-tauri/`）全绿（插件注册编译无误）。
  - `npx vue-tsc --noEmit` 全绿（无类型报错）。
  - `npm run build` 构建成功且 dist 产物一致。
- [ ] **B 级实跑**：
  - `npm run tauri dev` 启动，主界面呈现 5 步向导框架。
  - 项目创建（例如新建 `测试工程项目1`）成功并可在下拉列表切换。
  - 点击“选择文件”可唤起 Windows 原生文件选择器，选取测试文件（如 `.docx` 或 `.md`）后成功摄取并展示在资料列表中（显示分块数）。
  - 点击“一键同步通用知识包”成功从云端下载并安装，状态显示“通用知识包已就绪”。
  - 资料与项目删除功能正常工作。

---

## 8. 快速验证顺序（Maker）

1. `npx vitest run`（workdir=`desktop`）
2. `cargo check`（workdir=`desktop/src-tauri`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）

---

## 9. 停止条件

- 发现基线或工作树不符；
- 必须修改 `engine/**` 或 `desktop/**` 以外文件；
- 相同测试或编译失败连续两次；
- 依赖版本与 Tauri 2 冲突或下载异常。

---

## 10. 候选交付要求

- 候选提交仅包含 `desktop/**` 文件。
- 完成说明写至 `docs/dev-flow/tasks/V2-T9/rounds/01/maker-completion.md` 并单独提交。
- 不 amend、不 rebase、不 push，候选提交后立即冻结并交回。
