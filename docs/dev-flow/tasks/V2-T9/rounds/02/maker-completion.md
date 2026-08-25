# Maker 完成说明 — V2-T9 第 2 轮

- **任务合同**：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v2.md`
- **转发消息**：`docs/dev-flow/tasks/V2-T9/02-planner-to-maker-message-v2.md`
- **起始 SHA**：`07cbe6c34ada77185111975c7067354d55ba31fb`
- **候选 SHA**：`ed86991a68bfced448853ca9bc5590b655fc5df5`
- **完成时间**：2026-08-25

---

## 1. 交付文件清单

本轮交付严格仅限 `desktop/**` 与 `engine/**` 目录：

### 引擎后端 (`engine/**`)
1. `engine/app/embedding.py`：注入国内镜像环境变量 `os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")`，防止首次模型下载超时。
2. `engine/app/materials/router.py`：
   - 提取通用 `_process_file` 单文件解析、分块、向量化与入库方法；
   - 新增 `POST /projects/{name}/materials/scan` 端点，扫描项目 `files/` 目录下未入库或已存在合规文件，分块向量化入库并返回 `IngestResult` 列表。
3. `engine/app/writing/router.py`：
   - 新增 `GET /writing/templates` 端点，列出 14 种投前咨询标准报告类型及其字数预算和模板规范。
4. `engine/tests/test_materials.py`：新增 4 项扫描端点自动化单测（空目录、多文件扫描入库、过滤不支持后缀、404）。
5. `engine/tests/test_writing_router.py`：新增 2 项模板端点自动化单测（默认 14 类模板与安装通用包后的模板详情）。

### 桌面端 (`desktop/**`)
1. `desktop/src-tauri/capabilities/default.json`：追加 `"shell:allow-open"` 权限，支持原生打开本地文件夹。
2. `desktop/src/lib/engineApi.ts`：
   - 新增 `TemplateItem`、`LLMConfig`、`OutlineRequest`、`ChapterInfo`、`OutlineResult` 接口定义；
   - 新增 `scanMaterials`、`getTemplates`、`generateOutline`、`getProjectFilesDir`、`openProjectDir` 方法。
3. `desktop/src/stores/project.ts`：
   - 扩展管理 `reportType`（选定模板）、`templates`（14 类模板列表）、`loadingTemplates`、`outlineMd`（大纲文本）、`outlineChapters`（章节列表）、`generatingOutline`；
   - 新增 `scanMaterials`、`loadTemplates`、`generateOutline`、`setOutlineMd`（含实时章节解析同步 `parseChaptersFromOutline`）、`setReportType` 方法。
4. `desktop/src/components/Step1Project.vue`：
   - 资料管理卡片头部增加「📁 打开资料目录」与「🔄 扫描本地资料」按钮；
   - 更新操作提示文案，支持“直接拷入目录 + 一键扫描摄取”的高效协同模式。
5. `desktop/src/components/Step2Outline.vue`（新创建）：
   - 14 类投前咨询报告模板选择卡片网格，展示字数预算与模板规范提示；
   - 「🪄 AI 智能生成大纲」按钮（自动读取 Settings 中的 LLM Key/Url/Model 并展示 Loading 态）；
   - 双栏编辑器：左侧多行 Markdown 源码编辑（实时统计行数与字数），右侧实时章节目录结构树预览；
   - 底部向导导航：「← 上一步：项目与资料」与「下一步：章节写作 →」（大纲就绪时激活）。
6. `desktop/src/views/Home.vue`：在 `currentStep === 2` 时渲染 `Step2Outline.vue`。
7. `desktop/src/tests/project.test.ts`：新增 7 项单测，测试套件用例增至 35 项全部通过。
8. `desktop/dist/**`：构建输出产物同步更新。

---

## 2. 核心设计与实现说明

1. **本地文件夹协同增强（落实用户交互建议）**：
   - 用户既可通过「选择文件」弹窗或拖拽进行资料导入，也可点击「📁 打开资料目录」在 Windows Explorer 中直接打开当前项目的 `files/` 文件夹；
   - 拷入一份或多份工程底稿后，点击「🔄 扫描本地资料」，引擎调用 `POST /projects/{name}/materials/scan` 秒级自动识别、解析、分块切片并建立向量索引，并刷新资料表格。
2. **14 类标准报告模板选择**：
   - 覆盖《产业发展规划报告》《企业发展规划报告》《园区发展规划报告》《可行性研究报告》《项目建议书》《政府和社会资本合作项目特许经营方案》等 14 类投前咨询标准报告；
   - 选定模板后显示建议字数预算及模板特殊编写规范要求。
3. **AI 大纲智能生成与实时在线编辑联动**：
   - 读取 Settings 中的 DeepSeek/LLM 配置，调用 `/writing/outline` 生成符合行业规范的层级结构大纲；
   - 实现大纲源码与章节目录结构树的双向同步：用户在 Markdown 文本框中编辑章标题时，右侧章节列表自动实时重新解析并展示章序号与标题。

---

## 3. 快速验证记录

严格按照合同第 8 条约定的快速验证顺序执行：

```bash
# 1. 引擎测试套件
python -m pytest engine/tests -q
# 结果：69 passed in 57.12s（覆盖全部 69 项后端单测）

# 2. 前端 Vitest 单元测试
npx vitest run (desktop)
# 结果：3 个测试文件，35 项测试全部通过（通过率 100%）
# ✓ src/tests/api.test.ts (7 tests)
# ✓ src/tests/engine.test.ts (5 tests)
# ✓ src/tests/project.test.ts (23 tests)

# 3. Rust 编译与权限检查
cargo check (desktop/src-tauri)
# 结果：Finished `dev` profile in 1.01s，Exit Code 0

# 4. Vue/TypeScript 严格类型检查
npx vue-tsc --noEmit (desktop)
# 结果：无类型报错，Exit Code 0

# 5. 前端生产打包构建
npm run build (desktop)
# 结果：Vite 构建打包成功（dist 产物一致），Exit Code 0
```

---

## 4. 已知风险与后续切片说明

- **Step 3 章节流式写作（SSE）**：将在第 3 切片 S3 中基于本切片生成/编辑好的 `outlineMd` 和 `outlineChapters` 进行多章节并发/流式编写。
- **Step 4 审阅修改与 Step 5 Docx 导出**：留至后续切片实现。

---

## 5. 冻结声明

- 代码变更严格限定在 `desktop/**` 与 `engine/**`。
- 本地工作树已验证且保持干净，无 `git push`、无 `git rebase`、无 `git commit --amend`。
- 正式交付候选 SHA：`ed86991a68bfced448853ca9bc5590b655fc5df5`，交回评审。
