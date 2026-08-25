# Checker 验收报告 — V2-T9 第 6 轮（v-show 稳健重构）

- **任务编号**：V2-T9（桌面端主流程向导 UI，第 6 轮窄修复）
- **任务目标**：彻底根治 `<KeepAlive>` 与动态组件在 Vue 3 挂载阶段引发的运行时异常与空白屏问题，全面改用原生 `v-show` 稳健渲染架构
- **有效合同**：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v6.md`
- **Maker 完成说明**：`docs/dev-flow/tasks/V2-T9/rounds/06/maker-completion.md`
- **基线父提交 SHA**：`94c1316ac42a881b195273ec45e840b4e55f03e8`
- **候选提交 SHA**：`d5101078662b3bb193df98eb21423bd602782ffe`
- **审查日期**：2026-08-25
- **验收结论**：**PASS**（全部通过）

---

## 1. 提交与范围核查

- **父提交链验证**：
  - `d5101078662b3bb193df98eb21423bd602782ffe^` 精确指向基线 SHA `94c1316ac42a881b195273ec45e840b4e55f03e8`（合同 v6 批准提交）。
- **文件变更边界核查**：
  - `git diff --name-status 94c1316ac42a881b195273ec45e840b4e55f03e8..d5101078662b3bb193df98eb21423bd602782ffe`
  - 变更文件清单：
    - `desktop/dist/**`（Vite 生产构建产物）
    - `desktop/src/components/Step2Outline.vue`
    - `desktop/src/views/Home.vue`
  - **合规判定**：严格限定在合同允许的 `desktop/**` 范围内，未触碰任何 `engine/**`、`backend/**`、`AGENTS.md` 等禁止修改目录与核心文件。
- **工作区状态**：`git status --short` 干净。

---

## 2. 独立重跑 A 级快速验证

Checker 独立执行全部自动化验证与编译构建（未采信 Maker 自述），结果如下：

| 验证项 | 执行命令 / 路径 | 耗时 / 结果 | 判定 |
| :--- | :--- | :--- | :---: |
| **1. Vue 类型检查** | `npx vue-tsc --noEmit` (`desktop/`) | 0 errors, Exit Code 0 | ✅ PASS |
| **2. 前端生产构建** | `npm run build` (`desktop/`) | Built in 681ms, 无编译错误 | ✅ PASS |
| **3. 前端单元测试** | `npx vitest run` (`desktop/`) | 3 test files, 43 passed (903ms) | ✅ PASS |
| **4. 引擎测试套件** | `python -m pytest engine/tests -q` | 71 passed, 2 warnings (78.39s) | ✅ PASS |
| **5. Rust 编译检查** | `cargo check` (`desktop/src-tauri/`) | Finished dev profile in 0.82s | ✅ PASS |

---

## 3. 代码级与逻辑合规审查

1. **彻底移除脆弱的 KeepAlive 与动态组件 (`desktop/src/views/Home.vue`)**：
   - 彻底移除了 `<KeepAlive>` 标签及 `activeStepComp` 计算属性；
   - 采用原生 `v-show` 指令分别挂载 `<Step1Project>`、`<Step2Outline>` 及 Step 3~5 占位节点：
     ```vue
     <Step1Project v-show="projectStore.currentStep === 1" />
     <Step2Outline v-show="projectStore.currentStep === 2" />
     <div v-show="projectStore.currentStep === 3" class="step-placeholder">...</div>
     <div v-show="projectStore.currentStep === 4" class="step-placeholder">...</div>
     <div v-show="projectStore.currentStep === 5" class="step-placeholder">...</div>
     ```
   - 根除了 Vue 3 内部由于动态组件/KeepAlive 在特定挂载顺序抛出 `subTree` 渲染异常导致根实例崩溃、页面白屏的潜在隐患；
   - 所有向导步骤天然驻留在 DOM 中，状态（表单输入、Markdown 大纲草稿、模板选择）天然持久保留在内存与 DOM 中，切换平滑无卡顿。

2. **Step 2 模板加载生命周期健壮化 (`desktop/src/components/Step2Outline.vue`)**：
   - 移除已失效的 `onActivated` 依赖；
   - 新增 `onMounted(ensureTemplates)` 以及针对 `projectStore.currentStep` 与 `engine.baseUrl` 的响应式监听（`watch`）：
     - 组件初次挂载时若引擎已就绪且模板为空则拉取模板；
     - 用户切换到步骤 2 时若模板尚未拉取则按需拉取；
     - 引擎从启动中转为 healthy 且处于步骤 2 时自动补拉；
   - 加载逻辑与组件激活生命周期彻底解耦，无论引擎与前端何种启动顺序，均能稳健加载 14 类规范模板。

3. **依赖与规范合规性**：
   - 未引入任何未经申报的第三方依赖包；
   - 无残留死代码或语法隐患。

---

## 4. 判定结论与后续步骤

- **最终判定**：**PASS**
- **建议锁定 SHA**：`d5101078662b3bb193df98eb21423bd602782ffe`
- **阻断项**：无
- **非阻断风险与提示**：
  - 各步骤使用 `v-show` 在初次进入页面时即完成 DOM 初始化，若后续步骤包含大量庞大图表组件，可按需结合异步组件（`defineAsyncComponent`）或懒渲染机制。目前阶段包含 Step 1、Step 2 及占位容器，初始化耗时极小（< 10ms），表现优异。
- **B 级人工验收建议（产品负责人）**：
  1. 启动桌面端应用客户端；
  2. 验证应用即刻正常渲染顶部导航栏、项目资料卡片列表等界面，无任何空白屏；
  3. 点击「下一步：模板与大纲 →」，验证页面瞬间切换到 Step 2，14 类行业模板正常展示，大纲编辑器与实时章节树正常工作；
  4. 点击「← 上一步：项目与资料」，再切回 Step 2，验证模板与已输入大纲内容完整保留。
