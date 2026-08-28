# Planner 至 Maker 派发消息：任务 V2-T31 第 1 轮

- 目标任务：V2-T31（大模型思考链纯中文绝对纯化硬防线）
- 依据合同：`docs/dev-flow/tasks/V2-T31/01-planner-task-contract-v1.md`
- 精确起始 SHA：`4d128223462ebf89fc8487ffe79f976d21c32549`

---

## 核心任务要点

1. **后端提示词资产强化 (`engine/app/writing/prompts.py`)**：
   - 检查并强化以下系统提示词，全面注入纯中文思考链绝对防线：
     - `_BASE_WRITING_PROMPT`
     - `_OUTLINE_BASE_PROMPT`
     - `ORDER_SYSTEM_PROMPT`
     - `_HINT_SYSTEM_PROMPT`
     - `_MODIFY_SYSTEM_PROMPT`
     - `FAST_REVIEW_SYSTEM_PROMPT`
     - `FULL_EXPERT_REVIEW_SYSTEM_PROMPT`
     - `COMPLIANCE_REVIEW_SYSTEM_PROMPT`
     - `NUMERICAL_REVIEW_SYSTEM_PROMPT`
     - `TECH_REVIEW_SYSTEM_PROMPT`
   - 确保包含明确禁止出现 'Okay', 'Let me', 'First', 'Next', 'I should' 等英文思考句式的约束。

2. **后端组装与用户 Prompt 注入 (`engine/app/writing/writer.py`, `outline.py`)**：
   - 在各接口的用户 Prompt 末尾统一追加纯中文思考链与语言规范约束。

3. **前端思维链面板展示优化 (`desktop/src/components/Step3Writing.vue`, `Step4Review.vue`)**：
   - 确保动态构思卡片与展开面板提示文字规范统一为 `🧠 深度技术推演与工程构思过程 (纯中文)` 与 `思维推演中 (纯中文)...`。

4. **单测覆盖与 5 项全量门禁**：
   - 增补相关提示词防线断言测试；
   - 运行 5 项验证确保 100% 绿灯。
