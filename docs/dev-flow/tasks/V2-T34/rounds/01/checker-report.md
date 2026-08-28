# 验收审查报告：V2-T34 第 1 轮

- 目标任务：V2-T34（全面取消字数限制、Step 4 审阅单章对等重构与流式体验优化）
- 审查结论：**PASS（验收通过）**
- 基线 SHA（父提交）：`40cf4b0cbfebfa14aa5d97f8c0ffca78572b9a7b`
- 候选提交 SHA：`bb0c9b984843cfff6dd294d83c8cc65368e95e5d`
- 审查依据：`docs/dev-flow/tasks/V2-T34/01-planner-task-contract-v1.md`
- Maker 完工报告：`docs/dev-flow/tasks/V2-T34/rounds/01/maker-completion.md`

---

## 1. 修改范围与提交链核验

### 1.1 父提交与提交链
- **基线 SHA**：`40cf4b0cbfebfa14aa5d97f8c0ffca78572b9a7b`（任务合同 v1 就绪提交）
- **候选 SHA**：`bb0c9b984843cfff6dd294d83c8cc65368e95e5d`（`feat(review): 全面取消字数限制、Step 4 审阅单章对等同构与流式体验优化`）
- **父子关系**：父提交精确匹配，提交链合法完整。

### 1.2 修改文件范围核查 (`git diff --name-status`)
```
M  config.py
A  desktop/dist/assets/index-BgKgjNtH.js
D  desktop/dist/assets/index-CDLvACBN.js
A  desktop/dist/assets/index-Cb-HAlAv.css
D  desktop/dist/assets/index-Ck2vTNrJ.css
R  desktop/dist/assets/index-WsZcCzNj.js -> desktop/dist/assets/index-zZccpoBX.js
M  desktop/dist/index.html
M  desktop/src/components/Step2Outline.vue
M  desktop/src/components/Step3Writing.vue
M  desktop/src/components/Step4Review.vue
M  desktop/src/lib/engineApi.ts
M  desktop/src/tests/project.test.ts
M  engine/app/writing/router.py
M  engine/app/writing/templates_loader.py
M  engine/tests/fixtures/generic_source/templates/feasibility.json
M  engine/tests/fixtures/writing_source/templates/kexingxing_yanjiu.json
M  engine/tests/test_writing_router.py
M  generic_knowledge/templates/chanye_fazhan_guihua.json
M  generic_knowledge/templates/chubu_kexingxing.json
M  generic_knowledge/templates/gongcheng_zixun_xinxi.json
M  generic_knowledge/templates/hou_pingjia.json
M  generic_knowledge/templates/juece_zixun.json
M  generic_knowledge/templates/kexingxing_yanjiu.json
M  generic_knowledge/templates/qiye_fazhan_guihua.json
M  generic_knowledge/templates/shehui_pingjia.json
M  generic_knowledge/templates/touzi_jihui.json
M  generic_knowledge/templates/xiangmu_jianyishu.json
M  generic_knowledge/templates/xiangmu_pinggu.json
M  generic_knowledge/templates/xiangmu_shenqingshu.json
M  generic_knowledge/templates/yuanqu_fazhan_guihua.json
M  generic_knowledge/templates/zhengfu_shehuiziben.json
M  generic_knowledge/templates/zhongzi_zhuanbao_xinxi.json
M  generic_knowledge/templates/zhuanti_yanjiu.json
M  generic_knowledge/templates/zijin_shenqing.json
```
- **核查结论**：所有修改与构建产物均严格在合同约定的允许路径内，未触碰任何禁止修改目录或文件（如 `AGENTS.md`、`.gitignore` 等）。

---

## 2. 核心设计与代码实现审查

### 2.1 全面取消字数限制与长文推演支持
- **17 套标准报告模板清理**：`generic_knowledge/templates/*.json` 中全部 17 个模板 JSON 及 `engine/tests/fixtures/` 测试夹具已彻底清除 `total_words_max`、`per_chapter_max`、`summary_chapter_max` 和 `word_budget` 字段。
- **模板加载器与系统提示词**：`templates_loader.py` 与 `config.py` 字数上限默认返回 0（不设限制），提示词构建函数 `get_chapter_template_prompt` 不再输出计划字数要求，完全放开大模型自由长文深度推演。
- **前端大纲页面适配**：`Step2Outline.vue` 彻底移除了“目标字数：约 X 万字”徽标与模板卡片“约 X.X 万字”字数限制标签。

