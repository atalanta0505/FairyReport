# 任务合同 V2-T9 v4 — 导航流转加固：步骤状态持久化与 KeepAlive 缓存（防止自动跳回 Step 1）

- 状态：READY_FOR_MAKER（2026-08-25 产品负责人反馈点击进入大纲页面后自动跳回前一页）
- 依据：用户实操反馈与多步向导状态保持需求
- 精确起始 SHA：`87393b4bf282f6e91129b0a7c6f0590a7ba609f1`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

根治向导流转中可能出现的自动跳回/页面重置问题：
1. **步骤状态 sessionStorage 持久化 (`desktop/src/stores/project.ts`)**：
   - 将 `currentStep` 绑定到 `sessionStorage`（初始化时优先从 `sessionStorage.getItem("frl_current_step")` 读取，`setStep` 时同步写入）。
   - 防止开发环境下 Vite HMR 或微刷新导致内存中的 `currentStep` 瞬间重置回 1。
2. **向导组件 KeepAlive 缓存与视口重置 (`desktop/src/views/Home.vue`)**：
   - 使用 `<KeepAlive>` 缓存 `Step1Project` 与 `Step2Outline`，避免步骤切换时组件频繁销毁与重复触发 `onMounted` 异步拉取；
   - 监听 `currentStep` 变化，切换步骤时自动平滑重置 `.main-content` 滚动条至顶部（`scrollTop = 0`），防止上一页底部的点击事件误触发下一页底部的「上一步」按钮。
3. **大纲生成与模板交互加固 (`desktop/src/components/Step2Outline.vue`)**：
   - 增加防抖与状态保护，确保模板切换与大纲生成时向导步骤严格锁定。

---

## 2. 允许修改

- `desktop/src/stores/project.ts`
- `desktop/src/views/Home.vue`
- `desktop/src/components/Step2Outline.vue`
- `desktop/src/components/Step1Project.vue`
- `desktop/src/tests/project.test.ts`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T9/**`

---

## 3. 禁止修改

- `engine/**`、`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿。
- [ ] `npx vitest run`（`desktop/`）全绿（覆盖 sessionStorage 与步骤保持单测）。
- [ ] `cargo check`、`npx vue-tsc --noEmit`、`npm run build` 全绿。
- [ ] B 级实跑：点击「下一步：模板与大纲 →」平滑切入 Step 2，视口自动置顶，状态稳定驻留不跳回，支持顺畅点击「AI 智能生成大纲」与编辑。

---

## 5. 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `npx vue-tsc --noEmit`（workdir=`desktop`）
3. `npm run build`（workdir=`desktop`）
4. `python -m pytest engine/tests -q`
