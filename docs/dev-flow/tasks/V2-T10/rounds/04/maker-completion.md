# Maker 完成说明 — V2-T10 第 4 轮（根除标题正文粘连与单行表格智能还原）

## 基本信息

- **任务 ID**：V2-T10
- **轮次**：第 4 轮
- **完成时间**：2026-08-25
- **有效合同**：[`docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v4.md`](file:///d:/Repo/FairyReport_lite/docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v4.md)
- **精确起始 SHA**：`34f5cfdca0cfd25d194511d739815e9821867c29`
- **候选交付 SHA**：`1348e979fc8efa41a601e1d3642bb0b391ca73ea`

---

## 1. 核心实现范围与修改文件清单

### 1.1 Markdown 预处理与智能还原升级
- **文件**：[`desktop/src/lib/markdown.ts`](file:///d:/Repo/FairyReport_lite/desktop/src/lib/markdown.ts)
  - 升级 `normalizeMarkdown(md: string, knownHeadings?: string[]): string` 函数：
    1. **标题双换行规范化**：正则 `([^#\n])\s*(#{1,6}\s+)` -> `$1\n\n$2`，确保标题独立起行并空行；
    2. **单行表格连写自动还原**：正则 `\|\s*\|` -> `|\n|`，彻底还原由 `||` 连接在单行的 GFM 表格（表头、分隔行 `|---|---|`、数据行）；
    3. **表格与前置正文粘连规范化**：正则 `^([^|\n].*?)(\|.+?\|\s*\n\s*\|[-: ]+?\|)` -> `$1\n\n$2`；
    4. **标题与加粗/来源标签/表格粘连拆解**：正则 `(#{1,6}\s+[^\n*|【]*?)\s*(\*\*|【源|\|)` -> `$1\n\n$2`；
    5. **最低级标题（H3/H4）与正文句式词粘连拆解**：针对 `### 1.1.6 主要技术经济指标项目主要技术经济指标...`、`### 1.1.7 绩效目标本项目...`、`### 1.2.1 基本信息项目单位为...` 等，基于中文句式起始词（项目、本项目、该项目、本工程、工程、根据、按照、依据、经查、经核实、经测算、经评估、经分析、经过、为贯彻、为实现、为满足、总投资、总用地、总建筑面积、规划建设、建设内容、建设规模为、建设地点位于、主要建设内容、主要指标如下、主要包括、涵盖、包含、如下表、如下所示、如下：、由、针对）进行精准断行 `$1\n\n$2$3`；
    6. **已知大纲标题库精确前缀匹配断行**：支持传入 `knownHeadings` 对大纲标题进行精确前缀断行；
  - 在 `extractSubHeadings` 与 `markdownToHtml` 的入口参数中兼容并注入 `knownHeadings`，确保子标题树纯净（不再混入正文内容）且排版 HTML 结构严格分离标题与正文段落。

### 1.2 大模型写作提示词强约束双重加固
- **文件**：[`engine/app/writing/writer.py`](file:///d:/Repo/FairyReport_lite/engine/app/writing/writer.py)
  - 在 `_build_writing_system_prompt` 的核心规则中增加：
    - `8. **Markdown 格式规范（极重要）**：每个标题（#、##、###）必须独占一行并空一行再写正文，严禁标题与正文连在同一行！表格每行末尾必须输出标准换行符 \n，严禁使用 || 连写在同一行！`；
  - 在 `_build_chapter_write_args` 的写作要求中追加：
    - `- **格式规范（极重要）：每个标题（#、##、###）必须独占一行且空一行后再写正文，严禁标题与正文连在同一行；表格每行末尾必须输出标准换行符 \n，严禁使用 || 连写在同一行**`。
- **文件**：[`engine/app/writing/prompts.py`](file:///d:/Repo/FairyReport_lite/engine/app/writing/prompts.py)
  - 在 `_MODIFY_SYSTEM_PROMPT` 修改提示词中增加同样的标题独占行与表格多行换行约束。

### 1.3 单元测试覆盖
- **文件**：[`desktop/src/tests/markdown.test.ts`](file:///d:/Repo/FairyReport_lite/desktop/src/tests/markdown.test.ts)
  - 新增单行 `||` 表格自动还原为标准 GFM 多行表格及 HTML `<table>` 渲染测试；
  - 新增标题与加粗、引用标签、表格粘连的自动拆解测试；
  - 新增最低级标题与多类中文句式词粘连自动拆解测试；
  - 新增已知大纲标题库精确前缀断行测试；
  - 新增 `extractSubHeadings` 提取纯净子标题（确保标题不混入正文）与 `markdownToHtml` 独立标签渲染测试。
- **文件**：[`engine/tests/test_writing_router.py`](file:///d:/Repo/FairyReport_lite/engine/tests/test_writing_router.py)
  - 新增 `test_markdown_formatting_rules_in_prompts`，验证写作系统提示词、修改系统提示词与用户写作提示词均包含 Markdown 格式与分行强约束。

### 1.4 生产构建产物
- **文件**：[`desktop/dist/**`](file:///d:/Repo/FairyReport_lite/desktop/dist)
  - 重新编译生成前端生产静态产物。

---

## 2. 快速验证记录

严格按照合同第 5 节指定顺序执行快速验证：

1. **桌面端单元测试**：
   ```powershell
   cd desktop
   npx vitest run
   # 输出：4 passed (api.test.ts, engine.test.ts, markdown.test.ts, project.test.ts), 87 passed (87)
   ```
2. **后端引擎端测试**：
   ```powershell
   python -m pytest engine/tests/test_writing_router.py -q
   # 输出：22 passed in 31.98s
   ```
3. **桌面端 TypeScript 类型检查**：
   ```powershell
   cd desktop
   npx vue-tsc --noEmit
   # 输出：退出码 0，无任何类型报错
   ```
4. **桌面端生产构建**：
   ```powershell
   cd desktop
   npm run build
   # 输出：✓ built in 911ms，产物完整输出至 desktop/dist/
   ```
5. **Rust / Tauri 编译检查**：
   ```powershell
   cd desktop/src-tauri
   cargo check
   # 输出：Finished dev profile in 0.89s，无错误
   ```

---

## 3. 设计决策与技术说明

1. **表格单行连写智能还原机制**：
   - 大模型在输出 Markdown 表格时，偶尔会将多行表格通过 `||` 连成一行（如 `|序号|指标||---|---|| 1 | 库容 |`）。通过在前置预处理器中将 `\|\s*\|` 还原为标准换行 `|\n|`，能够无缝让单行表格还原为标准多行 GFM Table，并被后续解析器解析为标准 `<table>` 表格。
2. **三层标题断行解构架构**：
   - 第一层：通过标点/标记界定（`**`、`【源`、`|`），将标题与正文加粗段、来源标签、表格解耦；
   - 第二层：通过工程咨询高频句式词（`项目`、`本项目`、`根据`、`经查`、`总投资`、`建设内容` 等），在正文与标题紧贴时精准识别分界点并补全双换行符；
   - 第三层：支持已知大纲标题库前缀精确切分，作为最强兜底。
3. **提示词 + 解析器双重加固（Defense-in-Depth）**：
   - 既在 LLM 写作 Prompt 层面通过强规则约束大模型输出标准独立换行与多行表格，又在客户端解析引擎层面具备 100% 自动容错与智能还原能力，确保无论网络波动、模型版本变化或流式截断均能稳定呈现高质量排版。

---

## 4. 冻结声明与交回

- 本地候选提交 SHA：`1348e979fc8efa41a601e1d3642bb0b391ca73ea`
- 严格遵循修改范围：仅修改合同允许的 `desktop/src/lib/markdown.ts`、`desktop/src/tests/markdown.test.ts`、`desktop/dist/**`、`engine/app/writing/writer.py`、`engine/app/writing/prompts.py`、`engine/tests/test_writing_router.py` 与任务文档。
- 严格禁止修改约束：未触碰 `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore` 等禁止路径。
- 无 `git push`、无 `git commit --amend`、无 `git rebase`。
- 本轮编码与测试全部完成，提交本完成说明后冻结工作树，交由 Checker 验收。
