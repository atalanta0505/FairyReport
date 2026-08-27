# 任务合同 V2-T21 v1 — 拓扑推荐章节写作顺序、断点智能续写、Step 3 目录平铺一体化与纯净排版画布

- 状态：ACCEPTED（2026-08-27 Round 01 独立验收全绿，锁定候选提交 `82aa6ae30a47a697e6bbd5e44efb6e8f6456a6ce`）
- 依据：用户关于第一章综述推演耗时长、全书写作推荐拓扑顺序（如 2~10 -> 1 -> 11）、一键写作断点续写防清空、Step 3 导航对齐 Step 4 平铺一体化与移除源码视图的建议
- 精确起始 SHA：`8485a13db2a56135eeecdcd20612e766c308dc8e`
- 验收候选 SHA：`82aa6ae30a47a697e6bbd5e44efb6e8f6456a6ce`
- 验收报告：`docs/dev-flow/tasks/V2-T21/rounds/01/checker-report.md`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **模板与拓扑推荐写作顺序联动 (`engine/app/writing/templates_loader.py`, `router.py`, `desktop/src/stores/project.ts`)**：
   - 后端 `templates_loader.py` 实现 `get_writing_order(report_type, total_chapters)` 与 `get_writing_order_reason(report_type)`，支持读取模板配置或基于 `is_summary` 规则自动推导（先主体论证章，再第 1 章概述，最后收尾结论章，如可研 `2,3,4,5,6,7,8,9,10,1,11`）；
   - 后端 `router.py` 在 `TemplateItemOut` 与 `/writing/outline` 返回 `writing_order` 与 `writing_order_reason`；
   - 前端 Pinia Store `project.ts` 维护并在大纲生成/加载时持久化 `writingOrder`，并在写任何章节时，将当前项目中**所有已写好的其它章节全量组装传入 `predecessor_chapters`**，使第 1 章自动获取各章数据底稿，大幅提速推演并实现 100% 数据自洽。
2. **断点智能续写与资产防误删 (`desktop/src/stores/project.ts`)**：
   - 升级 `writeAllChapters`：默认按照 `writingOrder` 序列循环，自动过滤已生成章节（`chapters[seq].trim().length > 0`），仅对未完成章节进行断点续写；
   - 若全书已全部生成，友好提示用户，绝不擅自清空已有正文；
   - 保持单章「重新生成」作为唯一覆盖写入入口。
3. **Step 3 目录导航栏对齐 Step 4 平铺一体化 (`desktop/src/components/Step3Writing.vue`)**：
   - 彻底去除 `.chapter-card` 大盒子与独立嵌套滚动，采用统一的 `.outline-tree-scrollable` 单一定高外层平滑滚动；
   - 顶栏展示「💡 推荐写作顺序」流程指引胶囊；
   - 节点右侧平铺展示状态徽标（`已完成 ✓` / `撰写中` / `未生成`）与单章操作按钮（`✍️` / `🗑️`）。
4. **Step 3 移除源码视图，纯净出版级排版工作台 (`desktop/src/components/Step3Writing.vue`)**：
   - 移除顶部「排版视图 / 源码视图」切换组，画布直接呈现 10.5pt 出版级所见即所得排版正文；
   - 顶栏保留「💡 写作提示 (Hint)」、「📚 参考资料 (N)」、「📋 复制 Markdown」；
   - 修复流式打字机与思考推演卡片的平滑切换。
5. **单测覆盖与快速验证**：
   - 适配 `engine/tests/` 与 `desktop/src/tests/`；
   - 运行 5 项全量门禁（pytest, vitest, vue-tsc, build, cargo check）。

---

## 2. 允许修改

- `engine/app/writing/templates_loader.py`
- `engine/app/writing/router.py`
- `engine/tests/**`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/stores/project.ts`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T21/**`

---

## 3. 禁止修改

- `backend/**`、根目录核心文件、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿。
- [ ] `npx vitest run`、`npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] 模板与大纲接口支持返回推荐写作顺序（如可研报告 `[2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 11]`）。
- [ ] 一键全书写作按推荐顺序执行，并自动跳过已写完章节进行断点续写，绝不清空已有正文。
- [ ] 写第 1 章时，后台正确收到已生成的第 2~10 章全文作为 `predecessor_chapters`。
- [ ] Step 3 左侧导航栏呈 Flat 平铺一体化多级目录树，右侧画布纯净展示出版级排版工作台（无源码视图干扰）。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
5. `cargo check`（workdir=`desktop/src-tauri`）
