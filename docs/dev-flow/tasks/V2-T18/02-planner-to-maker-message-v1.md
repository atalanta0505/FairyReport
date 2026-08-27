# Planner -> Maker 任务派发消息 — V2-T18 第 1 轮

- **任务 ID**：`V2-T18`
- **轮次**：第 1 轮（Round 01）
- **有效合同**：`docs/dev-flow/tasks/V2-T18/01-planner-task-contract-v1.md`
- **精确起始 SHA**：`600748c10fa8072120e2ef64dbcf9222cf648a52`

请 Maker 严格按照合同约定范围，完成：
1. `desktop/src/lib/markdown.ts` 根除过度正则导致的标题断行/掉字缺陷，更新单测；
2. `desktop/src/components/Step4Review.vue` 左侧导航栏 Word 树形平滑全局滚动与删除冗余按钮；
3. `engine/app/writing/prompts.py`、`desktop/src/lib/engineApi.ts` 与 `Step4Review.vue` 审阅问题精准句子定位与黄色呼吸波纹高亮；
4. 全量 A 级门禁重跑与候选提交。
