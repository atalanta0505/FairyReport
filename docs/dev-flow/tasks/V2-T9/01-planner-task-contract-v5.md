# 任务合同 V2-T9 v5 — 窄修复：Home.vue 中 KeepAlive 语法合规化（<component :is> 动态组件模式）

- 状态：READY_FOR_MAKER（2026-08-25 产品负责人反馈 KeepAlive 编译报错）
- 依据：用户截图反馈 `[plugin:vite:vue] <KeepAlive> expects exactly one child component.`
- 精确起始 SHA：`14d3040c1110034a781b0a82ec4581cbb47c5035`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

根治 Vue 3 模板编译器对 `<KeepAlive>` 内部子节点的严格校验报错：
- **根因**：Vue 3 中 `<KeepAlive>` 内部直接放置多个带 HTML 注释与 `v-if/v-else-if` 的普通 DOM `<div>` 节点时，编译器将注释解析为多余兄弟节点，抛出 `<KeepAlive> expects exactly one child component.` 编译错误。
- **解决方案**：
  1. 将 Step 1 与 Step 2 抽象为动态计算组件 `activeStepComp`，使用 Vue 3 官方推荐的标准 `<KeepAlive><component :is="activeStepComp" v-if="activeStepComp" /></KeepAlive>` 语法；
  2. 将 Step 3~5 的静态占位 `<div>` 移至 `<KeepAlive>` 外层按条件渲染；
  3. 彻底消除 Vue 模板编译错误。

---

## 2. 允许修改

- `desktop/src/views/Home.vue`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T9/**`

---

## 3. 禁止修改

- `engine/**`、`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `npx vue-tsc --noEmit`（`desktop/`）全绿。
- [ ] `npm run build`（`desktop/`）全绿，无 Vite Vue 编译警告或错误。
- [ ] `npx vitest run`（`desktop/`）全绿（43 tests）。
- [ ] B 级实跑：启动应用无任何 Vite 红屏遮罩报错，Step 1 与 Step 2 切换平滑。

---

## 5. 快速验证顺序

1. `npx vue-tsc --noEmit`（workdir=`desktop`）
2. `npm run build`（workdir=`desktop`）
3. `npx vitest run`（workdir=`desktop`）
