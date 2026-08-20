# Checker 验收报告 — V2-T6 第 1 轮

- 状态：**PASS**
- 精确候选 SHA：8afc02c81c23aefe7c3c481850a51f7f967bef46
- 依据合同：`tasks/V2-T6/01-planner-task-contract-v1.md`
- 基线 SHA：da921f14ce13f2b313c2b9ad9296832565785ce0

## 独立检查边界

- 独立重跑（Windows PowerShell 5.1，Python 3.14.2，工作目录 `D:\Repo\FairyReport_lite`，HEAD=97b9a10 完成说明提交，其下 engine/ 与候选完全一致）：
  - `python -m pytest engine/tests backend/tests -q` → exit 0：**101 passed, 2 warnings**（engine 64 + backend 37）
  - `python -c "from engine.app.main import app"` → exit 0：engine ok
- 独立构造样例（临时目录脚本，不入仓库）：用自建 md（H1/H2/H3 + 加粗 + 斜体 + 表格 + 全局引用）调 `md_to_docx`/`build_merged_md` 生成 docx，再用 python-docx 读回断言：title/heading 层级/表格(1 张、含表头)/加粗 run/斜体 run、正文引用编号 `[1]`、参考文献表含 policy.md、`[Z]` 保留——全部为 True。
- 逐条核对合同 §8：阅读 engine/app/export/（docx_builder.py/router.py）源码与 test_export.py，见下表。
- 未重跑：Word 打开产物目视检查（合同 §10 明示为 T9 GUI 阶段人工项，B 级，不阻塞）。

## 验收标准逐条核对

| 合同标准 | 证据等级(A/B/C/D) | 证据与结论 |
|---|---|---|
| §8.1 样例 md（标题层级/加粗/斜体/表格）导出读回断言结构一致 | A | `test_export_basic_structure`（Title/Heading/表格 cell=指标、产能/加粗 run/斜体 run）+ 独立脚本复验全真；`docx_builder.py:33` md_to_docx、`:109` _add_table、`:134` _add_formatted_paragraph。符合。 |
| §8.2 多章按 seq 合并顺序正确；标题页/报告标题存在 | A | `test_export_multi_chapter_order`（第一章<第二章<第三章 index）；`docx_builder.py:216-230` `_sort_key` 按 seq 数值升序；`md_to_docx` title 非空时 `add_heading(title, level=0)` Title 样式。符合。 |
| §8.3 全局参考文献表生成（编号全局唯一、列表与正文标记对应） | A | `test_export_refs_numbering_global`（【源:policy.md】→[1]、清单含 policy.md、[Z] 保留）+ 独立脚本复验；`docx_builder.py:236-240` merge_global_refs+global_assign_ref_numbers+generate_global_ref_list。符合。 |
| §8.4 chapters 空 → 422 | A | `test_export_422_empty_chapters`；`router.py:44` `not req.chapters → 422`；`:46-48` 非字符串值也 422（`test_export_422_non_string_chapter`）。符合。 |
| §8.5 产物真实落盘且返回 path 可读、size 一致 | A | `test_export_returns_path_and_size`（exists + getsize==size + 落在 exports/）；`router.py:69-70` `os.path.getsize`。符合。 |
| §8.6 回归：95 全绿 | A | 独立重跑 engine 64 + backend 37 = 101 passed；`git diff` 无既有 test 的 M/D，既有测试未删未放宽。符合。 |
| §8.7 测试不联网 | A | test_export.py 纯本地 python-docx 读写，`grep` export 模块无 requests/httpx/urlopen/凭据/backend/根模块 import。符合。 |

## 移植忠实性

- 逐字比对根 `exporter.py` 与 `engine/app/export/docx_builder.py`：
  - `md_to_docx`：逻辑逐字一致（默认样式 Times New Roman/宋体、`$$...$$` 占位提取、表格检测与拼接、Heading/段落分支、`doc.save`）；仅新增可选 `title` 参数在开头 `add_heading(title, level=0)`（合同 §4 标题页要求）。
  - `_add_table`：一致（跳分隔行、剥首尾 `|` 切 cell、`Table Grid`、cell 先 clear 再 add_run、字号 Pt(10)）。
  - `_parse_inline_formatting`：一致（`(\*\*(.+?)\*\*|\*(.+?)\*)`，加粗/斜体/前后平文）。
  - `_add_formatted_paragraph`：一致（先 `_LATEX_INLINE.split`，奇数段斜体公式，偶数段走格式解析）。
  - `_parse_md_line`、`_has_latex_formulas`、`_LATEX_DISPLAY`/`_LATEX_INLINE` 正则、`generate_report_ref`：逐字一致。
  - 唯一 import 变更：`from ref_manager import ...` → `from ..writing.refs import ...`，符合"仅 import 变更"约定；`build_merged_md` 为新增合规函数（复用 T5 refs 函数，不重写引用逻辑）。

## 修改范围复核

- `git diff da921f1..8afc02c` 是否严格落在允许路径内：**是**。5 项全部在 `engine/**`（app/export/ + app/main.py + tests/test_export.py）。
- 是否触碰禁止路径：**否**。无 backend/**、根目录 exporter.py/ref_manager.py 等产品文件、generic_knowledge/**、steps/、components/、converters/、根 requirements.txt、.opencode/、AGENTS.md 改动。
- 父链核对：`git log --oneline da921f1..8afc02c` 仅 8afc02c 一个提交；`8afc02c^ == da921f1`；完成说明提交 `97b9a10` 父 == 8afc02c，其改动仅 `docs/dev-flow/tasks/V2-T6/rounds/01/maker-completion.md`（独立提交，符合 §12）。
- `git diff --check da921f1..8afc02c` → exit 0，无空白/冲突标记。

## 阻断项（仅 FAIL）

无。

## 非阻断风险

- LaTeX 公式仅以斜体文本 `$...$` 保留（同现版，不渲染为 Word 公式对象），Word 目视检查为 T9 人工项。
- `generate_report_ref`（独立生成 report_ref.md）与 `build_merged_md`（嵌入式参考文献表）并存：router 走嵌入式，`generate_report_ref` 为忠实移植保留复用，无冲突。
- 文件名时间戳粒度为秒（`%Y%m%d_%H%M%S`），同秒连续导出同项目会覆盖；属可接受限制（可后续加毫秒/随机后缀）。
- 第三方库弃用警告（starlette httpx、chromadb asyncio）：与本任务无关，仅记录。

## 判定

- PASS：锁定 8afc02c81c23aefe7c3c481850a51f7f967bef46；剩余人工项：Word 打开产物目视检查（T9 GUI，合同 §10）。