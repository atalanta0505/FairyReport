# V2-T34 任务第 1 轮 Maker 完工报告

## 1. 任务基本信息
- **任务编号**：V2-T34
- **任务轮次**：第 1 轮（Round 01）
- **起始基准 SHA**：`40cf4b0cbfebfa14aa5d97f8c0ffca78572b9a7b`
- **候选代码提交 SHA**：`bb0c9b984843cfff6dd294d83c8cc65368e95e5d`
- **有效任务合同**：`docs/dev-flow/tasks/V2-T34/01-planner-task-contract-v1.md`
- **有效转发消息**：`docs/dev-flow/tasks/V2-T34/02-planner-to-maker-message-v1.md`

---

## 2. 核心修改文件清单与说明

### 2.1 全面取消字数限制相关修改
1. `generic_knowledge/templates/*.json`（共 17 类专业报告模板）：
   - 彻底移除了所有根级别 `total_words_max`、`per_chapter_max`、`summary_chapter_max` 字段以及每个章节中的 `word_budget` 字段。
2. `engine/tests/fixtures/generic_source/templates/feasibility.json` & `engine/tests/fixtures/writing_source/templates/kexingxing_yanjiu.json`：
   - 清理测试夹具中的字数上限字段。
3. `engine/app/writing/templates_loader.py` & `config.py`：
   - 更新字数获取函数在字段缺失时默认返回 0（不设限制）；
   - 更新提示词装配函数 `get_chapter_template_prompt`，不再强制输出计划字数要求，支持大模型自由深度长文推演。
4. `engine/app/writing/router.py` & `engine/tests/test_writing_router.py`：
   - 适配 `TemplateItemOut.total_words_max` 默认值为 0，更新路由单测断言。
5. `desktop/src/components/Step2Outline.vue`：
   - 移除模板卡片及大纲头部的“目标字数：约 X 万字”徽标与字数规划约束，更新引导文案为规范编制指南。

### 2.2 Step 3 构思卡片即时关闭与流式正文呈现
1. `desktop/src/components/Step3Writing.vue`：
   - 引入 `isThinkingStage = computed(() => isCurrentChapterWriting.value && projectStore.writingProgress?.stage !== 'writing' && (!currentChapterText.value || currentChapterText.value.trim().length === 0))`；
   - 构思卡片绑定 `v-if="isThinkingStage"`，编辑排版画布绑定 `v-show="!isThinkingStage"`；
   - 保证一旦大模型输出首个正文字符或进入 `writing` 阶段，构思占位卡片立即无缝关闭，流式正文直接呈现在 10.5pt 规范排版画布上。

### 2.3 Step 4 审阅页面与 Step 3 左右架构 100% 对等重构
1. `desktop/src/components/Step4Review.vue`：
   - **单章聚焦主画布**：基于 `projectStore.selectedChapterSeq` 进行单章出版级排版展示，支持直接就地点击编辑并在 300ms 内自动落盘保存；
   - **左侧目录导航树同构**：采用与 Step 3 100% 对等的平铺一体化目录树（`grid-template-columns: 350px 1fr`），支持当前选中章圆圈高亮、子标题展开、审阅状态药丸、预警角标 `⚠️ N` 与小节直达；
   - **单一最高标准**：彻底废除“常规审查”与“全维精审”模式切换胶囊，统一执行国家发改委投资项目编制最高水准；
   - **视图模式切换**：提供“📝 最终排版正文”与“🔍 修订差异对比”Tab 切换，Diff 视图采用全宽单栏段落级内联比对，清晰展示增删改统计；
   - **双向联动与脉冲动效**：正文中的审阅问题高亮与 540px 全高专家诊断总台账抽屉支持双向点击定位与脉冲动效（`issue-card-pulse`、`issue-canvas-pulse`）。
2. `desktop/src/lib/engineApi.ts`：
   - 完善 `TemplateItem`（`total_words_max?: number`）、`ReviewIssue` 与 `NumericalCheckItem` 类型定义。

### 2.4 自动化测试补充
1. `desktop/src/tests/project.test.ts`：
   - 新增 `V2-T34: 模板取消字数限制适配与自由长文推演支持` 单元测试；
   - 新增 `V2-T34: isThinkingStage 计算逻辑与流式首字到达即时切换` 单元测试。

---

## 3. 门禁验证结果（严格按 5 步顺序执行）

| 验证序号 | 命令 | 预期与执行结果 | 状态 |
| :--- | :--- | :--- | :--- |
| **Step 1** | `npx vitest run` | 6 个测试文件、169 项测试全部通过（0 失败） | **PASS** |
| **Step 2** | `npx vue-tsc --noEmit` | 0 处类型错误，编译退出码 0 | **PASS** |
| **Step 3** | `npm run build` | 构建成功，生成优化后的生产包（1.18s） | **PASS** |
| **Step 4** | `python -m pytest engine/tests -q` | 129 项 Python 测试用例全部通过（105.26s） | **PASS** |
| **Step 5** | `cargo check` | Tauri Rust 后端语法与类型检查通过（1.23s） | **PASS** |

---

## 4. 关键设计决策与实现细节

1. **字数限制向后兼容性**：
   - 在模板及引擎中完全解除字数限制的同时，保留数据模型对旧字段的容错处理（默认返回 0），确保旧项目数据无缝迁移。
2. **Step 3 与 Step 4 视觉与心智模型统一**：
   - 用户在步骤 3 写作与步骤 4 审阅之间切换时，左侧目录树结构、选中状态徽标、高亮颜色与布局完全一致，消除了原先卡片墙视图带来的认知负荷。
3. **单章聚焦与段落级 Diff 对比**：
   - 摒弃左右双栏在小屏幕下的局促感，采用全宽单栏内联 Diff 呈现，结合行号与颜色背景，使专家修订差异一目了然。

---

## 5. 已知风险与代码冻结声明

- **已知风险**：无已知阻塞性风险。
- **代码冻结声明**：Maker 确认已完成本轮全部需求开发并通过全部 5 项门禁验证，现正式冻结候选代码并交付候选 SHA：`bb0c9b984843cfff6dd294d83c8cc65368e95e5d`，请求进入 Checker 独立验收环节。
