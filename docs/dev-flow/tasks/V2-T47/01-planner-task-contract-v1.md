# 任务合同 V2-T47 v1 — 节首句标点与段落融合、审阅文本框首行缩进及正文引用行内紧随修复

- **状态**：READY_FOR_MAKER
- **依据**：产品负责人反馈的 3 项排版与格式缺陷（附带截图）：
  1. 章节写作与正文导出中，每节第一句话常无标点符号且孤立换行成句；
  2. 步骤 4 审阅修改文本框缺失 2 字符首行缩进，且存在节首句标点缺失问题；
  3. 正文中引用标记（如 `[1]`、`【源:...】`）频现单独另起一行成为独立新段落。
- **根因分析**：
  1. **节首概括短句孤立且缺句号**：大模型生成时易在末级小节标题下输出 1 行无句号概括语并回车，`normalize_chapter_markdown` 未进行标点补全与段落融合；
  2. **Step 4 编辑器样式漏配**：`Step4Review.vue` 缺失 `.rich-rendered-editor :deep(p) { text-indent: 2em; }` 首行缩进样式；
  3. **引用换行未清理与 Prompt 约束缺失**：大模型生成时在引用前插入了多余换行符，后处理未将孤立换行引用标签（`\n\n【源:...】` 或 `\n\n[1]`）提升融合至前句末尾。
- **精确起始 SHA**：`59021131bb5bda27a30ab3a1da31727a77649214`
- **工作树门禁**：干净工作树

---

## 1. 允许修改

- `engine/app/writing/prompts.py`
- `engine/app/writing/writer.py`
- `engine/app/writing/refs.py`
- `engine/app/export/docx_builder.py`
- `desktop/src/lib/markdown.ts`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/components/Step3Writing.vue`
- `engine/tests/**`
- `desktop/src/tests/**`
- `docs/dev-flow/tasks/V2-T47/**`

---

## 2. 验收标准

- [ ] 提示词强化：严禁小节标题下输出孤立无标点导引短句；严禁引用标记另起一行；
- [ ] `normalize_chapter_markdown` 与 `docx_builder.py`：自动补齐节首孤立短句句号 `。` 并与后文段落合并；自动清除引用标签前后的多余换行符，使其自然附着在句末；
- [ ] `Step4Review.vue`：配置标准中文正文排版样式（`text-indent: 2em; line-height: 1.8; text-align: justify;`），与 Step 3 完美对齐；
- [ ] Word 导出（`.docx`）与 Markdown 导出（`.md`）：正文中 `[1]`、`[2]` 不再作为单独段落存在，首句标点完整无误；
- [ ] 5 项全量流水线门禁全部绿灯通过。
