# Maker 实施总结 — V2-T48 v1

- **任务 ID**：V2-T48
- **合同版本**：v1 (docs/dev-flow/tasks/V2-T48/01-planner-task-contract-v1.md)
- **起始 SHA**：e6ee83b6da772fcad7e2cab39d5501fb8fa677c1

---

## 1. 交付成果

1. **节标题与正文解耦机制（双端强化 + 骨架引导 + 导出层兜底）**：
   - **后端清洗与分流 (`engine/app/writing/writer.py`)**：
     - 大幅扩展 `_REPORT_TITLE_KEYWORDS` 咨询行业核心词库（覆盖总体规划、建设安排、技术工艺、市场分析等 70+ 词汇）；
     - 解除 `pattern_num_dense` 120 字符长度限制；
     - 增加首字符优先匹配机制（`start_idx_match`），避免正文深处的词汇扩展吞并整句；
     - 支持限定括号 `（如适用）`、`（可选）` 等规范后缀识别；
     - 增加复合标题 `^[与及和]` 防误拆保护；
     - 支持基于大纲骨架（`skeleton`）的精准标题识别与回退；
   - **Word 导出层安全兜底 (`engine/app/export/docx_builder.py`)**：
     - 新增 `_split_heading_and_body` 与 `_BODY_STARTERS`（正文引导词库）；
     - 遇到异常超长标题或包含正文引导特征时，严格解耦：Word Heading 样式仅写入纯净节标题，粘连正文以独立的 Normal 首行缩进段落紧随输出，WPS / Word 目录绝对纯净。
   - **前端同步 (`desktop/src/lib/markdown.ts`)**：
     - `normalizeMarkdown` 深度对齐后端提取算法，确保前后端清洗效果一致。

2. **彻底根除双句号与双标点**：
   - **生成端 (`engine/app/writing/prompts.py`)**：提示词强制约束严禁在引用标签与陈述句之间或之后连续输出多个标点；
   - **清洗端 (`engine/app/writing/writer.py` & `desktop/src/lib/markdown.ts`)**：
     - 修复 `normalize_chapter_markdown` 中移动句末标点至引用标记前时的后置标点消除逻辑；
     - 全局清洗所有 `(【...】|\[\d+\])[。！？；!?,，、]{2,}` 与任意连续重复标点；
   - **引用数字编号 (`engine/app/writing/refs.py`)**：在 `number_all_citations` 完成 `[N]` 替换后，自动补充全文本重复标点清洗。

3. **修复章节写作页面（Step 3）引用标签换行错误**：
   - **富文本 HTML 解析器 (`desktop/src/lib/markdown.ts`)**：
     - 修复 `markdownToHtml` 行内硬换行识别逻辑：在 `trim()` 之前保存原行是否有双空格 `  `、反斜杠 `\` 或 `<br>`；
     - 普通中文多行段落与行内引用标签在未显式输入硬换行标记时，不再盲目插入 `<br />`，消除引用标签被强制折行问题；
   - **流式保存清洗 (`desktop/src/stores/project.ts`)**：
     - 在 `writeSingleChapterStream` 写作完成回调中，先执行 `normalizeMarkdown` 规范化清洗，再同步保存至 pinia store、后端磁盘及本地工作区。

4. **单元测试与实际工程文档验证**：
   - 前端新增 3 项 Vitest 测试（测试复合标题、连贯段落无 `<br />`、多标点清洗）；
   - 后端新增 2 项 Pytest 测试（测试标题粘连解耦、多句号消除、骨架解析）；
   - 对用户真实项目《安徽省利辛县生态皮革加工项目可行性研究》执行真实导出实测，33 个小节标题均严格纯净，WPS 目录完全正常，全文 0 处双句号。

---

## 2. 5 项全量流水线门禁验证

| 门禁项 | 命令 | 结果 |
| :--- | :--- | :---: |
| **前端单元测试** | `npm --prefix desktop run test` | **184/184 passed** (6 files) |
| **Vue 类型检查** | `npm --prefix desktop run typecheck` | **0 errors** |
| **前端打包构建** | `npm --prefix desktop run build` | **Build passed (917ms)** |
| **后端单元测试** | `python -m pytest engine/tests/` | **139/139 passed** (0 failed) |
| **Rust 壳层编译** | `cargo check --manifest-path desktop/src-tauri/Cargo.toml` | **Finished dev profile (1.93s)** |
