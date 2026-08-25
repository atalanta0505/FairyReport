# Maker 完成说明 — V2-T10 第 1 轮（Step 3 章节流式写作开发）

## 基本信息

- **任务 ID**：V2-T10
- **轮次**：第 1 轮
- **完成时间**：2026-08-25
- **有效合同**：[`docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v1.md`](file:///d:/Repo/FairyReport_lite/docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v1.md)
- **精确起始 SHA**：`74dbb2779774697ee5ca021759ea403cb5c18ff2`
- **候选交付 SHA**：`8702340573822f65fc025ed6534f05d648ee9ba7`

---

## 1. 核心实现范围与修改文件清单

### 1.1 本地 Python 引擎章节持久化端点
- **文件**：[`engine/app/writing/router.py`](file:///d:/Repo/FairyReport_lite/engine/app/writing/router.py)
  - 增加 `ChaptersData` 数据结构模型（`chapters: dict[str, str]`, `updated_at: str`）与 `ChapterSaveRequest`；
  - 增加 `GET /projects/{name}/chapters` 与 `/writing/projects/{name}/chapters`：读取 `%LOCALAPPDATA%/FairyReport/projects/<name>/chapters.json`，不存在时返回空映射；
  - 增加 `POST /projects/{name}/chapters/{seq}` 与 `/writing/projects/{name}/chapters/{seq}`：落盘保存单章 Markdown 内容至 `chapters.json` 并同步写入 `chapters/chapter_{seq}.md` 单文件；
  - 增加 `DELETE /projects/{name}/chapters/{seq}` 与 `/writing/projects/{name}/chapters/{seq}`：从 `chapters.json` 中移除单章并清理对应 markdown 文件。
- **文件**：[`engine/tests/test_writing_router.py`](file:///d:/Repo/FairyReport_lite/engine/tests/test_writing_router.py)
  - 补充 `GET/POST/DELETE /projects/{name}/chapters` 单元测试用例，验证落盘、文件写入与删除行为。

### 1.2 桌面端 API 客户端与 SSE 流式通道
- **文件**：[`desktop/src/lib/engineApi.ts`](file:///d:/Repo/FairyReport_lite/desktop/src/lib/engineApi.ts)
  - 声明 `ChaptersData` 与 `ChapterStreamRequest` 接口；
  - 实现 `getProjectChapters(baseUrl, projectName)`、`saveProjectChapter(baseUrl, projectName, seq, text)`、`deleteProjectChapter(baseUrl, projectName, seq)`；
  - 实现 `streamChapterWriting(baseUrl, req, onChunk, onDone, onError)`：使用 `@tauri-apps/plugin-http` fetch 原生通道接入 SSE 流式分块，兼容多行 Markdown 换行解析与 `[DONE]` 终止符，支持 `AbortController` 实时中止任务。

### 1.3 桌面端 Store 状态管理与双重持久化
- **文件**：[`desktop/src/stores/project.ts`](file:///d:/Repo/FairyReport_lite/desktop/src/stores/project.ts)
  - 增加状态：
    - `chapters: ref<Record<number, string>>({})`
    - `chapterStatuses: ref<Record<number, 'idle' | 'writing' | 'completed' | 'error'>>({})`
    - `selectedChapterSeq: ref<number>(1)`
    - `batchWriting: ref<boolean>(false)`
    - `currentWritingSeq: ref<number | null>(null)`
  - 增加方法与双重备份机制：
    - `getChaptersStorageKey` / `loadChaptersFromLocal` / `saveChaptersToLocal`（localStorage key: `frl_chapters_${projectName}`）；
    - `loadChapters(baseUrl, projectName)`：从后端引擎读取并同步写入 localStorage，引擎异常时自动降级从 localStorage 恢复；
    - `saveChapter(baseUrl, seq, text, immediate)`：即时写入 state 与 localStorage，并防抖（300ms）落盘至后端引擎；
    - `deleteChapter(baseUrl, seq)`：清除指定章节在 state、localStorage 与引擎中的记录；
    - `writeSingleChapterStream(baseUrl, seq, llmConfig, hint)`：单章 SSE 流式生成，自动汇总前序章节提供上文连贯性，实时打字机累加正文并落盘；
    - `writeAllChapters(baseUrl, llmConfig)`：顺序批量流式生成全书所有大纲章节；
    - `stopWriting()`：实时中止正在执行的单章或全书批量流式写作；
    - 在 `loadProjects`、`selectProject`、`deleteProject` 中建立与章节状态的联动同步与清理。

### 1.4 Step 3 章节流式写作组件与主流程接入
- **文件**：[`desktop/src/components/Step3Writing.vue`](file:///d:/Repo/FairyReport_lite/desktop/src/components/Step3Writing.vue) [NEW]
  - **左侧章节目录与控制面板**：
    - 报告概览（总章节数、已完成章节数、全书累计字数统计）；
    - 全局控制：「🚀 一键开始全书写作」与「⏹ 停止全书写作」；
    - 章节列表卡片：序号徽标、章标题、字数、状态徽标（`正在撰写中…` 旋转微标 / `已完成 ✓` / `生成异常` / `未生成`）；
    - 卡片快速操作：单章独立写作「✍️」与清空「🗑️」；
  - **右侧流式写作与实时编辑器**：
    - 当前选定章节标题、序号与实际字数统计；
    - 章节写作提示（Writing Hint）可折叠输入区；
    - 实时流式打字机画布与正文编辑器：大模型 SSE 推送时文字逐字实时流式输出，配合平滑自动下滚；生成完成后支持用户直接自由润色编辑，并触发防抖自动落盘；
  - **底部导航**：
    - `← 上一步：模板与大纲`（返回 Step 2）；
    - `下一步：审阅修改 →`（已完成章节 > 0 时激活进入 Step 4）。
- **文件**：[`desktop/src/views/Home.vue`](file:///d:/Repo/FairyReport_lite/desktop/src/views/Home.vue)
  - 引入并挂载 `<Step3Writing v-show="projectStore.currentStep === 3" />`，替换原有静态占位容器。

### 1.5 单元测试与生产构建
- **文件**：[`desktop/src/tests/project.test.ts`](file:///d:/Repo/FairyReport_lite/desktop/src/tests/project.test.ts)
  - 覆盖客户端 API 请求、SSE 数据流解析与异常处理、Store 各章加载与 localStorage 降级、手动编辑防抖落盘、单章与全书批量流式写作、任务中止与项目切换清理；
- **文件**：[`desktop/dist/**`](file:///d:/Repo/FairyReport_lite/desktop/dist)
  - 重新编译生产前端静态分发产物。

---

## 2. 快速验证记录

严格按照合同第 5 节指定顺序执行验证：

1. **引擎测试**：
   ```powershell
   python -m pytest engine/tests -q
   # 输出：77 passed, 2 warnings in 64.75s (0:01:04)
   ```
2. **桌面端单元测试**：
   ```powershell
   cd desktop
   npx vitest run
   # 输出：3 passed (api.test.ts, engine.test.ts, project.test.ts), 61 passed (61)
   ```
3. **桌面端 TypeScript 类型检查**：
   ```powershell
   cd desktop
   npx vue-tsc --noEmit
   # 输出：退出码 0，无任何类型错误
   ```
4. **桌面端生产构建**：
   ```powershell
   cd desktop
   npm run build
   # 输出：✓ built in 861ms，产物完整生成至 desktop/dist/
   ```
5. **Rust / Tauri 编译检查**：
   ```powershell
   cd desktop/src-tauri
   cargo check
   # 输出：Finished `dev` profile in 1.04s，无错误
   ```

---

## 3. 设计决策与说明

1. **双重持久化与降级容灾**：
   - 章节内容在 SSE 接收过程中实时暂存并写入 `localStorage`（键名 `frl_chapters_<projectName>`），单章生成完毕或用户手动编辑修改时自动落盘至引擎端点；
   - 在引擎离线或网络抖动场景下，前端无缝从 `localStorage` 读取章节内容，保证用户编写的数据绝对不丢失。
2. **多章节前序依赖上下文（Predecessor Context）**：
   - 在单章写作与批量全书写作时，自动收集当前章节之前已生成的章节正文，并通过 `predecessor_chapters` 字段传至后端 ChapterWriter，确保各章节内容承接自然、前后逻辑连贯。
3. **批量写作与单章写作的状态隔离与可控中止**：
   - 支持独立单章流式生成与全书一键顺序批量生成；点击停止按钮时通过 `AbortController` 优雅中止当前活跃连接，并安全保留已接收的正文段落。

---

## 4. 冻结声明与交回

- 本地候选提交 SHA：`8702340573822f65fc025ed6534f05d648ee9ba7`
- 严格遵循禁止修改约束：未触碰 `backend/**`、`generic_knowledge/**`、`AGENTS.md`、`.gitignore` 等禁止路径。
- 无 `git push`、无 `git commit --amend`、无 `git rebase`。
- 本轮编码与测试全部完成，提交本完成说明后冻结工作树，交由 Checker 进行验收。
