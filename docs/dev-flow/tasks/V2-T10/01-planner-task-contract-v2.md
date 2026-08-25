# 任务合同 V2-T10 v2 — Step 3 单栏排版就地编辑器 + 章节多级标题导航与精确定位

- 状态：READY_FOR_MAKER（2026-08-25 产品负责人提出两项关键体验增强）
- 依据：用户实测流式写作很好，提出两项优化需求：
  1. 正文编辑框不分栏，直接在原文本框内显示为排版后的 Markdown 预览格式且支持直接就地编辑；
  2. 章节完成后，在左侧导航栏中呈现该章所有层级的子标题链接，点击某一子标题后光标与视口立即平滑跳转定位到正文对应位置。
- 精确起始 SHA：`6361a525f053bc7c98e1ae1871a25ee761a2938a`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

实现 Step 3 单栏排版就地可编辑渲染引擎与左侧多级标题目录树跳转定位：
1. **轻量级零依赖 Markdown 排版与标题解析库 (`desktop/src/lib/markdown.ts`)** [NEW]：
   - 实现 `markdownToHtml(md: string): string`：将 Markdown 语法（标题 `#~####`、粗体 `**`、列表 `- / 1.`、引用 `>`、表格 `|`、段落与换行）渲染为优雅的语义化 HTML，并自动为各级标题注入唯一锚点 ID（`id="h-{seq}-{index}"`）；
   - 实现 `extractSubHeadings(md: string, chapterSeq?: number): SubHeading[]`：准确提取章节内所有层级的子标题（包含级别、标题文字与定位锚点 ID）；
   - 实现 `htmlToMarkdown(html: string): string`：用于 `contenteditable` 编辑器在用户就地编辑修改时准确反序列化为标准 Markdown 格式并同步至持久化存储。
2. **单栏排版就地可编辑画布 (`desktop/src/components/Step3Writing.vue`)**：
   - 移除原有的简陋纯文本 `textarea`，升级为**单栏排版就地可编辑渲染画布**（`<div contenteditable="true" class="rich-rendered-editor">`）；
   - 具备出版级技术报告样式规范：章节主标题（H1）、二级标题（H2）、三级小节（H3）、段落首行缩进/行高、加粗与引用样式；
   - 大模型流式输出时：逐字流式渲染排版效果并平滑自动滚动；
   - 写作完成或日常查看时：用户直接在排版好的正文上点击即可就地修改润色，300ms 防抖物理落盘；
   - 顶部提供小巧的模式切换辅助按钮（`👁️ 排版视图` / `📝 源码视图`），满足不同习惯需求。
3. **左侧章节卡片多级标题目录与精确定位跳转**：
   - 当章节存在已撰写内容时，左侧对应章节卡片下方呈现层级缩进的多级子标题目录列表（H2/H3/H4）；
   - 点击任一子标题链接：
     - 若当前未选中该章，自动切换至该章；
     - 自动平滑滚动右侧编辑器至目标标题所在位置（`scrollIntoView({ behavior: 'smooth', block: 'start' })`）；
     - 目标标题呈现 1.5 秒轻量高亮呼吸动画（Highlight Pulse），提示用户精准定位。

---

## 2. 允许修改

- `desktop/src/lib/markdown.ts` [NEW]
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/tests/markdown.test.ts` [NEW]
- `desktop/src/tests/project.test.ts`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T10/**`

---

## 3. 禁止修改

- `engine/**`、`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `npx vitest run`（`desktop/`）全绿（包含 Markdown 解析、反解析、子标题提取与定位测试）。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：
  1. Step 3 正文区直接呈现优美排版的预览效果且可直接在上面就地输入编辑；
  2. 左侧章节卡片展开展示当前章所有子标题，点击子标题右侧正文瞬间平滑滚动定位并高亮高亮指示。

---

## 5. 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `npx vue-tsc --noEmit`（workdir=`desktop`）
3. `npm run build`（workdir=`desktop`）
