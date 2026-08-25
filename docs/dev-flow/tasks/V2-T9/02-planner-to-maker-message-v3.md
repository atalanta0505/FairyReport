# 致 Maker 转发消息 — V2-T9 第 3 轮（窄修复）

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`f6137f394142f1cf1b4cfc24d3fe3a4f6be59299`
- 有效合同：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v3.md`

## 唯一主要行为

在本地 Python 引擎中新增 `POST /projects/{name}/open-folder`，调用 `os.startfile(files_dir)`（Windows 原生），前端 `engineApi.openProjectDir` 改造为调用该接口，解决 Tauri 前端 shell open 唤起本地文件夹失败的问题。

## 实现导航

1. `engine/app/projects/router.py`：新增 `POST /{name}/open-folder` 端点，确保 `settings.files_dir(name)` 存在并调用 `os.startfile`（非 Windows 平台 fallback subprocess）。
2. `engine/tests/test_projects.py`：添加测试（mock os.startfile）。
3. `desktop/src/lib/engineApi.ts`：更新 `openProjectDir(baseUrl, projectName)` 调用引擎接口。
4. `desktop/src/stores/project.ts` & `desktop/src/components/Step1Project.vue`：适配调用。
5. `desktop/src/tests/project.test.ts`：更新单测。
6. 重建 `desktop/dist/**`。

## 允许修改

- `engine/app/projects/router.py`
- `engine/tests/test_projects.py`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/stores/project.ts`
- `desktop/src/components/Step1Project.vue`
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
2. 完成说明写到 `docs/dev-flow/tasks/V2-T9/rounds/03/maker-completion.md`，单独提交；
3. 不 amend、不 rebase、不 push；
4. 冻结工作树交回。
