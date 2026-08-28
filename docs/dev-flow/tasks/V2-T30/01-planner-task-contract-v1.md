# 任务合同 V2-T30 v1 — 三源参考文献引用量与分类统计口径清晰化（底稿/国标/百度联网分类汇总、双向锚点联动与外链直达）

- 状态：READY_FOR_MAKER（待产品负责人批准）
- 依据：用户关于“启动V2-T30：三源参考文献引用量与统计口径清晰化”的明确指示
- 精确起始 SHA：`afbc38db4db1da04f5e71465e905d548325a7209`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **三源参考文献引用量与分类统计口径清晰化 (`desktop/src/components/Step3Writing.vue`, `Step4Review.vue`, `desktop/src/lib/markdown.ts`)**：
   - **三源分类统计指示卡片**：
     - 在 Step 3 与 Step 4 的参考资料抽屉（`showRefDrawer`）顶部，将原有单行粗略文本升级为**三源分类统计卡片组**：
       1. 📄 **项目底稿资料**：`N 份`（引用 `M 处`）；
       2. ⚖️ **行业国标规程**：`N 项`（引用 `M 处`）；
       3. 🌐 **百度联网检索**：`N 条`（引用 `M 处`）；
     - 清晰呈现三类权威来源的引用数量与频次分布。
   - **分类筛选 Tab 升级与角标计数**：
     - Step 3 与 Step 4 统一支持分类筛选 Tab，并在按钮上实时显示对应分类的条目数量：
       `[ 全部 (N) ]` | `[ 📄 项目底稿 (N) ]` | `[ ⚖️ 国标规程 (N) ]` | `[ 🌐 百度联网 (N) ]`；
     - 切换分类时即时过滤，空状态下展示精准友好的空态提示。

2. **正文引用标记与抽屉双向定位 / 高亮联动 (`desktop/src/components/Step3Writing.vue`, `Step4Review.vue`, `desktop/src/lib/markdown.ts`)**：
   - **正文内联引用标记可交互化**：
     - 在 `markdownToHtml` 解析时，将 `【源:...】`、`【标:...】`、`【网:...】` 转换为具有语义化 class 与数据属性的内联标签：
       `<span class="inline-ref-tag type-${type}" data-ref-type="${type}" data-ref-title="${escapedTitle}" title="点击查看参考资料出处">${rawTag}</span>`；
     - 点击正文中的内联引用标记时，自动滑出参考资料抽屉，切换至对应分类 Tab，并平滑滚动高亮（脉冲呼吸动画 2 秒）定位至该条资料卡片；
   - **抽屉卡片反向定位正文出处**：
     - 资料卡片提供 `[ 🎯 定位正文出处 ]` 按钮或点击交互，点击后自动在主画布正文中查找首个匹配的引用标记，滚动平滑居中并触发呼吸高亮。

3. **百度联网权威源真实外链与出处展示优化 (`desktop/src/lib/markdown.ts`, `engine/app/writing/refs.py`)**：
   - 对于 `【网:...】` 来源，严格提取 URL 并渲染标准外链按钮 `<a :href="refItem.url" target="_blank">🔗 访问原网页出处 ↗</a>`；
   - 若无 URL 则展示引擎检索归档说明，保障政务公文可追溯性。

4. **单测覆盖与 5 项全量门禁**：
   - 在 `desktop/src/tests/` 与 `engine/tests/` 增补针对三源分类统计、双向锚点匹配、外链解析的单元测试；
   - 保证 5 项门禁（Vitest、vue-tsc、build、pytest、cargo check）全部绿灯。

---

## 2. 允许修改

- `desktop/src/lib/markdown.ts`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `engine/app/writing/refs.py`
- `engine/tests/**`
- `docs/dev-flow/tasks/V2-T30/**`

---

## 3. 禁止修改

- `generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] Step 3 与 Step 4 参考资料抽屉呈现 📄 项目底稿、⚖️ 国标规程、🌐 百度联网 3 类明确统计卡片；
- [ ] 资料抽屉 Tab 支持分类切换与数量角标（全部/底稿/国标/网络）；
- [ ] 正文中的引用标记可点击滑出抽屉并精准定位该资料卡片（带高亮动画）；
- [ ] 抽屉资料卡片支持点击反向定位正文对应引用位置；
- [ ] 5 项全量门禁全部绿灯通过。

---

## 5. 快速验证顺序

1. `npx vitest run`（`desktop/`）
2. `npx vue-tsc --noEmit`（`desktop/`）
3. `npm run build`（`desktop/`）
4. `python -m pytest engine/tests -q`
5. `cargo check`（`desktop/src-tauri/`）
