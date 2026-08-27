# 任务合同 V2-T22 v1 — 导航自适应滚动修复、中文极速审阅推演、AI 一键直接修订、正文问题持久化高亮与全书章节标题完善

- 状态：ACCEPTED（已由 Checker 独立验收通过并锁定）
- 依据：用户关于 Step 3 导航自适应滚动条失效与文字垂直挤压截断、审阅思考推演出现英文且耗时过长、AI 修订去除悬浮弹窗、正文问题持久化高亮、未写章节标题显式呈现的反馈
- 精确起始 SHA：`1dd22a3e9c6efc196f7c4db3fa0592e35182103f`
- 验收锁定 SHA：`e82e32d57e96fa4641198cfe018f6c90c63437e3`
- 验收结论：PASS（`docs/dev-flow/tasks/V2-T22/rounds/01/checker-report.md`）
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **Step 3 侧边栏布局与自适应垂直滚动修复 (`desktop/src/components/Step3Writing.vue`)**：
   - 为 `.sidebar-panel` 设置固定可用视口高度 `height: calc(100vh - 165px); min-height: 0; overflow: hidden;`；
   - 为 `.outline-tree-scrollable` 设置 `flex: 1; min-height: 0; overflow-y: auto;`；
   - 为 `.chapter-tree-node` 设置 `flex-shrink: 0; min-height: 38px;`，消除 flex 压缩坍塌，彻底根除章标题文字被垂直挤压截断问题，恢复自适应全局滚动条。
2. **全书审阅思维推演纯中文与极速约束 (`engine/app/writing/prompts.py`, `writer.py`)**：
   - 强化 `FAST_REVIEW_SYSTEM_PROMPT` 与 `FULL_EXPERT_REVIEW_SYSTEM_PROMPT`：注入【纯中文推演绝对铁律】与【极速审查长度约束（300~500 字，5~10 秒完成）】；
   - 在用户 Prompt 末尾注入强约束指令，杜绝 DeepSeek-R1 等模型输出 24,000+ 字符英文分析。
3. **AI 修订去除悬浮遮罩弹窗，实现直接就地修订与内联 Diff (`desktop/src/components/Step4Review.vue`)**：
   - 彻底移除 `showRevisionModal` 遮罩大弹窗；
   - 在顶栏与诊断抽屉中提供 `[ ⚡ AI 一键智能修订 ]`，点击直接提取本章诊断建议触发修订，正文顶部展示轻量内联心跳进度条，完成后自动就地切换至全宽单栏内联 Diff 模式。
4. **Step 4 正文审阅问题持久化高亮与批注标记 (`desktop/src/components/Step4Review.vue`)**：
   - 正文排版渲染时，自动匹配 `issues` 中的 `quote` / 关键词，使用 `<mark class="review-issue-highlight severity-${issue.severity}">` 进行浅黄/浅红底纹与波浪线高亮标注；
   - 支持悬浮提示诊断详情，点击联动定位至诊断卡片。
5. **全书连贯预览未写作章节标准化呈现章标题 (`desktop/src/components/Step4Review.vue`)**：
   - 在全书预览中为所有章节标准化渲染章标题栏（`第 X 章：章节名称` + `字数标签`），未写章节下方显示清晰占位提示，避免用户误解。
6. **单测覆盖与快速验证**：
   - 适配 `engine/tests/` 与 `desktop/src/tests/`；
   - 运行 5 项全量门禁（pytest, vitest, vue-tsc, build, cargo check）。

---

## 2. 允许修改

- `engine/app/writing/prompts.py`
- `engine/app/writing/writer.py`
- `engine/tests/**`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T22/**`

---

## 3. 禁止修改

- `backend/**`、根目录核心文件、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿。
- [ ] `npx vitest run`、`npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] Step 3 章节导航栏具有自适应滚动条，11+ 章节完整垂直排布，标题文字 100% 完整无挤压截断。
- [ ] 常规审查思考推演 100% 为纯中文且在 5~10 秒内极速产出结果。
- [ ] 点击 AI 智能修订不弹出遮罩模态窗，直接在正文上方就地运行并展示单栏内联 Diff。
- [ ] Step 4 正文中存在审阅问题的关键词/语句具备持久化高亮底色与波浪线。
- [ ] 全书预览中所有章节均有清晰的标准章标题栏。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
5. `cargo check`（workdir=`desktop/src-tauri`）
