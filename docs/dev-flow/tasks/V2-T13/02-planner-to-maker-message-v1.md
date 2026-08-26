# Planner -> Maker 指派消息 — V2-T13 第 1 轮

Maker 请注意：

请严格依据 [`docs/dev-flow/tasks/V2-T13/01-planner-task-contract-v1.md`](file:///D:/Repo/FairyReport_lite/docs/dev-flow/tasks/V2-T13/01-planner-task-contract-v1.md) 执行章节流式写作动态构思指示与左侧目录全章收起展开的编码与测试任务。

## 1. 核心实现要点

1. **`engine/app/writing/llm_client.py` & `router.py`**：
   - 捕获 `reasoning_content` / `thought`，通过 SSE 向前端透传思考事件与前置准备阶段事件（`rag`, `skeleton`, `reasoning`）。
2. **`desktop/src/lib/engineApi.ts` & `project.ts`**：
   - 解析 SSE 结构化消息，维护 `writingProgress`（含 `elapsedSeconds` 实时计时器与 `thoughtText`）。
3. **`desktop/src/components/Step3Writing.vue`**：
   - **动态构思等待卡片**：在生成中且无正文字数时居中展示多阶段流水线、秒级构思计时器与思考推演折叠窗；
   - **左侧目录展开收起**：每个有子标题的卡片增加 `▼/▶` 单章收起展开按钮，顶部工具栏增加 `[ ⊞ 全部展开 ]` / `[ ⊟ 全部收起 ]` 快捷操作。
4. **测试与构建**：
   - 适配 `engine/tests/test_writing_router.py` 与 `desktop/src/tests/project.test.ts`；
   - 重建 `desktop/dist/**`。

## 2. 快速验证

- `python -m pytest engine/tests -q`
- `npx vitest run`（`desktop/`）
- `npx vue-tsc --noEmit`（`desktop/`）
- `npm run build`（`desktop/`）
- `cargo check`（`desktop/src-tauri/`）

完成后提交候选 commit 并编写 `docs/dev-flow/tasks/V2-T13/rounds/01/maker-completion.md`，交回候选 SHA。
