# Maker Completed Instructions — V2-T36 v1

- **任务 ID**：V2-T36
- **完成时间**：2026-08-30
- **工作区状态**：干净（除用户新增教材未跟踪外）

---

## 1. 交付改动概要

1. **移除 Diff 冗余视图与 Tab (`desktop/src/components/Step4Review.vue`)**：
   - 彻底移除了 `viewMode` 模式切换及顶栏 `[ 📝 最终排版正文 | 🔍 修订差异对比 ]` Tab；
   - 彻底移除了 `<div class="canvas-diff-view">` 及全宽红绿代码对比 DOM 与样式；
   - 页面始终保持在单一、沉浸、纯粹的【出版级排版正文】。

2. **外科手术式局部精准修补（Targeted Patching）**：
   - **后端能力**：
     - `engine/app/writing/writer.py`：新增 `modify_paragraph` 方法，毫秒级响应、零副作用针对单一/局部段落进行深度重构；
     - `engine/app/writing/router.py`：新增 `POST /writing/revise-paragraph` 端点；
   - **前端集成**：
     - `desktop/src/lib/engineApi.ts`：新增 `reviseParagraph` 接口调用；
     - `desktop/src/stores/project.ts`：新增 `runParagraphRevision` 与 `undoChapterRevision`，支持针对问题 quote/snippet 提取目标段落并原位替换；
     - `desktop/src/components/Step4Review.vue`：
       - 右侧诊断抽屉的每张问题卡片上新增 `[ ⚡ 局部修复 ]` 按钮，点击后 1~2 秒内精准修补该段落；
       - 顶部 `[ ⚡ AI 智能修订 ]` 升级为全章问题段落外科手术式批量修补；
       - 顶部新增 `[ ↩️ 撤销修改 ]` 按钮，支持一键安全回滚至上一快照版本。

3. **修订后自动清除问题与黄标高亮**：
   - 单条问题修复后：自动从 `chapterReviews[seq].issues` 中移除该项并持久化，正文中该处黄色高亮背景立即消失，顶部问题数递减；
   - 全章批量修订后：清空该章待修问题清单，正文中黄色警告高亮彻底清除，恢复干净排版，顶部建议数清零，保留 `[ 🔍 审阅本章 ]` 供随时复检。

4. **左侧导航栏按审阅状态规范打标**：
   - 升级章节状态徽标为审阅生命周期状态：
     - `已审阅 ✓`（绿）
     - `待修改 (N)`（橙黄）
     - `待审阅`（灰蓝）
     - `待撰写`（暗灰）
     - `审阅中…`（动画）
   - 与顶栏统计严格对齐。

5. **单测覆盖与 5 项门禁全部通过**：
   - Vitest：174/174 passed
   - vue-tsc：0 error
   - npm run build：Built in 878ms
   - Pytest：130/130 passed
   - cargo check：Finished dev profile
