# Planner 给 Maker 的任务派发消息 (V2-T21 Round 01)

请严格依据任务合同 `docs/dev-flow/tasks/V2-T21/01-planner-task-contract-v1.md` 执行编码与测试工作。

- 精确起始 SHA：`6318344e29bde3052110ac6cd404efff859992b8`
- 实施要点：
  1. 后端 `templates_loader.py` 实现 `get_writing_order` 与 `get_writing_order_reason`，并在 `router.py` 的 `/writing/templates` 和 `/writing/outline` 接口透传；
  2. 前端 `engineApi.ts` 扩展 `writing_order` 字段；
  3. 前端 `project.ts` 维护 `writingOrder`，在 `writeAllChapters` 中实现推荐顺序循环与断点智能续写（跳过已有正文章节），在 `writeSingleChapterStream` 中将所有已写完的其它章节全量传入 `predecessor_chapters`；
  4. 前端 `Step3Writing.vue` 重构为与 Step 4 一致的 Flat 平铺多级目录树与推荐顺序徽标，移除源码视图切换按钮；
  5. 增补单测并跑通 5 项门禁后，创建候选 commit 并提交 `maker-completion.md`。
