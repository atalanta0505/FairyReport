# 致 Maker 的转发消息 V2-T6 v1

你是当前唯一可写 Maker。

工作目录：D:\Repo\FairyReport_lite
精确起始 SHA：本合同提交后的 master HEAD（开工前核实，工作树须干净）
有效合同：docs/dev-flow/tasks/V2-T6/01-planner-task-contract-v1.md

唯一主要行为：引擎可把章节 markdown 合并导出为 docx（含表格/行内格式/全局参考文献表），返回本地产物路径。

实现导航：
- 只读移植根目录 exporter.py（md_to_docx、_add_table、_add_formatted_paragraph、_parse_inline_formatting、_parse_md_line、_has_latex_formulas、generate_report_ref）
- 新建 engine/app/export/{router.py,docx_builder.py}：POST /export/docx {project,title,chapters{seq:md},include_refs} → 按 seq 合并 → 全局参考文献表复用 engine/app/writing/refs.py（global_assign_ref_numbers/generate_global_ref_list）→ 存 ENGINE_DATA_DIR/exports/ → 返回 {path,size_bytes}；chapters 空→422
- 现版行为忠实移植（含 LaTeX 检测）

允许修改：
- engine/**、docs/dev-flow/tasks/V2-T6/**

禁止修改：
- backend/**、根目录产品文件、generic_knowledge/**、steps/、components/、converters/、根 requirements.txt、.opencode/、AGENTS.md；既有测试不得删除或放宽

快速验证顺序：
1. python -m pytest engine/tests backend/tests -q（95 回归须全绿 + 新增）
2. python -c "from engine.app.main import app"

停止条件：
- 基线/工作树不符；新依赖；越界；同一失败两次；python-docx 在 3.14 下异常两次无解 → 停止报告。

进度纪律：每阶段报告"已完成/当前在做/异常/是否仍在合同内"；超 3 分钟命令不执行，标记移交。

完成时：
1. 只提交 engine/**；
2. 创建本地候选提交；
3. 不 amend、不 rebase、不 push；
4. 完成说明写到 docs/dev-flow/tasks/V2-T6/rounds/01/maker-completion.md；
5. 冻结并交回。
