# Planner 派工信 — V2-T49 v1

- **任务 ID**：V2-T49
- **接收者**：Maker
- **合同参考**：docs/dev-flow/tasks/V2-T49/01-planner-task-contract-v1.md

---

## 实施要点

1. **后端清洗保护**：
   - 在 `engine/app/writing/writer.py` 的 `normalize_chapter_markdown` 中：
     - 若内容包含 `# 参考文献` 或 `## 参考文献`，切分为 `(body_text, ref_text)`，仅清洗 `body_text` 后再拼接；
     - 修复 `[，。；！？]?\s*\n+\s*(\[Z...\]|\[\d+\])` 规则，前置标点不可为无标点换行，且后置不能为 `\s+\[` 开头的文献条目。
2. **后端导出与参考文献独立成行**：
   - 在 `engine/app/export/docx_builder.py` 中：
     - `format_ref_appendix` 确保每个条目间有标准空行；
     - `md_to_docx` 主循环识别 `re.match(r'^(\[\d+\])\s*(.*)', stripped)`，调用 `_add_ref_item` 逐条写入 Word；
     - `_add_ref_item`：仿宋 10.5pt，悬挂缩进 `left_indent = Pt(24), first_line_indent = Pt(-24)`，无首行缩进；
     - `para_lines` 循环加入 `re.match(r'^\[\d+\]\s*', next_stripped)` 中断保护。
   - 在 `engine/app/writing/refs.py` 的 `generate_global_ref_list` 中同步增加条目隔离空行。
3. **前端渲染与清洗同步**：
   - 在 `desktop/src/lib/markdown.ts` 中：
     - `normalizeMarkdown` 同样切分保护 `# 参考文献`，修正正则；
     - `generateBibliographySection` 保持条目间空行；
     - `markdownToHtml` 识别 `^\[\d+\]\s+` 为 `<p class="ref-entry-line">`，段落收集加入中断。
4. **验证与回归**：
   - 前端与后端新增针对参考文献独立条目断行与导出的单元测试；
   - 运行 5 项全量流水线门禁。
