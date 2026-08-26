# 致 Maker 转发消息 — V2-T11 第 1 轮（全层级大纲细化与骨架靶向正文填充范式升级）

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`ee369b260d42029518bf732c78f9bb5d900a0aca`
- 有效合同：`docs/dev-flow/tasks/V2-T11/01-planner-task-contract-v1.md`

## 核心实现任务

1. **`engine/app/writing/outline.py`**：
   - 升级 `_build_outline_system_prompt`：
     ```python
     base += """
要求：
0. 禁止开场白：不要输出确认语或自我介绍，直接输出大纲内容。
1. 深度要求（极重要）：大纲必须全面细化下钻至三级（###）或四级（####）末级实施小节，每个二级节（##）下必须细分 2~5 个具体的末级小节，构建全书完整的标题骨架，严禁输出只有一级章或二级节的粗粒度空章。
2. 大纲要覆盖当前报告类型的完整专业结构与标准规范
3. 所有级别的标题都必须带编号：
   - 一级（#）：`# 第一章 xxx`
   - 二级（##）：`## 1.1 xxx`
   - 三级（###）：`### 1.1.1 xxx`
   - 四级（####）：`#### 1.1.1.1 xxx`
   - 五级（#####）：`##### 1.1.1.1.1 xxx`
4. 标题只写简明主题词，禁止添加括号描述。
5. 标题标记（#）只用于结构性标题，不要对描述性、阐释性文字使用 # 格式。
6. 返回纯 Markdown，不要包含 JSON 或代码块标记。
"""
     ```

2. **`engine/app/writing/writer.py`**：
   - 实现 `_extract_chapter_skeleton(outline_md: str, chapter_seq: int) -> str`：
     - 从 `outline_md` 中提取给定 `chapter_seq` 的所有标题行（从 `# 第X章` 开始，直到下一章 `# 第X+1章` 之前的所有 `##`、`###`、`####` 标题行，按原顺序拼接）；
   - 在 `ChapterWriter._build_chapter_write_args` 中：
     - 提取 `skeleton = _extract_chapter_skeleton(outline_md, ch_seq)`；
     - 在 prompt 中注入：
       ```python
       f"## 待填充的本章结构骨架（已锁定）\n"
       f"{skeleton}\n\n"
       ```
     - 在 `写作要求` 中强调骨架靶向填空指令：
       ```python
       f"## 写作要求（骨架靶向填充模式）\n"
       f"- **骨架锁定（最高优先级）：必须严格保留上方【待填充的本章结构骨架】中的所有标题行（#、##、###、####）及其完整文字与层级，严禁增删、修改或调换任何标题顺序！**\n"
       f"- **末级小节精准填充：在每一个最低级别标题（### / ####）下方空一行，直接开始深入填充详实、专业、严谨的正文分析、工程参数、合规论证与数据表格！**\n"
       f"- **非末级标题禁止堆砌正文：一级章（#）和二级节（##）作为分类与结构导引，正文必须具体归属到对应的末级小节下方！**\n"
       f"- **格式规范（极重要）：每个标题（#、##、###）必须独占一行且空一行后再写正文，严禁标题与正文连在同一行；表格每行末尾必须输出标准换行符 \\n，严禁使用 || 连写在同一行**\n"
       f"- 对事实性陈述插入引用标记：只能使用上方「参考资料」中实际出现的标签【源:文件名】、【网:标题】或 [Z]\n"
       f"- 请输出完整的章节正文（Markdown 格式），直接从标题和正文开始，禁止任何开场白或字数统计元数据标注\n"
       ```

3. **`engine/tests/test_writing_router.py`**：
   - 增加对 `_extract_chapter_skeleton` 的单测（验证三级/四级标题提取与跨章截断）；
   - 增加对 `_build_chapter_write_args` 中骨架块与骨架靶向填空要求提示词的断言；
   - 验证 `_build_outline_system_prompt` 中全层级下钻深度要求断言。

4. **验证与交付**：
   - 运行 `python -m pytest engine/tests -q`；
   - 运行 `npx vitest run`（`desktop/`）；
   - 运行 `npx vue-tsc --noEmit` 与 `npm run build`（`desktop/`）；
   - 运行 `cargo check`（`desktop/src-tauri`）；
   - 创建候选 commit，编写并提交 `docs/dev-flow/tasks/V2-T11/rounds/01/maker-completion.md`，交回候选 SHA。
