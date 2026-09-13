# Planner 任务合同 — V2-T49 v1

- **任务 ID**：V2-T49
- **任务目标**：修复报告末尾《参考文献》在 Word 导出与 Markdown 渲染中被错误合并为单一段落/块引用（“糊成一团”）的问题，使其清晰、规范地“一行一行独立列出”。
- **起始 SHA**：f5985bcbb0a798c9378555f711de0feb7356e26b

---

## 1. 问题根因分析

1. **Markdown 清洗误吞换行符**：
   - `normalize_chapter_markdown`（后端）与 `normalizeMarkdown`（前端）中的行内引用换行融合规则：
     `r'([，。；！？])?\s*\n+\s*(\[Z(?:-[^\]]+)?\]|\[\d+\])\s*([，。；！？])?'`
     前置标点使用了可选匹配 `?`，且未排除参考文献章列表项，导致 `> 依据 GB/T 7714...\n\n[1]` 以及条目间 `[1]...\n[2]...` 的换行符被无差别抹除，整章文献与前置引用块被粘连为单行。
2. **Word 导出段落聚合器缺少条目断行保护**：
   - `docx_builder.py` 在执行普通段落收集时，未将 `^[\[\d+\]]\s*` 纳入段落切分终结条件，遇到连续非空行的参考文献条目时，按普通段落全部拼接为单一 `merged_para`，并赋予正文段落首行缩进 2 字符。
3. **前端 HTML 排版未识别条目样式**：
   - `markdown.ts` 中 `markdownToHtml` 缺少对 `^\[\d+\]\s+` 独立条目行的解析，将其作为普通段落渲染进同一 `<p>` 标签。
4. **生成端条目隔离不足**：
   - `format_ref_appendix`、`generate_global_ref_list` 与 `generateBibliographySection` 在追加条目时，条目之间缺少标准 Markdown 独立段落所需的隔离空行。

---

## 2. 修复范围与技术设计

1. **隔离与清洗保护 (`engine/app/writing/writer.py` & `desktop/src/lib/markdown.ts`)**：
   - 在 `normalize_chapter_markdown` 与 `normalizeMarkdown` 中，检测到 `# 参考文献` / `## 参考文献` 时将其与正文彻底隔离，参考文献附录内容保持原样，不受正文换行消除与小节标点规则干扰；
   - 引用清洗正则增加约束，严禁匹配以 `[N] [` 开头的参考文献条目。
2. **Word 独立条目渲染与断行防御 (`engine/app/export/docx_builder.py`)**：
   - 在 `md_to_docx` 主循环中新增对 `^(\[\d+\])\s*(.*)` 的条目解析，调用专用的 `_add_ref_item`；
   - `_add_ref_item` 采用悬挂缩进（`left_indent = Pt(24), first_line_indent = Pt(-24)`），五号（10.5pt）仿宋，行间独立；
   - 在普通段落收集循环 `para_lines` 中，增加 `re.match(r'^\[\d+\]\s*', next_stripped)` 断行中断条件，防止吞并条目。
3. **前端渲染同步 (`desktop/src/lib/markdown.ts`)**：
   - `markdownToHtml` 识别 `^\[\d+\]\s+` 为独立条目，生成 `<p class="ref-entry-line">`，并在段落循环中防御；
   - 样式保障其无首行缩进，单行独立。
4. **条目生成端标准化空行隔离 (`docx_builder.py`, `refs.py`, `markdown.ts`)**：
   - 确保 `format_ref_appendix`、`generate_global_ref_list`、`generateBibliographySection` 每个参考文献条目后均附带空行。

---

## 3. 验收标准与门禁

1. 导出的 Word 文档中，各参考文献条目 `[1]`、`[2]`、`[3]`... 各自独立成行成段，悬挂对齐，无首行缩进，不被合并进 blockquote；
2. 5 项全量流水线门禁全部绿灯通过；
3. 真实项目导出验证：参考文献章纯净清晰，逐行分明。
