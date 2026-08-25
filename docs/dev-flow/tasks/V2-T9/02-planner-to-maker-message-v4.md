# 致 Maker 转发消息 — V2-T9 第 4 轮（导航流转加固）

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`87393b4bf282f6e91129b0a7c6f0590a7ba609f1`
- 有效合同：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v4.md`

## 唯一主要行为

实现向导步骤 `currentStep` 的 `sessionStorage` 状态持久化、在 `Home.vue` 中接入 `<KeepAlive>` 缓存各步骤组件、切换步骤时自动重置视口滚动条至顶部，彻底解决点击进入 Step 2 后可能发生的自动跳回或热刷新重置问题。

## 实现导航

1. `desktop/src/stores/project.ts`：
   - `const initialStep = Number(sessionStorage.getItem("frl_current_step")) || 1;`
   - `const currentStep = ref<number>(initialStep >= 1 && initialStep <= 5 ? initialStep : 1);`
   - `setStep(step)` 时同步写入 `sessionStorage.setItem("frl_current_step", String(step))`。
2. `desktop/src/views/Home.vue`：
   - 使用 `<KeepAlive>` 缓存步骤组件；
   - 监听 `projectStore.currentStep`，在切换时通过 `nextTick` 将 `.main-content` 的 `scrollTop` 重置为 `0`；
   - 确保顶部导航栏点击切换与底部流转按钮无缝配合。
3. `desktop/src/tests/project.test.ts`：更新单测，测试 `sessionStorage` 步骤保持与恢复逻辑。
4. 重建 `desktop/dist/**`。

## 允许修改

- `desktop/src/stores/project.ts`
- `desktop/src/views/Home.vue`
- `desktop/src/components/Step2Outline.vue`
- `desktop/src/components/Step1Project.vue`
- `desktop/src/tests/project.test.ts`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T9/**`

## 禁止修改

- `engine/**`、`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

## 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `npx vue-tsc --noEmit`（workdir=`desktop`）
3. `npm run build`（workdir=`desktop`）
4. `python -m pytest engine/tests -q`

## 完成时

1. 只提交允许范围（`desktop/**` 候选提交）；
2. 完成说明写到 `docs/dev-flow/tasks/V2-T9/rounds/04/maker-completion.md`，单独提交；
3. 不 amend、不 rebase、不 push；
4. 冻结工作树交回。
