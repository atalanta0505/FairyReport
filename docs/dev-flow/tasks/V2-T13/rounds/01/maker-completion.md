# Maker 完成报告 — V2-T13 第 1 轮（章节流式写作动态构思指示与左侧目录全章收起展开）

## 1. 基本信息

- 任务编号：V2-T13
- 轮次：第 1 轮
- 有效合同：`docs/dev-flow/tasks/V2-T13/01-planner-task-contract-v1.md`
- 转发消息：`docs/dev-flow/tasks/V2-T13/02-planner-to-maker-message-v1.md`
- 精确起始 SHA：`37e63ba130c25a0a382e705b630043c594c920ba`
- 候选交付 SHA：`b1dd22ab88a38541c4fb8b7886fa70fefbf2ceaa`

---

## 2. 变更文件清单

- `engine/app/writing/llm_client.py`：
  - 在 `chat_stream_iter` 中捕获 `delta.get("reasoning_content")`、`delta.get("reasoning")` 与 `delta.get("thought")`，当有思考片段时以 JSON 结构 `{"type": "thought", "chunk": ...}` 透传；当有正文时正常产出文本；
  - 在 `chat_stream` 中累积正文时智能过滤 thought JSON 片段，确保返回完整干净正文。
- `engine/app/writing/router.py`：
  - 在 `_stream_chapter` 生成器内分阶段 yield 结构化阶段指示事件：
    - RAG 检索前：`{"type": "stage", "stage": "rag", "message": "🔍 正在双源检索工程底稿与标准规程库..."}`；
    - 骨架锁定前：`{"type": "stage", "stage": "skeleton", "message": "📋 正在提取并锁定章节全层级大纲骨架..."}`；
    - 模型推理前：`{"type": "stage", "stage": "reasoning", "message": "🧠 大模型正在深度构思与组织水利专业论证与数据表格..."}`；
  - 增强异常捕获，保障发生错误时以 SSE error event 规范透传。
- `desktop/src/lib/engineApi.ts`：
  - 定义 `WritingProgressEvent` 类型，升级 `streamChapterWriting` 支持可选的 `onProgress` 回调；
  - 结构化解析 SSE 中的 `type === 'stage'` 与 `type === 'thought'` 事件，将阶段状态与思考文本实时派发给上层状态机；纯文本或正文内容正常通过 `onChunk` 累积。
- `desktop/src/stores/project.ts`：
  - 新增 `ChapterWritingProgress` 类型与 `writingProgress: ref<ChapterWritingProgress | null>(null)`；
  - 在 `writeSingleChapterStream` 中初始化 progress 并在生成期间启动 1 秒周期定时器自增 `elapsedSeconds`；
  - 接收 stage / thought / chunk 更新状态，在正文首块到达或任务完成/出错/中止时正确清理定时器与 progress。
- `desktop/src/components/Step3Writing.vue`：
  - **右侧动态构思指示卡片**：当章节生成中且正文字数为 0 时，居中展示沉浸式动态构思卡片：
    - 三段流水线步进指示（双源检索 ✓ -> 骨架提取锁定 ✓ -> 专业论证推演 动态波形）；
    - 实时秒级计时器（`⚡ 构思已耗时 X 秒`）；
    - 动态音频波形指示；
    - 思维链推演折叠窗（可展开查看 AI 实时推理细节与字符数统计）；
    - 贴心提示说明；
    - 首个正文字词到达时平滑淡出并切换为打字机排版正文。
  - **左侧目录全章收起与展开**：
    - 管理 `collapsedChapters = ref<Record<number, boolean>>({})`；
    - 目录顶部增加全局快捷控制栏（`[ ⊞ 全部展开 ]` / `[ ⊟ 全部收起 ]`）；
    - 每个有子小节标题的章节卡片提供 `▼ 收起` / `▶ 展开` 切换；
    - 选中章节或开始生成某章时自动联动展开该章。
- `engine/tests/test_writing_router.py`：新增对 SSE 阶段指示事件、思考片段透传与 LLMClient thought 处理的完整单元测试。
- `desktop/src/tests/project.test.ts`：新增 `streamChapterWriting` 阶段/思考事件派发与 `useProjectStore.writingProgress` 状态管理测试。
- `desktop/dist/**`：重新编译并更新前端分发静态产物。

---

## 3. 设计决策与核心实现

1. **结构化事件流式协议设计 (`engine/` 与 `desktop/src/lib/engineApi.ts`)**：
   - 采用标准 JSON SSE 格式透传 `type: "stage"` 与 `type: "thought"`，与纯文本正文 chunks 互不冲突；
   - `streamChapterWriting` 具有自适应解析能力，在 `resp.body.getReader()` 和 `resp.text()` 两种模式下均能准确区分阶段消息、思考消息与正文内容，保证向后兼容。
2. **精准的构思等待与平滑打字机切换体验 (`desktop/src/components/Step3Writing.vue`)**：
   - 针对大模型在水利专业论证、长文本骨架填充时前置思考时间较长（数十秒至数分钟）的问题，提供流水线打勾步进、秒级动态计时器、思考细节折叠窗与波形动效；
   - 一旦首个正文 Token 到达（`currentChapterWords > 0`），等待卡片自动淡出，排版画布无缝呈现打字机式流式排版，彻底消除用户界面“空白卡死”疑虑。
3. **左侧目录智能层级折叠 (`desktop/src/components/Step3Writing.vue`)**：
   - 支持单章独立折叠与全书一键全部展开/全部收起；
   - 智能联动：用户切换选中章节或启动某章写作时，系统自动展开目标章节的子标题树，兼顾目录整洁与操作直达。

---

## 4. 验证记录

严格按照合同规定的快速验证顺序执行并通过：

1. `python -m pytest engine/tests -q`
   - 结果：`84 passed, 2 warnings in 42.56s`（全绿，含新增的阶段指示与思考流式单测）。
2. `npx vitest run`（`desktop/`）
   - 结果：`4 passed (4), 94 passed (94)`（全绿，含新增的 progress 状态机与事件回调单测）。
3. `npx vue-tsc --noEmit`（`desktop/`）
   - 结果：通过（退出码 0，无任何 TypeScript 类型错误）。
4. `npm run build`（`desktop/`）
   - 结果：通过（成功构建前端静态资源至 `desktop/dist/`）。
5. `cargo check`（`desktop/src-tauri/`）
   - 结果：通过（`Finished dev profile in 0.77s`）。

---

## 5. 已知风险与后续建议

- 无向后兼容风险，所有修改均严格限制在任务合同允许范围内，所有禁止修改文件（如 `generic_knowledge/**`、`backend/**`、`AGENTS.md` 等）均未受影响。
- 对于不输出 `reasoning_content` 的普通 LLM 模型，系统将在构思阶段正常展示双源检索、骨架锁定与专业论证推演波形状态，正文到达后无缝过渡。

---

## 6. 冻结声明

Maker 本轮编码与测试工作已全部完成，代码、静态资源与测试均已验证通过并冻结，特此交付候选 commit SHA `b1dd22ab88a38541c4fb8b7886fa70fefbf2ceaa`。
