# 任务合同 V2-T24 v1 — 彻底移除全书审阅耗时预估弹窗与虚假预估耗时，改为顶栏一键直启审阅，清理残留水利文案

- 状态：READY_FOR_MAKER（已获产品负责人批准）
- 依据：用户关于“这个审阅时间悬浮窗口也不要了。相应的时间预计也不用报了，因为报的预计和事实出入太大”的明确指令，逐个攻坚问题 1
- 精确起始 SHA：`9c17a3ef9c1aac8cbd54e7410c487bf385752b72`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **彻底移除全书审阅耗时预估弹窗 (`desktop/src/components/Step4Review.vue`)**：
   - 彻底删除 `showEstimateModal` 响应式变量及其对应的模态遮罩 DOM（`<div v-if="showEstimateModal" class="estimate-modal-overlay">...</div>`）；
   - 彻底清理对应的 CSS 样式（`.estimate-modal-overlay`, `.estimate-modal-card`, `.estimate-preview-grid` 等）；
   - 彻底删除静态估算算法与相关逻辑（`estimatedMinutes`, `estimatedSeconds` 等）；

2. **顶栏一键直启审阅与真实计时反馈 (`desktop/src/components/Step4Review.vue`)**：
   - 在顶部操作区保留清晰直观的审查模式切换胶囊（`[ ⚡ 常规审查 (推荐) ]` 与 `[ 🔍 全维精审 ]`）；
   - 点击 `[ 🚀 运行全书审阅 ]` 时，无需任何中间弹窗确认，直接以当前选定模式立即启动全书审阅；
   - 审阅进行中时，顶部动态看板仅展示**真实已耗时**（`已耗时 N 秒`）、当前章节进度（`第 X/Y 章`）及实时发现的问题统计，杜绝虚假预估；

3. **清理残留“水利”文案 (`desktop/**`, `engine/**`)**：
   - 全局排查并替换所有残余的“水利”占位文字，统一规范为“国家发改委投资项目与工程咨询专业论证水准”。

4. **单测覆盖与 5 项全量门禁**：
   - 确保 `pytest`、`vitest`、`vue-tsc`、`npm run build`、`cargo check` 100% 通过。

---

## 2. 允许修改

- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `engine/app/writing/prompts.py`
- `docs/dev-flow/tasks/V2-T24/**`

---

## 3. 禁止修改

- `backend/**`、根目录核心资产、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] Step 4 页面点击“运行全书审阅”不再弹出任何模态悬浮窗，直接启动审阅；
- [ ] 界面上不再出现静态虚假预估耗时，仅展示真实累积秒数；
- [ ] 界面与提示词中不再出现残留的“水利”字样；
- [ ] 5 项全量门禁全部绿灯通过。

---

## 5. 快速验证顺序

1. `npx vitest run`（`desktop/`）
2. `npx vue-tsc --noEmit`（`desktop/`）
3. `npm run build`（`desktop/`）
4. `python -m pytest engine/tests -q`
5. `cargo check`（`desktop/src-tauri/`）
