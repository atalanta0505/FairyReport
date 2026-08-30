# 任务合同 V2-T42 v1 — 全局字数实时响应、单章审阅计时修复、问题清单正文序排序、修订推演流式打字与 Word 标题粘连消除

- **状态**：READY_FOR_MAKER
- **依据**：产品负责人反馈的 5 项明确体验优化指示：
  1. 图 1：流式输出与正文变动时，实时统计并滚动全书总字数和本章字数（标签统一为“本章字数”与“总字数”）；
  2. 图 2：修复单章审阅（「🔍 审阅本章」）红框内心跳条计时器停留在 0s 的问题，确保单章与全书审阅均秒级实时递增；
  3. 图 3：问题清单（当前章问题与全书问题）严格按照其在正文中出现的物理先后顺序（从章首到章尾）进行排序，定位顺畅；
  4. 图 4：将 AI 专家修订推演过程接入 SSE 实时流式输出接口（`/writing/revise_paragraph_stream`），推演打字实时跳动；
  5. 图 5：彻底消除 Word 导出中节标题与正文粘连（如 `2.3.1 宏观层面必要性从宏观层面看...` 自动断行分段），并在文末参考文献中完整输出权威联网的原始完整 URL。
- **精确起始 SHA**：`9fdf42cd211f74803cdb2f50172fe1940e35b4df`
- **工作树门禁**：干净工作树

---

## 1. 允许修改

- `desktop/src/components/Step3Writing.vue`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/stores/project.ts`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/lib/markdown.ts`
- `engine/app/writing/router.py`
- `engine/app/writing/writer.py`
- `engine/app/export/docx_builder.py`
- `engine/app/writing/refs.py`
- `engine/tests/**`
- `desktop/src/tests/**`
- `docs/dev-flow/tasks/V2-T42/**`

---

## 2. 验收标准

- [ ] 步骤 3 / 步骤 4 标签统一为“本章字数”与“总字数”，流式写作与修改时字数实时响应且不为 0；
- [ ] 单章审阅心跳条每秒递增计时，绝不停留于 0s；
- [ ] 诊断问题清单按照在正文出现的自然先后位置严格升序排序；
- [ ] 修订推演过程支持 SSE 流式实时打字输出；
- [ ] 导出 Word 时节标题与正文 100% 独立成段，文末参考文献包含完整 URL；
- [ ] 5 项全量流水线门禁全部绿灯通过。
