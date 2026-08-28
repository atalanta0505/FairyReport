# 任务合同 V2-T27 v1 — 正文编辑与诊断批注的高亮持久联动与防漂移

- 状态：READY_FOR_MAKER（待产品负责人批准）
- 依据：用户关于“step4中，左侧导航栏虽然标准了问题，但正文中完全没有任何持久化的高亮显示啊”的明确指令，逐个攻坚问题 4
- 精确起始 SHA：`64f75188435bddb3a70095ec6523bcfe503328cc`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **正文审阅问题持久化高亮多级容错匹配算法增强 (`desktop/src/components/Step4Review.vue`)**：
   - 升级 `applyIssueHighlightsToHtml`：
     - 实现多级特征提取链路：`issue.quote` ➔ 引号提取（`[“"「『]([^”"」』]+)[”"」』]`）➔ 关键指标/数值模式 ➔ 8~12 字符特征滑动窗口；
     - 标点与空白泛化容错（全半角符号、空白规整）；
     - 渲染规范分级标记 `<mark class="review-issue-highlight severity-{severity}" data-issue-id="{id}" data-chapter-seq="{seq}" title="{cat}: {msg}">{quote}</mark>`；
   - 保证就地编辑防漂移：编辑时自动保存纯净 Markdown，重新同步时根据最新文本重算高亮。

2. **正文高亮与诊断卡片双向精准定位与呼吸波纹联动 (`desktop/src/components/Step4Review.vue`)**：
   - 点击正文 `<mark>` 标签直接滑出诊断抽屉并居中聚焦对应卡片（`openDiagnosticDrawerAndFocusIssue`）；
   - 升级 `locateIssueInCanvas`：优先定位已高亮的 `<mark>` 节点，次级定位匹配关键词/位置段落与表格，居中对齐并触发 2.5s 金黄色呼吸波纹高亮（`.issue-highlight-pulse`）。

3. **单测覆盖与 5 项全量门禁**：
   - 确保 `pytest`、`vitest`、`vue-tsc`、`npm run build`、`cargo check` 100% 通过。

---

## 2. 允许修改

- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T27/**`

---

## 3. 禁止修改

- `backend/**`、根目录核心资产、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] Step 4 审阅后，正文中准确呈现审阅问题的高亮波浪线批注（支持 warning/error/suggestion 分级色彩）；
- [ ] 点击正文高亮标记，右侧抽屉自动滑出并居中聚焦对应问题卡片；
- [ ] 点击问题卡片「定位正文」，正文对应段落/高亮处自动居中并播放呼吸波纹动画；
- [ ] 在正文中编辑文字后，Markdown 数据源不被 mark 标签污染且高亮自适应防漂移；
- [ ] 5 项全量门禁全部绿灯通过。

---

## 5. 快速验证顺序

1. `npx vitest run`（`desktop/`）
2. `npx vue-tsc --noEmit`（`desktop/`）
3. `npm run build`（`desktop/`）
4. `python -m pytest engine/tests -q`
5. `cargo check`（`desktop/src-tauri/`）
