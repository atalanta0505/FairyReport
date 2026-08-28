# Planner -> Maker 任务派发消息：V2-T35 (Round 01)

- **任务编号**：V2-T35 (Round 01)
- **基线提交 SHA**：`070abcfcf77b5bcd128866c4a6f1534ec1a24a91`
- **任务合同**：`docs/dev-flow/tasks/V2-T35/01-planner-task-contract-v1.md`

【核心实现范围】
1. **Step 4 审阅页面像素级规整对齐 Step 3 (`desktop/src/components/Step4Review.vue`)**：
   - 彻底移除顶层全宽 `<header class="step4-header card">`；
   - 顶层直接进入 `.writing-layout` 双栏布局（350px 侧边栏 + 1fr 主画布），两栏顶部对齐；
   - 左侧目录树：去除 `⚠️ N` 预警角标，去除独立白色方块边框（`.chapter-tree-node` 设为 `border: none; background: transparent;`），与 Step 3 完全同构；
   - 右侧主画布头部（`.editor-header`）：左侧 `[第 N 章]` 徽标 + 标题 + 统计状态；右侧 `排版正文/Diff切换` + `审阅本章` + `AI智能修订` + 抽屉按钮；
   - 全书审阅进度条与思考推演卡片内联在右侧主画布顶部。
2. **问题清单段落/句子级绝对精准定位与呼吸波纹联动 (`desktop/src/components/Step4Review.vue`)**：
   - 升级 `locateIssueInCanvas(issue)`：支持跨章节自动切换 + 多级穿透匹配（`<mark>` -> `p, td, tr, li` 正则滑动窗口 -> 数值/关键词定位）；
   - 找到目标 DOM 元素后，调用 `targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' })` 并施加 2.5 秒金黄色呼吸波纹脉冲高亮（`.issue-canvas-pulse`），杜绝仅定位到章标题。
3. **发改委教材标准全要素财务报表强化 (`engine/app/writing/prompts.py` & `writer.py`)**：
   - 在提示词中强化投资估算与财务分析章节输出包含全要素（建筑工程费、设备购置费、安装工程费、其他费、基本预备费、建设期利息、流动资金、资金筹措分年度计划等）的标准三线财务报表。
4. **单测覆盖与 5 项全量门禁**：
   - 依次执行：
     1. `npx vitest run`（`desktop/`）
     2. `npx vue-tsc --noEmit`（`desktop/`）
     3. `npm run build`（`desktop/`）
     4. `python -m pytest engine/tests -q`
     5. `cargo check`（`desktop/src-tauri/`）
   - 创建候选 commit，编写并提交 `docs/dev-flow/tasks/V2-T35/rounds/01/maker-completion.md`，交回候选 SHA。\n