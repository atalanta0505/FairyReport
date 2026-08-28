# 任务合同 V2-T25 v1 — 彻底隐藏 Diff 视图顶部的“修改指令”文本块，只呈现纯粹清晰的正文段落级 Diff

- 状态：ACCEPTED（已由独立 Checker Agent 验收通过并锁定）
- 依据：用户关于“这个修订指令完全不用展示。修订diff做得挺好”的明确指令，逐个攻坚问题 2
- 精确起始 SHA：`65fec6cf1d5191a393dbb058b85c6b19066003a1`
- 候选提交 SHA：`8e6b61bacf3e289d55ad6bd1b51835c6df3d732e`
- 验收报告：`docs/dev-flow/tasks/V2-T25/rounds/01/checker-report.md`（PASS）
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **彻底移除 Diff 视图常驻操作栏中的“修改指令”文本块 (`desktop/src/components/Step4Review.vue`)**：
   - 彻底删除 `<div v-if="projectStore.activeRevision" class="diff-instruction-summary"><strong>修改指令：</strong>{{ projectStore.activeRevision.instruction }}</div>` DOM 节点；
   - 彻底清理 `.diff-instruction-summary` 对应的 CSS 样式规则；
   - 保证 `diff-sticky-header` 呈现单行紧凑高雅布局：左侧标题与章节徽标、中间三色行数统计、右侧采纳/重新生成/放弃三操作按钮，正文 Diff 画布垂直可视空间扩大。

2. **单测覆盖与 5 项全量门禁**：
   - 确保 `pytest`、`vitest`、`vue-tsc`、`npm run build`、`cargo check` 100% 通过。

---

## 2. 允许修改

- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T25/**`

---

## 3. 禁止修改

- `backend/**`、根目录核心资产、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [x] Step 4 进入 Diff 差异对比视图后，顶部常驻栏不再出现“修改指令：...”大段文本；
- [x] Diff 顶部栏布局紧凑美观，新增/删除/未修改统计与采纳/重新生成/放弃功能完好；
- [x] 5 项全量门禁全部绿灯通过。

---

## 5. 快速验证顺序

1. `npx vitest run`（`desktop/`）
2. `npx vue-tsc --noEmit`（`desktop/`）
3. `npm run build`（`desktop/`）
4. `python -m pytest engine/tests -q`
5. `cargo check`（`desktop/src-tauri/`）
