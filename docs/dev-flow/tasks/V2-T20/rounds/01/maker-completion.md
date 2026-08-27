# Maker 交付报告 (Round 01)

## 1. 任务基本信息
- **任务编号**：V2-T20
- **轮次**：Round 01
- **有效合同**：`docs/dev-flow/tasks/V2-T20/01-planner-task-contract-v1.md`
- **转发消息**：`docs/dev-flow/tasks/V2-T20/02-planner-to-maker-message-v1.md`
- **精确起始 SHA**：`59af1cf74ca60cf625902bc9277d1ca4e7a83d78`
- **候选提交 SHA**：`45a94801d957ad81aff9dad54eb634c3c4507b8f`

---

## 2. 修改文件清单
### 前端（`desktop/`）
- `desktop/src/lib/markdown.ts`：升级 `normalizeMarkdown` 正则，已知大纲标题后紧随任意中文/空格/标点时无条件截断并插入 `\n\n`；升级 `extractSubHeadings`，确保返回纯净标题文本；
- `desktop/src/components/Step4Review.vue`：
  - 右侧长文档画布重构：移除每章顶部的 `.chapter-block-header` 与底部的 `.chapter-divider-rule`，形成 100% 连贯长文档流；
  - 左侧平铺一体化目录树：去除 `.chapter-tree-node` 独立卡片边框背景，由外层单一全局垂直滚动条滚动；
  - 将单章重新审阅触发按钮放置于右侧体检抽屉“各章评价”卡片中；
- `desktop/src/tests/markdown.test.ts`：增补无标点中文直接紧连正文、空格粘连、纯净提取等单测用例；
- `desktop/dist/**`：生产构建输出产物更新。

### 后端（`engine/`）
- `engine/app/writing/prompts.py`：在 `_BASE_WRITING_PROMPT` 与 `_MODIFY_SYSTEM_PROMPT` 中注入【标题换行硬约束（最高优先级）】与【Markdown 格式规范】；
- `engine/app/writing/writer.py`：
  - 新增 `normalize_chapter_markdown(text, skeleton)` 并在 `write_chapter`、`modify_chapter` 中全量执行规范化清洗；
  - 增强 `_build_chapter_write_args` 与 `_build_writing_system_prompt` 写作要求中的标题换行与格式约束；
- `engine/app/writing/rag.py`：增强 `query_rag`，支持接收 `topic` 与 `report_name` 参数，构造复合政务检索 Query（`f"{report_name} {topic} {query_text} 产业政策 规程 建设方案"`）；
- `engine/app/writing/router.py`：
  - `ChapterRequest` 增补 `report_name` 字段；
  - 在 `chapter` 与 `_stream_chapter` 中向 `query_rag` 传入 `topic` 与 `report_name`；
  - 在 `save_project_chapter` 中执行 `normalize_chapter_markdown`，确保落盘正文纯净规范；
- `engine/tests/test_writing_unit.py`：增补 `test_normalize_chapter_markdown_heading_separation_and_skeleton` 与 `test_query_rag_composite_query`；
- `engine/tests/test_writing_router.py`：更新提示词断言与章节保存断言用例。

---

## 3. 核心设计决策
1. **已知大纲标题靶向截断**：前端 `normalizeMarkdown` 提取大纲所有标题并降序排序后，匹配 `^(#{1,6}\s+...)`，只要标题后紧随剩余字符（无论是否有冒号、逗号、空格或直接为中文正文字符），无条件剥离首部标点并在已知标题边界处插入 `\n\n`，彻底根除“### 1.1.1 建设地点本项目位于...”此类粘连导致的标题加粗断行异常。
2. **Step 4 全景一体化长文档流**：移除右侧画布中人工制造的每章操作条与分隔线，使各章正文如 Word/飞书长文档般自然流转，通过章内 H1-H4 层次化排版直接呈现；左侧目录树改造为 Flat 扁平多级树，全局单一定高垂直滚动。
3. **复合政务 RAG 精准度提升**：外部政务联网检索词结合项目名称、产业方向与章节标题（`{report_name} {topic} {chapter_title} 产业政策 规程 建设方案`），大幅提高发改委、水利部等 `.gov.cn` 规范文件命中率。

---

## 4. 测试与门禁验证记录
严格执行全量门禁流水线：
1. **后端单元与路由测试**：`python -m pytest engine/tests -q`
   - 结果：**121 passed, 2 warnings in 67.93s**
2. **前端单元测试**：`npx vitest run`（`desktop/`）
   - 结果：**5 test files passed, 125 tests passed in 1.11s**
3. **前端 TypeScript 静态检查**：`npx vue-tsc --noEmit`（`desktop/`）
   - 结果：**0 errors, exit code 0**
4. **前端生产构建**：`npm run build`（`desktop/`）
   - 结果：**Built in 1.12s, exit code 0**
5. **桌面端 Rust / Tauri 检查**：`cargo check`（`desktop/src-tauri`）
   - 结果：**Finished dev profile in 0.93s, exit code 0**

---

## 5. 已知风险与冻结声明
- **已知风险**：无破坏性改动。所有大纲骨架与 Markdown 渲染向后兼容。
- **冻结声明**：本轮次编码工作已全部完成，代码树已验证通过，正式冻结并交回 Coordinator。
