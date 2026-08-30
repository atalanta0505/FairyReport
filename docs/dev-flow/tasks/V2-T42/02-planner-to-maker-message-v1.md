# Planner to Maker Message — V2-T42 v1

- **任务 ID**：V2-T42
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T42/01-planner-task-contract-v1.md`)
- **起始精确 SHA**：`9fdf42cd211f74803cdb2f50172fe1940e35b4df`

---

## 交付任务

请 Maker 依次完成以下 5 项任务：

1. **图 1：字数统计实时响应与标签统称**：
   - 在 `Step3Writing.vue` 和 `Step4Review.vue` 中，将“当前字数”统称为“本章字数”，侧边栏为“总字数”；
   - 修正 `currentChapterText` 与 `currentChapterWords` 绑定逻辑，在流式生成（SSE onChunk）与画布 input 时毫秒级实时计算与递增。

2. **图 2：单章审阅秒级计时器修复**：
   - 在 `Step4Review.vue` 的 `handleReviewSingleChapter` 中启动 `reviewTimer` 并递增 `reviewElapsedSeconds`，保证单章审阅即时每秒跳动。

3. **图 3：问题清单按正文物理位置严格升序排序**：
   - 在 `Step4Review.vue` 中根据各问题在正文中出现的字符索引（`indexOf`）对 `currentChapterIssues` 进行排序，确保抽屉列表与正文自上而下顺序 100% 一致。

4. **图 4：修订推演过程接入流式打字输出**：
   - 在 `engine/app/writing/router.py` 中新增 `POST /writing/revise_paragraph_stream` 流式接口；
   - 在 `desktop/src/lib/engineApi.ts` 与 `projectStore.runParagraphRevision` 中支持流式接收 `thought` 事件，推演文本实时流式打字输出。

5. **图 5：消除 Word 节标题粘连与输出完整参考文献原链接**：
   - 在 `engine/app/export/docx_builder.py` 与 `normalize_chapter_markdown` 中强化对多级节标题与正文边界的拆分，确保如 `2.3.1 宏观层面必要性从宏观层面看...` 自动拆分为标题段与正文段；
   - 确保联网参考文献输出原始完整 URL。

6. **全量 5 项流水线门禁验证**。
