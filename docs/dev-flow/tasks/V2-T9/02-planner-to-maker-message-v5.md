# 致 Maker 转发消息 — V2-T9 第 5 轮（KeepAlive 语法合规窄修复）

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`14d3040c1110034a781b0a82ec4581cbb47c5035`
- 有效合同：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v5.md`

## 唯一主要行为

在 `desktop/src/views/Home.vue` 中重构 `<KeepAlive>` 的使用方式，使用 Vue 3 官方推荐的标准 `<KeepAlive><component :is="activeStepComp" v-if="activeStepComp" /></KeepAlive>`，将占位 `div` 移至外层，消除 Vite Vue 编译器的 `<KeepAlive> expects exactly one child component.` 报错。

## 实现导航

1. `desktop/src/views/Home.vue`：
   - 引入 `computed`，定义：
     ```ts
     const activeStepComp = computed(() => {
       if (projectStore.currentStep === 1) return Step1Project;
       if (projectStore.currentStep === 2) return Step2Outline;
       return null;
     });
     ```
   - 模板重构为：
     ```vue
     <div v-if="view === 'wizard'" class="wizard-content">
       <KeepAlive>
         <component :is="activeStepComp" v-if="activeStepComp" />
       </KeepAlive>

       <!-- 步骤 3：章节写作（占位） -->
       <div v-if="projectStore.currentStep === 3" class="step-placeholder">
         ...
       </div>
       <!-- 步骤 4：审阅修改（占位） -->
       <div v-else-if="projectStore.currentStep === 4" class="step-placeholder">
         ...
       </div>
       <!-- 步骤 5：成果导出（占位） -->
       <div v-else-if="projectStore.currentStep === 5" class="step-placeholder">
         ...
       </div>
     </div>
     ```
2. 重建 `desktop/dist/**`。
3. 快速验证并交付。

## 允许修改

- `desktop/src/views/Home.vue`
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
2. 完成说明写到 `docs/dev-flow/tasks/V2-T9/rounds/05/maker-completion.md`，单独提交；
3. 不 amend、不 rebase、不 push；
4. 冻结工作树交回。
