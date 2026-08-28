# 任务完工报告：V2-T30 第 1 轮

- 目标任务：V2-T30（三源参考文献引用量与分类统计口径清晰化、双向锚点联动与外链直达）
- 有效合同：`docs/dev-flow/tasks/V2-T30/01-planner-task-contract-v1.md`
- 精确起始 SHA：`e120b09337ff447814b609c1fa41982b61f885df`
- 候选提交 SHA：`1702bb4c89585316c59a86b423e5baee2badd57f`

---

## 1. 变更清单与文件列表

### 1.1 三源参考文献分类统计与语义化内联标签解析 (`desktop/src/lib/markdown.ts`)
- **`ReferencesSummary` 与 `getReferencesSummary`**：
  - 定义 `ReferencesSummary` 接口，包含 `material`、`standard`、`web` 3 大权威来源的条目数与引用频次，以及 `totalCount` 与 `totalCitations`；
  - 实现 `getReferencesSummary(refs: ReferenceItem[]): ReferencesSummary`，实现高内聚统计计算；
- **语义化内联引用标签 (`inline-ref-tag`)**：
  - 在 `formatInline` / `markdownToHtml` 中，将正文中的 `【源:...】`、`【标:...】`、`【网:...】` 及 `[Z]` 转换为带有语义化 class 与数据属性的内联标签：
    `<span class="inline-ref-tag type-${type}" data-ref-type="${type}" data-ref-title="${escapedTitle}" title="点击查看参考资料出处">${rawTag}</span>`；
  - 分别赋予 `.type-material`（工程底稿/靛蓝）、`.type-standard`（行业国标/琥珀）、`.type-web`（百度联网/翠绿）3 种高辨识度专属配色；
- **纯净 Markdown 反向还原 (`htmlToMarkdown` & `cleanInlineHtml`)**：
  - 更新反向序列化解析正则，在用户就地编辑 contenteditable 画布并保存时，将 `inline-ref-tag` 纯净还原为原始 `【...:...】` 或 `[Z]` 文本，彻底杜绝 HTML 标签与数据属性污染 Markdown 源码；
- **标准化三源分类标签命名**：
  - 将 `extractReferences` 中的 `typeLabel` 统一命名为 `项目底稿`、`国标规程`、`百度联网`。

### 1.2 Step 3 章节写作参考资料抽屉升级与双向定位联动 (`desktop/src/components/Step3Writing.vue`)
- **顶部三源分类统计卡片组**：
  - 将原有单行概括文本升级为三源分类卡片网格（`drawer-summary-grid`）：
    1. 📄 **项目底稿**：`N 份`（引用 `M 处`）
    2. ⚖️ **国标规程**：`N 项`（引用 `M 处`）
    3. 🌐 **百度联网**：`N 条`（引用 `M 处`）
- **分类筛选 Tab 与实时计数角标**：
  - 支持 `[ 全部 (N) ]` | `[ 📄 项目底稿 (N) ]` | `[ ⚖️ 国标规程 (N) ]` | `[ 🌐 百度联网 (N) ]` 实时筛选；
  - 根据选中的分类提供精准友好的空状态说明；
- **正文 ➔ 抽屉点击跳转与卡片脉冲高亮**：
  - 在富文本编辑画布上监听点击事件，点击正文内联引用标签 `.inline-ref-tag` 时自动滑出参考资料抽屉、切换至对应分类 Tab 并平滑滚动定位至该资料卡片，触发 2 秒呼吸高亮动画（`.ref-card-pulse`）；
- **抽屉 ➔ 正文反向定位出处**：
  - 每个参考资料卡片提供 `[ 🎯 定位正文出处 ]` 操作按钮，点击后在主画布正文中查找匹配的 `.inline-ref-tag[data-ref-title="..."]`，平滑滚动居中并触发 2 秒醒目呼吸高亮（`.inline-ref-pulse`）；
- **百度联网权威源真实外链展示**：
  - 对于 `type === 'web'` 资料卡片，提供高辨识度的外链按钮 `<a :href="refItem.url" target="_blank" class="ref-external-link">🔗 访问原网页出处 ↗</a>`；若无 URL 则展示 `🌐 百度检索在线实时快照已归档入库` 归档标记。

### 1.3 Step 4 专家审阅参考资料抽屉升级与双向定位联动 (`desktop/src/components/Step4Review.vue`)
- **全书三源分类统计卡片组与筛选 Tab**：
  - 右侧抽屉 2（📚 全书参考资料台账）顶部集成三源分类统计卡片组与带实时计数的分类 Tab 导航；
- **全书正文 ➔ 抽屉 / 抽屉 ➔ 正文双向锚点联动**：
  - 在 `handleCanvasClick` 中支持点击 `.inline-ref-tag` 唤起全书参考资料抽屉并高亮卡片；
  - 抽屉卡片 `[ 🎯 定位正文出处 ]` 支持跨章节反向定位，若目标章节处于折叠状态则自动展开并平滑居中滚动至目标内联引用标签并触发呼吸脉冲；
- **百度联网真实外链直达**：
  - 渲染标准外部超链接与权威快照说明。

### 1.4 单元测试覆盖与生产包打包
- `desktop/src/tests/markdown.test.ts`：增补 V2-T30 测试用例（三源分类统计计算、语义化标签转换、HTML 纯净反向还原）；
- `desktop/src/tests/project.test.ts`：增补全书多章节三源合并统计一致性与正文标签属性特征匹配测试；
- `desktop/dist/**`：重新编译打包最新前端生产产物。

---

## 2. 5 项全量门禁执行记录

按合同约定顺序执行 5 项全量验证：

1. `npx vitest run`（`desktop/`）:
   - **PASS**: 5 test files, 151 passed (100%).
2. `npx vue-tsc --noEmit` (`desktop/`):
   - **PASS**: 0 type errors.
3. `npm run build` (`desktop/`):
   - **PASS**: 生产包构建成功，耗时 1.21s。
4. `python -m pytest engine/tests -q`:
   - **PASS**: 127 passed, 0 failures (100%).
5. `cargo check` (`desktop/src-tauri/`):
   - **PASS**: finished dev profile in 1.19s, 0 errors.

---

## 3. 设计决策与说明

1. **三源统计口径清晰化与认知减负**：过去参考资料抽屉仅展示粗略的“共命中 N 份底稿”，未区分底稿文件、国家行业标准与网络检索内容。升级后，三源分类统计卡片组清晰呈现“📄 项目底稿 / ⚖️ 国标规程 / 🌐 百度联网”的数量与引用次数，让政务公文与工程咨询编制人员一目了然；
2. **正文与抽屉双向交互闭环**：通过 HTML5 数据属性（`data-ref-type`、`data-ref-title`）在正文 `.inline-ref-tag` 与抽屉 `.ref-card-item` 之间建立高可靠的解耦索引；正文点击即查出处，卡片点击即反查正文上下文，配合 2 秒平滑滚动与醒目呼吸波纹，极大提升审阅与核查效率；
3. **零污染 Markdown 反向解析**：在 contenteditable 中渲染丰富的内联语义化标签的同时，确保 `htmlToMarkdown` 在用户编辑后能 100% 纯净还原为原始 Markdown 标签，彻底避免富文本标记污染 Markdown 源文本。

---

## 4. 冻结声明

- 本轮所有功能开发、单测编写与 5 项全量门禁均已绿灯通过；
- 工作树修改范围严格符合合同允许路径；
- 候选提交 SHA `1702bb4c89585316c59a86b423e5baee2badd57f` 代码已冻结，交付验收。
