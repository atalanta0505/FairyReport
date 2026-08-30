# 任务合同 V2-T36 v1 — Step 4 审阅与修改体验全面升级：移除 Diff 冗余视图、外科手术式局部精准修订、修订后清除问题高亮、左侧导航按审阅状态规范打标

- **状态**：READY_FOR_MAKER
- **依据**：产品负责人（Fairy）关于“移除 Diff 冗余视图与长时间等待、转向针对问题段落的外科手术式局部精准修订、修订采纳后自动清除问题高亮黄标、左侧导航栏按审阅状态规范打标（已审阅/待修改/待审阅）”的明确产品定案
- **精确起始 SHA**：`d67cebafb878d75384bd50eaf9375768b163a146`
- **工作树门禁**：`git status --short` 必须干净（用户新增教材作为只读资料保留在工作区）

---

## 1. 唯一主要变化

1. **移除 Diff 冗余视图与切换 Tab (`desktop/src/components/Step4Review.vue`)**：
   - 彻底移除 `viewMode` 中的 `'diff'` 模式以及头部切换 Tab（`[ 📝 最终排版正文 | 🔍 修订差异对比 ]`）；
   - 彻底移除 `<div class="canvas-diff-view">` 及所有全宽红绿代码行对比 DOM 和 CSS；
   - 页面始终保持在纯粹、沉浸的【出版级排版正文】。

2. **外科手术式局部精准修订（Targeted Patching）(`desktop/src/components/Step4Review.vue`、`desktop/src/stores/project.ts`、`engine/app/writing/`)**：
   - **单条问题精准局部修复**：
     - 在右侧诊断抽屉各问题卡片上增加 `[ ⚡ 修复此项 ]` 按钮；
     - 仅提取问题所在定位的 1~2 个段落（约 100~200 字）与专家修改建议，调用 LLM 局部重构（耗时 1~2 秒）；
     - 生成后原位替换正文对应段落，95% 以上无缺陷段落绝对保持原样，零副作用；
   - **全章批量外科手术修补**：
     - 顶部 `[ ⚡ AI 智能修订 ]` 升级为对本章清单中的问题段落执行批量局部修补与原位替换，几秒内全章修复完毕；
   - **版本撤销保障**：
     - 修订完成后在顶栏提供 `[ ↩️ 撤销修改 (恢复上版) ]` 按钮，支持一键安全回滚。

3. **修订后自动清除问题清单与正文黄标高亮 (`desktop/src/components/Step4Review.vue`、`desktop/src/stores/project.ts`)**：
   - 单条问题修复后：自动将该问题从本章问题清单（`chapterReviews[seq].issues`）中移除，正文中的黄色高亮背景立即消失，待修计数递减；
   - 全章智能修订后：自动清空本章待修问题清单并同步更新持久化，正文黄色警告高亮彻底清除，顶部建议数清零，保留 `[ 🔍 审阅本章 ]` 供用户随时重新体检。

4. **左侧导航栏按审阅状态规范打标 (`desktop/src/components/Step4Review.vue`)**：
   - 纠正直接复用写作状态（“已完成 ✓”）的逻辑，切换为审阅生命周期状态：
     - `已审阅 ✓`（绿色）：已执行过专家审阅，且无待修建议（或已全部修复）；
     - `待修改 (N)`（橙黄色）：已执行过专家审阅，但存在 N 处待修建议；
     - `待审阅`（灰蓝色）：章节正文已撰写，但尚未点击审阅；
     - `待撰写`（暗灰色）：章节正文为空；
     - `审阅中…`（加载动画）：当前章节正在执行审阅。
   - 与顶栏 `已审阅 X / Y` 统计严格对齐。

5. **单测覆盖与 5 项全量门禁**：
   - 补充/更新相关单测；
   - 依次通过 5 项验证流水线（Vitest, vue-tsc, build, Pytest, cargo check）。

---

## 2. 允许修改

- `desktop/src/components/Step4Review.vue`
- `desktop/src/stores/project.ts`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/tests/**`
- `engine/app/writing/router.py`
- `engine/app/writing/writer.py`
- `engine/tests/**`
- `docs/dev-flow/tasks/V2-T36/**`

---

## 3. 禁止修改

- `AGENTS.md`、`.gitignore`
- `generic_knowledge/` 下的用户新增教材文件

---

## 4. 验收标准

- [ ] 彻底移除 Step 4 的 Diff 切换 Tab 与红绿代码对比视图，主视口始终保持出版级排版正文；
- [ ] 诊断抽屉提供单条问题 `[ ⚡ 修复此项 ]` 功能，1~2 秒内精准局部替换目标段落；
- [ ] 顶部 `[ ⚡ AI 智能修订 ]` 升级为全章批量外科手术式修补，快速完成且不篡改无问题段落；
- [ ] 修订完成后自动清除对应问题和正文黄色高亮背景，顶栏待修数正确清零/递减；
- [ ] 修订完成后提供 `[ ↩️ 撤销修改 ]` 按钮，点击可一键回滚恢复；
- [ ] 左侧导航栏状态徽标准确呈现 `已审阅 ✓` / `待修改 (N)` / `待审阅` / `待撰写` / `审阅中…`；
- [ ] 5 项全量门禁（Pytest、Vitest、vue-tsc、build、cargo check）全部绿灯通过。

---

## 5. 快速验证顺序

1. `npx vitest run`（`desktop/`）
2. `npx vue-tsc --noEmit`（`desktop/`）
3. `npm run build`（`desktop/`）
4. `python -m pytest engine/tests -q`
5. `cargo check`（`desktop/src-tauri/`）
