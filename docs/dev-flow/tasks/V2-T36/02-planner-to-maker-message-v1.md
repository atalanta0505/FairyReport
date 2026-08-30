# Planner to Maker Message — V2-T36 v1

- **任务 ID**：V2-T36
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T36/01-planner-task-contract-v1.md`)
- **精确起始 SHA**：`d67cebafb878d75384bd50eaf9375768b163a146`

---

## 交付任务

请 Maker 依据合同实现以下四大改动：

1. **移除 Diff 冗余视图与切换 Tab (`desktop/src/components/Step4Review.vue`)**：
   - 彻底移除 `viewMode === 'diff'` 模式以及 `[ 📝 最终排版正文 | 🔍 修订差异对比 ]` Tab；
   - 移除所有 Diff 相关的 DOM / CSS 代码，页面保持单一出版级排版正文。

2. **外科手术式局部精准修订（Targeted Patching）**：
   - 在右侧诊断抽屉的每张问题卡片上增加 `[ ⚡ 修复此项 ]`（或局部修复按钮）；
   - 根据问题 quote / snippet / location 仅提取对应段落，请求后端仅重构该段落并原位替换；
   - 顶部 `[ ⚡ AI 智能修订 ]` 升级为全章批量段落级精准修补；
   - 增加版本快照与 `[ ↩️ 撤销修改 (恢复上版) ]` 按钮。

3. **修订后自动清除问题与黄标高亮**：
   - 局部/全章修订完成后，自动将已修复项移出 `chapterReviews[seq].issues` 并同步持久化；
   - 正文中对应黄色高亮背景立即消失，顶部问题数清零/递减。

4. **左侧导航栏按审阅状态规范打标**：
   - 呈现 `已审阅 ✓`（绿）/ `待修改 (N)`（橙）/ `待审阅`（灰蓝）/ `待撰写`（暗灰）/ `审阅中…`（动画）；
   - 与顶栏计数完全对齐。

5. **门禁验证**：
   - 跑通 Vitest、vue-tsc、build、Pytest、cargo check。
