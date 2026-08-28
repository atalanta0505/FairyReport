# 任务合同 V2-T26 v1 — 未写作章节在导航与正文中的明确“待撰写 / 未生成”占位与排版呈现

- 状态：ACCEPTED（已由独立 Checker Agent 验收通过并锁定）
- 依据：用户关于“没有写作的章，将章标题列出，不然用户会以为是当前章没有完成写作”的明确指令，逐个攻坚问题 3
- 精确起始 SHA：`6e3a588529e397859c681c364b23de33d49f7b7d`
- 候选提交 SHA：`f63cc3138ee16ce6021d2a64935eaf30444e2f41`
- 验收报告：`docs/dev-flow/tasks/V2-T26/rounds/01/checker-report.md`（PASS）
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **左侧导航栏未编写章节明确状态指示 (`desktop/src/components/Step4Review.vue`)**：
   - 增加未编写章节判定（`!projectStore.chapters[ch.seq] || !projectStore.chapters[ch.seq].trim()`）；
   - 在左侧目录树节点旁渲染显式 `[待撰写]` 灰色状态胶囊（`.badge-unwritten`）；
   - 顶栏元数据栏展示 `待撰写 K 章`；

2. **右侧主画布未编写章节结构化列出与占位引导 (`desktop/src/components/Step4Review.vue`)**：
   - 保留未编写章节的标准章标题栏，明确展示 `第 X 章` 与完整章标题，字数标签标注 `待撰写 · 0字`；
   - 在正文排版区域呈现出版级占位引导卡片：
     `📝 第 X 章《[章标题]》待撰写：本章节大纲已就绪，当前尚未生成正文。您可直接在此处点击输入排版正文，或返回【步骤 3 报告写作】执行 AI 自动撰写。`
   - 保持 contenteditable 就地编辑与自动落盘能力。

3. **单测覆盖与 5 项全量门禁**：
   - 确保 `pytest`、`vitest`、`vue-tsc`、`npm run build`、`cargo check` 100% 通过。

---

## 2. 允许修改

- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T26/**`

---

## 3. 禁止修改

- `backend/**`、根目录核心资产、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [x] Step 4 左侧导航栏中，未写作的章节旁显示明确的 `[待撰写]` 状态指示；
- [x] Step 4 右侧画布中，未写作的章节清晰列出章序号与章标题，并呈现优雅的待撰写占位引导卡片；
- [x] 用户可在待撰写章节卡片内直接点击输入正文并实时保存；
- [x] 5 项全量门禁全部绿灯通过。

---

## 5. 快速验证顺序

1. `npx vitest run`（`desktop/`）
2. `npx vue-tsc --noEmit`（`desktop/`）
3. `npm run build`（`desktop/`）
4. `python -m pytest engine/tests -q`
5. `cargo check`（`desktop/src-tauri/`）
