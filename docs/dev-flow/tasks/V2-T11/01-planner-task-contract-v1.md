# 任务合同 V2-T11 v1 — 全层级大纲细化与骨架靶向正文填充范式升级

- 状态：READY_FOR_MAKER（2026-08-26 产品负责人批准 V2-T11 实施方案）
- 依据：产品负责人设计指示：
  “在编写大纲时，就完成所有级别的标题编写，即生成一个完整的大纲，这样后面发送给LLM时，让LLM从最低级别的标题开始填充内容。”
- 精确起始 SHA：`ee369b260d42029518bf732c78f9bb5d900a0aca`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **Step 2 大纲生成系统提示词下钻强化 (`engine/app/writing/outline.py` & `prompts.py`)**：
   - 在 `_build_outline_system_prompt` 中追加强规则：
     - **全层级深度覆盖**：大纲生成必须细化下钻至三级（`###`）或四级（`####`）末级小节，每个二级节（`##`）下必须细分 2~5 个具体的末级实施小节，构建全书完整的末级标题骨架，严禁输出粗粒度空章。
2. **Step 3 章节专属结构骨架提取与骨架靶向填空重构 (`engine/app/writing/writer.py`)**：
   - 新增 `_extract_chapter_skeleton(outline_md: str, chapter_seq: int) -> str`：
     - 准确提取当前章的纯结构骨架（包含该章的所有 `##`、`###`、`####` 标题行，自动剔除描述性说明及其他章节内容）；
   - 重构 `_build_chapter_write_args` 写作提示词组装：
     - 在用户 Prompt 中注入 `## 待填充的本章结构骨架（已锁定）\n{skeleton}\n`；
     - 升级核心写作指令为**“骨架靶向填空模式（Skeleton Infilling）”**：
       1. **严格骨架锁定**：严格保留本章结构骨架中的所有标题行（#、##、###、####），不得增删、修改或调换任何标题顺序！
       2. **末级小节精准填充**：在每一个最低级别标题（### / ####）下方空一行，直接开始深入填充详实、专业、严谨的正文分析、工程参数、合规论证与数据表格！
       3. **非末级标题禁止堆砌正文**：一级章（#）和二级节（##）仅作为结构导引，正文必须具体归属到对应的末级小节下方！
       4. **严格格式排版**：每个标题必须独占一行并空一行再写正文，严禁标题与正文连在同一行；表格每行末尾必须输出标准换行符 `\n`，严禁使用 `||` 连写在同一行！
3. **单元测试与全量验证**：
   - 在 `engine/tests/test_writing_router.py` 中新增骨架提取 `_extract_chapter_skeleton` 与骨架靶向填空 Prompt 结构测试断言；
   - 验证 `desktop/src/tests/`、`vue-tsc`、`npm run build`、`pytest` 全绿。

---

## 2. 允许修改

- `engine/app/writing/outline.py`
- `engine/app/writing/prompts.py`
- `engine/app/writing/writer.py`
- `engine/tests/test_writing_router.py`
- `desktop/src/tests/**`（若需适配单测）
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T11/**`

---

## 3. 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿（含新增骨架提取与靶向填充提示词测试）。
- [ ] `npx vitest run`（`desktop/`）全绿。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：
  1. 大纲生成时自动产出包含末级（`###` / `####`）小节的完整树形大纲；
  2. 章节写作时 LLM 严格按照当前章结构骨架在每个末级小节下方填充详实正文。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
