# Maker 完成说明 — V2-T5 第 1 轮（引擎写作链路：大纲/写作/审阅/修订/提示 + 用户 Key 直连 + SSE）

## 合同与基线

- 有效合同：`tasks/V2-T5/01-planner-task-contract-v1.md`（v1）
- 起始 SHA：`68a3b2ca0d13f3fd1e6cf7d8f4705da1041836d4`（已核对：`git status --short` 干净，HEAD 与合同基线一致）
- 轮次目录：rounds/01（合同 §12 未规定预留；rounds/ 尚不存在，启用 01）

## 唯一主要行为变化

引擎凭请求携带的 llm_config（用户自带 Key，不存储）生成大纲、流式写作章节（双源 RAG + 字数预算 + 适用时技术分析框架）、技术审阅、修订，并管理章节提示；引用格式【源:x】/[Z] 与现版一致。

## 候选

- 候选 SHA：`63f32931203096669bbce49d09af95e75c23a55c`
- 父提交：`68a3b2ca0d13f3fd1e6cf7d8f4705da1041836d4`
- 提交标题：V2-T5 引擎写作链路：大纲/章节(SSE)/审阅/修订/提示 + 用户Key直连
- 精确修改文件（16 项，均在 engine/**）：
  - `engine/app/writing/__init__.py`
  - `engine/app/writing/prompts.py` — 提示词资产 + 配置常量原文移植（_OUTLINE_BASE_PROMPT/ORDER_SYSTEM_PROMPT/_BASE_WRITING_PROMPT/_HINT_SYSTEM_PROMPT/_MODIFY_SYSTEM_PROMPT/TECH_REVIEW_SYSTEM_PROMPT/TECH_WRITING_FRAMEWORK/TECH_INSUFFICIENT_DATA_RULES/_FS_CHAPTER_TEMPLATE/REPORT_TYPES/TECH_*/TECH_CHAPTER_KEYWORDS/REPORT_WORD_LIMITS/TEMPLATE_MAP/TEMPERATURE_*/FREQUENCY_PENALTY/PRESENCE_PENALTY/TOP_P/RAG_RESULTS_PER_SOURCE）；中文提示词原文不改写
  - `engine/app/writing/templates_loader.py` — 从已安装通用包目录读模板 JSON（替代根 config.py 的 _load_template）；版本变化缓存失效；提供 load_template/get_word_limit/get_chapter_word_limit/get_summary_chapter_limit/is_summary_chapter/get_template_notes/get_template_outline_md/get_chapter_template_prompt/get_chapter_word_budget/require_installed（未装→TemplatesNotInstalled→409）
  - `engine/app/writing/llm_client.py` — httpx 直连 OpenAI 兼容 chat/completions；chat/chat_messages/chat_stream/chat_stream_iter；1+3 指数退避重试（RETRY_DELAYS=[2,4,8]，测试可 monkeypatch）；上游 5xx/连接错误→502、超时→504、4xx 非 429 不重试直返；key 只从请求 llm_config 取不落盘；mask_key 脱敏；_transport 可注入（测试 MockTransport 不联网）
  - `engine/app/writing/refs.py` — 移植 ref_manager（strip_fabricated_labels/extract_chapter_refs/build_chapter_ref_section/_parse_ref_section/merge_global_refs/global_assign_ref_numbers/generate_global_ref_list）
  - `engine/app/writing/hints.py` — 移植 hint_store（存储改挂 ENGINE_DATA_DIR/projects/<project>/hints）
  - `engine/app/writing/rag.py` — 双源 RAG（项目库 ProjectVectorStore + 通用包 GenericStore generic_kb）；【源:filename】/[Z] 格式同 kb.py；嵌入走 get_embedder 可注入接口
  - `engine/app/writing/outline.py` — 移植 OutlineGenerator/_build_outline_system_prompt/_extract_chapter_titles/parse_chapter_seq/build_outline_json 等（模板函数改调 templates_loader）
  - `engine/app/writing/writer.py` — 移植 ChapterWriter/技术分析三件/_parse_outline_hierarchy/_allocate_section_budgets/_build_section_quota_block/check_chapter_word_limit/parse_tech_review_result/_build_cross_chapter_lock 等（模板函数改调 templates_loader；_build_chapter_write_args 增 chapter_budget/is_summary 参数注入字数预算与结构配额块）
  - `engine/app/writing/router.py` — 5 端点：POST /writing/outline、POST /writing/chapter（stream=true SSE 透传 / stream=false JSON）、POST /writing/review、POST /writing/revise、POST+GET /writing/hints；llm_config 缺字段→422（Pydantic）；通用包未装→409
  - `engine/app/main.py` — 挂载 writing_router
  - `engine/tests/conftest.py` — autouse fixture 增 set_llm_transport(None) 重置（避免泄漏 MockTransport）
  - `engine/tests/test_writing_unit.py` — 16 例（strip_fabricated_labels/_allocate_section_budgets 等价/parse_outline_hierarchy/build_section_quota_block/parse_tech_review_result/mask_key/llm 非流式/流式/502/504/4xx不重试/缺配置422）
  - `engine/tests/test_writing_router.py` — 13 例（422/409/outline 章序对齐模板/chapter SSE 格式+RAG 引用标记/chapter 非流式 JSON/502/504/review parse/revise/hints 存取/脱敏）
  - `engine/tests/fixtures/writing_source/` — 小型构建 fixture（policy.md + templates/kexingxing_yanjiu.json，匹配 TEMPLATE_MAP["可行性研究报告"]，含 chapters+outline_md 3 章）

