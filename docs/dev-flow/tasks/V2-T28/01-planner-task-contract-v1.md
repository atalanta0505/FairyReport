# 任务合同 V2-T28 v1 — 关键章节标准三线表自动规范生成与表格字数智能剥离

- 状态：ACCEPTED（第 1 轮独立审查通过，锁定候选 SHA `92e24dac5d0c7287aa596c269acbfeff0f669710`）
- 依据：用户关于“该做图表的章节中好像都没有做相应的图表。图表中的文字可以不计入总体字数内，但报告模板上要求上要有的功能，一定得做上呢”的明确指令，逐个攻坚问题 5 & 6
- 精确起始 SHA：`c00ac48975c173a0d1e9494253748fecf5d81660`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **引擎写作提示词注入关键章节标准三线表强制生成硬约束 (`engine/app/writing/prompts.py` & `writer.py`)**：
   - 在 `_BASE_WRITING_PROMPT` 与 `_build_chapter_write_args` 中：
     - 新增【标准三线表生成硬要求（最高优先级）】：在涉及**主要技术经济指标**（如 1.1.6）、**建设规模方案比选**（如 3.2.1）、**场址方案比选**（如 4.1.2）、**技术路线比选**（如 5.1.1）、**关键设备比选与设备清单**（如 5.2.1/5.2.2）、**工程方案比选**（如 5.3.1）、**总投资估算构成与资金筹措**（如 7.1.2/7.1.5）、**财务评价指标与债务清偿**（如 7.2.3/7.4.3）、**风险评价矩阵**（如 9.1.8）等小节，**必须强制输出标准的 Markdown 三线表格**；
     - 规范表格结构：包含明确表头、规范对齐分隔线（`| :--- | :---: | ---: |`）、具体工程量纲单位（如 万元、万m³、%、kW 等）及方案比选推荐结论，严禁全篇纯文字堆砌；
     - 表格格式防粘连：表格每行以标准 `\n` 结尾，表格前后强制空行。
   - 升级字数统计口径：在 `writer.py` 的 `_count_content_chars` 中，增加剥离 Markdown 表格字符 `_strip_markdown_tables`，纯正文计算字数。

2. **前端排版与预览：出版级三线表 CSS 渲染与字数精准展示 (`desktop/src/`)**：
   - 在 `desktop/src/lib/markdown.ts` 中：
     - 实现 `stripMarkdownTables(md: string): string`；
     - 实现 `countContentCharsExcludingTables(md: string): number`；
   - 在 `desktop/src/components/Step4Review.vue` 与 `Step3Writing.vue` 中：
     - 升级 `.spec-typography table` 样式为中国工程咨询出版级标准三线表：
       - 顶边框：`2px solid #334155`（加粗顶线）；
       - 底边框：`2px solid #334155`（加粗底线）；
       - 表头底边框：`1px solid #475569`（栏目线）；
       - 去除表格左右外边框与纵向竖线（`border-left: none; border-right: none;`，单元格无竖线）；
       - 表头背景清爽浅灰（`#f8fafc`），文字加粗居中/左对齐；
     - 字数统计呈现与徽标：统一显示为 `X 字 (正文)`，已排除表格和图表文字。

3. **Word 导出：出版级原生三线表格式支持 (`engine/app/export/docx_builder.py`)**：
   - 升级 `_add_table`：
     - 设置 Word 原生表格边框为标准三线表（Top/Bottom Border 1.5pt，Header Bottom Border 0.75pt，清除竖线与内部横线）；
     - 表头单元格居中/左对齐加粗，单元格紧凑内边距。

4. **单测覆盖与 5 项全量门禁**：
   - 增补 `engine/tests/` 与 `desktop/src/tests/` 针对三线表生成、字数剥离与导出格式的测试用例；
   - 确保 `vitest`、`vue-tsc`、`build`、`pytest`、`cargo check` 100% 绿灯。

---

## 2. 允许修改

- `engine/app/writing/prompts.py`
- `engine/app/writing/writer.py`
- `engine/app/export/docx_builder.py`
- `engine/tests/**`
- `desktop/src/lib/markdown.ts`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T28/**`

---

## 3. 禁止修改

- `generic_knowledge/**`（只读资产库）、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [x] 写作要求与技术分析框架中注入了明确的标准三线表强制生成约束；
- [x] 字数统计方法准确剥离 Markdown 表格行，正文字数不被表格结构符和数据膨胀；
- [x] 前端 Step 3 与 Step 4 画布中的表格呈现规范的出版级三线表视觉样式（加粗顶底线、细栏目线、无竖线）；
- [x] Word (.docx) 导出支持原生出版级三线表格式；
- [x] 全量 5 项 A 级门禁（Vitest、vue-tsc、build、pytest、cargo check）全部绿灯通过。

---

## 5. 快速验证顺序

1. `npx vitest run`（`desktop/`）
2. `npx vue-tsc --noEmit`（`desktop/`）
3. `npm run build`（`desktop/`）
4. `python -m pytest engine/tests -q`
5. `cargo check`（`desktop/src-tauri/`）
