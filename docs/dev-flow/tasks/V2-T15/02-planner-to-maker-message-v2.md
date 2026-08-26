# Planner 指派消息 — V2-T15 第 2 轮

- 任务：`V2-T15` 第 2 轮（Step 4 全书一体化审阅与全景单栏内联工作台重构）
- 精确起始 SHA：`999da87f8596832bd44c1db6648eb100b4ffdc14`
- 有效合同：`docs/dev-flow/tasks/V2-T15/01-planner-task-contract-v2.md`
- 指派对象：Maker Agent

请 Maker Agent 严格按照合同要求执行编码、单测与构建验证：
1. 重构 `desktop/src/components/Step4Review.vue` 为全书一体化工作台（左侧全书多级标题导航，右侧 100% 满屏连贯全文展示，移除双栏 Diff 保留全宽单栏内联高亮，抽屉式展现专家诊断报告与参考资料，废除 100 分制改为健康达标度）；
2. 在 `engine/app/writing/router.py` 与 `desktop/src/stores/project.ts` 中实现全书审阅档案 `full_review.json` 持久化；
3. 清除所有代码与 UI 中硬编码的“水利”字样；
4. 完成全套验证并交付候选 SHA。
