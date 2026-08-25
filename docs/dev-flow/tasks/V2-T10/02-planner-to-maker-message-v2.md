# 致 Maker 转发消息 — V2-T10 第 2 轮（Markdown 排版渲染与三模视图）

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`6361a520cf8198f121d58fe18b8fe6676cf20a2e`
- 有效合同：`docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v2.md`

## 唯一主要行为

实现 Step 3 章节 Markdown 排版渲染与三模视图切换（排版预览 / 源码编辑 / 分栏对照），让用户告别黑压压的源码堆积，享受清爽的排版视觉效果：
1. **新建 `desktop/src/lib/markdown.ts`**：
   - 编写轻量高效的 Markdown-to-HTML 解析函数 `renderMarkdown(md: string): string`；
   - 支持 H1~H4 标题、段落换行、粗体/斜体、来源标签 `【源:...】` 自动高亮徽章、列表、表格和引用块；
   - 纯原生 TS 实现，0 外部 npm 依赖。
2. **重构 `desktop/src/components/Step3Writing.vue`**：
   - 增加视图模式状态 `viewMode: ref<'preview' | 'edit' | 'split'>('preview')`；
   - 顶部工具栏增加切换按钮：`[👁️ 排版预览 (推荐)]`、`[✏️ 源码编辑]`、`[📖 分栏对照]`；
   - **排版预览区 (`.markdown-rendered-view`)**：
     - 美观的报告排版样式（标题边框、段落 1.8 行高与间距、来源标签圆角徽章 `tag-badge`、表格边框斑马纹）；
     - 流式输出时实时响应并打字机平滑自动滚屏；
   - **源码编辑区 (`.markdown-raw-editor`)**：
     - 纯文本编辑，失焦/输入防抖实时落盘；
   - **分栏对照区 (`.markdown-split-view`)**：
     - 左栏源码编辑，右栏实时排版预览。
3. **单元测试与产物**：
   - 新建 `desktop/src/tests/markdown.test.ts`；
   - 重建 `desktop/dist/**`。

## 允许修改

- `desktop/src/lib/markdown.ts` [NEW]
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/tests/markdown.test.ts` [NEW]
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T10/**`

## 禁止修改

- `engine/**`、`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

## 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `npx vue-tsc --noEmit`（workdir=`desktop`）
3. `npm run build`（workdir=`desktop`）
4. `python -m pytest engine/tests -q`

## 完成时

1. 只提交允许范围（`desktop/**` 候选提交）；
2. 完成说明写到 `docs/dev-flow/tasks/V2-T10/rounds/02/maker-completion.md`，单独提交；
3. 不 amend、不 rebase、不 push；
4. 冻结工作树交回。
