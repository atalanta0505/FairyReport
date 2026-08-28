# 验收审查报告：V2-T32 第 1 轮

- 状态：PASS
- 审查者：Checker Agent
- 审查时间：2026-08-28 13:50:00
- 任务：V2-T32（Word 导出出版级排版与三线表、图表附录格式规范化）
- 依据合同：`docs/dev-flow/tasks/V2-T32/01-planner-task-contract-v1.md`
- 候选提交 SHA：`3198d1313dcaf72f72b6a908920460db3673e426`
- 基线（父提交）SHA：`756aaf300539c39600e1cfeb76fa1cba9087c53d`

---

## 1. 提交与修改范围审查

- **父链与提交历史**：
  - 基线父提交：`756aaf300539c39600e1cfeb76fa1cba9087c53d`（上轮验收基线）
  - 任务合同就绪提交：`d238a0045f22319fcad6849bc52ee24075191240`
  - 候选提交：`3198d1313dcaf72f72b6a908920460db3673e426`
  - 完工报告提交：`45458e02fe2c862cf1f1527ae08cd3054512dddf`
  - 候选提交信息：`feat(export): Word 导出出版级排版升级与国家标准三线表、图表附录规范化`
- **候选提交变更文件清单（`git show --name-status 3198d13`）**：
  - `engine/app/export/docx_builder.py` (Modified)
  - `engine/tests/test_export.py` (Modified)
  - `exporter.py` (Modified)
- **权限与范围判定**：
  - 代码修改严格限定在合同允许的 `engine/app/export/**`、`exporter.py` 与 `engine/tests/**` 范围内；
  - 严守只读边界，未触碰 `generic_knowledge/**`、`AGENTS.md` 或 `.gitignore`；
  - 工作树干净，无未追踪或未提交的脏代码。

---

## 2. 核心功能与代码设计审查

1. **页面设置与正文出版级排版规范 (`engine/app/export/docx_builder.py`, `exporter.py`)**：
   - **标准页边距**：
     - 上边距：2.54cm（72pt）；
     - 下边距：2.54cm（72pt）；
     - 左边距：2.8cm（79.37pt）；
     - 右边距：2.6cm（73.7pt）；
     - 在 `_init_document_styles` 中对全部 `doc.sections` 初始化配置；
   - **正文字体与段落排版**：
     - 中文字体：严格设置为 `仿宋`（通过 `w:eastAsia` 注入）；
     - 西文字体：`Times New Roman`（通过 `w:ascii` 与 `w:hAnsi` 注入）；
     - 字号：小四（12pt / `Pt(12)`）；
     - 行距：1.35 倍行距，段前 0pt，段后 2pt；
     - 首行缩进：严格缩进 2 字符（`Pt(24)`）；
     - 对齐方式：两端对齐（`WD_ALIGN_PARAGRAPH.JUSTIFY`）；
     - 基础 `Normal` 样式与 `_add_formatted_paragraph` 保持严格一致。

2. **严格出版级各级标题层级规范**：
   - **Title（报告总标题 / Level 0）**：黑体 22pt（二号），居中加粗，段前 12pt / 段后 12pt，无首行缩进；
   - **Heading 1（Level 1）**：黑体 16pt（三号），居左加粗，段前 12pt / 段后 6pt，无首行缩进，`keep_with_next=True`；
   - **Heading 2（Level 2）**：黑体 14pt（四号），居左加粗，段前 6pt / 段后 3pt，无首行缩进，`keep_with_next=True`；
   - **Heading 3（Level 3）**：楷体 12pt（小四），居左加粗，段前 3pt / 段后 2pt，无首行缩进，`keep_with_next=True`；
   - **Heading 4+（Level 4+）**：仿宋 12pt（小四），居左加粗，段前 2pt / 段后 1pt，无首行缩进，`keep_with_next=True`；
   - 全级标题均设置 `keep_with_next=True` 防止跨页孤行，并清空首行与左右缩进。

