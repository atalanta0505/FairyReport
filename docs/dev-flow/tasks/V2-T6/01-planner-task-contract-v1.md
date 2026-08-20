# 任务合同 V2-T6 v1 — 引擎导出：合并报告生成 docx

- 状态：DRAFT（待产品负责人批准）
- 产品决定来源：`00-product-decision-v4.md` 路线图 T6
- 精确起始 SHA：本合同提交后的 master HEAD
- 工作树门禁：`git status --short` 必须干净

## 1. 背景与目标

移植现版 exporter.py 到引擎：把各章 markdown 合并为完整报告并导出 docx（标题/表格/行内格式/全局参考文献表），桌面 UI（T9）调用后直接打开产物。

## 2. 唯一主要行为变化

**引擎可把章节 markdown 合并导出为 docx 文件（含表格、行内格式、全局参考文献表），返回本地产物路径。**

## 3. 明确不做

- 不做 UI 打开/另存为（T9）
- 不改写作链路（T5 产物只读复用 refs.py）
- 不动 backend/**、根目录、generic_knowledge/**

## 4. 实现导航

- 只读移植根目录 `exporter.py`：md_to_docx、_add_table、_add_formatted_paragraph、_parse_inline_formatting、_parse_md_line、_has_latex_formulas、generate_report_ref
- 新建 `engine/app/export/router.py`（+ 同目录 `docx_builder.py` 承载移植逻辑）：
  - `POST /export/docx` {project, title, chapters: {seq: markdown}, include_refs: bool 默认 true} → 合并（按 seq 排序）→ 全局参考文献表经 `engine/app/writing/refs.py` 的 global_assign_ref_numbers/generate_global_ref_list → 生成 docx 到 ENGINE_DATA_DIR/exports/（文件名含项目名+时间戳）→ 返回 {path, size_bytes}
  - chapters 为空/非法 → 422
- LaTeX 公式检测等现版行为忠实移植

## 5. 允许修改

- `engine/**`
- `docs/dev-flow/tasks/V2-T6/**`

## 6. 禁止修改

- `backend/**`、根目录产品文件、`generic_knowledge/**`、steps/、components/、converters/、根 requirements.txt、.opencode/、AGENTS.md；既有测试不得删除或放宽

## 7. 依赖

无新增（python-docx 已在批准清单）。

## 8. 验收标准

- [ ] 导出含标题层级/加粗/斜体/表格的样例 md → 用 python-docx 读回断言结构一致
- [ ] 多章按 seq 合并顺序正确；标题页/报告标题存在
- [ ] 全局参考文献表生成（编号全局唯一、列表与正文标记对应）
- [ ] chapters 空 → 422
- [ ] 产物真实落盘且返回 path 可读、size 一致
- [ ] 回归：95 全绿
- [ ] 测试不联网

## 9. Maker 快速测试（按顺序）

1. `python -m pytest engine/tests backend/tests -q`
2. `python -c "from engine.app.main import app"`

## 10. Evidence Runner / 人工项

- Word 打开产物目视检查为 T9 GUI 阶段人工项（B 级），不阻塞本切片。

## 11. GUI / 人工验收项

- 无。

## 12. 候选提交与完成说明要求

- 候选只含 engine/**；完成说明单独提交到 rounds/01/maker-completion.md
- 不 amend、不 rebase、不 push

## 13. 停止条件

- 基线/工作树不符；新依赖；越界；同一失败两次；
- python-docx 在 Python 3.14 下行为异常两次尝试无解 → 停止报告。

## 14. 已知基线失败

- 无（95 passed）。
