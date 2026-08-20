# Checker 验收报告 — V2-T5 第 1 轮

- 状态：**PASS**
- 精确候选 SHA：63f32931203096669bbce49d09af95e75c23a55c
- 依据合同：`tasks/V2-T5/01-planner-task-contract-v1.md`
- 基线 SHA：68a3b2ca0d13f3fd1e6cf7d8f4705da1041836d4

## 独立检查边界

- 独立重跑（Windows PowerShell 5.1，Python 3.14.2，工作目录 `D:\Repo\FairyReport_lite`，HEAD=ed0b547 完成说明提交，其下 engine/ 与候选完全一致）：
  - `python -m pytest engine/tests backend/tests -q` → exit 0：**95 passed, 2 warnings**（engine 58 + backend 37）
  - `python -c "from engine.app.main import app"` → exit 0：engine ok
- 逐条核对合同 §8：阅读 engine/app/writing/（prompts/outline/writer/llm_client/rag/refs/hints/templates_loader/router）全部源码与新增测试，见下表。
- 关键约束审查：提示词原文移植逐字比对（脚本归一化空白后 9/9 命中根 config.py/outline.py/writer.py）；RAG 双源格式核对；Key 落盘检查；parse_tech_review_result 既有行为比对。
- 未重跑：真实 LLM 联调（合同 §10 明示为 T8/T9 GUI 阶段人工项，切片全打桩不联网）。

## 验收标准逐条核对

| 合同标准 | 证据等级(A/B/C/D) | 证据与结论 |
|---|---|---|
| §8.1 llm_config 缺失/不完整 → 422 | A | Pydantic `LLMConfig.api_key/base_url/model` 均 `min_length=1`（`router.py:35-38`）；`LLMClient.__init__` 三字段二次校验抛 422（`llm_client.py:102-107`）；`test_outline_422_missing_api_key`/`test_llm_missing_config_raises_422` 通过。符合。 |
| §8.2 通用包未安装时 outline → 409 明确语义 | A | `router.py:79` `_require_pack()` → `TemplatesNotInstalled → 409`；`templates_loader.py:175` require_installed；`test_outline_409_no_pack`（detail 含"未安装"）通过。符合。 |
| §8.3 已安装(stub 包)+LLM 打桩：outline 章数/顺序与模板一致 | A | `test_outline_returns_template_chapters`（seqs==[1,2,3]）；`outline.py:78` 模板有 outline_md 时直接返回，`_extract_chapter_titles` 顺序解析。符合。 |
| §8.4 chapter 流式：SSE 正确、含 RAG 引用标记；非流式 JSON 可用 | A | `test_chapter_stream_sse_format_and_rag`（`data: `+`data: [DONE]`+`【源:sample.md】`注入 prompt）；`test_chapter_nonstream_json`；`router.py:139-180` StreamingResponse 透传 SSE，`:190` chat_stream_iter。符合。 |
| §8.5 字数预算分配逻辑存在且被测试覆盖（_allocate_section_budgets 等价） | A | `writer.py:210-273` `_allocate_section_budgets`/`_build_section_quota_block` 移植；`test_allocate_section_budgets_distributes_by_h3`/`_no_h3_split_by_h2`/`test_build_section_quota_block_contains_budgets` 断言逐额与逗号格式。符合。 |
| §8.6 review 返回 parse 后结构；revise 返回修订文本 | A | `test_review_parse`（status/需补充/清单 1 条）；`test_revise_returns_text`；`router.py:182-207` review/revise 端点 + `writer.py:637` parse_tech_review_result。符合。 |
| §8.7 strip_fabricated_labels 用例通过 | A | `refs.py:14` 移植；`test_strip_fabricated_labels_keeps_valid_replaces_fabricated`/`_empty_rag_noop` 通过（保留有效【源:policy.md】、编造→[Z]）。符合。 |
| §8.8 hints 存/取/前章提示正确 | A | `hints.py` 存/取挂 `ENGINE_DATA_DIR/projects/<p>/hints`；`get_predecessor_hints` 移植；`test_hints_save_and_get`/`test_hints_get_empty_when_missing` 通过。符合。 |
| §8.9 上游 5xx/超时→502/504；key 不落盘不泄露 | A | `llm_client.py:59-69` `_map_error`（Timeout→504、5xx→502）；`test_llm_502_on_upstream_5xx`（4 次重试后 502）/`test_llm_504_on_timeout`/`test_chapter_502`/`test_chapter_504` 通过；key 仅存 `LLMClient.instance` 内存 + `Authorization` 头，无任何落盘（grep 全 engine 仅 hints.py/templates_loader.py 有文件写入且不涉 key），`test_key_not_leaked_in_request_headers`+`test_mask_key` 通过。符合。 |
| §8.10 回归：engine 29 + backend 37 = 66 全绿 | A | 独立重跑 engine 58 + backend 37 = 95 passed；`git diff` 无既有 test 的 M/D，既有测试未删未放宽。符合。 |
| §8.11 测试全打桩（LLM MockTransport、嵌入 stub）不联网 | A | `llm_client.set_transport(httpx.MockTransport)` 注入；嵌入走 conftest 的 `DeterministicStubEmbedder`；`test_writing_unit/router.py` 无真实网络调用。符合。 |