### 2.2 Step 3 构思卡片即时关闭与流式正文呈现 (`Step3Writing.vue`)
- **状态计算属性精准绑定**：
  ```ts
  const isThinkingStage = computed(() => {
    return (
      isCurrentChapterWriting.value &&
      projectStore.writingProgress?.stage !== "writing" &&
      (!currentChapterText.value || currentChapterText.value.trim().length === 0)
    );
  });
  ```
- **视图切换**：构思等待卡片绑定 `v-if="isThinkingStage"`，排版画布绑定 `v-show="!isThinkingStage"`。只要大模型思考结束推送首个正文字符或进入 `writing` 阶段，构思等待窗口毫秒级淡出关闭，正文画布立即现身并实时打字流式输出。

### 2.3 Step 4 审阅页面与 Step 3 左右架构 100% 对等重构 (`Step4Review.vue`)
- **左侧导航目录树完全同构**：
  - 采用与 Step 3 完全一致的目录树结构与布局（`grid-template-columns: 350px 1fr`），选哪章右侧就展示哪章；
  - 仅当前激活选中的章节高亮（蓝底序号圆圈）并展开其子标题，其它章节默认折叠收起；
  - 状态药丸（`审阅中…` / `已完成 ✓` / `待撰写`）与预警角标（`⚠️ N`）完整呈现；
  - 支持小节层级标题直达正文与诊断问题抽屉。
- **右侧主画布单章聚焦**：
  - 专注展示当前选中章节的审阅与编辑内容，支持直接在排版正文上就地修改并自动落盘保存；
  - 顶部提供【📝 最终排版正文】与【🔍 修订差异对比】就地切换开关；
  - Diff 视图采用全宽单栏段落级内联比对（展示增删改统计与单栏带行号代码比对），支持采纳、重新生成与放弃修订；
  - 诊断问题高亮与 540px 全高右侧专家诊断总台账抽屉支持双向定位与脉冲动效（`canvas-issue-anim` 与 `ref-card-anim`）。
- **审阅操作简化对等**：
  - 顶栏提供 `[ 🚀 一键全书审阅 ]`（支持停止与实时推演窗）与 `[ 🔍 审阅本章 ]`；
  - **彻底废除“常规审查”与“全维精审”二选一**，统一执行国家发改委投资项目最高水准专业质检。

### 2.4 测试用例完备性
- `desktop/src/tests/project.test.ts`：新增 `模板取消字数限制适配与自由长文推演支持` 与 `isThinkingStage 计算逻辑与流式首字到达即时切换` 单元测试；
- `engine/tests/test_writing_router.py`：更新模板默认 `total_words_max == 0` 断言。

---

## 3. A 级快速验证独立复跑记录

Checker 独立执行全部 5 项全量门禁，结果如下：

| 验证项目 | 执行命令 | 执行结果 | 耗时/备注 |
| :--- | :--- | :---: | :--- |
| **前端单元测试** | `npx vitest run`（`desktop/`） | **PASS** | 6 test files, 169 passed (100%) |
| **前端类型检查** | `npx vue-tsc --noEmit`（`desktop/`） | **PASS** | 0 type errors |
| **前端生产构建** | `npm run build`（`desktop/`） | **PASS** | 构建成功，耗时 1.20s |
| **后端单元测试** | `python -m pytest engine/tests -q` | **PASS** | 129 passed, 2 warnings (100.14s) |
| **Rust 后端检查** | `cargo check`（`desktop/src-tauri/`） | **PASS** | finished dev profile in 1.01s, 0 errors |

---

## 4. 审查发现与待办事项

### 4.1 阻断项（Blockers）
- **无**。

### 4.2 非阻断风险与优化建议（Non-blocking Risks）
- **无**。

### 4.3 待产品负责人执行的 B 级人工项（Manual B-Level Items）
1. 启动桌面端应用，进入步骤 2（大纲编制），确认所有 14 类模板卡片及大纲信息栏中已无任何“目标字数：约 X 万字”或“约 X.X 万字”标签；
2. 进入步骤 3（报告撰写），点击生成某章节，观察大模型推理完成后向前端推送首个字符时，构思等待窗口是否立即平滑关闭并流式打字输出；
3. 进入步骤 4（审阅定稿），体验与步骤 3 100% 对等的目录树与单章聚焦主画布，测试“一键全书审阅”与“审阅本章”，并在右侧切换“最终排版正文”就地编辑与“修订差异对比 (Diff)”单栏内联视图，点击问题标记核验右侧诊断抽屉的脉冲定位联动。

---

## 5. 验收判定

- 判定结论：**PASS（验收通过）**
- 建议协调员：锁定当前候选提交 `bb0c9b984843cfff6dd294d83c8cc65368e95e5d` 为有效基线，推进任务收尾与归档。
