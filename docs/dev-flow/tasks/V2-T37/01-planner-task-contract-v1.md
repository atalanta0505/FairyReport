# 任务合同 V2-T37 v1 — Step 4 智能修订流式思考与极速重构优化（解决超时卡顿、展示思考推演过程、修完自动关闭心跳、文案规范为“已修改 ✓”）

- **状态**：READY_FOR_MAKER
- **依据**：产品负责人（Fairy）关于“全章智能修订因串行阻塞请求导致过慢与 500 超时、修改时需实时展示思考推理过程并在完成后自动关闭窗口、文案优化为‘🟢 已修改 ✓’”的明确产品指示
- **精确起始 SHA**：`1212dd34dc72c237df9cfc7a95d253ec351eeceb`
- **工作树门禁**：`git status --short` 必须干净（用户新增教材作为只读资料保留在工作区）

---

## 1. 唯一主要变化

1. **AI 智能修订流式改造与思考推理展示 (`engine/app/writing/router.py`, `desktop/src/lib/engineApi.ts`, `desktop/src/stores/project.ts`, `desktop/src/components/Step4Review.vue`)**：
   - 后端新增 `POST /writing/revise_stream` SSE 流式端点，返回 `stage`、`thought`（思考推演内容）、`chunk`、`done` 事件；
   - 彻底废除全章修订时前台 `for (const issue of issues)` 串行阻塞循环 10+ 次导致 500 超时与卡死的问题；
   - 升级为：点击 `⚡ AI 智能修订` 时，汇总本章所有问题清单与修改建议，发起**单次流式精准修订**；
   - 在主界面顶部修订心跳条中实时流式展示【纯中文思考推演过程】（带打字机流式更新）；
   - 修订完成后（SSE `done`），自动将 `revisingSeq` 置为 `null`，停止计时器并平滑自动关闭心跳条窗口。

2. **单条卡片 `[ ⚡ 局部修复 ]` 极速单段落修补**：
   - 点击单条卡片时，仅修补该单一问题所在段落（1~2 秒完成），不触发全章循环；
   - 修复成功后从清单移除该项并原位更新正文，清除该处高亮。

3. **顶栏状态文案微调**：
   - 章节顶部状态徽标：已审阅且无问题（或修改完毕）时，文案规范显示为 `🟢 已修改 ✓`（替换原 `🟢 发改委标准达标 ✓`）。

4. **单测覆盖与 5 项全量门禁**：
   - 补充/更新流式修订单测；
   - 依次通过 5 项流水线（Vitest, vue-tsc, build, Pytest, cargo check）。

---

## 2. 允许修改

- `engine/app/writing/router.py`
- `engine/app/writing/writer.py`
- `engine/tests/**`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/stores/project.ts`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/**`
- `docs/dev-flow/tasks/V2-T37/**`

---

## 3. 禁止修改

- `AGENTS.md`、`.gitignore`
- `generic_knowledge/` 下的用户新增教材文件

---

## 4. 验收标准

- [ ] 点击 `[ ⚡ AI 智能修订 ]` 采用单次流式请求，10~15 秒内流式输出，彻底杜绝 500 超时卡死；
- [ ] 修订过程中顶部实时展示 AI 思考推演过程（纯中文 thought stream）；
- [ ] 修订完成后，自动清空本章已修复问题项，原位更新正文，心跳条窗口自动关闭；
- [ ] 顶栏达标文案规范显示为 `🟢 已修改 ✓`；
- [ ] 5 项全量门禁（Pytest、Vitest、vue-tsc、build、cargo check）全部绿灯通过。

---

## 5. 快速验证顺序

1. `npx vitest run`（`desktop/`）
2. `npx vue-tsc --noEmit`（`desktop/`）
3. `npm run build`（`desktop/`）
4. `python -m pytest engine/tests -q`
5. `cargo check`（`desktop/src-tauri/`）
