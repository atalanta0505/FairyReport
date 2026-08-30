# 任务合同 V2-T39 v1 — 思考推演全链路流式计时、问题序号逐项流水线智能修订、繁简清洗与全书参考文献编号体系

- **状态**：READY_FOR_MAKER
- **依据**：产品负责人（Fairy）指示：
  1. 无论是写作、审阅还是修订，但凡在 LLM 推理思考环节，一律实时流式输出思考文字并秒级计时；
  2. 智能修订按照问题清单中的序号（1, 2, 3...），一个接一个地执行精准局部修补与原位替换；
  3. 联网与参考资料引用中的繁体字自动转简与机构名清洗；
  4. 全书总参考文献清单与文内 `[1][2]...` 统一编号体系。
- **精确起始 SHA**：`7a60e805b112de033030adb8ab1cbc09aa4a1368`
- **工作树门禁**：干净工作树

---

## 1. 唯一主要变化

1. **AI 智能修订按问题清单序号逐项流水线精准修补 (`desktop/src/stores/project.ts`, `desktop/src/components/Step4Review.vue`)**：
   - 当点击 `⚡ AI 智能修订` 时，系统按该章问题清单中的序号（1 到 N）逐项发起外科手术式修复；
   - 顶部心跳条显示 `正在按序号修复 (i/N)：[维度] 问题描述` 与秒级计时；
   - 修订推演窗口实时流式展示大模型推演过程；
   - 每完成一项，正文原位替换，对应问题卡片打勾 `✓` 并消除黄色高亮标记；全部完成后平滑复核并关闭心跳条。

2. **繁体字引用清洗、自动转简与去噪 (`engine/app/writing/web_search.py`, `engine/app/writing/prompts.py`, `engine/app/writing/refs.py`)**：
   - 在 `web_search.py` 的 `clean_title` 与 `clean_snippet` 中集成轻量高效的繁简体汉字映射转换，将如 `製革及毛皮加工工業水污染物排放標準中華人民共和國生態環境部` 自动转简为 `制革及毛皮加工工业水污染物排放标准` 并剥离冗余的部委/机构后缀；
   - 在 `prompts.py` 纯中文防线中增加国家通用规范简体汉字硬约束；
   - 在 `Step4Review.vue` 审阅中支持繁体字识别与转简建议。

3. **全书参考文献总清单与 `[1][2]...` 统一编号体系 (`engine/app/writing/refs.py`, `desktop/src/lib/markdown.ts`, `desktop/src/components/Step4Review.vue`, `desktop/src/components/Step5Export.vue`)**：
   - 在 `desktop/src/lib/markdown.ts` 中实现文内引用标签（`【源:...】`、`【标:...】`、`【网:...】`）到全局数字编号（`[1]`、`[2]`...）的无缝转换与去重；
   - 在 Step 4 与 Step 5 增加引用格式视图切换器（「语义标签」与「标准编号 [1][2]」）；
   - 在全书文末自动生成规范的《全书参考文献总清单》（符合 GB/T 7714 格式）。

4. **单测覆盖与 5 项流水线门禁**：
   - 补充/更新逐项修订、繁简转换、全书引用编号单测；
   - 依次通过 5 项流水线（Vitest, vue-tsc, build, Pytest, cargo check）。

---

## 2. 允许修改

- `engine/app/writing/web_search.py`
- `engine/app/writing/prompts.py`
- `engine/app/writing/refs.py`
- `engine/app/writing/router.py`
- `engine/app/writing/writer.py`
- `engine/tests/**`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/lib/markdown.ts`
- `desktop/src/stores/project.ts`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/components/Step5Export.vue`
- `desktop/src/tests/**`
- `docs/dev-flow/tasks/V2-T39/**`

---

## 3. 验收标准

- [ ] 写作、审阅（单章/全书）、修订（单项/逐项全修）在 LLM 推理思考时均具备秒级计时器与实时思考流式推演窗；
- [ ] 点击「⚡ AI 智能修订」时，系统按照问题清单序号逐个修复，每项修复成功即刻在正文原位替换并消除黄色高亮；
- [ ] 繁体字网页引用标题（如 `製革及毛皮加工工業...`）在抓取与 RAG 注入时自动转换为规范简体汉字并去除尾部多余机构后缀；
- [ ] 导出与预览支持按全书首次出现顺序赋予 `[1][2]...` 编号，并在文末生成全书参考文献总清单；
- [ ] 5 项全量流水线门禁全部绿灯通过。
