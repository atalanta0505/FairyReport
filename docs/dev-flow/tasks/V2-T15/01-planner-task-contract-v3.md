# 任务合同 V2-T15 v3 — Step 4 章节导航栏优化与审阅流式思考推演 / 实时进度反馈改造

- 状态：ACCEPTED（2026-08-26 Checker 独立验收通过，锁定 SHA `b0d4a03e69e35ac4ce28d6c389cadc0c01e9e184`）
- 依据：产品负责人确认 2 项核心诉求（左侧章节导航栏支持每章子标题内部自如滚动、长章标题 100% 完整显示无省略截断；专家审阅支持 SSE 流式思考推演输出、章节流转看板与每章即时落盘刷新）
- 精确起始 SHA：`76db1f2316ca815c189b5194c104f09b1648686f`
- 候选交付 SHA：`b0d4a03e69e35ac4ce28d6c389cadc0c01e9e184`
- 验收报告：`docs/dev-flow/tasks/V2-T15/rounds/03/checker-report.md`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **左侧章节导航栏交互与布局优化 (`desktop/src/components/Step4Review.vue`)**：
   - **长章节标题 100% 完整显示**：`.ch-title-text` 改为 `white-space: normal; word-break: break-word; line-height: 1.35;`，导航面板宽度优化为 `320px`，确保收起或展开状态下任何长度的章节标题完整清晰呈现，杜绝 `...` 截断；
   - **每章子标题内部独立平滑滚动**：`.subheadings-subtree` 增加 `max-height: 280px; overflow-y: auto;` 并配置自定义轻量滚动条，单章多达数十个子标题时可在卡片内流畅滚动，彻底根除底部文字被裁切截断问题；
   - 保持外层 `.outline-tree-scrollable` 的平滑全树滚动。

2. **后端专家审阅 SSE 流式端点与思考推演支持 (`engine/app/writing/router.py`, `writer.py`)**：
   - 在 `engine/app/writing/router.py` 中新增 `POST /writing/review_stream` SSE 流式端点；
   - 实现 `_stream_review` 生成器，流式推送：
     - `{"type": "stage", "stage": "init", "message": "🔍 正在对照国家发改委规程与工程底稿进行合规核查..."}`
     - `{"type": "thought", "chunk": "..."}`（捕获并推送 DeepSeek / 大模型思维链 `reasoning_content`）
     - `{"type": "chunk", "chunk": "..."}`（大模型输出的诊断 JSON 字符流）
     - `{"type": "done", "review": {...}}`（最终解析的结构化诊断字典）

3. **前端 API 与 Pinia Store 流式对接 (`desktop/src/lib/engineApi.ts`, `desktop/src/stores/project.ts`)**：
   - `desktop/src/lib/engineApi.ts` 新增 `streamChapterReview` SSE 请求方法，解析 stage / thought / chunk / done 事件；
   - `desktop/src/stores/project.ts` 升级 `runFullBookReview`：
     - 新增 `reviewProgress` 状态（包含 `currentSeq`、`currentTitle`、`currentIndex`、`totalTarget`、`percent`、`elapsedSeconds`、`thoughtText`、`completedIssuesCount`）；
     - 各章节调用 `streamChapterReview`，实时更新 `thoughtText`；
     - **每完成一章立即保存该章 review 并触发全书诊断统计即时刷新**（右侧诊断抽屉与左侧预警点无需等待全部章节跑完即可实时看到最新结果）；
     - `stopBatchReview` 支持安全一键终止，保留已审阅完成的章节结论。

4. **前端 Step 4 审阅看板与实时 AI 思考推演窗 (`desktop/src/components/Step4Review.vue`)**：
   - **动态章节流转看板**：展示 `⚡ 正在深度审阅 第 2/4 章：《第二章 项目建设背景和必要性》（进度 50%）· 已耗时 85s`；
   - **AI 专家审阅实时思考推演窗**：可折叠/展开，动态打字机展示大模型在审阅当前章时的实时推理过程（如核对数值一致性、查验规程条文等）；
   - 正文上方常驻 `[ ⏹ 停止审阅 ]`，点击立即安全中止。

5. **单元测试与产物构建**：
   - 在 `engine/tests/` 中增加 `/writing/review_stream` 端点单测；
   - 在 `desktop/src/tests/` 中补充 `streamChapterReview` 与 `reviewProgress` 单测；
   - 重新构建 `desktop/dist/**`。

---

## 2. 允许修改

- `desktop/src/components/Step4Review.vue`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/stores/project.ts`
- `engine/app/writing/router.py`
- `engine/app/writing/writer.py`
- `engine/tests/test_writing_review.py`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T15/**`

---

## 3. 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [x] `npx vitest run`（`desktop/`）全绿（123/123 通过）。
- [x] `python -m pytest engine/tests -q` 全绿（95/95 通过）。
- [x] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [x] B 级实跑：
  1. 左侧章节导航栏：章节标题自然换行，收起与展开均 100% 完整显示无 `...` 截断；
  2. 左侧子标题列表：多达数十项时可在该章卡片内自如平滑滚动，无底部切断；
  3. 执行「全书全维专家审阅」时，顶栏清晰呈现当前正在审阅的章节、序号与完成百分比；
  4. 展开「AI 思考推演窗」可看到大模型实时的思考链打字流式输出；
  5. 每章审阅完成时，左侧预警小黄点与右侧诊断抽屉实时刷新；
  6. 点击「停止审阅」可立即中止并保留已完成章节。

---

## 5. 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `python -m pytest engine/tests -q`
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
5. `cargo check`（workdir=`desktop/src-tauri`）
