# Planner 至 Maker 派发消息：任务 V2-T33 第 1 轮

- 目标任务：V2-T33（Mermaid 专业工程流程图与拓扑图渲染优化）
- 依据合同：`docs/dev-flow/tasks/V2-T33/01-planner-task-contract-v1.md`
- 精确起始 SHA：`5fbbe7a7bf7fcba1fa5749f7baaa7e6e5898d9e2`

---

## 核心任务要点

1. **新建 `desktop/src/lib/mermaid.ts` 渲染引擎**：
   - 0 外部依赖原生 TypeScript 实现；
   - 支持 `graph TD` / `graph LR` / `subgraph` / 多种节点形状 / 带文本连线；
   - 动态计算布局并生成 SVG 矢量图；
   - 支持顶部工具栏（切换源码/视图、复制代码、全屏放大）与语法容错降级；
2. **`desktop/src/lib/markdown.ts` 与 Vue 画布适配**：
   - `markdownToHtml` 遇到 ```` ```mermaid ```` 时调用渲染器输出富交互流程图卡片；
   - `htmlToMarkdown` 无损反向序列化；
   - `Step3Writing.vue` 与 `Step4Review.vue` 样式与交互支持；
3. **Word 导出端流程图转换 (`engine/app/export/docx_builder.py`, `exporter.py`)**：
   - 将 Mermaid 流程图转换为标准三线【工艺/工程流程步骤与拓扑关系对照表】；
4. **单测覆盖与 5 项全量门禁**：
   - 新建 `desktop/src/tests/mermaid.test.ts`；
   - 更新 `engine/tests/test_export.py`；
   - 运行 5 项全量门禁并交付候选提交 SHA。
