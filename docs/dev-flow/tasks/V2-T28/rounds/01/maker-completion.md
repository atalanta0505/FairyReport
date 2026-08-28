# 任务完工报告：V2-T28 第 1 轮

- 目标任务：V2-T28（关键章节标准三线表自动规范生成与表格字数智能剥离）
- 有效合同：`docs/dev-flow/tasks/V2-T28/01-planner-task-contract-v1.md`
- 精确起始 SHA：`04c9e0d9b4b08051752b04ecf5c531d0ecdfa0ce`
- 候选提交 SHA：`92e24dac5d0c7287aa596c269acbfeff0f669710`

---

## 1. 变更清单与文件列表

### 1.1 核心代码
- `engine/app/writing/prompts.py`
  - 在 `_BASE_WRITING_PROMPT` 中注入【标准三线表格强制规范（最高优先级）】，明确在主要技术经济指标（如 1.1.6）、方案比选（如 3.2.1/4.1.2/5.1.1/5.3.1）、关键设备清单（如 5.2.1/5.2.2）、总投资与资金筹措（如 7.1.2/7.1.5）、财务评价与清偿（如 7.2.3/7.4.3）、风险评价矩阵（如 9.1.8）等章节小节强制输出标准 Markdown 三线表格（表头 + 对齐分隔线 `| :--- | :---: | ---: |` + 完整数据行与工程量纲单位）；
- `engine/app/writing/writer.py`
  - 在 `_build_writing_system_prompt` 与 `_build_chapter_write_args` 中增强标准三线表提示与前后空行防粘连约束；
  - 实现 `_strip_markdown_tables(text: str) -> str`，在 `_count_content_chars` 中剥离 Markdown 标题行与表格行，实现纯正文字数精准核算。
- `engine/app/export/docx_builder.py`
  - 升级 `_add_table` 与新增 `_set_three_line_table_borders`，通过 OXML 边框属性精确配置 Word 原生表格为出版级标准三线表（顶底线 1.5pt 加粗 `#334155`，表头底线 0.75pt 细线 `#475569`，清除所有纵向竖线与内部横线，表头居中加粗并配置浅灰 `#F8FAFC` 底色）；
- `desktop/src/lib/markdown.ts`
  - 实现并导出 `stripMarkdownTables(md: string): string` 与 `countContentChars(md: string): number`（以及别名 `countContentCharsExcludingTables`）；
- `desktop/src/components/Step3Writing.vue`
  - 升级 `.rich-rendered-editor table` 为出版级标准三线表视觉样式（顶底加粗 2px `#334155`，表头底线 1px `#475569`，无纵向竖线与外边框，表头浅灰 `#f8fafc` 居中/左对齐）；
  - 字数计算与统计展示全面接入 `countContentChars`，呈现为 `X 字 (正文)`；
- `desktop/src/components/Step4Review.vue`
  - 升级 `.spec-typography table` 为出版级标准三线表视觉样式；
  - 顶部指标胶囊、左侧目录概览、连贯排版画布章标题栏、Markdown 源码卡片及单章诊断报告字数统计统一接入 `countContentChars` 并标记 `(正文)`。

### 1.2 单测与产物构建
- `desktop/src/tests/markdown.test.ts`：新增 `stripMarkdownTables` 与 `countContentChars` 单测套件（验证表格剥离、多级标题剥离、来源标签剥离与纯正文字数准确统计）；
- `engine/tests/test_writing_unit.py`：新增三线表提示词硬约束注入与 `_strip_markdown_tables`/`_count_content_chars` 单元测试；
- `engine/tests/test_export.py`：新增 Word 导出原生出版级标准三线表（边框 OXML 属性、表头加粗底色）断言测试；
- `desktop/dist/**`：基于最新代码完成全量生产构建。

---

## 2. 5 项全量门禁执行记录

按合同规定顺序执行 5 项快速验证：

1. `npx vitest run`（`desktop/`）:
   - **PASS**: 5 test files, 144 passed (100%).
2. `npx vue-tsc --noEmit` (`desktop/`):
   - **PASS**: 0 type errors.
3. `npm run build` (`desktop/`):
   - **PASS**: 生产包正常生成于 `desktop/dist/`，耗时 1.16s。
4. `python -m pytest engine/tests -q`:
   - **PASS**: 127 passed, 0 failures (100%).
5. `cargo check` (`desktop/src-tauri/`):
   - **PASS**: finished dev profile in 1.19s, 0 errors.

---

## 3. 设计决策与说明

1. **三线表规范标准定义**：严格采用中国工程咨询与出版行业通用三线表标准（顶线加粗 1.5pt/2px、底线加粗 1.5pt/2px、栏目线细线 0.75pt/1px、无竖线与数据横线），表头具有明确工程量纲与方案比选推荐结论；
2. **表格字数剥离逻辑**：采用纯正文有效字符核算口径，在前后端统一剥离 Markdown 标题行（`^#{1,6}\s+.*$`）、表格行（`^\s*\|.*?\|\s*$`）及来源引用标签，保证字数真实反映正文分析深度，不被结构符虚增；
3. **Word 原生导出高保真**：通过 python-docx OXML 直接操作 `w:tblBorders` 与 `w:tcBorders`，确保导出的 `.docx` 在 Microsoft Word 和 WPS 中均直接呈现标准出版级三线表，无需人工二次调整表格格式。

---

## 4. 冻结声明

- 本轮所有编码实现与测试用例均已完成并通过全部 5 项全量门禁；
- 工作树修改范围严格符合合同允许清单；
- 候选提交 SHA `92e24dac5d0c7287aa596c269acbfeff0f669710` 代码冻结，准备交回。
