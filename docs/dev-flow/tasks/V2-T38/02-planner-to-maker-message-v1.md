# Planner to Maker Message — V2-T38 v1

- **任务 ID**：V2-T38
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T38/01-planner-task-contract-v1.md`)
- **精确起始 SHA**：`a4a01690dbf4ffc6746a316f94533af420da3e02`

---

## 交付任务

请 Maker 依据合同完成以下 4 个核心事项：

1. **总字数与本章字数实时统计**：
   - 在 `Step3Writing.vue` 和 `Step4Review.vue` 的 `onEditorInput` 中，输入时立即同步更新 `projectStore.chapters[projectStore.selectedChapterSeq] = md`；
   - 在 `project.ts` 的 `writeSingleChapterStream` 中，chunk 到达时以响应式解构赋值更新 `chapters.value`，使字数在流式输出时实时递增。

2. **质检与修订思考推演实时流式输出**：
   - 在 `desktop/src/lib/engineApi.ts` 中修复 `parsed.type === "thought"` 时的字段读取（支持 `parsed.thought || parsed.chunk || ""`）；
   - 在 `Step4Review.vue` 中绑定流式实时推演展示并支持自动滚动。

3. **全面清理“国家发改委”等部委办局名称**：
   - 彻底替换所有 UI 文本、台账标题、提示词中出现的“国家发改委”、“发改委”，改为“行业规程与工程编制规范”、“投资项目编制规程”、“行业工程咨询标准”等。

4. **单测与 5 项全量门禁**。