## 关键设计决策

- **提示词原文不改写**：prompts.py 逐字移植 config.py/outline.py/writer.py 的中文提示词资产，保证写作质量对齐现版（合同 §13 停止条件：不擅自简化提示词）。
- **用户 Key 不落盘**：llm_config 随请求传入，LLMClient 只在内存持有 api_key，不写文件、不入库；日志脱敏 mask_key（前2后4）；异常 detail 不含 key。Key 的持久化由 T8 桌面端 keychain 管理（合同 §3）。
- **流式重试边界**：chat_stream_iter 在连接/首响应阶段重试 1+3（yielded=False）；一旦 yield 开始后不再重试，错误转 LLMError（避免重复输出）。
- **字数预算注入**：_build_chapter_write_args 增加 chapter_budget/is_summary 参数，调用 _parse_outline_hierarchy + _allocate_section_budgets + _build_section_quota_block（现版函数等价移植）把结构配额块注入 user prompt，chapter_budget 透传 _build_writing_system_prompt 触发规则7。
- **RAG 双源**：rag.py 复用 T3 ProjectVectorStore（项目库）与 T4 GenericStore（通用包 generic_kb）；通用包未装时通用库检索静默跳过（outline/chapter 端点已 require_installed 前置 409）。
- **模板从已安装包读**：templates_loader 经 T4 GenericStore 的 state 找已装版本目录，读 templates/<name>.json，替代根 config.py 读 generic_knowledge/；缓存按版本隔离。
- **parse_tech_review_result 正则格式**：移植自现版，正则期望"关键词：值"冒号格式（如 `校核结果：需补充` / `原因：...` / `资料清单：`）；现版提示词输出"【校核结果】"括号格式与正则不匹配为现版既有行为，本切片忠实移植不改写（测试用冒号格式验证移植等价）。

## 验收标准对照