3. **列表与引用块出版级排版规范**：
   - **无序列表（`- ` / `* `）与有序列表（`1. ` / `1、`）**：仿宋 12pt，左缩进 24pt，首行悬挂缩进 -12pt，1.35 倍行距，段前 0pt / 段后 2pt，两端对齐；
   - **引用块（`> `）**：楷体 10.5pt，左右缩进 24pt（2 字符），首行缩进 0pt，1.35 倍行距，左侧注入单实线边框（`w:sz="24"`，颜色 `#94A3B8`）与浅灰底纹（`#F8FAFC`），字体颜色 `#334155`。

4. **国家标准三线表高品质深度实现**：
   - **三线表边框属性（`_set_three_line_table_borders`）**：
     - 顶线：1.5pt（`w:val="single" w:sz="12" w:space="0" w:color="334155"`）；
     - 底线：1.5pt（`w:val="single" w:sz="12" w:space="0" w:color="334155"`）；
     - 栏目线（表头下底线）：0.75pt（`w:val="single" w:sz="6" w:space="0" w:color="475569"`）；
     - 隐藏纵向竖线与数据行横线（`insideH="none"`, `insideV="none"`, `left="none"`, `right="none"`）；
   - **单元格内边距优化**：注入 `w:tblCellMar`，上下边距 6pt（`120 dxa`），左右边距 8pt（`160 dxa`）；
   - **跨页防断与表头重复**：
     - 数据行全部注入 `w:cantSplit` 避免单元格跨页被截断；
     - 表头行注入 `w:tblHeader` 实现跨页自动重复表头；
   - **单元格样式与对齐**：
     - 表头单元格：浅灰背景（`#F1F5F9`），黑体加粗 10.5pt（五号），水平居中、垂直居中；
     - 数据单元格：仿宋 10pt（五号），文本居左、纯数字/百分比智能右对齐、支持 Markdown 对齐标记（`:---` / `:---:` / `---:`），垂直居中，单倍行距。

5. **三源参考文献与资料出处附录规范化**：
   - `format_ref_appendix`：自动按“项目底稿资料”、“国家与行业规程标准”、“互联网与第三方参考”、“AI自有知识”四大类输出序号与来源出处 Markdown；
   - `build_merged_md` 与 `generate_report_ref` 全链路统一接入，与后端 `writing.refs` 模块无缝互通。

6. **双轨同步维护**：
   - 根目录 `exporter.py` 与 `engine/app/export/docx_builder.py` 保持 100% 算法、样式与 XML 属性同步，保证单机离线导出与服务化导出效果完全一致。

7. **单元测试覆盖与断言完整性 (`engine/tests/test_export.py`)**：
   - `test_export_publication_typography_and_margins`：断言页面边距（上/下 72pt、左 79.37pt、右 73.7pt）、正文仿宋/Times New Roman、首行缩进 24pt、行距 1.35、两端对齐、Title/H1/H2/H3/H4+ 字体/字号/间距/`keep_with_next`、引用块底纹边框与缩进、列表悬挂缩进；
   - `test_export_standard_three_line_table_format`：断言三线表顶底 sz=12 (1.5pt)、表头底线 sz=6 (0.75pt)、`insideH="none"`、`tblCellMar` 120/160 dxa、表头黑体居中加粗与浅灰背景、`cantSplit` 与 `tblHeader`；
   - `test_export_refs_numbering_global`：断言三源参考文献附录四大分类与全局编号替换；
   - `test_export_multi_chapter_order`、`test_export_returns_path_and_size`、`test_export_422_*` 全面验证多章排序、落盘及异常入参防御。

---

## 3. A 级快速验证门禁独立复跑记录

Checker 独立执行全部 5 项门禁命令，结果如下：

| 门禁项 | 执行命令 | 工作目录 | 独立复跑结果 | 判定 |
| :--- | :--- | :--- | :--- | :--- |
| **Gate 1 - Engine Pytest** | `python -m pytest engine/tests -q` | 仓库根目录 | 128 passed, 2 warnings, 0 failures（耗时 101.15s） | **PASS** |
| **Gate 2 - Vitest 单测** | `npx vitest run` | `desktop/` | 5 个测试文件通过，共 151 个测试用例全部通过（耗时 1.20s） | **PASS** |
| **Gate 3 - Vue 类型检查** | `npx vue-tsc --noEmit` | `desktop/` | 0 个类型错误与警告 | **PASS** |
| **Gate 4 - 前端构建打包** | `npm run build` | `desktop/` | Vite 生产包构建成功（dist 更新，耗时 1.29s） | **PASS** |
| **Gate 5 - Tauri Cargo Check** | `cargo check` | `desktop/src-tauri/` | Finished `dev` profile in 1.09s，0 error | **PASS** |

