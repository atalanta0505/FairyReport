# 任务合同 V2-T35 v1 — Step 4 审阅页面像素级规整对齐 Step 3、去除预警角标、问题清单段落级多级穿透精准定位与发改委教材标准全要素财务报表强化

- 状态：READY_FOR_MAKER（待产品负责人批准）
- 依据：产品负责人（Fairy）关于“Step 4 左侧导航栏与整体布局像素级规整对齐 Step 3、去除 ⚠️ N 预警角标、解决点击问题只能定位到章标题的痛点实现段落级精准定位与呼吸高亮、结合新增教材通用知识强化全要素完整财务报表”的明确授权与要求
- 精确起始 SHA：`070abcfcf77b5bcd128866c4a6f1534ec1a24a91`
- 工作树门禁：`git status --short` 必须干净（用户新增教材作为只读资料保留在工作区）

---

## 1. 唯一主要变化

1. **Step 4 审阅页面整体布局像素级对齐 Step 3 (`desktop/src/components/Step4Review.vue`)**：
   - **彻底删除顶层全宽卡片** `<header class="step4-header card">`，消除双层 Header 压迫；
   - 页面顶层直接呈现 `.writing-layout`（350px 左侧栏 + 1fr 右侧主画布），左右两栏顶部齐平；
   - **左侧导航目录树完全同构与纯化**：
     - 彻底移除 `⚠️ N` 预警角标；
     - 彻底移除章节节点的独立白色方块边框（`.chapter-tree-node` 设为 `border: none; background: transparent;`），应用 Step 3 完全相同的无边框平铺列表；
     - 头部卡片展示 `📑 章节目录与导航` + 项目名胶囊 + 统计条（总章节 / 已审阅 / 总字数）+ `💡 推荐写作顺序` 胶囊；
     - 主操作按钮为蓝色通栏大按钮 `🚀 一键全书审阅`（`btn btn-primary btn-block`，审阅中切换为红色 `⏹ 停止全书审阅`）；
     - 仅当前激活选中的章节高亮（蓝底圆圈徽标）并展开子标题，未选章节保持纯白紧凑；
   - **右侧主画布头部（`.editor-header`）结构对齐**：
     - 左侧标题区：`[第 N 章]` 蓝色徽标 + 章节标题，第二行展示 `当前字数: X 字 (正文) · 🟢 达标 / 🟡 存在 N 处待核 / ⏳ 待专家审阅`；
     - 右侧操作区：
       - `[ 📝 最终排版正文 | 🔍 修订差异对比 ]` 模式切换 Tab；
       - `[ 🔍 审阅本章 ]` 单章即时体检按钮；
       - `[ ⚡ AI 智能修订 ]` 智能重构按钮；
       - `[ 📋 专家诊断报告 (N) ]`、`[ 📚 参考资料 (N) ]`、`[ 📄 复制 Markdown ]` 抽屉与快捷操作按钮。
   - **全书审阅心跳与思考推演窗口**：若触发一键全书审阅，进度指示与思考推演卡片内联在右侧主画布顶部（或浮动在画布上方），不破坏整页的双栏结构。

2. **问题清单段落/句子级绝对精准定位与呼吸高亮脉冲联动 (`desktop/src/components/Step4Review.vue`)**：
   - 彻底升级 `locateIssueInCanvas(issue)`，杜绝回退到章标题的模糊体验：
     - 若问题属于其他章节，先自动切换选中章 `selectChapter(issue.chapterSeq)` 并 `await nextTick()`；
     - 在当前章正文 DOM（`editorCanvasRef`）中执行多层穿透查找算法：
       1. **第 1 级**：精确查找 `<mark data-issue-id="${issue.id}">`；
       2. **第 2 级**：若未打上 mark，遍历正文中的所有块级元素（`p`, `td`, `tr`, `li`, `h2..h6`, `blockquote`），使用去标点与空白的泛化正则及 **前缀滑动窗口（8~16 字符）** 模糊匹配 `issue.quote`；
       3. **第 3 级**：若无 quote，在正文块级元素中匹配 `issue.message` 中提取的核心数值（如 `3500万元`、`18.5%`）或 `issue.location` 子标题名；
     - 找到目标 DOM 元素后，调用 `targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' })` 居中平滑滚入视口；
     - 动态注入 `.issue-canvas-pulse` CSS 类，触发持续 2.5 秒的金黄色呼吸波纹脉冲高亮动画，确保用户一眼锁定具体哪一段、哪句话。

3. **发改委教材标准全要素财务报表强化 (`engine/app/writing/prompts.py` & `writer.py`)**：
   - 结合新增《2024 - 决策评价》、《2024 - 方法实务》教材标准，在系统提示词与投资估算/财务分析章节要求中，强化输出包含全要素（建筑工程费、设备购置费、安装工程费、工程建设其他费、基本预备费、建设期利息、流动资金、资金筹措分年度计划、主要财务指标汇总表等）的标准三线财务报表。

4. **单测覆盖与 5 项全量门禁**：
   - 适配 `desktop/src/tests/` 与 `engine/tests/`；
   - 依次通过 5 项快速验证流水线（Vitest, vue-tsc, build, Pytest, cargo check）。

---

## 2. 允许修改

- `desktop/src/components/Step4Review.vue`
- `desktop/src/stores/project.ts`
- `desktop/src/lib/markdown.ts`
- `desktop/src/tests/**`
- `engine/app/writing/prompts.py`
- `engine/app/writing/writer.py`
- `engine/tests/**`
- `docs/dev-flow/tasks/V2-T35/**`

---

## 3. 禁止修改

- `AGENTS.md`、`.gitignore`
- `generic_knowledge/` 下的用户新增教材文件

---

## 4. 验收标准

- [ ] Step 4 审阅页面彻底移除顶层全宽 Header，顶层直接呈现与 Step 3 完全相同的双栏布局；
- [ ] Step 4 左侧导航栏彻底移除 `⚠️ N` 预警角标与章节独立白方框边框，变为统一的平铺树状菜单；
- [ ] Step 4 右侧主画布头部与 Step 3 结构对称统一；
- [ ] 点击诊断问题或“定位正文”能 100% 居中平滑定位到具体段落/句子，并触发 2.5 秒金黄色呼吸波纹脉冲高亮，杜绝仅定位到章标题；
- [ ] 投资估算与财务分析提示词强化全要素标准三线财务大表；
- [ ] 5 项全量门禁（Pytest、Vitest、vue-tsc、build、cargo check）全部绿灯通过。

---

## 5. 快速验证顺序

1. `npx vitest run`（`desktop/`）
2. `npx vue-tsc --noEmit`（`desktop/`）
3. `npm run build`（`desktop/`）
4. `python -m pytest engine/tests -q`
5. `cargo check`（`desktop/src-tauri/`）\n