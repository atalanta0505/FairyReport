# 任务合同 V2-T34 v1 — 全面取消字数限制、Step 4 审阅单章对等重构与流式体验优化

- 状态：ACCEPTED（已验收锁定）
- 依据：产品负责人（Fairy）关于“全面取消所有字数限制与计划字数、Step 4 与 Step 3 采用对等逐章开展策略、一键全书/单章审阅、不区分常规/精审、思考完毕流式首字到达即关闭构思卡片”的明确授权与要求
- 精确起始 SHA：`40cf4b0cbfebfa14aa5d97f8c0ffca78572b9a7b`
- 锁定验收 SHA：`bb0c9b984843cfff6dd294d83c8cc65368e95e5d`
- 验收报告：`docs/dev-flow/tasks/V2-T34/rounds/01/checker-report.md`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **全面取消所有字数限制与大纲计划字数展示**：
   - 清理所有模板 JSON（`generic_knowledge/templates/*.json`）及测试 fixture 中的 `total_words_max`、`per_chapter_max`、`summary_chapter_max`、`word_budget` 等字段；
   - 适配 `templates_loader.py`、`outline.py`、`writer.py`、`config.py`，支持无字数上限自由长文推演，移除对 `word_budget` 的强依赖；
   - 适配前端 `desktop/src/components/Step2Outline.vue`：彻底删除模板列表与信息栏上的 `目标字数：约 X 万字`、`约 X.X 万字` 徽标与字数提示标签。

2. **Step 3 写作页面构思卡片即时关闭 (`desktop/src/components/Step3Writing.vue`)**：
   - 依据 `stage === 'writing'` 或 `currentChapterText.trim().length > 0` 判定；
   - 只要大模型推理完成并向前端推送首个正文字符，构思等待窗口**毫秒级淡出关闭**，正文画布立即现身并实时打字流式输出。

3. **Step 4 审阅页面与 Step 3 左右架构 100% 对等单章重构 (`desktop/src/components/Step4Review.vue`, `desktop/src/stores/project.ts`)**：
   - **左侧导航目录树完全同构**：选哪章右侧就展示哪章；仅当前激活选中的章节高亮并展开其子标题，其它章节默认折叠收起；序号徽标与状态药丸（`已完成 ✓` / `待撰写`，若有审阅问题在右侧叠加 `⚠️ N`）与 Step 3 完全统一；
   - **右侧主画布单章聚焦**：专注展示当前选中章节的审阅与编辑内容；顶部提供【最终排版正文】与【纯净段落级 Diff 对比】就地切换开关；诊断问题高亮与右侧抽屉双向定位脉冲联动；
   - **顶栏操作对等简化**：
     - `[ 🚀 一键全书审阅 ]`：后台自动按顺序轮巡全书各章并展示全局进度；
     - `[ 🔍 审阅本章 ]`：单章就地即时重新诊断；
     - **彻底废除“常规审查”与“全维精审”模式选择**，统一执行国家发改委投资项目最高水准专业质检。

4. **单测覆盖与 5 项全量门禁**：
   - 增补与适配 `desktop/src/tests/` 及 `engine/tests/`；
   - 运行 5 项全量门禁（Pytest 129+、Vitest 169+、vue-tsc、build、cargo check）确保 100% 绿灯。

---

## 2. 允许修改

- `generic_knowledge/templates/*.json`
- `engine/app/writing/templates_loader.py`
- `engine/app/writing/outline.py`
- `engine/app/writing/writer.py`
- `engine/app/writing/router.py`
- `config.py`
- `desktop/src/components/Step2Outline.vue`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/stores/project.ts`
- `desktop/src/tests/**`
- `engine/tests/**`
- `docs/dev-flow/tasks/V2-T34/**`

---

## 3. 禁止修改

- `AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [x] 所有报告模板与大纲页面彻底移除字数限制与计划字数展示；
- [x] Step 3 章节写作在大模型思考结束推送首个正文字符时立即淡出关闭构思等待卡片；
- [x] Step 4 审阅页面与 Step 3 左右架构完全对等（单章聚焦，导航目录树 100% 同构，选哪章审哪章）；
- [x] Step 4 审阅入口简化为 `一键全书审阅` 与 `单章审阅`，移除常规/精审二选一；
- [x] 5 项全量门禁（Pytest、Vitest、vue-tsc、build、cargo check）全部绿灯通过。

---

## 5. 快速验证顺序

1. `npx vitest run`（`desktop/`）
2. `npx vue-tsc --noEmit`（`desktop/`）
3. `npm run build`（`desktop/`）
4. `python -m pytest engine/tests -q`
5. `cargo check`（`desktop/src-tauri/`）
