# Planner to Maker Message — V2-T40 v1

- **任务 ID**：V2-T40
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T40/01-planner-task-contract-v1.md`)
- **起始精确 SHA**：`4d1d14e92a59fd47dca23f4ce630d2492df73a4e`

---

## 交付任务

请 Maker 依据合同执行以下 3 项具体改进：

1. **坚决杜绝全章重写**：
   - 检查 `desktop/src/stores/project.ts` 与 `Step4Review.vue`，彻底移除任何 `reviseChapter` 全章重写相关的兜底分支；
   - 修订始终精准锁定问题所在的单段落/短句/数据，只对该局部段落调用 `reviseParagraph` 并原位替换。

2. **移除审阅期“学术编号”切换按钮**：
   - 从 `Step4Review.vue` 工具栏中移除 `refViewMode`（`🏷️ 语义标签视图` / `🔢 学术编号 [1][2]`）按钮与状态变量；
   - 审阅画布正文保持语义标签视图（`【源:...】`、`【标:...】`、`【网:...】`）。

3. **导出期全书参考文献自动排序、文内替换与文末《参考文献》章**：
   - 在 `desktop/src/lib/markdown.ts`、`engine/app/writing/refs.py`、`engine/app/export/docx_builder.py` 中，确保导出时自动将全文按首次出现先后顺序赋予 `[1]`, `[2]`, `[3]`... 统一编号并替换正文标签；
   - 在导出报告文末自动作为最后一章生成格式严谨的《参考文献》章（学术标准著录格式）。

4. **全量 5 项流水线门禁验证**。
