# Maker 完成说明 — V2-T9 第 1 轮

- **任务合同**：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v1.md`
- **转发消息**：`docs/dev-flow/tasks/V2-T9/02-planner-to-maker-message-v1.md`
- **起始 SHA**：`8b7a6474d6cd978bc204ca018708fe431f7c69db`
- **候选 SHA**：`6736512931bf00855b4c4122021c9e296a7bab49`
- **完成时间**：2026-08-25

---

## 1. 交付文件清单

本轮交付严格仅限 `desktop/**` 目录：
1. `desktop/package.json` & `desktop/package-lock.json`：新增 `@tauri-apps/plugin-dialog@^2.2.0`
2. `desktop/src-tauri/Cargo.toml` & `desktop/src-tauri/Cargo.lock`：新增 `tauri-plugin-dialog = "2"`
3. `desktop/src-tauri/src/lib.rs`：注册 `.plugin(tauri_plugin_dialog::init())`
4. `desktop/src-tauri/capabilities/default.json`：追加 `"dialog:default"` 权限
5. `desktop/src/lib/engineApi.ts`：引擎 HTTP 客户端（项目 CRUD、资料摄取与删除、通用知识包状态与同步）
6. `desktop/src/stores/project.ts`：Pinia store（向导步骤、活动项目、资料列表、通用包状态、加载态与错误处理）
7. `desktop/src/components/Step1Project.vue`：Step 1 项目管理、通用知识包同步卡片、资料文件选择/拖拽上传与列表表格、下一步流转
8. `desktop/src/views/Home.vue`：5 步向导顶部导航栏与视图容器集成
9. `desktop/src/tests/project.test.ts`：16 项新增单元测试（涵盖 engineApi 与 useProjectStore）
10. `desktop/dist/**`：前端构建打包产物

---

## 2. 核心设计与实现说明

1. **向导框架（Wizard Layout）**：
   - 在 `Home.vue` 顶部构建 5 步向导（1.项目与资料 -> 2.模板与大纲 -> 3.章节写作 -> 4.审阅修改 -> 5.成果导出），状态高亮与步骤跳转联动。
   - 步骤 2~5 设置了结构清晰的占位组件与“下一步/返回上一步”流转按钮。
2. **Step 1 项目与资料管理**：
   - 项目管理：支持下拉切换、内联输入创建新项目、删除项目及级联清理。
   - 通用知识包检测与同步：首启检测 `/generic/status`，未就绪展示警告并提供“一键同步”按钮，调用 `/generic/update` 传入服务端地址与 Token。
   - 资料管理：集成 `@tauri-apps/plugin-dialog` 原生文件选择对话框（过滤 `.docx, .xlsx, .csv, .md, .txt`）并支持拖拽，调用 `/projects/{name}/materials/ingest` 进行解析分块与向量化入库，表格实时显示文件大小、分块数与删除操作。
3. **引擎通信与错误处理**：
   - `engineApi.ts` 封装原生 fetch，统一处理 JSON 响应与 `detail` 错误解析，封装为 `EngineApiError`。

---

## 3. 快速验证记录

在 Windows 环境下按合同约定顺序执行快速验证命令：

```bash
# 1. Vitest 单元测试
npx vitest run
# 结果：3 个测试套件，28 项测试全部通过（原 12 项 + 新增 16 项）
# ✓ src/tests/api.test.ts (7 tests)
# ✓ src/tests/engine.test.ts (5 tests)
# ✓ src/tests/project.test.ts (16 tests)

# 2. Rust 插件与编译检查
cargo check (desktop/src-tauri)
# 结果：tauri-plugin-dialog 编译注册成功，Exit Code 0

# 3. TypeScript / Vue 严格类型检查
npx vue-tsc --noEmit (desktop)
# 结果：无类型报错，Exit Code 0

# 4. 前端构建
npm run build (desktop)
# 结果：生产环境 dist 打包成功，Exit Code 0
```

---

## 4. 已知风险与后续切片说明

- **Step 2 ~ Step 5 业务功能**：将在后续切片（S2 模板与大纲、S3 章节流式写作、S4 审阅修改与 Docx 导出）中逐步实现。
- **纯浏览器模式对话框**：在纯浏览器测试环境中使用 mock，在 Tauri 桌面环境下直接调用 Windows 原生对话框。

---

## 5. 冻结声明

- 代码变更严格限制在 `desktop/**`。
- 本地工作树已验证且保持干净，无 `git push`、无 `git rebase`、无 `git commit --amend`。
- 正式交付候选 SHA：`6736512931bf00855b4c4122021c9e296a7bab49`，交回评审。
