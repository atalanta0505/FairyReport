# 致 Maker 转发消息 — V2-T9 第 2 轮

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`b8be9b42211910ef61e1273966fbdf1c3bc938b8`
- 有效合同：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v2.md`

## 唯一主要行为

实现 Step 1 文件夹协同增强（打开本地资料文件夹 + 扫描本地目录摄取）与 Step 2 模板选择与大纲 AI 生成/在线编辑组件。

## 实现导航

1. `engine/app/embedding.py`：注入镜像环境变量 `os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")`。
2. `engine/app/materials/router.py`：实现 `POST /projects/{name}/materials/scan`，扫描 `files/` 目录下未入库或修改的文件，调用 chunking 和向量化入库。
3. `engine/app/writing/router.py`：实现 `GET /writing/templates`，返回 14 类报告类型及字数预算。
4. `desktop/src-tauri/capabilities/default.json`：确认/追加 `"shell:allow-open"`。
5. `desktop/src/lib/engineApi.ts`：扩展 `scanMaterials`、`getTemplates`、`generateOutline`。
6. `desktop/src/stores/project.ts`：扩展管理 `reportType`、`outlineMd`、`outlineChapters`、`generatingOutline`。
7. `desktop/src/components/Step1Project.vue`：添加「📁 打开资料目录」与「🔄 扫描本地资料」按钮及交互逻辑。
8. `desktop/src/components/Step2Outline.vue`：实现 14 种报告模板选择卡片/列表、调用 AI 生成大纲、大纲 Markdown 在线编辑与章节列表解析、上下步导航。
9. `desktop/src/views/Home.vue`：在 `currentStep === 2` 时渲染 `Step2Outline.vue`。
10. `engine/tests/` & `desktop/src/tests/`：添加/更新自动化测试。

## 允许修改

- `desktop/**`
- `engine/**`
- `docs/dev-flow/tasks/V2-T9/**`

## 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

## 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `cargo check`（workdir=`desktop/src-tauri`）
4. `npx vue-tsc --noEmit`（workdir=`desktop`）
5. `npm run build`（workdir=`desktop`）

## 停止条件

- 基线或工作树不符；
- 必须越界修改；
- 同一失败尝试两次未果。

## 完成时

1. 只提交允许范围（`desktop/**` 与 `engine/**` 候选提交）；
2. 完成说明写到 `docs/dev-flow/tasks/V2-T9/rounds/02/maker-completion.md`，单独提交；
3. 不 amend、不 rebase、不 push；
4. 冻结工作树交回。
