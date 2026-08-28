# 任务完工报告：V2-T32 第 1 轮

- 目标任务：V2-T32（Word 导出出版级排版与三线表、图表附录格式规范化）
- 有效合同：`docs/dev-flow/tasks/V2-T32/01-planner-task-contract-v1.md`
- 精确起始 SHA：`756aaf300539c39600e1cfeb76fa1cba9087c53d`
- 候选提交 SHA：`3198d1313dcaf72f72b6a908920460db3673e426`

---

## 1. 变更清单与文件列表

### 1.1 Word 导出出版级排版升级与国家标准三线表规范 (`engine/app/export/docx_builder.py`, `exporter.py`)
- **国家公文与工程咨询出版级页面设置**：
  - 标准页边距：上 2.54cm (72pt)、下 2.54cm (72pt)、左 2.8cm (79.37pt)、右 2.6cm (73.7pt)；
- **出版级正文字体与段落规范**：
  - 中文字体：`仿宋`（`FangSong` / `仿宋_GB2312`），西文字体：`Times New Roman`；
  - 字号：小四（12pt / `Pt(12)`）；
  - 行距与间距：1.35 倍行距，段后 2pt，段前 0pt；
  - 缩进与对齐：严格首行缩进 2 字符（`Pt(24)`），两端对齐（`WD_ALIGN_PARAGRAPH.JUSTIFY`）；
- **严格出版级各级标题层级**：
  - **Title（报告总标题 / Level 0）**：黑体 22pt（二号），居中加粗，段前 12pt / 段后 12pt，首行缩进 0pt；
  - **Heading 1（Level 1）**：黑体 16pt（三号），居左加粗，段前 12pt / 段后 6pt，首行缩进 0pt，`keep_with_next=True`；
  - **Heading 2（Level 2）**：黑体 14pt（四号），居左加粗，段前 6pt / 段后 3pt，首行缩进 0pt，`keep_with_next=True`；
  - **Heading 3（Level 3）**：楷体 12pt（小四），居左加粗，段前 3pt / 段后 2pt，首行缩进 0pt，`keep_with_next=True`；
  - **Heading 4+（Level 4+）**：仿宋 12pt（小四），居左加粗，段前 2pt / 段后 1pt，首行缩进 0pt，`keep_with_next=True`；
- **列表与引用块优雅排版**：
  - 无序列表（`- ` / `* `）与有序列表（`1. `）：仿宋 12pt，左缩进 24pt，首行悬挂缩进 -12pt；
  - 引用块（`> `）：楷体 10.5pt，左右缩进 24pt，首行缩进 0pt，左侧单实线边框（`w:sz="24"`，颜色 `#94A3B8`）与浅灰底纹（`#F8FAFC`）；
- **国家标准三线表高品质强化**：
  - 顶线与底线：1.5pt（`w:sz="12"`，颜色 `#334155`）；
  - 栏目线（表头下线）：0.75pt（`w:sz="6"`，颜色 `#475569`）；
  - 隐藏纵向竖线与数据行横线；
  - 表头单元格：浅灰底纹（`#F1F5F9`），字体 10.5pt（五号），黑体加粗，水平垂直居中；
  - 数据单元格：字体 10pt（五号），仿宋，文本居左、数值/序号自动右对齐或按 Markdown 对齐指示居中；
  - 单元格内边距优化：上下 6pt（`120 dxa`），左右 8pt（`160 dxa`），单倍行距；
  - 跨页防断行（`w:cantSplit`）与表头跨页自动重复（`w:tblHeader`）；
- **参考文献与三源附录生成规范化**：
  - `format_ref_appendix`：支持在导出 Word 时按项目底稿、国家与行业规程标准、互联网参考、AI自有知识自动生成结构化参考文献附录 Markdown。

### 1.2 单元测试覆盖与断言强化 (`engine/tests/test_export.py`)
- `test_export_publication_typography_and_margins`：全量断言页面边距（上/下 2.54cm，左 2.8cm，右 2.6cm）、正文首行缩进 24pt、1.35 倍行距、中文字体仿宋、各级标题字体/字号/段前段后间距/`keep_with_next`、引用块左右缩进与底纹、列表悬挂缩进；
- `test_export_standard_three_line_table_format`：全量断言三线表顶底 1.5pt、栏目线 0.75pt、单元格内边距 `tblCellMar`、表头加粗居中与浅灰背景、`cantSplit` 与 `tblHeader`；
- `test_export_refs_numbering_global`：断言三源参考文献与资料出处附录各分类与对应编号。

---

## 2. 5 项全量门禁执行记录

按合同约定顺序执行 5 项全量快速验证：

1. `python -m pytest engine/tests -q`:
   - **PASS**: 128 passed, 2 warnings (100%).
2. `npx vitest run`（`desktop/`）:
   - **PASS**: 5 test files, 151 passed (100%).
3. `npx vue-tsc --noEmit` (`desktop/`):
   - **PASS**: 0 type errors.
4. `npm run build` (`desktop/`):
   - **PASS**: 生产包构建成功，耗时 1.36s。
5. `cargo check` (`desktop/src-tauri/`):
   - **PASS**: finished dev profile in 1.05s, 0 errors.

---

## 3. 设计决策与说明

1. **国家出版物与工程咨询标准排版遵循**：正文统一采用仿宋（小四 12pt、1.35 倍行距、首行缩进 2 字符、两端对齐），一级二级标题采用黑体，三级标题采用楷体，四级标题采用仿宋加粗，层级分明且段前段后间距自然适中，设置 `keep_with_next=True` 确保跨页不孤行；
2. **专业标准三线表 XML 深度注入**：通过 python-docx底层 `parse_xml` 注入 `tblBorders`（顶底 12 / 栏目线 6）、`tblCellMar`（内边距）、`w:cantSplit`（防跨页孤行）以及 `w:tblHeader`（跨页自动重复表头），全面满足工程咨询可行性研究报告出版级质量标准。

---

## 4. 冻结声明

- 本轮所有功能开发、单测编写与 5 项全量门禁均已 100% 绿灯通过；
- 工作树修改范围严格符合合同允许路径；
- 候选提交 SHA `3198d1313dcaf72f72b6a908920460db3673e426` 代码已冻结，交付验收。
