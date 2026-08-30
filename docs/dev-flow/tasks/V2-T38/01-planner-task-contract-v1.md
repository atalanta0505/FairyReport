# 任务合同 V2-T38 v1 — 实时字数双重统计、流式质检推演全景展现、全面去部委办局名称与修订推演流式化

- **状态**：READY_FOR_MAKER
- **依据**：产品负责人（Fairy）指示：
  1. “总字数”和“本章字数”必须支持编辑与流式写作时实时毫秒级统计；
  2. 审阅质检时提供实时流式推演与质检内容实时查看窗口；
  3. 全面清理应用中所有“国家发改委”等部委办局名称，统一规范为“行业规程与工程编制标准”等专业表述；
  4. 修复修订推演窗口流式实时输出机制。
- **精确起始 SHA**：`a4a01690dbf4ffc6746a316f94533af420da3e02`
- **工作树门禁**：除用户教材外无未跟踪代码修改

---

## 1. 唯一主要变化

1. **总字数与本章字数实时双重统计响应 (`desktop/src/components/Step3Writing.vue`, `desktop/src/components/Step4Review.vue`, `desktop/src/stores/project.ts`)**：
   - 编辑器 `onEditorInput` 触发时，立即同步更新内存中 `projectStore.chapters[seq]`，字数与状态指示器 0ms 实时响应，300ms 防抖落盘；
   - 流式写作与流式修订过程中，每次 chunk 到达时以响应式解构赋值更新 `chapters.value`，保证顶栏字数与侧边栏总字数随打字机流式递增实时跳动。

2. **质检内容与修订推演实时流式窗口 (`desktop/src/lib/engineApi.ts`, `desktop/src/stores/project.ts`, `desktop/src/components/Step4Review.vue`)**：
   - 修复 `engineApi.ts` 中 `parsed.thought || parsed.chunk || ""` 字段解析，确保 DeepSeek/OpenAI `reasoning_content` 思考推演流实时推流至前端；
   - 审阅与修订心跳条中展示实时流式思考推演窗与诊断内容流，支持自动滚动与打字动画。

3. **全面清理部委办局名称 (`desktop/src/`, `engine/app/writing/`)**：
   - 检索并替换所有前后台 UI 文本、占位符、提示信息、文档模板与 Prompt 中的“国家发改委”、“发改委”等部委办局字样；
   - 规范替换为“行业规程与工程编制规范”、“投资项目编制规程”、“专业咨询标准”、“出版级排版标准”等中立严谨的专业表述。

4. **单测覆盖与 5 项流水线门禁**：
   - 补充/更新实时字数统计与流式推演测试；
   - 依次通过 5 项流水线（Vitest, vue-tsc, build, Pytest, cargo check）。

---

## 2. 允许修改

- `desktop/src/lib/engineApi.ts`
- `desktop/src/lib/markdown.ts`
- `desktop/src/stores/project.ts`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/**`
- `engine/app/writing/**`
- `engine/tests/**`
- `docs/dev-flow/tasks/V2-T38/**`

---

## 3. 验收标准

- [ ] 在正文中输入或删除文字时，“本章字数”与“总字数”实时响应跳动；流式写作时字数随流式进度实时递增；
- [ ] 审阅质检与智能修订时，思考推演窗能实时流式打字输出模型思维链（thought / reasoning_content）；
- [ ] 应用界面所有组件（包含标签、按钮、台账、提示、占位符等）不再出现“国家发改委”或“发改委”字样；
- [ ] 5 项门禁（Vitest, vue-tsc, build, Pytest, cargo check）全部通过。
