# Maker 实施总结 — V2-T49 v1

- **任务 ID**：V2-T49
- **合同版本**：v1 (docs/dev-flow/tasks/V2-T49/01-planner-task-contract-v1.md)
- **起始 SHA**：f5985bcbb0a798c9378555f711de0feb7356e26b

---

## 1. 交付成果

1. **参考文献章隔离保护与清洗规则修复 (`engine/app/writing/writer.py` & `desktop/src/lib/markdown.ts`)**：
   - 在 `normalize_chapter_markdown` 与 `normalizeMarkdown` 中增加前置检测：若文本包含独立的 `# 参考文献` 或 `## 参考文献` 章，将其与正文彻底隔离切分，参考文献列表内容保持原样，绝不参与正文断行消除、标点吸收与小节引导句融合；
   - 修复学术编号 `[N]` 融合正则：增加 `(?!\s*\[)` 否定断言，严禁误吞以 `[N] [` 开头的参考文献条目，且要求前置有实际中文字符或标点，杜绝误消除前置换行。

2. **Word 导出逐条独立排版与断行防御 (`engine/app/export/docx_builder.py`)**：
   - 在 `md_to_docx` 主循环中新增参考文献条目解析（`re.match(r'^(\[\d+\])\s*(.*)', stripped)`），调用专用的 `_add_ref_item`；
   - `_add_ref_item`：五号 10.5pt 仿宋，出版级悬挂缩进（`left_indent = Pt(24), first_line_indent = Pt(-24)`），无首行缩进，条目间微距独立排列；
   - 在普通段落收集循环 `para_lines` 中，增加 `re.match(r'^\[\d+\]\s*', next_stripped)` 中断保护，彻底防止正文段落吞并参考文献条目；
   - 在 `format_ref_appendix` 与 `engine/app/writing/refs.py`（`generate_global_ref_list`）中，确保生成的 Markdown 中每个参考文献条目后均有标准空行隔离。

3. **前端渲染同步与样式优化 (`desktop/src/lib/markdown.ts`, `Step3Writing.vue`, `Step4Review.vue`)**：
   - `markdownToHtml` 新增识别 `^\[\d+\]\s+` 为独立的 `<p class="ref-entry-line">`，并在段落收集中加入中断保护；
   - `generateBibliographySection` 保持条目间标准空行；
   - 在 Step 3 与 Step 4 富文本编辑器样式中增加 `.ref-entry-line` 专属悬挂缩进排版规则，防止被通用段落的 `text-indent: 2em` 污染。

4. **自动化单元测试与实测验证**：
   - `desktop/src/tests/markdown.test.ts` 新增 2 项 V2-T49 单元测试（条目逐行独立渲染、隔离保护）；
   - `engine/tests/test_export.py` 新增 1 项 V2-T49 单元测试（Word 导出逐条独立成段、悬挂缩进核验）；
   - 对用户真实项目《安徽省利辛县生态皮革加工项目可行性研究》执行端到端合并导出 Word 实测：文末参考文献全部 8 个条目各自独立成段，悬挂缩进整齐，与上方说明引用块完美分离，彻底告别“糊成一团”。

---

## 2. 5 项全量流水线门禁验证

| 门禁项 | 命令 | 结果 |
| :--- | :--- | :---: |
| **前端单元测试** | `npm --prefix desktop run test` | **186/186 passed** (6 files) |
| **Vue 类型检查** | `npm --prefix desktop run typecheck` | **0 errors** |
| **前端打包构建** | `npm --prefix desktop run build` | **Build passed (904ms)** |
| **后端单元测试** | `python -m pytest engine/tests/` | **140/140 passed** (0 failed) |
| **Rust 壳层编译** | `cargo check --manifest-path desktop/src-tauri/Cargo.toml` | **Finished dev profile (0.76s)** |
