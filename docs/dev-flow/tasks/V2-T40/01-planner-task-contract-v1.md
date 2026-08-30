# 任务合同 V2-T40 v1 — 彻底剔除全章重写修订方式、移除审阅期学术编号切换并规范导出期全书参考文献章

- **状态**：READY_FOR_MAKER
- **依据**：产品负责人（Fairy）明确指示：
  1. 坚决不采用全章重写作为修订方式。修订严格限定为问题定位的一小段文字、一句话或具体数据，进行外科手术式精准修改与原位替换；
  2. 移除步骤 4 中的“学术编号切换”按钮与状态，审阅与写作阶段纯粹保留语义化参考标签；
  3. 最终导出报告时（Word / Markdown），全文参考文献严格按首次出现顺序编号，将文内标签替换为 `[1][2]...`，并在文末作为最后一章规范生成《参考文献》章（学术论文与国家标准著录格式）。
- **精确起始 SHA**：`4d1d14e92a59fd47dca23f4ce630d2492df73a4e`
- **工作树门禁**：干净工作树

---

## 1. 唯一主要变化

1. **彻底杜绝全章重写，纯粹精准局部修补 (`desktop/src/stores/project.ts`, `desktop/src/components/Step4Review.vue`)**：
   - 彻底废除修订中任何对 `reviseChapter` 全章重写的调用或兜底；
   - 修订始终精准锁定问题所在的单段落/短句/数据，调用轻量级段落修补接口并原位替换；
   - 若未精确命中，仅针对首个非标题实质正文段落进行局部修补，绝不触碰整章其余内容。

2. **移除审阅期“学术编号切换”按钮 (`desktop/src/components/Step4Review.vue`)**：
   - 从 `Step4Review.vue` 的工具栏中移除 `refViewMode`（`🏷️ 语义标签视图` / `🔢 学术编号 [1][2]`）按钮与状态变量，审阅修改期专注纯净的语义标签排版与高亮批注。

3. **导出期全书参考文献自动排序、文内替换与文末独立章 (`engine/app/writing/refs.py`, `engine/app/export/docx_builder.py`, `desktop/src/lib/markdown.ts`, `desktop/src/views/Home.vue`)**：
   - 导出 Word 或生成最终全书终稿时：
     a) 扫描全书所有章节正文，按首次出现先后顺序为所有引用赋予 `[1]`, `[2]`, `[3]`... 统一编号；
     b) 将全文内 `【源:...】`、`【标:...】`、`【网:...】`、`[Z]` 替换为标准数字编号 `[1]`, `[2]`...（跨章复用）；
     c) 在报告最后自动追加独立的最后一章《参考文献》（如 `# 第 N 章 参考文献` 或 `# 参考文献`），按 `[1] xxxx; [2] xxxx` 规范列出全部引用的出版级学术著录信息。

4. **测试与 5 项流水线门禁**：
   - 更新前端与后端单测断言；
   - 通过 5 项全量流水线（Vitest, vue-tsc, build, Pytest, cargo check）。

---

## 2. 允许修改

- `desktop/src/components/Step4Review.vue`
- `desktop/src/stores/project.ts`
- `desktop/src/lib/markdown.ts`
- `desktop/src/views/Home.vue`
- `engine/app/writing/refs.py`
- `engine/app/export/docx_builder.py`
- `engine/tests/**`
- `desktop/src/tests/**`
- `docs/dev-flow/tasks/V2-T40/**`

---

## 3. 验收标准

- [ ] 修订逻辑中 100% 杜绝任何全章重写调用，始终只改目标局部段落或数据；
- [ ] `Step4Review.vue` 界面中已无“学术编号切换”按钮，画布正文保持语义标签视图；
- [ ] 导出 Word / Markdown 或汇总全书时，文内所有引用按首次出现顺序编号为 `[1][2]`，文末自动生成规范的《参考文献》独立章；
- [ ] 5 项全量流水线门禁全部绿灯通过。
