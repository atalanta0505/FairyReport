# 任务合同 V2-T44 v1 — 联网检索文献每章资料清单可点击与导出报告完整附链

- **状态**：READY_FOR_MAKER
- **依据**：产品负责人的明确要求：
  “联网检索的文献，需要在每章的资料清单里（不需要展示链接文本，可点击就行），以及导出的报告里附上完整链接。”
- **精确起始 SHA**：`b18d22265206eabdf89f80897806c0f01d1e60a7`
- **工作树门禁**：干净工作树

---

## 1. 允许修改

- `engine/app/writing/refs.py`
- `engine/app/export/docx_builder.py`
- `desktop/src/lib/markdown.ts`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/components/Step5Export.vue`
- `engine/tests/**`
- `desktop/src/tests/**`
- `docs/dev-flow/tasks/V2-T44/**`

---

## 2. 验收标准

- [ ] 在步骤 3、步骤 4 的每章参考资料抽屉中，联网检索文献条目支持直接点击标题跳转打开原网页（不呈现冗余杂乱的 raw 链接文本）；
- [ ] 章末 Markdown 的 `📎 本章参考资料` 中，网页链接格式化为优雅的 `-[标题](URL)` Markdown 超链接；
- [ ] 在步骤 5 全书参考文献排序清单中，联网文献标题支持点击直接在浏览器中打开；
- [ ] 在导出的 Word（`.docx`）与 Markdown（`.md`）的文末《参考文献》章中，联网检索条目 100% 完整附带原始 URL（`访问网址: https://...`）；
- [ ] 5 项全量流水线门禁全部绿灯通过。
