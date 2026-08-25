# 致 Maker 转发消息 — V2-T10 第 3 轮（排版引擎与标题断行规范化修复）

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`7f4bb358fc5500c50dc573bba7d6e641774e6224`
- 有效合同：`docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v3.md`

## 核心修复点

1. **`desktop/src/lib/markdown.ts`**：
   - 增加 `normalizeMarkdown(md: string): string` 预处理：
     - 正则 `([^\n])\s*(#{1,6}\s+)` -> `$1\n\n$2`，强制在粘连的标题标记前补齐换行，彻底拆开 `# 第一章...## 1.1...`；
     - 导出并在 `markdownToHtml` 与 `extractSubHeadings` 入口调用 `normalizeMarkdown`；
2. **`desktop/src/components/Step3Writing.vue`**：
   - 修复 scoped CSS 深度选择器：统一使用 `.rich-rendered-editor :deep(h1)`、`.rich-rendered-editor :deep(p)` 等（替换错误的 `:deep(.rich-rendered-editor h1)`）；
   - 正文字体规范化：
     - `p`：`font-size: 14.5px; font-weight: 400; color: #334155; line-height: 1.85; margin: 0 0 14px 0; text-indent: 2em; text-align: justify;`
     - `h1`: 20px, 700; `h2`: 17px, 600; `h3`: 15px, 600; `strong`: 600, `#0f172a`；
   - 左侧导航多级标题树优化：
     - 过滤 H1（卡片头部已有章标题），展示 H2（缩进 10px）与 H3/H4（缩进 20px/30px），单行省略截断；
3. **单测与产物**：
   - `desktop/src/tests/markdown.test.ts` 补充粘连 Markdown 自动断行测试；
   - 重建 `desktop/dist/**`。

## 允许修改

- `desktop/src/lib/markdown.ts`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/tests/markdown.test.ts`
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
2. 完成说明写到 `docs/dev-flow/tasks/V2-T10/rounds/03/maker-completion.md`，单独提交；
3. 不 amend、不 rebase、不 push；
4. 冻结工作树交回。
