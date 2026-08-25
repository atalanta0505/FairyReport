# 任务合同 V2-T10 v4 — Step 3 彻底根除最低级标题正文粘连与单行 Markdown 表格智能还原

- 状态：READY_FOR_MAKER（2026-08-25 产品负责人反馈最低级标题与正文粘连及表格未正常渲染）
- 依据：用户实测截图显示：
  1. 大模型生成的 Markdown 中，最低级标题（如 `### 1.1.6 主要技术经济指标`）与正文（`项目主要技术经济指标如下表所示：`）连写在同一行，导致该段正文被全量解析为 `<h3>` 标题，同时左侧子目录标题也包含该段正文；
  2. 大模型输出表格时未在每行末尾换行，而是使用 `||` 连接全部行（如 `|序号|指标名称|...||------|...|| 1 | ... || 2 | ... |`），导致表格无法被标准多行解析器识别。
- 精确起始 SHA：`d0e9306b3fae3ba15b50f75e9b8f2bf29a00aaae`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

实现标题与正文粘连智能解构、单行 Markdown 表格自动分行与提示词强约束双重加固：

1. **表格单行连写智能还原 (`desktop/src/lib/markdown.ts`)**：
   - 在 `normalizeMarkdown` 中增强表格单行粘连还原：
     - 正则匹配表格单元格连续闭合/开启标记 `\|\s*\|`（例如 `|备注||------|` 或 `|20.33公顷|| 2 |`），自动将其替换为标准换行 `|\n|`；
     - 确保单行表格被完美还原为标准多行 GFM Table（表头行、分隔行 `|---|---|`、数据行）；
2. **最低级标题与正文粘连智能解构 (`desktop/src/lib/markdown.ts`)**：
   - 在 `normalizeMarkdown` 中增加三层标题断行解构：
     - **第一层（加粗/引用/表格粘连）**：匹配 `(#{1,6}\s+.*?)(\*\*|【源|\|)` 自动拆分为 `$1\n\n$2`（解决 `### 1.1.1 建设地点**项目名称**`）；
     - **第二层（句式词断行）**：匹配 `(#{1,6}\s+\d+(?:\.\d+)*\s+[^\s#\n]{2,20}?)(项目|本项目|该|根据|按照|经|为|在|一、|主要|如下|表|包含|涵盖|总投资|建设|规划|由|经查|针对)([\u4e00-\u9fa5])` 自动拆分为 `$1\n\n$2$3`（解决 `### 1.1.6 主要技术经济指标项目主要...`、`### 1.1.7 绩效目标项目绩效目标...`、`### 1.2.1 基本信息项目单位为...`）；
     - **第三层（支持传入已知大纲标题库精确前缀匹配）**：若传入已知大纲子标题，精确匹配并断行；
3. **大模型写作提示词强约束双重加固 (`engine/app/writing/writer.py` & `prompts.py`)**：
   - 在 `_build_writing_system_prompt` 中追加强约束规则：
     - **标题独立换行**：每个标题（#、##、###）必须单独成行，标题后必须换行（空行）再写正文，严禁标题与正文连在同一行；
     - **表格多行输出**：所有表格每行（表头、分隔线、数据行）末尾必须输出标准换行符 `\n`，严禁使用 `||` 连在同一行输出；
4. **单测覆盖与静态产物重构**：
   - 在 `desktop/src/tests/markdown.test.ts` 补充单行 `||` 表格自动还原与各级标题句式粘连自动拆分单测；
   - 重新构建 `desktop/dist/**`。

---

## 2. 允许修改

- `desktop/src/lib/markdown.ts`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/tests/markdown.test.ts`
- `desktop/dist/**`
- `engine/app/writing/writer.py`
- `engine/app/writing/prompts.py`
- `engine/tests/test_writing_router.py`
- `docs/dev-flow/tasks/V2-T10/**`

---

## 3. 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `npx vitest run`（`desktop/`）全绿（覆盖单行表格还原与标题粘连拆解）。
- [ ] `python -m pytest engine/tests -q` 全绿。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：
  1. `1.1.6 主要技术经济指标`、`1.1.7 绩效目标` 等最低级标题与正文完全断开，标题独立为 H3，正文为标准 10.5pt 正常段落；
  2. 单行连写的 Markdown 表格完全恢复为标准表格（带表头、边框与斑马纹）；
  3. 左侧导航栏子标题目录中不再包含正文文本，纯净展示小节标题。

---

## 5. 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `python -m pytest engine/tests -q`
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