---

## 4. 任务合同标准对照表

| 合同验收标准 | 审查结果 | 状态 |
| :--- | :--- | :--- |
| `engine/app/export/docx_builder.py` 输出的 Word 文档正文符合仿宋/小四/1.35倍行距/首行缩进 2 字符两端对齐 | 页面边距与正文字体/字号/缩进/行距全部符合国家工程咨询出版级标准 | **已达成** |
| 各级标题严格匹配黑体/楷体/仿宋层级与字号间距，且配置 `keep_with_next=True` | Title/H1/H2/H3/H4+ 严格遵循黑体/楷体/仿宋字号梯次，段前段后适度且首行缩进 0pt | **已达成** |
| 表格输出符合顶底 1.5pt、栏目线 0.75pt、淡灰表头、`cantSplit` 与 `tblHeader` 标准三线表规范 | XML `tblBorders`、`tcBorders`、`tblCellMar`、`cantSplit`、`tblHeader` 深度注入，三线表精美规范 | **已达成** |
| 导出参考文献附录分类清晰、编号对应 | `format_ref_appendix` 按项目底稿、规程标准、互联网参考、AI自有知识分类生成，编号对应 | **已达成** |
| 5 项全量门禁（Pytest 128+、Vitest 151+、vue-tsc、build、cargo check）全部绿灯通过 | 独立复跑 5 项门禁全部 100% 绿灯通过 | **已达成** |

---

## 5. 阻断项与非阻断风险

- **阻断项（Blockers）**：无。
- **非阻断风险与建议（Non-blocking Notes）**：
  - 本轮注入的标准三线表与单元格底纹为通用 OpenXML 规范，在 Microsoft Word 2016+、WPS Office 以及 LibreOffice / macOS Pages 中均具有卓越渲染兼容性；对于极端旧版本或纯文本查看器，底层回退样式依然保证文本与表格结构清晰。

---

## 6. 待产品负责人执行的 B 级人工验证清单

- [ ] 打开 FairyReport Lite 应用，加载或编写一个包含多级标题、正文、引用块、项目清单和数据表格的可行性研究报告项目；
- [ ] 点击“导出 Word（.docx）”按钮，生成并导出 Word 文件；
- [ ] 使用 Microsoft Word 或 WPS Office 打开导出的 `.docx` 文件：
  - 检查页面边距是否为标准公文边距（上/下 2.54cm，左 2.8cm，右 2.6cm）；
  - 检查正文字体是否为仿宋/Times New Roman 小四号，首行缩进 2 字符，行距适中两端对齐；
  - 检查一级标题（黑体 16pt）、二级标题（黑体 14pt）、三级标题（楷体 12pt）层级是否清晰优雅；
  - 检查表格是否呈现加粗顶底线、细栏目线、无竖线与淡灰表头的标准三线表排版；
  - 检查跨页长表格是否在下一页自动重复表头且单元格无跨页断行；
  - 检查文档末尾的《参考文献与资料出处》附录是否按项目底稿、规程标准、第三方参考分类清晰列出。

---

## 7. 验收结论

**判定：PASS**

候选提交 `3198d1313dcaf72f72b6a908920460db3673e426` 严格按照任务合同要求，全面升级了 Word 导出的国家出版级排版规范，包括页面标准边距、仿宋/Times New Roman 正文排版、各级标题层级规范、引用与列表格式，并深度注入了顶底 1.5pt/栏目线 0.75pt/`tblCellMar`/`cantSplit`/`tblHeader` 的国家标准三线表与三源参考文献附录。单测覆盖完备，5 项 A 级门禁独立复跑全部 100% 绿灯通过（PASS）。建议产品负责人予以核准并锁定。
