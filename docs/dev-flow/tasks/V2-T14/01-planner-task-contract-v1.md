# 任务合同 V2-T14 v1 — Step 4 专家审阅与修改系统（合规检查、数值校验、专家批注与修改对比）

- 状态：READY_FOR_MAKER（2026-08-26 产品负责人批准 V2-T14 实施方案）
- 依据：产品负责人指令：“推进下一步‘专家审阅与修改（合规检查、数值校验、专家批注与修改对比）的开发’”
- 精确起始 SHA：`fcefc0b58c43ce33ab4c0dbb173caf819bc429e1`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **引擎后端审阅与修订接口增强 (`engine/app/writing/`)**：
   - `prompts.py`：新增/丰富合规审查、数值核验、全维专家诊断提示词，加固修订提示词；
   - `writer.py`：实现 `expert_review_chapter(chapter_title, chapter_text, report_type, review_mode="all", ...)`，实现通用的 `parse_expert_review_result`，支持结构化解析判定结论、评分、问题清单、数值核验表、修改建议与缺失资料清单；
   - `router.py`：
     - `POST /writing/review` 支持 `mode: "all" | "compliance" | "numeric" | "technical"` 并返回结构化审查诊断结果；
     - `POST /writing/revise` 支持针对指令和批注进行精准修订并返回修订文本；
     - 增加 `GET /projects/{name}/reviews` 与 `POST /projects/{name}/reviews/{seq}` 审阅结果持久化接口（落盘至 `reviews.json`）。
   - `engine/tests/test_writing_review.py`：新增审阅与修订完整单元测试。
2. **桌面端 Diff 差异比较与 API 客户端 (`desktop/src/`)**：
   - `desktop/src/lib/diff.ts`：实现行级/词级轻量 Diff 计算工具，支持增删改标记输出；
   - `desktop/src/tests/diff.test.ts`：Diff 算法单测；
   - `desktop/src/lib/engineApi.ts`：定义 `ExpertReviewResult` 与 `ReviewIssue` 等类型，提供 `reviewChapter`、`reviseChapter`、`getProjectReviews`、`saveProjectReview` 方法。
3. **桌面端 Store 状态流转 (`desktop/src/stores/project.ts`)**：
   - 维护 `chapterReviews: ref<Record<number, ExpertReviewResult>>({})` 与 `activeRevision: ref<{ seq: number; originalText: string; revisedText: string; instruction: string } | null>`；
   - 提供 `loadReviews`、`saveReview`、`runChapterReview`、`runChapterRevision`、`applyRevision`、`discardRevision` 等方法，并与项目生命周期联动。
4. **新建 Step 4 审阅修改组件 (`desktop/src/components/Step4Review.vue`)**：
   - **左侧章节与评审导航**：
     - 全书质量看板（已审阅数、达标率）；
     - 三大视图切换：`[ 📋 章节精审 ]` / `[ 📄 全书预览 ]` / `[ 📊 质量看板 ]`；
     - 章节列表：字数预算比例徽标与审阅状态徽标（`未审阅` / `⚠️ 待修正 (N)` / `✅ 已通过`）；
   - **右侧主工作台**：
     - 顶部操作栏：`[ 🔍 全维专家审阅 ]`、`[ 📏 数值校验 ]`、`[ ⚖️ 合规审查 ]`、`[ 🔧 AI 定向修订 ]`、`[ 💾 保存 ]`；
     - **可折叠专家诊断卡片**：展示结论徽标、评分、问题点详情、关键数值核验表、缺失资料清单（支持一键将建议填入修订意图）；
     - **Diff 对比工作台**（修订模式）：红绿双栏/内联高亮差异对比，提供 `[ ✅ 采纳修订 ]`、`[ 🔄 重新生成 ]`、`[ ↩ 放弃 ]`；
     - **排版就地编辑器**（常规模式）：10.5pt 就地富文本编辑与防抖自动落盘；
     - **全书连贯预览模式**：无缝拼接全书排版正文与大纲导航；
     - **全局质量看板模式**：图表/表格呈现字数分布与审阅健康度；
   - **底部向导流转**：
     - `← 上一步：章节写作`
     - `下一步：成果导出 →`。
5. **集成至主向导 (`desktop/src/views/Home.vue`)**：
   - 引入 `Step4Review` 替换原来的 Step 4 占位卡片：`<Step4Review v-show="projectStore.currentStep === 4" />`。
6. **单元测试与产物**：
   - 更新 `desktop/src/tests/project.test.ts`；
   - 重建 `desktop/dist/**`。

---

## 2. 允许修改

- `engine/app/writing/prompts.py`
- `engine/app/writing/writer.py`
- `engine/app/writing/router.py`
- `engine/tests/test_writing_review.py`
- `desktop/src/lib/diff.ts`
- `desktop/src/tests/diff.test.ts`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/stores/project.ts`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/views/Home.vue`
- `desktop/src/tests/project.test.ts`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T14/**`

---

## 3. 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿。
- [ ] `npx vitest run`（`desktop/`）全绿。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：
  1. 点击单章「全维专家审阅」/「数值校验」能生成结构化诊断报告与数值核查表；
  2. 点击「AI 定向修订」能生成修改并进入 Diff 对比视图，支持「采纳修订」与「放弃」；
  3. 切换「全书预览」与「质量看板」能正常展示全文与字数分布；
  4. 支持进入下一步 Step 5。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
5. `cargo check`（workdir=`desktop/src-tauri`）
