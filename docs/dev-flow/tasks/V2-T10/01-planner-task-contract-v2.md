# 任务合同 V2-T10 v2 — Step 3 章节 Markdown 排版渲染与三模视图（排版预览/源码编辑/双栏分屏）

- 状态：READY_FOR_MAKER（2026-08-25 产品负责人建议章节内容直接显示为格式化排版预览，而非黑压压的源码）
- 依据：用户实测截图反馈流式输出与大纲写作很棒，但源码聚集不便阅读与修改，要求直接显示为 Markdown 排版渲染格式
- 精确起始 SHA：`6361a520cf8198f121d58fe18b8fe6676cf20a2e`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

为 Step 3 章节流式写作与编辑器实现**专业级 Markdown 排版渲染引擎与三模视图切换**：
1. **轻量高性能 Markdown 排版解析器 (`desktop/src/lib/markdown.ts`)**：
   - 零额外外部依赖，纯 TypeScript 原生解析器；
   - 完整支持：
     - 各级标题（`#` 至 `####`）层级排版与左边框高亮；
     - 粗体（`**...**`）、斜体（`*...*`）、行内代码；
     - 来源引用标签（`【源:...】`）高亮徽章化渲染；
     - 无序/有序列表（`-`, `*`, `1.`, `(1)` 等）；
     - Markdown 表格（自动生成表头、边框与斑马纹）；
     - 引用块（`>`）与段落行距排版；
   - 支持实时增量渲染，在流式输出时平滑打字机呈现。
2. **Step 3 编辑器三模视图切换 (`desktop/src/components/Step3Writing.vue`)**：
   - 顶部增加三模视图切换器：
     - **`👁️ 排版预览 (默认)`**：清爽排版视图，层级标题清晰、段落舒朗、来源标签美观高亮；流式生成时实时打字机渲染；
     - **`✏️ 源码编辑`**：提供单栏纯文本/Markdown 源码精准编辑，带行距与清晰字体；
     - **`📖 分栏对照`**：左栏源码编辑、右栏实时排版预览，左右联动滚动；
   - 任何模式下的编辑均实时自动双向同步、防抖持久化落盘。
3. **单元测试与产物构建 (`desktop/src/tests/markdown.test.ts` & `desktop/dist/**`)**：
   - 编写排版解析器单测，验证标题、粗体、来源徽章、表格与列表解析；
   - 重建生产分发产物。

---

## 2. 允许修改

- `desktop/src/lib/markdown.ts` [NEW]
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/tests/markdown.test.ts` [NEW]
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T10/**`

---

## 3. 禁止修改

- `engine/**`、`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `npx vitest run`（`desktop/`）全绿（包含 markdown 渲染单测）。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：Step 3 默认以排版预览格式呈现各级标题、粗体、段落与引用标签，流式生成时也是排版视觉流式呈现；可随时无缝切换到源码编辑或分栏对照。

---

## 5. 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `npx vue-tsc --noEmit`（workdir=`desktop`）
3. `npm run build`（workdir=`desktop`）
4. `python -m pytest engine/tests -q`
