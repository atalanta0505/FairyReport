# Maker 完成说明 — V2-T6 第 1 轮（引擎导出：合并报告生成 docx）

## 合同与基线

- 有效合同：`tasks/V2-T6/01-planner-task-contract-v1.md`（v1）
- 起始 SHA：`da921f14ce13f2b313c2b9ad9296832565785ce0`（已核对：`git status --short` 干净，HEAD 与合同基线一致）
- 轮次目录：rounds/01（合同 §12 未规定预留；rounds/ 尚不存在，启用 01）

## 唯一主要行为变化

引擎可把章节 markdown 合并导出为 docx 文件（含表格、行内格式、全局参考文献表），返回本地产物路径。

## 候选

- 候选 SHA：`8afc02c81c23aefe7c3c481850a51f7f967bef46`
- 父提交：`da921f14ce13f2b313c2b9ad9296832565785ce0`
- 提交标题：V2-T6 引擎导出：合并章节 markdown 为 docx（标题/表格/行内格式/全局参考文献表）
- 精确修改文件（5 项，均在 engine/**）：
  - `engine/app/export/__init__.py`
  - `engine/app/export/docx_builder.py` — 移植 exporter.py：md_to_docx（含 title 参数插报告标题页）、_add_table、_add_formatted_paragraph、_parse_inline_formatting、_parse_md_line、_has_latex_formulas、generate_report_ref（引用函数改 import 自 engine.app.writing.refs）；LaTeX 公式检测/保留（$...$ / $$...$$）忠实移植；新增 build_merged_md（按 seq 合并各章正文、剥离 📎 段、include_refs 时 global_assign_ref_numbers 全局编号 + generate_global_ref_list 参考文献表附末尾）
  - `engine/app/export/router.py` — POST /export/docx {project, title, chapters{seq:md}, include_refs 默认 true}：chapters 空/非字符串→422；按 seq 合并；生成 docx 到 ENGINE_DATA_DIR/exports/<safe_project>_<timestamp>.docx；返回 {path, size_bytes}
  - `engine/app/main.py` — 挂载 export_router
  - `engine/tests/test_export.py` — 6 例（样例 md 读回断言标题层级/加粗/斜体/表格结构；多章按 seq 合并顺序；全局参考文献编号唯一且与正文标记对应/[Z] 保留；422 空 chapters；422 非字符串 chapter；产物落盘 path 可读 size 一致）

## 关键设计决策

- **忠实移植**：docx_builder 逐字移植 exporter.py 的 md_to_docx/_add_table/_add_formatted_paragraph/_parse_inline_formatting/_parse_md_line/_has_latex_formulas/generate_report_ref，仅改 import（ref_manager → engine.app.writing.refs）；LaTeX 检测与保留行为不变。
- **全局参考文献表嵌入 docx**：build_merged_md 在 include_refs=true 时调 merge_global_refs（合并去重各章 📎 段引用）+ global_assign_ref_numbers（全文一次性编号，【源:x】→[N]，两阶段占位替换避免冲突）+ generate_global_ref_list（按编号排序输出三层清单），把参考文献表 markdown 附到合并正文末尾，再 md_to_docx 转换。复用 T5 refs.py，不重写引用逻辑。
- **报告标题页**：md_to_docx 增 title 参数（可选，默认空保持现版行为），非空时 doc.add_heading(title, level=0) 用 Title 样式，与章标题（H1+）区分。
- **文件名安全化**：项目名经 _safe_filename 清洗（仅保留 \w\-），加时间戳防覆盖；产物落 ENGINE_DATA_DIR/exports/。
- **chapters 校验**：Pydantic dict + router 显式检查非空、值为字符串，非法→422。

## 验收标准对照

| 验收项（合同 §8） | 结果 | 证据 |
|---|---|---|
| 样例 md（标题层级/加粗/斜体/表格）导出读回断言结构一致 | ✅ | test_export_basic_structure（Title/Heading/表格 cell/加粗 run/斜体 run） |
| 多章按 seq 合并顺序正确；标题页/报告标题存在 | ✅ | test_export_multi_chapter_order（第一章<第二章<第三章 index）+ basic_structure 断 Title |
| 全局参考文献表生成（编号全局唯一、列表与正文标记对应） | ✅ | test_export_refs_numbering_global（正文【源:policy.md】→[1]、参考文献表含 policy.md、[Z] 保留） |
| chapters 空 → 422 | ✅ | test_export_422_empty_chapters |
| 产物真实落盘且返回 path 可读、size 一致 | ✅ | test_export_returns_path_and_size（exists + getsize==size + 在 exports/） |
| 回归：95 全绿 | ✅ | 101 passed（engine 64 = T5 58 + T6 6；backend 37；既有测试未删未放宽） |
| 测试不联网 | ✅ | 纯本地 python-docx 读写，无网络调用 |

## 快速验证记录（按合同 §9 顺序）

| 命令 | 结果 |
|---|---|
| `python -m pytest engine/tests backend/tests -q` | exit 0：101 passed, 2 warnings |
| `python -c "from engine.app.main import app"` | exit 0：engine ok |

首次失败记录：无（一次通过；python-docx 在 Python 3.14 下行为正常，paragraph.clear()/add_table/add_heading 均可用）。

## 明确保留（未改动）

- 根目录 exporter.py（只读参考移植，未改）、ref_manager.py、backend/**、generic_knowledge/**、steps/、components/、converters/、根 requirements.txt、.opencode/、AGENTS.md 均未动
- 既有测试未删未放宽

## 未执行项（移交 Evidence Runner / 人工）

- Word 打开产物目视检查（表格边框/字体渲染/公式显示）为 T9 GUI 阶段人工项（合同 §10，B 级），不阻塞本切片

## 已知风险、未完成项与范围外发现

- generate_report_ref（忠实移植）生成单独 report_ref.md 文件，但 router 用 build_merged_md 把参考文献表直接嵌入 docx（更符合"导出 docx 含参考文献表"语义）；两者并存，generate_report_ref 供需要单独 ref 文件的场景复用。
- LaTeX 公式仅以斜体文本 $...$ 保留（同现版，不渲染为 Word 公式对象）；Word 目视检查为人工项。
- 范围外发现：pytest 输出存在 starlette httpx 弃用警告与 chromadb asyncio 弃用警告（第三方库，与本任务无关，仅报告不处理）。

## 冻结声明

未 amend、未 rebase、未 push；候选 `8afc02c81c23aefe7c3c481850a51f7f967bef46` 已冻结，本完成说明为独立提交，等待独立 Checker 对精确 SHA 验收。
