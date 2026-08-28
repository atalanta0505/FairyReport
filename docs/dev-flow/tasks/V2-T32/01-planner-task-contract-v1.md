# 任务合同 V2-T32 v1 — Word 导出出版级排版与三线表、图表附录格式规范化

- 状态：ACCEPTED（验收通过并锁定 SHA）
- 依据：用户关于“Word 导出出版级排版与三线表、图表附录格式规范化，逐个攻克”的明确指示
- 精确起始 SHA：`756aaf300539c39600e1cfeb76fa1cba9087c53d`
- 锁定验收 SHA：`3198d1313dcaf72f72b6a908920460db3673e426`
- 审查报告：`docs/dev-flow/tasks/V2-T32/rounds/01/checker-report.md`（PASS）
- 工作树门禁：`git status --short` 干净

---

## 1. 唯一主要变化

1. **Word 导出国家公文与工程咨询出版级排版规范升级 (`engine/app/export/docx_builder.py`, `exporter.py`)**：
   - **页面设置**：
     - 标准页边距：上 2.54cm (72pt)、下 2.54cm (72pt)、左 2.8cm (79.37pt)、右 2.6cm (73.7pt)；
   - **正文字体与段落规范**：
     - 中文字体：`仿宋`（`仿宋_GB2312` / `FangSong`），西文字体：`Times New Roman`；
     - 字号：小四（12pt / `Pt(12)`）；
     - 行距：1.35 倍行距，段后 2pt，段前 0pt；
     - 首行缩进：严格缩进 2 字符（`Pt(24)`）；
     - 对齐方式：两端对齐（`WD_ALIGN_PARAGRAPH.JUSTIFY`）；
   - **各级标题出版级层级规范**：
     - **Title（报告总标题 / Level 0）**：黑体（`SimHei`），22pt（二号），居中加粗，段前 12pt，段后 12pt，无首行缩进；
     - **Heading 1（# 第一章 / Level 1）**：黑体，16pt（三号），居左加粗，段前 12pt，段后 6pt，无首行缩进，`keep_with_next=True`；
     - **Heading 2（## 1.1 节 / Level 2）**：黑体，14pt（四号），居左加粗，段前 6pt，段后 3pt，无首行缩进，`keep_with_next=True`；
     - **Heading 3（### 1.1.1 小节 / Level 3）**：楷体（`KaiTi`），12pt（小四），居左加粗，段前 3pt，段后 2pt，无首行缩进，`keep_with_next=True`；
     - **Heading 4（#### 1.1.1.1 末级小节 / Level 4）**：仿宋，12pt（小四），居左加粗，段前 2pt，段后 1pt，无首行缩进，`keep_with_next=True`；
   - **无序列表与引用块排版**：
     - 无序列表（`- ` / `* `）：仿宋，12pt，悬挂缩进 2 字符，无首行缩进；
     - 引用块（`> `）：楷体，10.5pt，左右缩进 2 字符，淡灰边框/底纹；
   - **国家标准三线表高品质强化**：
     - 顶线：1.5pt（`w:sz="12"`，颜色 `#334155`）；
     - 底线：1.5pt（`w:sz="12"`，颜色 `#334155`）；
     - 栏目线（表头下线）：0.75pt（`w:sz="6"`，颜色 `#475569`）；
     - 无竖线与数据行横线；
     - 表头单元格：背景淡灰（`#F1F5F9`），字体 10.5pt（五号），中黑/宋体加粗，水平居中，垂直居中；
     - 数据单元格：字体 10pt（五号），仿宋/宋体，文本居左，数值/序号居中或居右；
     - 跨页防断行（`w:cantSplit`）与表头跨页重复（`w:tblHeader`）；
     - 表格单元格内边距优化（上下 6pt，左右 8pt），单倍行距；
   - **参考文献与三源附录生成规范化**：
     - 若包含参考文献（`include_refs=True`），在文档末尾生成规范附录：
       - `## 参考文献与资料出处`
       - 按项目底稿、国家与行业规程标准、百度联网参考分类输出序号与出处；
   - 同步升级根目录 `exporter.py`，保持接口与排版逻辑一致。

2. **单测覆盖与 5 项全量门禁**：
   - 升级 `engine/tests/test_export.py`，断言字体（仿宋/黑体/Times New Roman）、三线表边框、表头样式、段落缩进与行距；
   - 运行 5 项全量快速验证门禁并确保 100% 绿灯通过。

---

## 2. 允许修改

- `engine/app/export/docx_builder.py`
- `engine/app/export/router.py`
- `exporter.py`
- `engine/tests/test_export.py`
- `docs/dev-flow/tasks/V2-T32/**`

---

## 3. 禁止修改

- `generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `engine/app/export/docx_builder.py` 输出的 Word 文档正文符合仿宋/小四/1.35倍行距/首行缩进 2 字符两端对齐；
- [ ] 各级标题严格匹配黑体/楷体/仿宋层级与字号间距；
- [ ] 表格输出符合顶底 1.5pt、栏目线 0.75pt、淡灰表头、`cantSplit` 与 `tblHeader` 标准三线表规范；
- [ ] 导出参考文献附录分类清晰、编号对应；
- [ ] 5 项全量门禁（Pytest 127+、Vitest 151+、vue-tsc、build、cargo check）全部绿灯通过。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（`desktop/`）
3. `npx vue-tsc --noEmit`（`desktop/`）
4. `npm run build`（`desktop/`）
5. `cargo check`（`desktop/src-tauri/`）
