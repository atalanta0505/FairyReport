# 任务合同 V2-T9 v6 — 窄修复：向导组件改用稳健 v-show 架构（根除空白屏与 KeepAlive 运行时异常）

- 状态：ACCEPTED（第 6 轮 PASS；锁定候选 d5101078662b3bb193df98eb21423bd602782ffe）
- 依据：用户截图反馈主窗口空白，排查确认为 KeepAlive 动态组件在 Vite/Vue 3 渲染阶段异常导致的挂载中断
- 精确起始 SHA：`3964f808f9723ec083b9e4a3d758d4a65c40134b`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

根治白屏问题，将向导组件渲染模式重构为最稳健的 `v-show` 模式：
- **根因**：`<KeepAlive>` 在包裹包含 `null` 分支的动态组件 `<component :is="activeStepComp" />` 时，在某些状态下触发 Vue 3 内部 `subTree` 渲染异常抛错，导致整个 Vue 根实例挂载中断，页面呈现白屏。
- **解决方案**：
  1. 废弃脆弱的 `<KeepAlive>` 与动态组件 `activeStepComp` 机制；
  2. 采用 Vue 原生 `v-show` 架构：
     ```vue
     <Step1Project v-show="projectStore.currentStep === 1" />
     <Step2Outline v-show="projectStore.currentStep === 2" />
     <div v-show="projectStore.currentStep === 3" class="step-placeholder">...</div>
     <div v-show="projectStore.currentStep === 4" class="step-placeholder">...</div>
     <div v-show="projectStore.currentStep === 5" class="step-placeholder">...</div>
     ```
  3. `v-show` 保证所有步骤组件始终驻留在 DOM 中，既天然保持了已填写大纲、模板选择及表单状态（无任何组件销毁与重建），又拥有 100% 的渲染稳定性与极速 CSS 切换性能。

---

## 2. 允许修改

- `desktop/src/views/Home.vue`
- `desktop/src/components/Step2Outline.vue`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T9/**`

---

## 3. 禁止修改

- `engine/**`、`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `npx vue-tsc --noEmit`（`desktop/`）全绿。
- [ ] `npm run build`（`desktop/`）全绿。
- [ ] `npx vitest run`（`desktop/`）全绿。
- [ ] B 级实跑：启动客户端即刻正常呈现完整的顶部导航、项目与资料列表界面，无任何白屏；点击「下一步：模板与大纲 →」瞬间切换至 Step 2 并保持全部状态。

---

## 5. 快速验证顺序

1. `npx vue-tsc --noEmit`（workdir=`desktop`）
2. `npm run build`（workdir=`desktop`）
3. `npx vitest run`（workdir=`desktop`）
