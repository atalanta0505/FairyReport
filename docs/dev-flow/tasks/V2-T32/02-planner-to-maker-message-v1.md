# Planner 至 Maker 派发消息：任务 V2-T32 第 1 轮

- 目标任务：V2-T32（Word 导出出版级排版与三线表、图表附录格式规范化）
- 依据合同：`docs/dev-flow/tasks/V2-T32/01-planner-task-contract-v1.md`
- 精确起始 SHA：`756aaf300539c39600e1cfeb76fa1cba9087c53d`

---

## 核心任务要点

1. **Word 排版与样式升级 (`engine/app/export/docx_builder.py`, `exporter.py`)**：
   - 设置文档全局边距与默认 Normal 样式（仿宋 12pt / Times New Roman，1.35 倍行距，两端对齐）；
   - 正文段落自动添加首行缩进 2 字符（`Pt(24)`）；
   - 标题层级（Title、H1、H2、H3、H4）定制中文字体（黑体/楷体/仿宋）、字号、段前段后间距与 `keep_with_next=True`，严禁首行缩进；
   - 列表（`- `）与引用块（`> `）差异化优雅排版；
   - 三线表应用顶底 1.5pt、栏目线 0.75pt、淡灰底纹（`#F1F5F9`）、表头加粗居中、`w:cantSplit` 跨页防断与 `w:tblHeader` 表头跨页重复；
   - 附录参考文献三源分类排版与编号输出。

2. **单测覆盖与 5 项全量门禁**：
   - 升级 `engine/tests/test_export.py`；
   - 运行 5 项全量门禁并确保 100% 绿灯。
