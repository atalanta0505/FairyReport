# Planner to Maker Message — V2-T39 v1

- **任务 ID**：V2-T39
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T39/01-planner-task-contract-v1.md`)
- **起始精确 SHA**：`7a60e805b112de033030adb8ab1cbc09aa4a1368`

---

## 交付任务

请 Maker 依据合同执行以下 4 个核心改进：

1. **繁体字引用清洗、自动转简与去噪**：
   - 在 `engine/app/writing/web_search.py` 中增加繁简转换与去除末尾机构名（如 `中華人民共和國生態環境部`、`中华人民共和国生态环境部`、`中国政府网` 等）；
   - 在 `prompts.py` 思考链防线中加入国家通用规范简体汉字硬约束。

2. **全书参考文献总清单与 `[1][2]...` 统一编号体系**：
   - 在 `desktop/src/lib/markdown.ts` 与 `engine/app/writing/refs.py` 中实现全局引用编号转换（`mergeGlobalRefNumbers` / `formatGlobalRefList`）；
   - 在 `Step4Review.vue` 与 `Step5Export.vue` 中支持一键切换语义标签与学术编号视图，并在导出时生成文末参考文献总清单。

3. **按问题清单序号逐项流水线智能修订**：
   - 在 `desktop/src/stores/project.ts` 中重构 `runSequentialRevisionStream`（或在 `Step4Review.vue` 的 `handleDirectRevision` 中），按照该章问题清单（1 到 N）逐项发起外科手术式段落修复；
   - 每项修复成功即刻在正文原位替换、对应问题打勾 `✓` 并消除黄色高亮；
   - 顶部心跳条显示 `正在修复第 (i/N) 项...`、秒级计时器与实时流式思考推演窗。

4. **全量 5 项流水线门禁验证**。
