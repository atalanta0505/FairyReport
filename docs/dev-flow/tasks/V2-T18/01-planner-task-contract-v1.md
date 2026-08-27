# 任务合同 V2-T18 v1 — 标题断行根除、Word树形导航窗格与问题句子级高亮定位

- 状态：ACCEPTED（已验收通过并锁定 SHA: `1e94dff51af135d16c33b1719470a24336d95cf5`，Checker Round 01 PASS）
- 依据：用户反馈（1）Markdown 渲染中标题行后几个字容易掉到正文行中；（2）Step 4 审阅左侧导航栏存在内嵌滚动条/无用展开按钮；（3）审阅问题清单点击未精准定位到具体句子。
- 精确起始 SHA：`e8d10d2653eb7b9c6655a8d27e6a4f0868eb1666`
- 候选交付 SHA：`1e94dff51af135d16c33b1719470a24336d95cf5`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **彻底根除标题断字与断行 Bug (`desktop/src/lib/markdown.ts`)**：
   - 移除 `normalizeMarkdown` 中基于常见词尾（如“分析/规范/任务/情况”）的过度启发式正则切分（杜绝 `8.1 经济影响分析` 误拆为 `8.1 经济影响` + `分析`、`1.3.3 主要标准规范` 误拆为 `1.3.3 主要标准` + `规范`、`1.1.2 项目建设目标与任务` 误拆为 `1.1.2 项目建设目标` + `与任务`）；
   - 大纲标题库前缀匹配（`knownHeadings`）仅在标题后紧跟中文标点符号（如 `，。：:（(《“`）时才执行断行拆分；
   - 只有单行内包含明确冒号/句号等正文标点时才执行标题正文拆分；
   - 在 `desktop/src/tests/markdown.test.ts` 中补充上述各类复合标题单行保持测试。

2. **左侧导航栏 Word 树形窗格重构与布局清爽化 (`desktop/src/components/Step4Review.vue`, `desktop/src/components/Step3Writing.vue`)**：
   - 删除左侧目录导航栏头部冗余的 `[ ⊞ 全部展开 ]` / `[ ⊟ 全部收起 ]` 按钮；
   - 移除 `.subheadings-subtree` 的局部 `max-height` 与内嵌 `overflow-y: auto`，彻底根除章节内部的次级滚动条/异常小横条；
   - 整体左侧导航栏改为统一的平滑主滚动条（Office Word 导航窗格模式），章（H1）/ 节（H2）/ 小节（H3）树形展开收起；
   - 在存在审阅问题的章节和小节标题旁标注醒目的问题数量预警角标（如 `⚠️ 2`）。

3. **审阅问题句子级精准定位与呼吸波纹高亮 (`desktop/src/lib/engineApi.ts`, `desktop/src/components/Step4Review.vue`, `engine/app/writing/prompts.py`)**：
   - `ReviewIssue` 接口增加 `quote?: string`（原文关键词或问题所在具体语句）；
   - `prompts.py` 审阅提示词要求输出 `quote` 字段；
   - 升级 `locateIssueInCanvas(issue)`：
     - 在正文 DOM 中递归查找包含 `issue.quote` 或 `issue.location` 或关键词的段落/表格/标题元素；
     - 调用 `targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' })` 使其精准居中展示；
     - 注入 `.issue-highlight-pulse` CSS 呼吸波纹黄色高亮类，闪烁 2.5 秒后平滑淡出恢复。

4. **单测适配与全量门禁**：
   - 更新 `desktop/src/tests/markdown.test.ts` 与 `desktop/src/tests/project.test.ts`；
   - 重新构建 `desktop/dist/**`；
   - 运行 5 项全量门禁（vitest, pytest, vue-tsc, build, cargo check）。

---

## 2. 允许修改

- `desktop/src/lib/markdown.ts`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/tests/**`
- `engine/app/writing/prompts.py`
- `engine/app/writing/writer.py`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T18/**`

---

## 3. 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `npx vitest run`（`desktop/`）全绿。
- [ ] `python -m pytest engine/tests -q` 全绿。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：
  1. 包含 `8.1 经济影响分析`、`1.3.3 主要标准规范`、`1.1.2 项目建设目标与任务` 的章节标题完整渲染为单行，后几个字不再掉到正文行；
  2. Step 4 左侧导航栏无多余按钮、无内部异常小横条，整栏平滑统一滚动，可顺畅折叠展开；
  3. 点击专家诊断问题清单中的「🎯 点击定位正文段落 →」，正文平滑居中滚动到问题所在段落/句子，并触发黄色呼吸波纹高亮。

---

## 5. 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `npx vue-tsc --noEmit`（workdir=`desktop`）
3. `npm run build`（workdir=`desktop`）
4. `python -m pytest engine/tests -q`
5. `cargo check`（workdir=`desktop/src-tauri`）
