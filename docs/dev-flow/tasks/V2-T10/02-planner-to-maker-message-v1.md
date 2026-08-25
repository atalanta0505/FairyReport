# 致 Maker 转发消息 — V2-T10 第 1 轮（Step 3 章节流式写作开发）

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`7cdea8e19c9689fa6b2c7e0c40e53a258a4362a4`
- 有效合同：`docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v1.md`

## 唯一主要行为

开发 Step 3 章节流式写作界面与全链路持久化：
1. **引擎后端端点扩展 (`engine/app/writing/router.py`)**：
   - 实现 `GET /projects/{name}/chapters` 与 `POST /projects/{name}/chapters/{seq}` 端点，存取 `%LOCALAPPDATA%/FairyReport/projects/<name>/chapters.json`（或每个章节单个 md 文件）；
2. **桌面端 API 扩展 (`desktop/src/lib/engineApi.ts`)**：
   - 封装 `getProjectChapters`、`saveProjectChapter` 以及 SSE 流式调用 `streamWriteChapter(baseUrl, req, onChunk, onDone, onError)`；
3. **Store 管理 (`desktop/src/stores/project.ts`)**：
   - 增加 `chapters`、`chapterStatuses`、`selectedChapterSeq`、`loadChapters`、`saveChapter`、`writeChapterStream`、`batchWriteAllChapters` 等；
   - 增加 `localStorage` 离线备份与防抖自动落盘；
4. **UI 组件开发 (`desktop/src/components/Step3Writing.vue`)**：
   - 左侧章节目录列表（各章状态、字数统计、单章/全书写作按钮）；
   - 右侧打字机流式写作编辑器与 Markdown 实时预览，支持随时人工润色；
   - 底部上下步流转导航；
5. **在 `Home.vue` 中接入 `Step3Writing`**：
   - 替换原来的 Step 3 占位卡片为 `<Step3Writing v-show="projectStore.currentStep === 3" />`；
6. **单元测试与产物**：
   - 编写引擎端点与前端 Store 单元测试，运行 build 与 cargo check。

## 允许修改

- `engine/app/writing/router.py`
- `engine/tests/test_writing_router.py`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/stores/project.ts`
- `desktop/src/components/Step3Writing.vue` [NEW]
- `desktop/src/views/Home.vue`
- `desktop/src/tests/project.test.ts`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T10/**`

## 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

## 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）

## 完成时

1. 只提交允许范围（`engine/**` 与 `desktop/**` 候选提交）；
2. 完成说明写到 `docs/dev-flow/tasks/V2-T10/rounds/01/maker-completion.md`，单独提交；
3. 不 amend、不 rebase、不 push；
4. 冻结工作树交回。
