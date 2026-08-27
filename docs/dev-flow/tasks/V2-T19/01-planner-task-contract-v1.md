# 任务合同 V2-T19 v1 — 审查双模式（⚡ 常规审查 vs 🔍 全维精审）、耗时预估与写作句数/字数硬控制

- 状态：ACCEPTED（2026-08-27 独立 Checker 验收通过，锁定 42899d71aaa81cc17e8dd81abfe486dbecd16d46）
- 依据：用户关于审查时长压缩、常规审查模式、纯中文思考链与写作字数硬控制的要求
- 精确起始 SHA：`456a71acc408bf45f88dd6af67eb77dbf49ff570`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **审查双模式与纯中文思考链 (`engine/app/writing/prompts.py`, `writer.py`, `router.py`)**：
   - 新增 `FAST_REVIEW_SYSTEM_PROMPT`（⚡ 常规审查：极速聚焦三大维度：1️⃣重点名词称谓一致性、2️⃣核心数值前后自洽性、3️⃣发改委与行业底线合规），单章输出精简诊断，推理耗时压缩 70% 至 8~12 秒；
   - 保持 `FULL_EXPERT_REVIEW_SYSTEM_PROMPT`（🔍 全维逐句精审：全科专家诊断）；
   - 在所有审阅提示词与写作提示词中强力注入纯中文思考链约束（`严禁任何英文思考句或英文词汇，100% 纯中文推演`）；
   - 后端 `/writing/review` 与 `/writing/review_stream` 支持 `mode="fast" | "all" | "compliance" | "numerical"`。
2. **前端审查模式切换与预估耗时确认弹窗 (`desktop/src/components/Step4Review.vue`, `project.ts`)**：
   - 顶栏提供 `[ ⚡ 常规审查 ]` 与 `[ 🔍 全维精审 ]` 切换入口（默认常规审查）；
   - 点击全书审阅时，展示耗时预估卡片（如：`⚡ 常规审查预计耗时 1~2 分钟，是否开始？`），用户确认后即刻启动流式体检；
   - 维持秒级流式计时器与一键中止功能。
3. **写作末级小节句数与字数硬控制 (`engine/app/writing/writer.py`, `prompts.py`)**：
   - 升级 `_build_section_quota_block`：不仅输出字数上限，更根据每句 35~50 字的专业规范换算并注入明确的句数硬约束指令（例如：`本小节正文控制在 X 句话以内（以句号『。』为准计），总字数约 Y 字，达到句数上限即行收尾，严禁长篇大套罗列空泛套话`）；
   - 升级写作系统提示词中的字数控制要求。
4. **单测覆盖与快速验证**：
   - 增补 `engine/tests/` 和 `desktop/src/tests/` 针对 `fast` 审查模式、纯中文思考约束、末级小节句数配额生成的单元测试；
   - 运行 5 项全量门禁（pytest, vitest, vue-tsc, build, cargo check）。

---

## 2. 允许修改

- `engine/app/writing/prompts.py`
- `engine/app/writing/writer.py`
- `engine/app/writing/router.py`
- `engine/tests/**`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/stores/project.ts`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T19/**`

---

## 3. 禁止修改

- `backend/**`、根目录核心代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿。
- [ ] `npx vitest run`、`npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] 常规审查 `fast` 模式正常运行，提示词聚焦三大核心维度且输出精简。
- [ ] 思考链约束包含 100% 纯中文指示。
- [ ] 小节配额包含明确的句数上限约束（以句号为准）。
- [ ] 前端 Step 4 提供模式切换与预估耗时确认。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
5. `cargo check`（workdir=`desktop/src-tauri`）
