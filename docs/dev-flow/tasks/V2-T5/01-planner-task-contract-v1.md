# 任务合同 V2-T5 v1 — 引擎写作链路：大纲/写作/审阅/提示 + 用户 Key 直连 + SSE

- 状态：DRAFT（待产品负责人批准）
- 产品决定来源：`00-product-decision-v4.md` D14（本地引擎、用户自带 Key 直连）
- 精确起始 SHA：本合同提交后的 master HEAD
- 工作树门禁：`git status --short` 必须干净

## 1. 背景与目标

把现版写作核心（outline/writer/hint_store/ref_manager 及 config.py 的提示词资产）移植进本地引擎，LLM 由用户自带 Key、随请求传入、引擎不存储；写作时双源 RAG（项目库 + 已安装通用包）；流式输出 SSE 供桌面 UI 消费。

## 2. 唯一主要行为变化

**引擎可凭请求携带的 llm_config 生成大纲、流式写作章节（含 RAG 与字数预算）、技术审阅、修订，并管理章节提示；引用格式与现版一致。**

## 3. 明确不做

- 不做导出（T6）、不做 UI（T8/T9）
- 不存储 LLM Key（随请求传入；T8 由桌面端 keychain 管理）
- 不改 backend/**（本切片纯 engine）
- 不改动根目录与 generic_knowledge/**（只读参考）

## 4. 实现导航

- 只读参考（移植而非 import）：
  - `outline.py`：OutlineGenerator、_build_outline_system_prompt、_extract_chapter_titles、parse_chapter_seq、模板章结构约束逻辑
  - `writer.py`：ChapterWriter、_build_writing_system_prompt、技术分析三件（_chapter_has_tech_keyword/_is_tech_analysis_applicable/_build_tech_analysis_rules）、_parse_outline_hierarchy/_allocate_section_budgets/_build_section_quota_block、check_chapter_word_limit、parse_tech_review_result
  - `hint_store.py`：save/load/get_predecessor_*（存储路径改挂 ENGINE_DATA_DIR）
  - `ref_manager.py`：strip_fabricated_labels、extract_chapter_refs、build_chapter_ref_section、merge_global_refs、global_assign_ref_numbers、generate_global_ref_list
  - `config.py`：TECH_REVIEW_SYSTEM_PROMPT、TECH_WRITING_FRAMEWORK、TECH_INSUFFICIENT_DATA_RULES、_FS_CHAPTER_TEMPLATE 等提示词资产与 REPORT_TYPES
- 新建 `engine/app/writing/`：
  - `llm_client.py` — httpx 直连 OpenAI 兼容 chat/completions；非流式与流式（SSE 透传）；重试 1+3 指数退避（同现版 llm.py）；上游 5xx/超时 → 502/504；key 只从请求 llm_config 取、不落盘、日志脱敏
  - `templates_loader.py` — 从已安装通用包目录读模板 JSON（经 T4 generic 模块的 state）；未安装 → 调用方得 409
  - `outline.py` / `writer.py` / `hints.py` / `refs.py` — 移植上述逻辑；RAG 走 engine materials vectorstore + generic collection，引用格式【源:x】/[Z] 同 kb.py
  - `router.py` — 端点（llm_config 缺字段 → 422）：
    - `POST /writing/outline` {project, report_type, llm_config} → outline_md + 章节列表
    - `POST /writing/chapter` {project, report_type, outline_md, chapter_seq, stream, llm_config} → SSE（data: ...，结束标记）或 JSON；含 RAG、字数预算、适用时的技术分析框架
    - `POST /writing/review` {chapter_text, report_type, chapter_title, llm_config} → 结构化审阅结果
    - `POST /writing/revise` {chapter_text, instruction, llm_config} → 修订文本
    - `POST /writing/hints` / `GET /writing/hints/{project}/{ch_seq}` — 本地存取，不需 llm_config
- 提示词资产以模块常量移植，保持中文原文不改写（保证写作质量对齐现版）

## 5. 允许修改

- `engine/**`
- `docs/dev-flow/tasks/V2-T5/**`
- `.gitignore`（如需）

## 6. 禁止修改

- `backend/**`、根目录现有产品文件、`generic_knowledge/**`、steps/、components/、converters/、根 requirements.txt、.opencode/、AGENTS.md
- 既有测试不得删除或放宽

## 7. 依赖

无新增（httpx 已在）。

## 8. 验收标准

- [ ] llm_config 缺失/不完整 → 422
- [ ] 通用包未安装时 outline → 409 明确语义
- [ ] 已安装（stub 包）+LLM 打桩：outline 返回的章数/顺序与 report_type 模板一致
- [ ] chapter 流式：SSE 格式正确、含 RAG 引用标记；非流式 JSON 路径可用
- [ ] 字数预算分配逻辑存在且被测试覆盖（_allocate_section_budgets 移植等价）
- [ ] review 返回 parse 后结构；revise 返回修订文本
- [ ] 虚构标签剥离（strip_fabricated_labels）用例通过
- [ ] hints 存/取/前章提示正确
- [ ] 上游 5xx/超时 → 502/504；key 不落盘不泄露（代码审查 + 日志脱敏用例）
- [ ] 回归：engine 29 + backend 37 = 66 全绿
- [ ] 测试全打桩（LLM MockTransport、嵌入 stub），不联网

## 9. Maker 快速测试（按顺序）

1. `python -m pytest engine/tests backend/tests -q`
2. `python -c "from engine.app.main import app"`

## 10. Evidence Runner / 人工项

- 真实 LLM 联调（用户自备 key 跑一章）为 T8/T9 GUI 阶段人工项，不阻塞本切片。

## 11. GUI / 人工验收项

- 无。

## 12. 候选提交与完成说明要求

- 候选只含 engine/**；完成说明单独提交到 rounds/01/maker-completion.md
- 不 amend、不 rebase、不 push

## 13. 停止条件

- 基线/工作树不符；新依赖；越界；同一失败两次；
- 现版提示词与模板逻辑在移植中遇到无法等价实现的两难 → 停止报告，不擅自简化提示词。

## 14. 已知基线失败

- 无（66 passed）。
