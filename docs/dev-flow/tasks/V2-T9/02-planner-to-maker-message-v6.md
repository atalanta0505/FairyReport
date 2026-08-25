# 致 Maker 转发消息 — V2-T9 第 6 轮（v-show 稳健重构）

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`3964f808f9723ec083b9e4a3d758d4a65c40134b`
- 有效合同：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v6.md`

## 唯一主要行为

彻底移除 `desktop/src/views/Home.vue` 中引发运行时白屏的 `<KeepAlive>` 与 `activeStepComp`，改用纯原生 `v-show` 模式渲染所有向导步骤（`Step1Project`、`Step2Outline`、各占位 `div`），在 `Step2Outline.vue` 中确保在组件挂载或切换到步骤 2 时加载模板。

## 实现导航

1. `desktop/src/views/Home.vue`：
   - 移除 `activeStepComp` 计算属性；
   - 模板重构为：
     ```vue
     <div v-if="view === 'wizard'" class="wizard-content">
       <!-- 步骤 1：项目与资料管理 -->
       <Step1Project v-show="projectStore.currentStep === 1" />

       <!-- 步骤 2：模板与大纲 -->
       <Step2Outline v-show="projectStore.currentStep === 2" />

       <!-- 步骤 3：章节写作（占位） -->
       <div v-show="projectStore.currentStep === 3" class="step-placeholder">
         ...
       </div>
       <!-- 步骤 4：审阅修改（占位） -->
       <div v-show="projectStore.currentStep === 4" class="step-placeholder">
         ...
       </div>
       <!-- 步骤 5：成果导出（占位） -->
       <div v-show="projectStore.currentStep === 5" class="step-placeholder">
         ...
       </div>
     </div>
     ```
2. `desktop/src/components/Step2Outline.vue`：
   - 移除已无用的 `onActivated`，使用 `onMounted` 与 watch `projectStore.currentStep`（当 `currentStep === 2` 时触发 `ensureTemplates()`）。
3. 重建 `desktop/dist/**`。
4. 快速验证并交付。

## 允许修改

- `desktop/src/views/Home.vue`
- `desktop/src/components/Step2Outline.vue`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T9/**`

## 禁止修改

- `engine/**`、`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

## 快速验证顺序

1. `npx vue-tsc --noEmit`（workdir=`desktop`）
2. `npm run build`（workdir=`desktop`）
3. `npx vitest run`（workdir=`desktop`）

## 完成时

1. 只提交允许范围（`desktop/**` 候选提交）；
2. 完成说明写到 `docs/dev-flow/tasks/V2-T9/rounds/06/maker-completion.md`，单独提交；
3. 不 amend、不 rebase、不 push；
4. 冻结工作树交回。
