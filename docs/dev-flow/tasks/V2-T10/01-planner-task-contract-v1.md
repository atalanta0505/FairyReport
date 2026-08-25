# 任务合同 V2-T10 v1 — Step 3 章节流式写作与打字机式实时渲染开发

- 状态：ACCEPTED（第 1 轮 PASS；锁定候选 8702340573822f65fc025ed6534f05d648ee9ba7）
- 依据：用户实测向导已进入 Step 3，需要实现结合工程底稿向量检索与大模型的全流程流式章节写作与管理界面
- 精确起始 SHA：`7cdea8e19c9689fa6b2c7e0c40e53a258a4362a4`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

实现桌面端主流程 **Step 3 章节流式写作（`Step3Writing.vue`）** 及全链路持久化：
1. **本地引擎章节持久化端点扩展 (`engine/app/writing/router.py`)**：
   - `GET /projects/{name}/chapters`：读取 `%LOCALAPPDATA%/FairyReport/projects/<name>/chapters.json`，返回所有章节内容映射 `{ chapters: { "1": "...", "2": "..." } }`；
   - `POST /projects/{name}/chapters/{seq}`：落盘保存单章 Markdown 内容；
   - `DELETE /projects/{name}/chapters/{seq}`：清空/重置指定章节；
   - 现有的 `POST /writing/chapter` 端点已支持 `stream=true`（SSE 流式推送，包含项目底稿向量 RAG、通用规范注入与字数预算控制）。
2. **桌面端 API 客户端与 Store 状态管理 (`desktop/src/lib/engineApi.ts` & `desktop/src/stores/project.ts`)**：
   - 增加 `getProjectChapters`、`saveProjectChapter`、`streamChapterWriting`（对接 SSE 流式响应）；
   - Store 增加：
     - `chapters: Record<number, string>` 与 `chapterStatuses: Record<number, 'idle' | 'writing' | 'completed' | 'error'>`；
     - `selectedChapterSeq: number`（当前选中的章节，默认第 1 章）；
     - `loadChapters`、`saveChapter`、`writeChapterStream`（单章流式生成）、`writeAllChapters`（全书批量顺序流式生成，支持取消/暂停）；
     - 双重本地缓存备份（`localStorage` key: `frl_chapters_<projectName>`）。
3. **Step 3 界面组件开发 (`desktop/src/components/Step3Writing.vue`)**：
   - **左侧章节目录树与总控面板**：
     - 报告总览（章节总数、已写完成数、总字数统计）；
     - **`🚀 一键开始全书写作`** 与 **`✍️ 单章流式写作`** 按钮；
     - 章节列表卡片（序号、章标题、字数、生成状态标签、重新生成与清空）；
   - **右侧打字机流式写作编辑器**：
     - 章节标题、建议字数预算与当前实际字数；
     - 章节写作提示（Writing Hint）输入框；
     - 实时 Markdown 流式打字机渲染区，支持生成过程中实时阅读与生成完成后自由润色编辑；
   - **底部导航**：
     - `← 上一步：模板与大纲`
     - `下一步：审阅修改 →`（已生成章节 > 0 时激活）。
4. **集成至主向导 (`desktop/src/views/Home.vue`)**：
   - 引入并挂载 `<Step3Writing v-show="projectStore.currentStep === 3" />`，替换原有的静态占位容器。

---

## 2. 允许修改

- `engine/app/writing/router.py`
- `engine/tests/test_writing_router.py`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/stores/project.ts`
- `desktop/src/components/Step3Writing.vue` [NEW]
- `desktop/src/views/Home.vue`
- `desktop/src/tests/project.test.ts`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T10/**`

---

## 3. 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿（含章节存取端点测试）。
- [ ] `npx vitest run`（`desktop/`）全绿（含单章/多章流式写作与持久化测试）。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：在 Step 3 界面中点击「一键开始全书写作」或「单章流式写作」，可实时看到大模型结合已摄取工程资料打字机式流式撰写报告，且刷新/切步后内容 100% 持久留存。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
