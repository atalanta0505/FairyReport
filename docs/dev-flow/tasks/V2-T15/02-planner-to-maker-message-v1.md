# Planner 指派消息 — V2-T15 第 1 轮

- **任务 ID**：`V2-T15`
- **指派对象**：Maker Agent
- **有效合同**：`docs/dev-flow/tasks/V2-T15/01-planner-task-contract-v1.md`
- **精确起始 SHA**：`d6e84eae8dd1a5607d96e636c648ddaa7b14a97b`

---

## 核心任务要求

请严格对照任务合同执行：

1. **诊断卡片自适应与功能说明 (`Step4Review.vue`)**：
   - 彻底修复 `.diagnostic-card` 高度截断问题，采用 `max-height: 480px; overflow-y: auto;` 自适应排版，确保「问题清单」「数值核验表」「缺失资料清单」「综合修改建议」四个选项卡完全可见且可顺畅点击切换；
   - 卡片收起时渲染为高度 44px 的通栏胶囊卡片，具有宽大点击热区；
   - 顶部审查操作栏补充全维（全科综合）、数值（关键指标自洽）、合规（发改委与水利规程）的功能定位与使用场景提示。
2. **审阅与修订前摇动态进度心跳 (`Step4Review.vue`)**：
   - 增加审阅与修订的动态耗时计时器与 4 阶段轮播心跳提示，消除等待卡死感。
3. **Diff 对比排版规范化与双栏同步滚动 (`Step4Review.vue`, `diff.ts`)**：
   - 在传入 Diff 算法前，对原文与修订正文统一调用 `normalizeMarkdown` 规范化断行，彻底消除单行源码粘连；
   - 左右双栏采用与正文相同的 10.5pt 水利工程排版样式；
   - 实现左右双栏滚动条实时比例联动（Sync Scroll）；
   - 单栏内联模式采用段落级浅红删除线与浅绿新增背景高亮。
4. **参考资料来源清单抽屉 (`Step3Writing.vue`, `Step4Review.vue`, `markdown.ts`)**：
   - 在 Step 3 与 Step 4 右侧顶部增加「📚 本章参考资料清单 (N)」抽屉；
   - 自动提取正文中 `【源:xxx】`、`[Z]`、`【网:xxx】` 标签并列表展示。
5. **全书跨章一致性体检 (`Step4Review.vue`, `project.ts`)**：
   - 在左侧侧边栏顶部增加「🚀 全书一键综合体检」；
   - 质量看板集中展示全书章节质量达标矩阵与全书缺失资料总台账。
6. **测试与交付**：
   - 补充前端单测并执行全量验证链（vitest, pytest, vue-tsc, build, cargo check）；
   - 创建候选 commit，输出完成报告 `docs/dev-flow/tasks/V2-T15/rounds/01/maker-completion.md`。
