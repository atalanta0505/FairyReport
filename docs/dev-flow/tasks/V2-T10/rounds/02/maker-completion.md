# Maker 完成说明 — V2-T10 第 2 轮（单栏排版就地编辑器与多级标题精准跳转）

## 基本信息

- **任务 ID**：V2-T10
- **轮次**：第 2 轮
- **完成时间**：2026-08-25
- **有效合同**：[`docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v2.md`](file:///d:/Repo/FairyReport_lite/docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v2.md)
- **精确起始 SHA**：`261b829633e08f51aa6d226a31c510aa27e997f3`
- **候选交付 SHA**：`3fb868af3a3d774f80266e78dbd70db520fe311d`

---

## 1. 核心实现范围与修改文件清单

### 1.1 轻量零依赖 Markdown 解析与标题提取工具
- **文件**：[`desktop/src/lib/markdown.ts`](file:///d:/Repo/FairyReport_lite/desktop/src/lib/markdown.ts) [NEW]
  - 定义 `SubHeading` 接口：`id`、`level`（1~4）、`title`、`raw`、`index`；
  - 实现 `markdownToHtml(md: string, chapterSeq?: number): string`：
    - 支持各级标题（`#` 至 `####`）转为语义化 `<h1~4>` 并自动注入唯一锚点 ID（`id="h-ch{seq}-idx{index}"`）；
    - 支持加粗 `<strong>`、斜体 `<em>`、删除线 `<del>`、行内代码 `<code>`（防二次干扰保护）；
    - 支持无序列表 `<ul><li>` 与有序列表 `<ol><li>`；
    - 支持 Markdown 标准表格解析为 `<table><thead><tbody>`；
    - 支持引用块 `<blockquote>`、代码块 `<pre><code class="...">`、分割线 `<hr />`、来源标签徽章（`.ref-badge`）；
  - 实现 `extractSubHeadings(md: string, chapterSeq?: number): SubHeading[]`：
    - 正则提取所有 H1~H4 标题，准确解析层级、纯文本标题与对应锚点 ID（自动跳过代码块内的假标题）；
  - 实现 `htmlToMarkdown(html: string): string`：
    - 将 `contenteditable` 编辑产生的 HTML 语义标签（标题、列表、表格、加粗、引用、来源徽章等）准确反向序列化为标准 Markdown 文本，用于就地编辑后的自动落盘保存。

### 1.2 单元测试套件
- **文件**：[`desktop/src/tests/markdown.test.ts`](file:///d:/Repo/FairyReport_lite/desktop/src/tests/markdown.test.ts) [NEW]
  - 覆盖 `markdownToHtml` 标题与锚点 ID 生成、内联格式、来源徽章、列表、表格、引用块、代码块解析；
  - 覆盖 `extractSubHeadings` 多级标题抽取与锚点对应测试；
  - 覆盖 `htmlToMarkdown` HTML 语义标签与表格/徽章反序列化回 Markdown；
  - 覆盖 XSS 实体转义与反转义保护。

### 1.3 Step 3 单栏排版就地可编辑主画布与多级标题跳转
- **文件**：[`desktop/src/components/Step3Writing.vue`](file:///d:/Repo/FairyReport_lite/desktop/src/components/Step3Writing.vue)
  - **右侧单栏排版就地编辑器**：
    - 废除原简陋纯文本 `textarea` 默认视图，升级为单栏出版级排版就地可编辑画布（`<div contenteditable="true" class="rich-rendered-editor">`）；
    - 具备完整出版级样式规范（标题分级带边距与底边线、行高 1.85、字号 15px、表格斑马纹与边框、引用块蓝条、代码块暗色容器、来源徽章高亮）；
    - 大模型流式输出打字机模式：实时将接收的 Markdown 转化为 HTML 渲染并平滑滚屏到底部；
    - 日常浏览与修改模式：支持直接在排版文字上点击输入、改字、删减，`@input` 提取最新 HTML 转为 Markdown 并通过 300ms 防抖自动落盘；
    - 顶部工具栏增加紧凑小巧的视图切换控件（`👁️ 排版视图` / `📝 源码视图`）；
  - **左侧章节目录树与多级标题定位**：
    - 在已有内容的章节卡片下方，自动展开该章提取出的多级子标题目录列表（H1/H2/H3/H4）；
    - 点击任意子标题：
      1. 若当前未选中该章，自动切换至该章；
      2. 确保进入排版视图并准确定位至对应锚点 DOM 元素；
      3. 平滑滚动到视口顶部（`scrollIntoView({ behavior: 'smooth', block: 'start' })`）；
      4. 目标元素播放 1.5 秒 `.heading-anchor-pulse` 呼吸高亮动画并自动移除，视觉引导清晰明了。

### 1.4 生产构建产物
- **文件**：[`desktop/dist/**`](file:///d:/Repo/FairyReport_lite/desktop/dist)
  - 重新编译生成前端静态分发产物。

---

## 2. 快速验证记录

严格按照合同第 5 节指定顺序执行验证：

1. **桌面端单元测试**：
   ```powershell
   cd desktop
   npx vitest run
   # 输出：4 passed (api.test.ts, markdown.test.ts, engine.test.ts, project.test.ts), 77 passed (77)
   ```
2. **桌面端 TypeScript 类型检查**：
   ```powershell
   cd desktop
   npx vue-tsc --noEmit
   # 输出：退出码 0，无任何类型错误
   ```
3. **桌面端生产构建**：
   ```powershell
   cd desktop
   npm run build
   # 输出：✓ built in 820ms，产物完整生成至 desktop/dist/
   ```
4. **Rust / Tauri 编译检查**：
   ```powershell
   cd desktop/src-tauri
   cargo check
   # 输出：Finished `dev` profile in 0.89s，无错误
   ```
5. **引擎单元测试**：
   ```powershell
   python -m pytest engine/tests -q
   # 输出：77 passed, 2 warnings in 40.41s
   ```

---

## 3. 设计决策与说明

1. **单栏排版就地可编辑（Single-Column In-Place WYSIWYG Editing）**：
   - 彻底摒弃传统左右分栏模式，直接在主画布上呈现格式化排版效果；
   - 配合 `contenteditable` 与 `htmlToMarkdown`，在用户直接改字时避免重新设置 `innerHTML` 以保证光标稳定不跳动，停止输入 300ms 后静默落盘至存储。
2. **确定性锚点 ID 与目录树联动**：
   - `markdownToHtml` 与 `extractSubHeadings` 采用完全一致的 ID 生成规则（`h-ch{seq}-idx{index}`），确保目录树上的每一个子标题都能 100% 对应到正文 DOM 节点。
3. **呼吸高亮动画（Highlight Pulse Animation）**：
   - 点击子标题跳转后，对目标标题节点施加 1.5 秒渐变淡出的黄色呼吸高亮（`headingPulse`），并在动画结束时自动清理类名，兼顾视觉引导与阅读体验。

---

## 4. 冻结声明与交回

- 本地候选提交 SHA：`3fb868af3a3d774f80266e78dbd70db520fe311d`
- 严格遵循禁止修改约束：未触碰 `engine/**`、`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore` 等禁止路径。
- 无 `git push`、无 `git commit --amend`、无 `git rebase`。
- 本轮编码与测试全部完成，提交本完成说明后冻结工作树，交由 Checker 进行验收。
