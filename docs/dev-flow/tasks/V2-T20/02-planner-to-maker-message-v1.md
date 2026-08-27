# Coordinator 派发消息 — V2-T20 第 1 轮

Maker 您好：

请作为唯一可写 Maker，严格按照任务合同 `docs/dev-flow/tasks/V2-T20/01-planner-task-contract-v1.md` 开展 V2-T20 第 1 轮编码与测试工作。

### 核心任务与修改指引

1. **`desktop/src/lib/markdown.ts`**：
   - 升级 `normalizeMarkdown`：
     - 在已知标题库 `knownHeadings` 匹配中，将正则改为允许直接跟随中文字符：
       `const reg = new RegExp(\`^(#{1,6}\\s+(?:\\d+(?:\\.\\d+)*\\s+)?${escaped})\\s*([:：，。—\\-\\u2014\\u2013\\s]*)([^\\n]+)$\`, "gm");`
       将 `restPart` 替换为 `\${hPart}\n\n\${cleanRest}`；
     - 确保 `extractOutlineHeadings` 能正确提取完整小节标题并无条件切断粘连正文。

2. **`desktop/src/components/Step4Review.vue`**：
   - **左侧导航栏**：
     - 去除 `.chapter-tree-node` 的边框盒子（`border: none; background: transparent;`）；
     - 将章节行与子标题行整合为平铺连续的树形结构；
     - 保证外层 `.outline-tree-scrollable` 具有全局垂直滚动条；
   - **右侧主画布**：
     - 去除 `.chapter-block-header`（带 `✍️ 本章AI修订 🔍 重新审阅` 的每章横条）和 `.chapter-divider-rule`（`第 N 章 完` 分界线）；
     - 将各章 `.rich-rendered-editor` 渲染为无缝连贯的整体文档流；
     - 保持就地 contenteditable 编辑与 300ms 防抖保存。

3. **`engine/app/writing/prompts.py` & `writer.py`**：
   - 注入【标题换行硬约束】至写作系统提示词；
   - 在 `ChapterWriter` 与 `router.py` 中，输出与存储时执行 `normalize_chapter_markdown`。

4. **`engine/app/writing/rag.py` & `router.py`**：
   - 在 `query_rag` 中优化联网检索词构造，支持传入 `topic` / `report_name` 组合成复合政务检索词。

5. **测试与 5 项全量门禁**：
   - 更新单测；
   - 运行 pytest, vitest, vue-tsc, build, cargo check；
   - 提交候选 commit，生成 `docs/dev-flow/tasks/V2-T20/rounds/01/maker-completion.md` 并交回候选 SHA。
