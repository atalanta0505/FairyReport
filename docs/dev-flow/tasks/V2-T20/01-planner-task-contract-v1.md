# 任务合同 V2-T20 v1 — 正文粘连彻底根除、Step 4 全景一体化长文档重构与外部政务 RAG 精准度增强

- 状态：READY_FOR_MAKER（2026-08-27 用户反馈自动批准）
- 依据：用户关于正文首句与标题粘连复现、审阅修改页面去章卡片分栏化/一体化大纲树与全局滚动条、外部 RAG 实效性的要求
- 精确起始 SHA：`cc37d05b68ba6e414e05fd0d96feea2a357819df`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **正文标题与首句粘连双端彻底根治 (`desktop/src/lib/markdown.ts`, `engine/app/writing/`)**：
   - **前端 `normalizeMarkdown` 升级**：针对传入的 `knownHeadings` 大纲标题库，不再依赖标点符号，只要匹配到已知大纲标题且该行后面还有紧随字符（无论中文正文字符、空格或标点），一律在标题边界处强制截断并插入双换行 `\n\n`；
   - **后端 Prompt 强化**：在写作系统提示词与章节写作要求中强力注入【标题换行硬约束】标注文档正误范例，禁止标题与正文同名同句同排输出；
   - **后端 Python 存储级清洗**：在返回前端及落盘保存时，对章节文本执行 Markdown 标题换行规范化。
2. **Step 4 审阅修改页面彻底一体化长文档重构 (`desktop/src/components/Step4Review.vue`)**：
   - **左侧导航栏**：彻底去除每章独立的卡片盒子（`.chapter-tree-node` 边框盒子），重构为类似 Word / 飞书的 **平铺式一体化多级目录树（Flat Unified Tree）**；配置统一的外层垂直滚动条，全书所有章节与子标题在同一个平滑滚动面板中自如滚阅；
   - **右侧主工作台**：彻底移除每章上方的操作卡片条（`[第1章] 第一章 概述...`）与章末分界线（`-------- 第 1 章 完 --------`），呈现 **100% 连贯的完整出版级报告长文档**（第一章正文结束后自然过渡到第二章标题与正文）；支持在全文任意位置就地输入编辑、光标自由跨章移动，防抖 300ms 自动按所属章节切片回存。
3. **外部政务 RAG 复合检索 Query 精准化增强 (`engine/app/writing/rag.py`, `router.py`)**：
   - 优化检索 Query 构造，从单一章名升级为智能复合检索词（`{project_name} + {topic} + {chapter_title} + 产业政策/工程标准/发改批复`），显著提升在 `.gov.cn` 权威政务网站上的检索命中率，在正文中生成真实可靠的 `🏷️ 【网:xxx】` 证据链。
4. **单测覆盖与快速验证**：
   - 增补 `desktop/src/tests/markdown.test.ts`、`project.test.ts` 及 `engine/tests/` 针对无标点粘连拆解、一体化树形导航与复合检索的单测；
   - 运行 5 项全量门禁（pytest, vitest, vue-tsc, build, cargo check）。

---

## 2. 允许修改

- `desktop/src/lib/markdown.ts`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `engine/app/writing/prompts.py`
- `engine/app/writing/writer.py`
- `engine/app/writing/rag.py`
- `engine/app/writing/router.py`
- `engine/tests/**`
- `docs/dev-flow/tasks/V2-T20/**`

---

## 3. 禁止修改

- `backend/**`、根目录核心文件、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿。
- [ ] `npx vitest run`、`npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] 无论标题后是否带标点，大纲标题与正文首句均 100% 独立成行，无任何粘连粗体现象。
- [ ] Step 4 左侧导航栏呈平铺一体化目录树，外层带全局垂直滚动条，无独立章卡片盒子。
- [ ] Step 4 右侧画布呈现 100% 连贯长文档流，无多余的章操作卡片条和章完分界线。
- [ ] 外部 RAG 检索支持复合政务 Query 增强。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
5. `cargo check`（workdir=`desktop/src-tauri`）
