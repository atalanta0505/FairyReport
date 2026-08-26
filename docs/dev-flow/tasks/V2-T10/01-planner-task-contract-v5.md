# 任务合同 V2-T10 v5 — 阶段持久化自恢复与全景小节标题正文智能解耦

- 状态：ACCEPTED（2026-08-26 Checker 验收通过，候选 SHA：9a63cca2fff7cfc4a2ec6a871144e9e115b73dca）
- 依据：用户实测截图及要求：
  1. 启动应用后自动恢复并进入用户上次所处的阶段页面（原 `sessionStorage` 仅在单会话有效，应用关闭重启后被重置为 1）；
  2. 依然存在部分最低级标题（如 `1.4.1 主要研究结论经研究论证，`、`1.4.2 问题与建议重点关注问题：`、`2.2.1 与经济社会发展规划衔接性国家...`、`2.2.2 与区域规划衔接性从...`、`2.2.4 与国土空间规划衔接性《利辛县...`、`2.3.1 宏观层面必要性从...`、`2.3.4 建设时机适当时当前` 等）与正文紧贴粘连，左侧导航树与右侧编辑器均受影响。
- 精确起始 SHA：`5335509930f78a7c2feac1b570220c8227bda641`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **跨会话阶段与项目持久化自恢复 (`desktop/src/stores/project.ts`)**：
   - 将 `getStoredStep()`、`setStoredStep(step)`、`getStoredProjectName()`、`setStoredProjectName(name)` 从 `sessionStorage` 升级为 `localStorage`（带 `sessionStorage` 降级兼容）；
   - 确保应用关闭、重启或刷新后，直接恢复到用户之前所处的精确阶段步骤（Step 1~5）及已选项目，杜绝回跳。
2. **全景小节标题正文智能解耦 (`desktop/src/lib/markdown.ts` & `Step3Writing.vue`)**：
   - **大纲标题库提取与精准断行（第一道防线）**：
     - 在 `markdown.ts` 中新增/导出 `extractOutlineHeadings(outlineMd: string): string[]`，提取大纲中全部 `#` ~ `####` 纯净标题；
     - 在 `Step3Writing.vue` 中提取 `projectStore.outlineMd` 的大纲标题列表，统一传入 `markdownToHtml` 与 `extractSubHeadings`；
     - 在 `normalizeMarkdown` 中，针对传入的已知大纲标题执行全局正则精确匹配，将粘连的后续正文强行拆分为 `$1\n\n$2`；
   - **工程咨询行业标题词法特征识别断行（第二道防线）**：
     - 在 `normalizeMarkdown` 中增强通用标题模式正则：
       `/(#{1,6}\s+\d+(?:\.\d+)*\s+[\u4e00-\u9fa5\w、—\-\/（）()]{1,20}?(?:概况|背景|进展|情况|分析|方案|建议|结论|目标|任务|内容|规模|地点|工期|来源|估算|指标|信息|依据|政策|规范|成果|其他|符合性|衔接性|必要性|适当时|要求|保障|评估|设计|组织|测算|预算|说明|构成|论证|原则|措施|布局|标准|选址|模式|效益|影响|评价|预案|附件|附表|附图))([，。：:（(《“\u4e00-\u9fa5].*)$/gm`
       自动将其拆解为 `$1\n\n$2`；
     - 全面覆盖“主要研究结论”、“问题与建议”、“与经济社会发展规划衔接性”、“宏观层面必要性”、“建设时机适当时”等各行业小节标题；
3. **单元测试与产物重构**：
   - 在 `desktop/src/tests/project.test.ts` 中更新为 `localStorage` 阶段持久化单测；
   - 在 `desktop/src/tests/markdown.test.ts` 中增加针对 1.4.1、1.4.2、2.2.1、2.2.2、2.2.4、2.3.1、2.3.4 等全场景小节粘连解耦单测；
   - 重新构建 `desktop/dist/**`。

---

## 2. 允许修改

- `desktop/src/stores/project.ts`
- `desktop/src/lib/markdown.ts`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/tests/project.test.ts`
- `desktop/src/tests/markdown.test.ts`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T10/**`

---

## 3. 禁止修改

- `backend/**`、`engine/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `npx vitest run`（`desktop/`）全绿（覆盖 localStorage 持久化及多场景小节粘连解耦）。
- [ ] `python -m pytest engine/tests -q` 全绿。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：
  1. 重启应用后自动停留在 Step 3（或用户最后停留的步骤）；
  2. `1.4.1 主要研究结论`、`1.4.2 问题与建议`、`2.2.1 与经济社会发展规划衔接性`、`2.2.2 与区域规划衔接性` 等全部小节标题与正文完全断开成独立段落；
  3. 左侧子标题目录纯净展示，不包含正文文本。

---

## 5. 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `npx vue-tsc --noEmit`（workdir=`desktop`）
3. `npm run build`（workdir=`desktop`）
4. `python -m pytest engine/tests -q`
