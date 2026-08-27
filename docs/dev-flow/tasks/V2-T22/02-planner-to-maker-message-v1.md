# 协调员派发消息：任务 V2-T22 第 1 轮

## 任务目标
执行任务合同 `docs/dev-flow/tasks/V2-T22/01-planner-task-contract-v1.md` 中的全部开发与测试工作。

## 关键交付项
1. 彻底修复 Step 3 侧边栏垂直高度计算与 flexbox 坍塌问题，为 `.sidebar-panel` / `.outline-tree-scrollable` / `.chapter-tree-node` 配置正确的自适应滚动与防压缩样式；
2. 强化 `prompts.py` 与 `writer.py` 审阅提示词，绝对锁定纯中文思考推演链，并严格约束常规快速审查思考时长在 5~10 秒内；
3. 彻底移除 Step 4 AI 修订遮罩 Modal 弹窗，实现顶栏与抽屉直接一键就地修订并自动呈现单栏内联 Diff；
4. 在 Step 4 正文中对审阅 issues 命中的语句/关键词进行持久化高亮底色与波浪线标注；
5. 在 Step 4 全书预览中为所有章节标准化渲染章标题栏（未写章节清晰呈现标题与待写提示）；
6. 运行并通过 5 项门禁。
