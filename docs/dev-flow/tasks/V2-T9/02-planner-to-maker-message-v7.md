# 致 Maker 转发消息 — V2-T9 第 7 轮（全链路大纲持久化）

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`72970f8087968536f98ef4ba021fb7a55ae58f0a`
- 有效合同：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v7.md`

## 唯一主要行为

实现 Step 2 报告大纲与选定模板的全链路持久化（后端文件落盘 + 前端自动同步与双重本地备份），彻底解决生成大纲后重启/刷新变为空白的问题。

## 实现导航

1. `engine/app/writing/router.py`：
   - 增加 `GET /projects/{name}/outline` 与 `POST /projects/{name}/outline` 端点，存取 `%LOCALAPPDATA%/FairyReport/projects/<name>/outline.json`（包含 `report_type`、`outline_md`、`chapters`）；
   - 在 `POST /writing/outline` 生成大纲时，若 `req.project` 存在，自动将生成结果落盘到对应项目的 `outline.json` 中。
2. `engine/tests/test_writing_router.py`：
   - 添加大纲存取端点的单测。
3. `desktop/src/lib/engineApi.ts`：
   - 增加 `getProjectOutline(baseUrl, projectName)` 与 `saveProjectOutline(baseUrl, projectName, data)`。
4. `desktop/src/stores/project.ts`：
   - 增加 `loadOutline` 与 `saveOutline`，在 `selectProject` / `loadProjects` 时自动为选定项目加载大纲；
   - 增加 `localStorage` 双重本地备份；
   - 在用户修改大纲内容或切换模板时防抖自动保存。
5. `desktop/src/components/Step2Outline.vue`：
   - 监听项目切换与挂载，自动恢复已存大纲与模板。
6. `desktop/src/tests/project.test.ts`：
   - 添加大纲持久化与自动回填测试。
7. 重建 `desktop/dist/**`。

## 允许修改

- `engine/app/writing/router.py`
- `engine/tests/test_writing_router.py`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/stores/project.ts`
- `desktop/src/components/Step2Outline.vue`
- `desktop/src/tests/project.test.ts`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T9/**`

## 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

## 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）

## 完成时

1. 只提交允许范围（`desktop/**` 与 `engine/**` 候选提交）；
2. 完成说明写到 `docs/dev-flow/tasks/V2-T9/rounds/07/maker-completion.md`，单独提交；
3. 不 amend、不 rebase、不 push；
4. 冻结工作树交回。
