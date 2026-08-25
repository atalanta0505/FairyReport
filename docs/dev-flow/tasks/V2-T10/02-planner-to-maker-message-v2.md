# 致 Maker 转发消息 — V2-T10 第 2 轮（单栏排版就地编辑器 + 标题跳转定位）

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`6361a525f053bc7c98e1ae1871a25ee761a2938a`
- 有效合同：`docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v2.md`

## 唯一主要行为

实现 Step 3 章节写作界面的单栏排版就地可编辑画布以及左侧多级标题点击精准定位跳转：
1. **新建轻量零依赖 Markdown 解析库 (`desktop/src/lib/markdown.ts`)**：
   - 导出 `markdownToHtml`（生成带 ID 的 H1~H4、加粗、列表、表格、段落语义化 HTML）；
   - 导出 `extractSubHeadings`（提取各章所有子标题及对应锚点 ID）；
   - 导出 `htmlToMarkdown`（就地编辑内容反向转换回 Markdown 文本）；
2. **重构 `Step3Writing.vue` 正文编辑区**：
   - 使用单个 `<div contenteditable="true" class="rich-rendered-editor">` 作为主编辑画布，不再分栏，直接呈现优美的排版格式；
   - 支持流式生成时打字机实时排版渲染，生成后可直接在文字上就地编辑输入；
   - 顶部提供小巧的视图切换按钮（`👁️ 排版视图` / `📝 源码视图`）；
3. **左侧章节导航栏增强**：
   - 展开已完成章节的子标题树（H2 / H3 / H4）；
   - 点击子标题链接自动平滑滚动并对目标标题执行呼吸高亮动画；
4. **单测与产物**：
   - 新建 `desktop/src/tests/markdown.test.ts` 测试解析与反向转换；
   - 运行 vitest、vue-tsc、build 与 cargo check。

## 允许修改

- `desktop/src/lib/markdown.ts` [NEW]
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/tests/markdown.test.ts` [NEW]
- `desktop/src/tests/project.test.ts`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T10/**`

## 禁止修改

- `engine/**`、`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

## 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `npx vue-tsc --noEmit`（workdir=`desktop`）
3. `npm run build`（workdir=`desktop`）

## 完成时

1. 只提交允许范围（`desktop/**` 候选提交）；
2. 完成说明写到 `docs/dev-flow/tasks/V2-T10/rounds/02/maker-completion.md`，单独提交；
3. 不 amend、不 rebase、不 push；
4. 冻结工作树交回。
