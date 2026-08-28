# 任务合同 V2-T33 v1 — Mermaid 专业工程流程图与拓扑图渲染优化

- 状态：READY_FOR_MAKER（待产品负责人批准）
- 依据：用户关于“Mermaid 图显示不 OK、按列表逐个攻克”的明确指示
- 精确起始 SHA：`5fbbe7a7bf7fcba1fa5749f7baaa7e6e5898d9e2`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **构建纯 TypeScript 高性能原生 Mermaid SVG 矢量渲染引擎 (`desktop/src/lib/mermaid.ts`)**：
   - 0 外部依赖，原生解析与计算：
     - 支持方向：`graph TD` / `graph TB` / `graph LR` / `graph RL` / `graph BT`、`flowchart TD` / `flowchart LR`；
     - 支持子图：`subgraph 区域名 ... end`（多子图嵌套与跨子图连线）；
     - 支持节点形状：矩形 `[text]`、圆角 `(text)`、胶囊 `([text])`、数据库/存储 `[(text)]`、圆形 `((text))`、菱形决策 `{text}`、梯形/平行四边形；
     - 支持连线类型：实线箭头 `-->`、虚线箭头 `-.->`、粗实线 `==>`、无箭头 `---`、带文本连线 `-->|文本|` 或 `-- 文本 -->`；
     - 支持样式与连线颜色自定义（`style`, `classDef`）；
   - **拓扑排序与几何布局算法**：
     - 基于 DAG 分层拓扑（Layered Graph Drawing）与节点碰撞避让，动态计算节点 (x, y) 坐标与画布 viewBox；
     - 连线采用平滑三次贝塞尔曲线（Cubic Bézier Curve）并生成标准 SVG 箭头 marker；
   - **国家工程咨询出版级蓝绿视觉风貌**：
     - 节点：柔和工程蓝/青绿渐变背景、深色边框、清晰字号、自动换行与内边距；
     - 子图：虚线圆角边框、淡青灰底色、顶部优雅标题徽标；
   - **交互与功能工具栏**：
     - 顶部工具栏：
       - `[ 📊 工艺/工程流程拓扑图 ]` 标识
       - `[ 👁️ 矢量拓扑 ]` / `[ 💻 源码 ]` 双视图一键切换
       - `[ 📋 复制代码 ]`
       - `[ 🔍 全屏弹窗查看 ]`
     - **语法容错保护**：遇到复杂/非法语法时，平滑降级为优雅代码块，绝对杜绝白屏或异常抛出。

2. **前端 Markdown 解析与双向编辑序列化联动 (`desktop/src/lib/markdown.ts`, `Step3Writing.vue`, `Step4Review.vue`)**：
   - `markdownToHtml`：识别 ```` ```mermaid ```` 代码块，自动调用 `renderMermaidToHtml(code)` 输出带 `data-mermaid-code="..."` 的结构化容器；
   - `htmlToMarkdown`：无损反向序列化回 ```` ```mermaid\n...\n``` ````，正文编辑后拓扑图与代码不丢失、不漂移；
   - 在 `Step3Writing.vue` 与 `Step4Review.vue` 中支持流程图卡片内联交互与全屏查看模态框。

3. **Word 导出端流程图出版级对照表转换 (`engine/app/export/docx_builder.py`, `exporter.py`)**：
   - 在 `docx_builder.py` 与 `exporter.py` 中检测 ```` ```mermaid ```` 代码块：
     - 解析流程图所有节点与工序流转关系；
     - 自动转换为符合国家发改委投资项目标准的**【工艺/工程流程步骤与拓扑关系对照表】**（包含工序号、工序名称、输入/前置、承接/输出、技术控制要点）或高雅的流程框文字块，在 Word 中达到出版级排版水准。

4. **单测覆盖与 5 项全量门禁**：
   - 编写 `desktop/src/tests/mermaid.test.ts`，覆盖 Mermaid 各种语法、子图、节点形状、双向序列化；
   - 更新 `engine/tests/test_export.py`，验证 Word 导出中 Mermaid 流程图的排版转换；
   - 运行 5 项全量门禁确保 100% 绿灯。

---

## 2. 允许修改

- `desktop/src/lib/mermaid.ts`（新建）
- `desktop/src/lib/markdown.ts`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/mermaid.test.ts`（新建）
- `desktop/src/tests/markdown.test.ts`
- `engine/app/export/docx_builder.py`
- `exporter.py`
- `engine/tests/test_export.py`
- `docs/dev-flow/tasks/V2-T33/**`

---

## 3. 禁止修改

- `generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] 前端能无依赖完整解析并渲染 `graph TD` / `graph LR` / `flowchart` 等工程流程图为出版级矢量 SVG；
- [ ] 流程图卡片具备视图切换、复制代码、全屏缩放与容错降级；
- [ ] 编辑正文时 `htmlToMarkdown` 能 100% 无损还原 Mermaid 代码块；
- [ ] Word 导出时 Mermaid 流程图被规范转换为工程流程对照表或流程框；
- [ ] 5 项全量门禁（Pytest 128+、Vitest 151+、vue-tsc、build、cargo check）全部绿灯通过。

---

## 5. 快速验证顺序

1. `npx vitest run`（`desktop/`）
2. `npx vue-tsc --noEmit`（`desktop/`）
3. `npm run build`（`desktop/`）
4. `python -m pytest engine/tests -q`
5. `cargo check`（`desktop/src-tauri/`）
