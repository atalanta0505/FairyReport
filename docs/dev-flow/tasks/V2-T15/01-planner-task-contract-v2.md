# 任务合同 V2-T15 v2 — Step 4 全书一体化审阅与全景单栏内联工作台重构

- 状态：ACCEPTED（2026-08-26 独立 Checker 验收通过，锁定 SHA：`039885c806542586472c0bd1a0b6765ca4b3e2bc`）
- 依据：产品负责人确认 5 项重构诉求（彻底消除纵向卡片挤压、全书一体化审阅与持久化、废除百分制改用达标度、左侧全书大纲导航+右侧全文画布、单栏内联代码式 Diff 与标签页切换、清除硬编码水利词）
- 精确起始 SHA：`999da87f8596832bd44c1db6648eb100b4ffdc14`
- 锁定候选 SHA：`039885c806542586472c0bd1a0b6765ca4b3e2bc`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **Step 4 界面架构重构：全书一体化工作台与 100% 满屏正文 (`desktop/src/components/Step4Review.vue`)**：
   - **右侧主画布 100% 空间专属展示全文**：
     - 彻底移除正文上方纵向堆叠的诊断折叠卡片与 AI 修订大面板，正文享有从顶到底的完整可视高度；
     - 顶部工作台提供 **「📝 最终排版正文」**、**「🔍 修订差异对比 (Diff)」** 与 **「📝 Markdown 源码」** 视图标签页切换；
     - 排版正文视图支持直接在排版文字上就地润色，防抖自动保存；
   - **单栏内联代码式 Diff 全宽呈现**：
     - 彻底移除狭窄拥挤的左右双栏对比，全宽采用单栏内联段落级高亮（浅红删除线 `<s>` + 浅绿新增背景 `<ins>`）；
     - Diff 视图顶部常驻 `[ ✅ 采纳全部修订并保存为正文 ]`、`[ 🔄 重新生成 ]` 与 `[ ↩ 放弃本次修订 ]`；
   - **左侧全书多级标题导航栏**：
     - 采用与 Step 3 类似的目录树结构，展示全书所有章节的 1、2、3 级标题（章、节、小节）；
     - 支持全章一键展开/收起；
     - 点击任意子标题，右侧全文画布自动平滑滚动定位并触发呼吸高亮；
     - 存在批注或数据疑点的小节自动标注小黄点/小红点预警；
   - **全高右侧抽屉（Slide-over Drawer）展示诊断详情与参考资料**：
     - 点击右上角 **「📋 专家诊断报告 (N)」**，从右侧滑出宽 `540px`、高 `100vh` 的全景抽屉，完整呈现全书问题清单、跨章数值核验表、缺失资料清单与综合建议，不挤占正文；
     - 点击抽屉中任意问题项，自动平滑滚动左侧正文至对应段落；
     - 点击右上角 **「📚 全书参考资料」**，从右侧滑出全书命中的底稿文件与标准规程清单。
2. **全书全维审阅与达标度评价体系升级 (`desktop/src/components/Step4Review.vue`, `desktop/src/stores/project.ts`)**：
   - **废除 100 分制**：改用客观的 **报告达标度 / 健康状态**（如：`🟢 达标（优良）`、`🟡 待完善（建议补正 3 处）`、`整体完整度 95%`）；
   - **一键全书全维审阅**：提供顶部醒目的 `[ 🚀 全书全维专家审阅 ]`，一键扫描全书合规合法、跨章数据自洽、工艺逻辑与缺失资料，带 4 阶段动态心跳与秒级计时器；
   - **全书 AI 协同修订**：支持全局统筹前后文一致性进行全书修订。
3. **全书审阅档案持久化 (`engine/app/writing/router.py`, `desktop/src/lib/engineApi.ts`, `desktop/src/stores/project.ts`)**：
   - 后端新增 `/projects/{name}/full_review` GET/POST/DELETE 接口，将全书审阅总档案持久化至 `full_review.json`；
   - 前端 Pinia store 增加 `fullBookReview` 状态与双备份机制（后端 `full_review.json` + `localStorage`）；
   - 进入 Step 4 或切换项目时自动加载并秒级恢复全书审阅与诊断状态。
4. **清除全部硬编码“水利”字样 (`desktop/src/**`, `engine/**`)**：
   - 彻底清除所有硬编码“水利”词汇，统一替换为通用的《国家发改委与行业编制规程符合性审查》、《10.5pt 工程咨询出版级排版》，并动态适配项目真实行业。
5. **单元测试与产物构建**：
   - 增补 `desktop/src/tests/` 和 `engine/tests/` 对应测试用例；
   - 重新构建 `desktop/dist/**`。

---

## 2. 允许修改

- `desktop/src/components/Step4Review.vue`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/lib/markdown.ts`
- `desktop/src/lib/diff.ts`
- `desktop/src/stores/project.ts`
- `engine/app/writing/router.py`
- `engine/tests/test_writing_review.py`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T15/**`

---

## 3. 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [x] `npx vitest run`（`desktop/`）全绿（119/119 通过）。
- [x] `python -m pytest engine/tests -q` 全绿（94 通过）。
- [x] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [x] B 级实跑：
  1. Step 4 右侧工作区 100% 满屏展示全文，无纵向折叠卡片挤压；
  2. 左侧展示全书多级标题导航，点击可平滑跳转至全文对应位置；
  3. 彻底移除双栏 Diff，单栏内联 Diff 全宽展示且红绿高亮清晰，标签页切换顺畅；
  4. 点击右上角「📋 专家诊断报告」与「📚 全书参考资料」可滑出右侧抽屉，点击问题可定位正文；
  5. 废除百分制，改为报告达标度与完成度状态；
  6. 全书审阅结果持久化保存并在重启/刷新后准确恢复；
  7. 全文无任何硬编码“水利”违和字样。

---

## 5. 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `python -m pytest engine/tests -q`
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
5. `cargo check`（workdir=`desktop/src-tauri`）
