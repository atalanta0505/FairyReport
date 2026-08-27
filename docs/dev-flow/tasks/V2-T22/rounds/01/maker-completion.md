# 任务完工报告：V2-T22 第 1 轮

- 状态：COMPLETED
- 有效合同：`docs/dev-flow/tasks/V2-T22/01-planner-task-contract-v1.md`
- 派发消息：`docs/dev-flow/tasks/V2-T22/02-planner-to-maker-message-v1.md`
- 精确起始 SHA：`1dd22a3e9c6efc196f7c4db3fa0592e35182103f`
- 候选提交 SHA：`e82e32d57e96fa4641198cfe018f6c90c63437e3`

---

## 1. 变更范围与实现摘要

1. **Step 3 侧边栏布局与自适应垂直滚动修复 (`desktop/src/components/Step3Writing.vue`)**：
   - 修复 `.sidebar-panel`：设置 `height: calc(100vh - 165px); min-height: 0; display: flex; flex-direction: column; overflow: hidden;`；
   - 修复 `.outline-tree-scrollable`：设置 `flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden; scrollbar-width: thin;`；
   - 修复 `.chapter-tree-node`：设置 `flex-shrink: 0; min-height: 38px;`，彻底消除 flex 压缩坍塌；
   - 优化 `.chapter-node-row`：设置 `padding: 8px 8px;`；
   - 优化 `.ch-title-text`：设置 `line-height: 1.35; font-size: 12.5px; white-space: normal; word-break: break-word;`；
   - 确保当有 11~20+ 章节时，章节节点从上到下完整排布，文字底部 100% 完整显示无截断，自适应全局垂直滚动条流畅可用。

2. **全书审阅思维推演纯中文与极速约束 (`engine/app/writing/prompts.py`, `writer.py`)**：
   - 强化 `FAST_REVIEW_SYSTEM_PROMPT` 与 `FULL_EXPERT_REVIEW_SYSTEM_PROMPT`：
     - 注入【思考链语言与长度铁律】：内部构思与推理推演过程必须 100% 使用纯中文进行水利与工程咨询专业论证，严禁夹杂任何英文思考句或英文单词（除 GB/T、ISO 等法定国家标准代码与标准工程单位外）；
     - 注入【极速常规审查约束】：思考推演链必须控制在 300~500 字符（约 5~8 秒内完成），直接聚焦专有名词、核心数值自洽与底线合规，严禁冗长发散与长篇复述；
   - 在 `ChapterWriter._build_expert_review_args` 用户 Prompt 结尾注入：`【思考链语言与长度约束】：内部推演过程必须 100% 使用纯中文，严禁英文！常规审查思考过程保持极速精炼（300-500字），快速输出 JSON 诊断结果。`

3. **AI 修订去除悬浮遮罩弹窗，实现直接就地修订与内联 Diff (`desktop/src/components/Step4Review.vue`)**：
   - 彻底移除 `showRevisionModal` 遮罩模态弹窗及其相关 DOM 节点与冗余逻辑；
   - 在 Step 4 顶栏提供 `[ ⚡ AI 一键智能修订 ]`，在「📋 专家诊断报告」抽屉各问题条目及抽屉顶部提供 `[ ⚡ 代入本章建议并一键修订 ]`；
   - 点击后直接收集本章当前诊断建议（或默认全维综合建议）作为指令，触发 `projectStore.runChapterRevision`；
   - 在画布顶部展示轻量内联心跳进度条（`AI 智能修订重构中...`），修订完成后**自动将 `viewMode` 切换至 `diff`（全宽单栏内联 Diff 模式）**；
   - 用户在内联 Diff 模式下可直观查看红删绿增，并可点击 `[ ✅ 采纳全部修订并保存为正文 ]`、`[ 🔄 重新生成 ]` 或 `[ ↩ 放弃本次修订 ]`。

4. **Step 4 正文审阅问题持久化高亮与批注标记 (`desktop/src/components/Step4Review.vue`)**：
   - 编写 `applyIssueHighlightsToHtml(html: string, seq: number): string`：
     - 提取 `projectStore.chapterReviews[seq]?.issues || []`；
     - 采用安全标签拆分算法，对正文匹配到的 `issue.quote`（或精准关键词）包裹 `<mark class="review-issue-highlight severity-${issue.severity}" data-issue-id="${issue.id}" data-chapter-seq="${seq}" title="${issue.category}: ${issue.message}">${quote}</mark>`；
     - 添加浅黄（warning）、浅红（error/danger）底色与波浪线高亮样式；
     - 点击该高亮标记时，自动打开专家诊断报告抽屉并滚动聚焦闪烁对应 issue 卡片；
     - 在 `htmlToMarkdown` 中天然剥离 mark 标签，保证回存数据为纯净 Markdown。

5. **全书连贯预览未写作章节标准化呈现章标题 (`desktop/src/components/Step4Review.vue`)**：
   - 在全书预览模式下，每个章节容器上方渲染标准化章标题栏：`<div class="chapter-block-header"><span class="ch-badge">第 {{ ch.seq }} 章</span> <h3 class="ch-title">{{ ch.title }}</h3> <span class="ch-word-tag">{{ (projectStore.chapters[ch.seq] || '').length }} 字</span></div>`；
   - 未生成正文的章节，在标题栏下方显示清晰虚线占位提示：`本章节暂未生成内容。可在此处直接输入排版文字，或返回步骤 3 自动写作...`，杜绝用户误以为漏章或生成失败。

---

## 2. 修改文件清单

- `engine/app/writing/prompts.py`
- `engine/app/writing/writer.py`
- `engine/tests/test_writing_review.py`
- `engine/tests/test_writing_unit.py`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/markdown.test.ts`
- `desktop/src/tests/project.test.ts`
- `desktop/dist/**`

---

## 3. 门禁验证记录

按合同约定顺序依次执行 5 项快速验证：

1. **Gate 1 - Python Pytest**
   - 命令：`python -m pytest engine/tests -q`
   - 结果：`125 passed, 2 warnings in 95.98s`（PASS）

2. **Gate 2 - Vitest 单元测试**
   - 命令：`npx vitest run`（workdir=`desktop`）
   - 结果：5 个测试文件、128 个测试用例全部通过（PASS）

3. **Gate 3 - Vue 静态类型检查**
   - 命令：`npx vue-tsc --noEmit`（workdir=`desktop`）
   - 结果：0 errors（PASS）

4. **Gate 4 - 前端生产打包构建**
   - 命令：`npm run build`（workdir=`desktop`）
   - 结果：`built in 1.05s`（PASS）

5. **Gate 5 - Tauri Rust 门禁**
   - 命令：`cargo check`（workdir=`desktop/src-tauri`）
   - 结果：`Finished dev profile in 0.95s`（PASS）

---

## 4. 已知风险与冻结声明

- 遵循 PROCESS.md 规范：严禁 `git push`、严禁 `git commit --amend`、严禁 `git rebase`。
- 本轮候选提交 SHA 为 `e82e32d57e96fa4641198cfe018f6c90c63437e3`，已完成工作区冻结并提交验收。
