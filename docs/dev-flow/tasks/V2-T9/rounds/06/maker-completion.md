# Maker 完成说明 — V2-T9 第 6 轮（v-show 稳健重构）

- **任务合同**：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v6.md`
- **转发消息**：`docs/dev-flow/tasks/V2-T9/02-planner-to-maker-message-v6.md`
- **起始 SHA**：`94c1316ac42a881b195273ec45e840b4e55f03e8`
- **候选 SHA**：`d5101078662b3bb193df98eb21423bd602782ffe`
- **完成时间**：2026-08-25

---

## 1. 交付文件清单

本轮修改严格限定于 `desktop/**` 与治理文档：

### 桌面端前端 (`desktop/**`)
1. `desktop/src/views/Home.vue`：
   - 彻底废除脆弱的 `<KeepAlive>` 与 `activeStepComp` 动态组件机制；
   - 模板层采用 Vue 原生 `v-show` 模式统一管理 Step 1（`Step1Project`）、Step 2（`Step2Outline`）及 Step 3~5 占位容器；
   - 彻底根除因 Vue 3 动态组件/KeepAlive 内部 `subTree` 渲染异常导致的根实例挂载中断与白屏现象；
   - 利用 `v-show` 保证所有步骤组件始终驻留在 DOM 中，天然保持已填写大纲、模板选择及表单状态（无组件销毁与重建）。
2. `desktop/src/components/Step2Outline.vue`：
   - 移除已无用的 `onActivated` 生命周期钩子引用；
   - 采用 `onMounted` 结合 `watch(() => projectStore.currentStep)` 与 `watch(() => engine.baseUrl)` 机制，当切换进入步骤 2 或引擎就绪时按需加载 14 类规范模板数据。
3. `desktop/dist/**`：
   - 重新执行 Vite 生产打包构建，更新静态资源与 HTML 产物。

---

## 2. 核心设计与修复说明

1. **v-show 极速与稳健架构**：
   - 针对用户反馈的主窗口白屏问题，排查确认为 `<KeepAlive>` 在包裹动态组件 `<component :is="activeStepComp" />` 且存在返回 `null` 分支时，在 Vite 生产/热重载某些环境下可能导致 Vue 3 挂载中断抛错；
   - 采用原生 `v-show` 架构后：
     1. 所有步骤节点及组件在初始挂载时一次性初始化，DOM 树结构绝对静态稳定；
     2. 步骤流转通过 CSS `display: none` 毫秒级切换，无任何组件卸载/重新挂载开销；
     3. 用户填写的 Markdown 大纲、选中的项目与模板状态天然 100% 保持在内存与 DOM 中，彻底杜绝状态丢失与渲染白屏。

---

## 3. 快速验证记录

严格按照合同第 5 条约定的快速验证顺序执行：

```bash
# 1. Vue/TypeScript 严格类型检查
npx vue-tsc --noEmit (desktop)
# 结果：无类型报错，Exit Code 0

# 2. 前端生产打包构建
npm run build (desktop)
# 结果：Vite 生产构建成功，静态资源更新无误，Exit Code 0

# 3. 前端 Vitest 单元测试
npx vitest run (desktop)
# 结果：3 个测试文件，43 项测试全部通过（通过率 100%）
# ✓ src/tests/api.test.ts (7 tests)
# ✓ src/tests/engine.test.ts (5 tests)
# ✓ src/tests/project.test.ts (31 tests)

# 4. Rust 编译检查
cargo check (desktop/src-tauri)
# 结果：Finished `dev` profile in 0.86s，Exit Code 0
```

---

## 4. 冻结声明

- 代码变更严格限定在 `desktop/**` 与任务文档。
- 本地工作树已验证且保持干净，无 `git push`、无 `git rebase`、无 `git commit --amend`。
- 正式交付候选 SHA：`d5101078662b3bb193df98eb21423bd602782ffe`，交回验收。
