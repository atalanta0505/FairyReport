# Planner 到 Maker 派工信 V2-T48 v1

- **目标任务**：彻底解决双句号、节标题正文粘连与行内引用换行缺陷
- **基线 SHA**：`e6ee83b6da772fcad7e2cab39d5501fb8fa677c1`
- **合同路径**：`docs/dev-flow/tasks/V2-T48/01-planner-task-contract-v1.md`

## 详细实施指南

1. **双句号与连续标点消除**：
   - 在 `writer.py` 与 `markdown.ts` 中：
     - 正则匹配引用标签前后的可选标点，统一保留单个后置标点；
     - 全局清除紧邻引用标记后的多余标点 `(【[^】]+】|\[\d+\])[。！？；!?,，、]{2,}`；
     - 全局清除重复的中文标点 `([。，、；])\1+`；
     - 清除引用标签前后同时存在标点的场景（如 `。【源:...】。` -> `【源:...】。`）；
   - 在 `refs.py` 的 `number_all_citations` 中加入防御清洗；
   - 在 `prompts.py` 强调严禁双标点。

2. **节标题正文彻底解耦与防粘连**：
   - 在 `docx_builder.py`：
     - `build_merged_md` 尝试加载项目 `outline.json`，把大纲作为 `skeleton` 传给 `normalize_chapter_markdown`；
     - 在 `_parse_md_line` / `md_to_docx` 中新增 `_split_heading_and_body`：若标题行超长（>35字符）或包含句式特征，自动提取纯标题（以大纲已知标题优先，或按句子开头主体/标点切分），Heading 样式仅写入纯标题，粘连的正文作为独立的 Normal 段落插入；
   - 在 `writer.py`：
     - 解除 `pattern_num_dense` 的 120 字符长度限制；
     - 扩充 `_REPORT_TITLE_KEYWORDS` 词表并支持 `（如适用）` 等括号；
   - 在 `desktop/src/lib/markdown.ts`：
     - 同步补齐多级数字标题拆分正则，确保前端预览与后端导出一致。

3. **Step 3 页面引用标签换行修复与存盘清洗**：
   - 在 `desktop/src/lib/markdown.ts` 的 `markdownToHtml`：
     - 修改 `paragraphLines` 合并逻辑，除显式换行（行尾双空格、反斜杠、`<br>`）外，中文段落内的软换行不添加 `<br />`，使行内引用自然流式贴紧句末；
   - 在 `desktop/src/stores/project.ts` 的 `writeSingleChapterStream` 结束时：
     - 调用 `normalizeMarkdown(chapters.value[seq], outlineHeadings)` 清洗后再存入 store 与磁盘。

4. **自动化测试与门禁验证**：
   - 前端补充针对双句号、标题解耦、无多余 `<br />` 的单元测试；
   - 后端补充针对长粘连段落拆分与 Word 纯标题导出的测试；
   - 执行 5 项全量流水线门禁。