## 关键约束审查

- 提示词原文移植：脚本归一化空白后比对 `TECH_REVIEW_SYSTEM_PROMPT`/`TECH_WRITING_FRAMEWORK`/`TECH_INSUFFICIENT_DATA_RULES`/`_FS_CHAPTER_TEMPLATE`（源 config.py）、`_HINT_SYSTEM_PROMPT`/`_BASE_WRITING_PROMPT`/`_MODIFY_SYSTEM_PROMPT`（源 writer.py）、`_OUTLINE_BASE_PROMPT`/`ORDER_SYSTEM_PROMPT`（源 outline.py），**9/9 均为根文件逐字子串**，中文提示词未改写。
- RAG 双源格式：`rag.py:50` 项目库 `【源:filename】`、`:64` 通用库 `[Z]`，与根 kb.py 一致；双源走 T3 `ProjectVectorStore` + T4 `GenericStore._get_collection`。
- Key 不落盘：`grep api_key` 仅命中 llm_client 内存/headers、router Pydantic 字段、测试常量；写文件仅 hints.py（存提示）与 templates_loader.py（读模板），无 Key 持久化；日志/异常无 Key 明文。

## 修改范围复核

- `git diff 68a3b2c..63f3293` 是否严格落在允许路径内：**是**。16 项全部在 `engine/**`（app/writing/、app/main.py、tests/、fixtures/）。
- 是否触碰禁止路径：**否**。无 backend/**、根目录产品文件、generic_knowledge/**、steps/、components/、converters/、根 requirements.txt、.opencode/、AGENTS.md 改动。
- 父链核对：`git log --oneline 68a3b2c..63f3293` 仅 63f3293 一个提交；`63f3293^ == 68a3b2c`；完成说明提交 `ed0b547` 父 == 63f3293，其改动仅 `docs/dev-flow/tasks/V2-T5/rounds/01/maker-completion.md`（独立提交，符合 §12）。
- `git diff --check 68a3b2c..63f3293` → exit 0，无空白/冲突标记。

## 已知限制核实（§6）

- `parse_tech_review_result` 正则 `(?:状态|校核结果|结论)[：:]\s*(通过|需补充|不适用)`（`writer.py:660`）期望冒号格式，而 `TECH_REVIEW_SYSTEM_PROMPT` 输出 `【校核结果】通过 / 需补充 / 不适用` 括号格式——经比对根目录 `writer.py` 的 `parse_tech_review_result` 使用**相同正则**、根 `config.py` 的 `TECH_REVIEW_SYSTEM_PROMPT` 使用**相同括号格式**，此差异为现版既有行为，候选忠实移植未引入。测试用冒号格式验证正则等价（status fallback 亦能兜底括号格式的 status 字段）。符合。

## 阻断项（仅 FAIL）

无。

## 非阻断风险

- chapter `stream=true` 下上游错误仅能以 SSE `error` event 返回（HTTP 已 200），与 `stream=false` 直返 502/504 的语义不同；属 SSE 特性，不阻断（合同未强制流式错误状态码）。
- `parse_tech_review_result` 冒号正则与括号提示词的既有错配：冒号格式可完整解析，括号格式仅 status 经 fallback 识别、reason/details 可能为空（现版既有行为，未改写）。
- 第三方库弃用警告（starlette httpx、chromadb asyncio）：与本任务无关，仅记录。
- 真实 LLM 联调未执行（合同 §10 人工项，T8/T9 GUI 阶段），不阻塞本切片。

## 判定

- PASS：锁定 63f32931203096669bbce49d09af95e75c23a55c；剩余人工项：真实 LLM 联调（用户自备 key 跑一章流式写作，T8/T9 落实）。