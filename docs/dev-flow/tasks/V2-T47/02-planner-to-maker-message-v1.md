# Planner to Maker Message — V2-T47 v1

- **任务 ID**：V2-T47
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T47/01-planner-task-contract-v1.md`)
- **起始精确 SHA**：`59021131bb5bda27a30ab3a1da31727a77649214`

---

## 交付任务

1. **优化 Prompt 写作规则 (`prompts.py`, `writer.py`)**：
   - 增加【节首句标点与段落连贯约束】：严禁在小节标题后输出孤立的无标点短句再另起一行，必须作为完整句子展开正文段落；
   - 增加【引用行内贴合约束】：`【源:...】`、`【标:...】`、`【网:...】` 必须作为行内修饰紧跟在陈述句末尾或句中，严禁单独另起一行或作为段首。

2. **后处理规范化清洗强化 (`writer.py`, `markdown.ts`, `refs.py`, `docx_builder.py`)**：
   - 在 `normalize_chapter_markdown` 中：
     - **引用换行提升（Citation Line Pull-up）**：检测 `\n+([ \t]*【(?:源|标|网):.+?】)` 或 `\n+([ \t]*\[\d+\])`，将其消除前置换行，紧贴前一句末尾；
     - **节首孤立无标点短句补标点与段落融合**：当标题下方紧跟一行较短（<= 80 字）且末尾无标点（非 `。！？；`、非表格、非列表）的文本，若其下一行又是普通中文正文时，自动补全句号 `。` 并合并为一个自然段落，杜绝悬挂孤句。

3. **修复 Step 4 审阅编辑画布首行缩进 CSS (`Step4Review.vue`)**：
   - 为 `.rich-rendered-editor` 补充完整排版规则：`:deep(p) { text-indent: 2em; line-height: 1.8; margin: 0 0 14px 0; text-align: justify; }`、`:deep(blockquote p) { text-indent: 0; }` 等。

4. **Word 导出段落合并优化 (`docx_builder.py`)**：
   - 确保 `[1]` 等引用标记不作为单独段落，首行缩进与标点完美符合工程报告规范。

5. **全量流水线门禁验证**。
