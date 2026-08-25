# 任务合同 V2-T9 v2 — 桌面主流程 UI（第 2 切片：Step 1 文件夹协同增强 + Step 2 模板选择与大纲生成/在线编辑）

- 状态：ACCEPTED（第 2 轮 PASS；锁定候选 ed86991a68bfced448853ca9bc5590b655fc5df5）
- 依据：`docs/dev-flow/tasks/V2-DESKTOP/00-product-decision-v4.md` 及 2026-08-25 产品负责人关于“本地文件夹协同”与大纲设计的明确反馈
- 精确起始 SHA：`b8be9b42211910ef61e1273966fbdf1c3bc938b8`（已验收锁定第 1 轮 6736512）
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

本切片承担两大核心能力演进：
1. **Step 1 文件夹协同与稳定性增强（落实用户建议）**：
   - **国内镜像加固**：在 `engine/app/embedding.py` 中默认注入 `HF_ENDPOINT=https://hf-mirror.com`，根治首次模型下载卡顿/超时。
   - **本地目录一键直达**：在 Step 1 增加 **「📁 打开资料目录」** 按钮，点击调用原生文件管理器打开当前项目的 `files/` 目录。
   - **本地文件夹一键扫描**：在 `engine/app/materials/router.py` 新增 `POST /projects/{name}/materials/scan` 端点；在 Step 1 增加 **「🔄 扫描本地资料」** 按钮，支持用户将多份文件直接拷入目录后一键自动识别、切片分块与向量化。
2. **Step 2 模板选择与大纲生成/编辑（核心业务落地）**：
   - **模板获取**：在 `engine/app/writing/router.py` 新增 `GET /writing/templates` 端点（返回 14 类投前咨询报告类型及建议字数预算）。
   - **大纲 AI 生成**：对接 `POST /writing/outline`，前端读取 Settings 中的用户 LLM key 配置与当前项目已摄取资料/通用知识库，一键生成结构化 Markdown 大纲。
   - **大纲在线编辑与章节解析**：实现 `Step2Outline.vue`，支持大纲 Markdown 在线实时编辑、章节标题树形结构解析与保存，提供「← 上一步：项目与资料」与「下一步：章节写作 →」双向向导流转。

---

## 2. 依赖引入与权限配置

- 无新增 npm/cargo 依赖（复用现有的 `@tauri-apps/plugin-dialog`、`@tauri-apps/plugin-shell` 与 `@tauri-apps/plugin-http`）。
- 权限配置：`desktop/src-tauri/capabilities/default.json` 确认包含 `"shell:allow-open"`（用于打开本地项目文件夹）。

---

## 3. 明确不做

- 不做 Step 3 章节流式写作（SSE）与 Step 4 审阅修改（留至第 3 切片 S3）。
- 不做 Step 5 Docx 导出（留至第 4 切片 S4）。
- 不做云端大纲同步（全流程纯本地离线计算）。

---

## 4. 实现导航

- **引擎后端扩展**：
  - `engine/app/embedding.py`：注入镜像环境变量 `os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")`。
  - `engine/app/materials/router.py`：新增 `POST /projects/{name}/materials/scan` 扫描并摄取本地 `files/` 目录下未入库文件。
  - `engine/app/writing/router.py`：新增 `GET /writing/templates` 列出 14 种报告类型。
- **桌面 API 客户端** (`desktop/src/lib/engineApi.ts`)：
  - 新增 `scanMaterials(baseUrl, projectName)`
  - 新增 `getTemplates(baseUrl)`
  - 新增 `generateOutline(baseUrl, req)`
  - 新增 `getProjectDir(name)` 辅助方法
- **状态管理** (`desktop/src/stores/project.ts`)：
  - 管理 `reportType`（选定模板）、`outlineMd`（大纲文本）、`outlineChapters`（章节列表）、`generatingOutline`（生成状态）。
- **UI 组件开发**：
  - `desktop/src/components/Step1Project.vue`：增加「📁 打开资料目录」与「🔄 扫描本地资料」按钮及提示说明。
  - `desktop/src/components/Step2Outline.vue`：
    - 模板选择网格/下拉列表（14 种报告类型，包含字数预算提示）；
    - AI 大纲生成控制栏（支持重新生成）；
    - 大纲编辑器（双栏或编辑预览一体，实时 Markdown 编辑并同步章节结构）；
    - 底部流转按钮（支持返回 Step 1，大纲就绪后进入 Step 3）。
  - `desktop/src/views/Home.vue`：在 `currentStep === 2` 时渲染 `Step2Outline.vue`。
- **测试**：
  - `engine/tests/test_materials.py` 与 `test_writing_router.py` 增补 scan 与 templates 测试。
  - `desktop/src/tests/project.test.ts` 增补大纲生成与模板选择测试。

---

## 5. 允许修改

- `desktop/**`
- `engine/**`（仅限于 `embedding.py`, `materials/router.py`, `writing/router.py` 及对应 tests）
- `docs/dev-flow/tasks/V2-T9/**`

---

## 6. 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 7. 验收标准

- [ ] **代码边界**：diff 严格限定在 `desktop/**`、`engine/**` 和 `docs/dev-flow/tasks/V2-T9/**`。
- [ ] **A 级自动化测试**：
  - `python -m pytest engine/tests -q` 全绿。
  - `npx vitest run`（`desktop/`）全绿（原有 28 项 + 新增测试全部通过）。
  - `cargo check`（`desktop/src-tauri/`）全绿。
  - `npx vue-tsc --noEmit` 全绿。
  - `npm run build` 构建成功且 dist 产物一致。
- [ ] **B 级实跑**：
  - 点击「📁 打开资料目录」可打开 Windows 文件夹；放入文件后点击「🔄 扫描本地资料」可秒级完成摄取分块。
  - 点击「选择文件」弹窗选取后分块摄取在 1~2 秒内秒级完成。
  - 流转至 Step 2，14 种模板可选；点击「AI 智能生成大纲」，调用 DeepSeek 成功生成完整结构化大纲并展示在编辑器中。
  - 支持在大纲编辑器中修改文字，点击下一步可正常流转。

---

## 8. 快速验证顺序（Maker）

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `cargo check`（workdir=`desktop/src-tauri`）
4. `npx vue-tsc --noEmit`（workdir=`desktop`）
5. `npm run build`（workdir=`desktop`）

---

## 9. 停止条件

- 发现基线或工作树不符；
- 必须修改 `backend/**` 或禁止修改目录；
- 相同测试或编译失败连续两次；
- 大纲生成遇到不可恢复的异常。

---

## 10. 候选交付要求

- 候选提交包含 `desktop/**` 与 `engine/**` 修改。
- 完成说明写至 `docs/dev-flow/tasks/V2-T9/rounds/02/maker-completion.md` 并单独提交。
- 不 amend、不 rebase、不 push，候选提交后立即冻结并交回。
