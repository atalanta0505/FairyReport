# 任务合同 V2-T10 v3 — Step 3 排版引擎与标题断行规范化修复（解决标题正文粘连与字体异常）

- 状态：READY_FOR_MAKER（2026-08-25 产品负责人反馈排版与字体大小异常）
- 依据：用户实测截图显示：
  1. 大模型生成的 Markdown 文本中，`# 第一章...## 1.1...### 1.1.1...` 等各级标题与正文粘连在同一行，导致解析器将整章误识别为 `<h1>`，致使正文通篇变成巨大粗体；
  2. Vue scoped 样式选择器中 `:deep(.rich-rendered-editor h1)` 编译未准确命中，导致浏览器默认样式兜底；
  3. 左侧导航栏子标题目录因粘连未拆分，呈现为单行长文本 `📌 第一章 概述## 1.1 项目概况### 1.1.1 项目名...`。
- 精确起始 SHA：`7f4bb358fc5500c50dc573bba7d6e641774e6224`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **Markdown 预处理与断行规范化 (`desktop/src/lib/markdown.ts`)**：
   - 增加 `normalizeMarkdown(md: string): string` 预处理流程：
     - 在所有未换行的标题标记前强制补全双换行（正则 `([^\n])\s*(#{1,6}\s+)` -> `$1\n\n$2`），彻底解开 `# 章标题## 节标题### 小节标题正文` 粘连；
     - 规范化代码块与表格周围的换行；
   - 在 `markdownToHtml` 与 `extractSubHeadings` 的入口处统一调用 `normalizeMarkdown`；
   - `extractSubHeadings` 针对解析出的子标题只截取本行内容，并精准清洗标题内容；
2. **出版级正文排版 CSS 修复 (`desktop/src/components/Step3Writing.vue`)**：
   - 修正 Vue 3 scoped CSS 深度选择器语法：统一改为 `.rich-rendered-editor :deep(h1)`、`.rich-rendered-editor :deep(h2)`、`.rich-rendered-editor :deep(p)`、`.rich-rendered-editor :deep(strong)` 等；
   - 出版级工程报告样式调优：
     - `h1`：20px, 粗体 700, 深色 `#0f172a`, 底边线 2px, 间距适度；
     - `h2`：17px, 粗体 600, `#1e293b`, 底边线 1px, 间距 18px/8px；
     - `h3`：15px, 粗体 600, `#334155`；
     - `h4`：14px, 粗体 600, `#475569`；
     - `p` (正文)：**14.5px, 常规字重 400 (正常文本字体，杜绝全篇加粗), 行高 1.85, 颜色 `#334155`, 中文段落首行缩进 2 字符 (`text-indent: 2em;`), 两端对齐 (`text-align: justify;`)**；
     - `strong`：粗体 600, `#0f172a`；
3. **左侧多级标题树状视觉优化 (`Step3Writing.vue`)**：
   - 过滤 H1（因卡片头部已是章标题），清晰呈现 H2（节）与 H3（小节）的层级树；
   - H2 缩进 10px, 字号 12px, 略加粗；H3 缩进 20px, 字号 11.5px, 颜色 `#64748b`；
   - 单行文本截断带省略号（`text-overflow: ellipsis; white-space: nowrap; overflow: hidden;`）；
4. **单测适配与产物重构**：
   - 在 `desktop/src/tests/markdown.test.ts` 补充粘连标题的自动规范化与提取单测；
   - 重新构建 `desktop/dist/**`。

---

## 2. 允许修改

- `desktop/src/lib/markdown.ts`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/tests/markdown.test.ts`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T10/**`

---

## 3. 禁止修改

- `engine/**`、`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `npx vitest run`（`desktop/`）全绿（包含粘连 Markdown 自动断行与层级提取单测）。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：
  1. 正文标题与段落层次分明，正文字体恢复为舒适的 14.5px 常规字体（非全篇巨型粗体），段落首行缩进 2 字符；
  2. 左侧章节卡片下方多级标题清晰分行分层展示（`2.1 ...`、`2.1.1 ...`），点击任一小节平滑滚动定位并黄色呼吸高亮。

---

## 5. 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `npx vue-tsc --noEmit`（workdir=`desktop`）
3. `npm run build`（workdir=`desktop`）
