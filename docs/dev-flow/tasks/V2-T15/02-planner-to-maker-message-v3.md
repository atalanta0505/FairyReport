# Planner to Maker Message — V2-T15 Round 03

- **任务 ID**：`V2-T15` 第 3 轮
- **精确起始 SHA**：`61122eef7e0af5b306934edcc9f4611252243182`
- **合同路径**：`docs/dev-flow/tasks/V2-T15/01-planner-task-contract-v3.md`

## 1. 目标与背景

产品负责人反馈：
1. **左侧章节导航栏**：每章子标题过多时在栏内无法自如滚动，且收起或平时长章标题被 `...` 截断看不起全貌；
2. **专家审阅等待体验**：全书多章审阅耗时较长（4~11 章串行审阅需数分钟），当前界面缺乏实时章节流转进度指示与 AI 思考推演流式输出，容易误以为卡死。

## 2. 核心实现要点

1. **左侧导航栏布局优化 (`desktop/src/components/Step4Review.vue`)**：
   - 侧边栏宽度优化为 `320px`；
   - `.ch-title-text` 改为 `white-space: normal; word-break: break-word; line-height: 1.35;`，长章节名称 100% 完整显示；
   - `.subheadings-subtree` 添加 `max-height: 280px; overflow-y: auto;` 与极简轻量滚动条，单章内部独立顺畅滚动。
2. **后端流式审阅端点 (`engine/app/writing/router.py`)**：
   - 新增 `POST /writing/review_stream`，通过 SSE 产生 `stage`、`thought`、`chunk`、`done` 事件，流式返回大模型思考链与诊断结果。
3. **前端 API 与 Store 流式与即时看板对接 (`desktop/src/lib/engineApi.ts`, `desktop/src/stores/project.ts`)**：
   - `streamChapterReview` 实现 SSE 解析；
   - `projectStore` 升级 `runFullBookReview`：维护 `reviewProgress`（当前章节序号、标题、进度百分比、实时思考文本、已发现问题数），**每审阅完一章立即落盘并刷新全书诊断状态**；
   - `stopBatchReview` 支持安全一键终止。
4. **前端 Step 4 动态看板与思维推演窗 (`desktop/src/components/Step4Review.vue`)**：
   - 顶部实时显示章节流转进度；
   - 展现可折叠/展开的「🧠 专家审阅实时思考推演窗」，流式打字输出大模型思考过程。
5. **测试与构建**：
   - 完善单测并重新构建 `desktop/dist/**`；
   - 跑通 `vitest`, `pytest`, `vue-tsc`, `build`, `cargo check`；
   - 创建候选 commit，输出完成报告 `docs/dev-flow/tasks/V2-T15/rounds/03/maker-completion.md`。
