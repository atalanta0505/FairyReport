# Planner 至 Maker 任务派发消息 — V2-T19 第 1 轮

Maker：

请严格按照任务合同 `docs/dev-flow/tasks/V2-T19/01-planner-task-contract-v1.md` 执行 V2-T19 第 1 轮开发工作。

### 核心实现要点：
1. **`engine/app/writing/prompts.py` 与 `writer.py`**：
   - 新增 `FAST_REVIEW_SYSTEM_PROMPT`（⚡ 常规审查：聚焦重点名词称谓、关键数值自洽、核心底线合规三大维度，大幅压缩 Token 消耗）；
   - 在审阅与写作提示词中强力注入 `100% 纯中文思考推演` 规则，严禁英文思考句；
   - 升级 `_build_section_quota_block`：在末级小节配额中根据字数预算自动折算并注入明确的句数硬约束指令（`本小节正文控制在 X 句话以内（以句号『。』为准计），总字数约 Y 字，严禁空泛套话`）；
   - `expert_review` 与 `_build_expert_review_args` 支持 `mode="fast"`。
2. **`engine/app/writing/router.py`**：
   - `/writing/review` 与 `/writing/review_stream` 支持 `mode="fast"`。
3. **`desktop/src/components/Step4Review.vue` 与 `project.ts`**：
   - 顶栏增加 `[ ⚡ 常规审查 (推荐) ]` 与 `[ 🔍 全维逐句精审 ]` 切换；
   - 运行全书审阅前提供预估耗时（常规审查 1~2 分钟，全维精审 4~6 分钟）与确认提示；
   - `runFullBookReview` 支持传入 `mode` 参数。
4. **单测覆盖与 5 项门禁**：
   - 增补后端与前端测试用例；
   - 重建 `desktop/dist/**`；
   - 运行全量 5 项门禁（pytest, vitest, vue-tsc, build, cargo check）；
   - 提交候选 commit，编写并提交 `docs/dev-flow/tasks/V2-T19/rounds/01/maker-completion.md`，交回候选 SHA。