| 验收项（合同 §8） | 结果 | 证据 |
|---|---|---|
| llm_config 缺失/不完整 → 422 | ✅ | test_outline_422_missing_api_key（Pydantic 校验）+ test_llm_missing_config_raises_422 |
| 通用包未安装时 outline → 409 明确语义 | ✅ | test_outline_409_no_pack（detail 含"未安装"） |
| 已安装(stub 包)+LLM 打桩：outline 章数/顺序与模板一致 | ✅ | test_outline_returns_template_chapters（seqs==[1,2,3]） |
| chapter 流式：SSE 格式正确、含 RAG 引用标记；非流式 JSON 可用 | ✅ | test_chapter_stream_sse_format_and_rag（data:+[DONE]+【源:sample.md】+prompt 含引用）+ test_chapter_nonstream_json |
| 字数预算分配逻辑存在且被测试覆盖（_allocate_section_budgets 等价） | ✅ | test_allocate_section_budgets_distributes_by_h3 / _no_h3_split_by_h2 |
| review 返回 parse 后结构；revise 返回修订文本 | ✅ | test_review_parse / test_revise_returns_text |
| 虚构标签剥离 strip_fabricated_labels 用例 | ✅ | test_strip_fabricated_labels_keeps_valid_replaces_fabricated |
| hints 存/取/前章提示正确 | ✅ | test_hints_save_and_get / test_hints_get_empty_when_missing（get_predecessor_hints 移植） |
| 上游 5xx/超时 → 502/504；key 不落盘不泄露 | ✅ | test_llm_502_on_upstream_5xx / test_llm_504_on_timeout / test_chapter_502 / test_chapter_504 / test_key_not_leaked + test_mask_key |
| 回归：engine 29 + backend 37 = 66 全绿 | ✅ | 95 passed（engine 58 = T3 20 + T4 9 + T5 29；backend 37；既有测试未删未放宽） |
| 测试全打桩（LLM MockTransport、嵌入 stub），不联网 | ✅ | LLMStub + MockTransport + DeterministicStubEmbedder；无网络调用 |

## 快速验证记录（按合同 §9 顺序）

| 命令 | 结果 |
|---|---|
| `python -m pytest engine/tests backend/tests -q` | exit 0：95 passed, 2 warnings |
| `python -c "from engine.app.main import app"` | exit 0：engine ok |

首次失败记录：
- 一次：`@_retry` 装饰 generator 函数时重试不生效（generator body 异常在迭代时抛出，未被 _retry 捕获/转换）→ 重写 chat_stream_iter 为内联重试循环，连接阶段重试、yield 后错误转 LLMError
- 一次：parse_tech_review_result 测试用括号格式"【原因说明】"无法匹配正则"原因："（现版既有格式与正则不匹配，忠实移植未改）→ 测试改用正则期望的冒号格式验证移植等价
- 一次：_build_section_quota_block 断言"1700"未匹配逗号格式"1,700" → 改断言"1,700"
- 一次：脱敏用例用 outline 端点（模板 outline_md 跳过 LLM，无请求）→ 改用 revise 端点（必调 LLM）

均在合同范围内修复，未触停止条件。

## 明确保留（未改动）

- backend/**（T1/T2/T4 产物）、根目录产品文件（outline.py/writer.py/hint_store.py/ref_manager.py/llm.py/config.py 仅只读参考移植，未改）、generic_knowledge/**、steps/、components/、converters/、根 requirements.txt、.opencode/、AGENTS.md 均未动
- 既有测试未删未放宽

## 未执行项（移交 Evidence Runner / 人工）

- 真实 LLM 联调（用户自备 key 跑一章真实流式写作）为 T8/T9 GUI 阶段人工项（合同 §10），不阻塞本切片

## 已知风险、未完成项与范围外发现

- parse_tech_review_result 正则期望"关键词：值"冒号格式，与现版提示词输出的"【关键词】"括号格式不完全匹配（现版既有行为，忠实移植未改写提示词/正则）；冒号格式可正常解析，括号格式 status 仍可通过 fallback 识别，其余字段可能空。
- chapter stream=true 上游错误以 SSE error event 返回（已 200 提交后无法改状态码），与 stream=false（直接返 502/504）不同；符合 SSE 语义。
- 范围外发现：pytest 输出存在 starlette httpx 弃用警告与 chromadb asyncio 弃用警告（第三方库，与本任务无关，仅报告不处理）。

## 冻结声明

未 amend、未 rebase、未 push；候选 `63f32931203096669bbce49d09af95e75c23a55c` 已冻结，本完成说明为独立提交，等待独立 Checker 对精确 SHA 验收。
