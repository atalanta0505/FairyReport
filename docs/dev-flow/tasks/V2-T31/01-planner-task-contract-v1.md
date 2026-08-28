# 任务合同 V2-T31 v1 — 大模型思考链纯中文绝对纯化硬防线（全链路提示词纯化、推演防混杂与防御）

- 状态：READY_FOR_MAKER（待产品负责人批准）
- 依据：用户关于“大模型思考链纯中文绝对纯化，逐个攻克”的明确指示
- 精确起始 SHA：`4d128223462ebf89fc8487ffe79f976d21c32549`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **大模型全链路提示词纯中文思考链绝对硬防线 (`engine/app/writing/prompts.py`, `writer.py`, `outline.py`)**：
   - 在所有系统提示词中全面注入最高优先级的【思考链纯中文绝对防线】约束：
     - `_BASE_WRITING_PROMPT`（章节正文写作）；
     - `_OUTLINE_BASE_PROMPT` 与 `ORDER_SYSTEM_PROMPT`（大纲生成与推荐顺序推演）；
     - `_HINT_SYSTEM_PROMPT`（章节编写提示 Hint 生成）；
     - `_MODIFY_SYSTEM_PROMPT`（章节 AI 修订）；
     - `FAST_REVIEW_SYSTEM_PROMPT`、`FULL_EXPERT_REVIEW_SYSTEM_PROMPT`、`COMPLIANCE_REVIEW_SYSTEM_PROMPT`、`NUMERICAL_REVIEW_SYSTEM_PROMPT`、`TECH_REVIEW_SYSTEM_PROMPT`（常规审查、全维精审与专项诊断）；
   - **硬性约束口径**：
     `【思考链与语言规范（最高优先级·纯中文绝对纯化防线）】：如果模型输出内部思维推演过程（reasoning_content / thought），该思考推演过程必须 100% 使用规范中文进行国家发改委投资项目与工程咨询专业论证，绝对禁止夹杂任何英文思考句子、英文短语或英文分析单词（法定国家标准代码如 GB/T、ISO 及法定工程量纲单位符号如 m³、kW·h、% 除外）！严禁出现 'Okay', 'Let me', 'First', 'Next', 'I should', 'We need to' 等任何英文构思句式！`
   - 在 `writer.py` 的用户 Prompt 注入点（如单章审阅、全书审阅、AI 修订）同步附带该硬防线约束。

2. **前端思考链展示与体验优化 (`desktop/src/components/Step3Writing.vue`, `Step4Review.vue`)**：
   - 构思指示卡片与展开抽屉中，思维链标题统一标注为 `🧠 深度技术推演与工程构思过程 (纯中文)`；
   - 动态流式打字与折叠状态提示强化（`思维推演中 (纯中文)...`）；
   - 保证思维链折叠组件在不同模型与流式 token 场景下排版优雅、稳定展开。

3. **单测覆盖与 5 项全量门禁**：
   - 在 `engine/tests/test_writing_unit.py` 与 `test_writing_review.py` 中增补针对提示词纯中文思考链防线的断言测试；
   - 运行 5 项全量快速验证门禁并确保 100% 绿灯通过。

---

## 2. 允许修改

- `engine/app/writing/prompts.py`
- `engine/app/writing/writer.py`
- `engine/app/writing/outline.py`
- `engine/tests/**`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T31/**`

---

## 3. 禁止修改

- `generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `engine/app/writing/prompts.py` 中所有核心系统提示词（写作、大纲、提示词、修订、快速审阅、全维精审等）均已包含【纯中文绝对纯化防线】；
- [ ] `writer.py` 与 `outline.py` 用户提示词装配点均严密注入纯中文推演铁律；
- [ ] 前端 Step 3 与 Step 4 思考链指示器与折叠面板标题明确呈现纯中文推演标识；
- [ ] 5 项全量门禁（Vitest 151+、vue-tsc、build、pytest 127+、cargo check）全部绿灯通过。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（`desktop/`）
3. `npx vue-tsc --noEmit`（`desktop/`）
4. `npm run build`（`desktop/`）
5. `cargo check`（`desktop/src-tauri/`）
