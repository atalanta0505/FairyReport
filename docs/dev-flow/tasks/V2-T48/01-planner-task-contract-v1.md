# 任务合同 V2-T48 v1 — 彻底根治双句号、节标题正文粘连与行内引用换行缺陷

- **状态**：READY_FOR_MAKER
- **依据**：产品负责人反馈的 4 项关键缺陷（附截图）：
  1. 引用标记中出现双句号（如 `[1]。。` 或 `【源:...】。。`）；
  2. 节标题缺失，正文部分粘连（如 `3.1.2 市场需求潜力国内皮革制品...` 整段被误判为 Heading 3，导致 WPS 目录出现长句，正文被赋予 Heading 样式）；
  3. 章节写作页面（Step 3）中的正文嵌入的引用标签，仍然存在换行错误（被 `<br />` 切断单独另起一行）；
  4. 导出文件中，标题和正文还是出现了部分粘连。
- **根因分析**：
  1. **双句号 `[1]。。`**：`normalize_chapter_markdown` 与 `normalizeMarkdown` 正则在将前置标点移动到引用标签后时，若引用标签后原本已带句号，则拼接产生双句号；全链路缺少连续标点去重及引用后标点去重；
  2. **节标题正文粘连**：`docx_builder.py` 的 `_parse_md_line` 缺少对超长标题和正文特征句式的防御，直接将 400+ 字符的长段作为 Heading 样式插入文档；`writer.py` 的 `pattern_num_dense` 限制了 120 字符长度且缺少关键词；`build_merged_md` 未加载大纲 `outline.json` 作为 `skeleton` 进行确定性拆分；
  3. **Step 3 页面引用换行**：`markdownToHtml` 在普通段落中对多行文本盲目 `join("<br />")`，将大模型换行处硬打断为 `<br />`；流式写作结束时未调用 `normalizeMarkdown` 清洗即保存。
- **精确起始 SHA**：`e6ee83b6da772fcad7e2cab39d5501fb8fa677c1`
- **工作树门禁**：干净工作树

---

## 1. 允许修改

- `engine/app/writing/writer.py`
- `engine/app/writing/refs.py`
- `engine/app/writing/prompts.py`
- `engine/app/export/docx_builder.py`
- `desktop/src/lib/markdown.ts`
- `desktop/src/stores/project.ts`
- `engine/tests/**`
- `desktop/src/tests/**`
- `docs/dev-flow/tasks/V2-T48/**`

---

## 2. 验收标准

- [ ] 标点清洗与去重：严禁产生 `[1]。。`、`【源:...】。。` 或任意连续中文句号/逗号；引用标签紧随句末且仅保留单标点；
- [ ] 节标题与正文彻底解耦：
  - `build_merged_md` 自动结合大纲骨架进行高精度拆分；
  - `docx_builder.py` 严格防御超长标题与正文粘连，Word 文档中 Heading 样式仅包含纯标题，正文完整保留为 Normal 样式段落，WPS 目录整洁；
  - `writer.py` 与 `markdown.ts` 解除 120 字符硬编码限制并扩充标题关键词库；
- [ ] Step 3 章节写作富文本渲染：普通中文段落行内软换行不再插入 `<br />`，引用标签自然流式贴合陈述句末尾；流式完成后规范化存盘；
- [ ] 现有测试全部通过，并补充针对本次修复的单元测试；
- [ ] 5 项流水线门禁全部绿灯通过。
