# 致 Maker 转发消息 — V2-T10 第 4 轮（根除标题正文粘连与单行表格还原）

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`d0e9306b3fae3ba15b50f75e9b8f2bf29a00aaae`
- 有效合同：`docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v4.md`

## 核心实现任务

1. **`desktop/src/lib/markdown.ts`**：
   - 增强 `normalizeMarkdown(md: string): string`：
     1. **表格单行粘连还原**：
        `text = text.replace(/\|\s*\|/g, "|\n|");`
        将 `|序号|指标|...||---|---|...|| 1 | ... || 2 | ... |` 彻底拆解为标准每行换行的 GFM 表格；
     2. **标题与加粗/引用/表格粘连拆解**：
        `text = text.replace(/(#{1,6}\s+.*?)(\*\*|【源|\|)/g, "$1\n\n$2");`
     3. **最低级标题与正文粘连智能拆解**：
        `text = text.replace(/(#{1,6}\s+\d+(?:\.\d+)*\s+[^\s#\n]{2,20}?)(项目|本项目|该|根据|按照|经|为|在|一、|主要|如下|表|包含|涵盖|总投资|建设|规划|由|经查|针对)([\u4e00-\u9fa5])/g, "$1\n\n$2$3");`
2. **`engine/app/writing/writer.py` & `prompts.py`**：
   - 在系统 Prompt 的核心规则中增加：
     - 标题必须单占一行并空一行再写正文，严禁标题与正文连在同一行；
     - 表格每行（表头、分隔线、数据行）末尾必须输出标准换行符 `\n`，严禁使用 `||` 连写在同一行。
3. **单测与产物**：
   - `desktop/src/tests/markdown.test.ts` 增加单行 `||` 表格与标题正文粘连的自动还原测试；
   - 运行 pytest、vitest、vue-tsc、build 与 cargo check。

## 允许修改

- `desktop/src/lib/markdown.ts`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/tests/markdown.test.ts`
- `desktop/dist/**`
- `engine/app/writing/writer.py`
- `engine/app/writing/prompts.py`
- `engine/tests/test_writing_router.py`
- `docs/dev-flow/tasks/V2-T10/**`

## 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

## 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `python -m pytest engine/tests -q`
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）

## 完成时

1. 只提交允许范围；
2. 完成说明写到 `docs/dev-flow/tasks/V2-T10/rounds/04/maker-completion.md`，单独提交；
3. 不 amend、不 rebase、不 push；
4. 冻结工作树交回。
