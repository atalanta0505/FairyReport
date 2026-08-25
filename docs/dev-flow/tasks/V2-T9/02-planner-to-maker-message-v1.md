# 致 Maker 转发消息 — V2-T9 第 1 轮

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`813b28f1677319cf0ff6e5df195ea3dd572486aa`
- 有效合同：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v1.md`

## 唯一主要行为

在桌面端构建 5 步向导主界面框架，并实现 **Step 1: 项目与资料管理**（项目增删选、文件选择/拖拽与摄取分块向量化、资料列表/删除）以及 **通用知识包首启检测与同步**。

## 依赖声明（随合同批准）

- npm: `@tauri-apps/plugin-dialog@^2.2.0`
- crate: `tauri-plugin-dialog = "2"`
- capabilities: `"dialog:default"`

## 实现导航

1. `desktop/package.json` + `desktop/src-tauri/Cargo.toml`：加入 plugin-dialog 依赖。
2. `desktop/src-tauri/src/lib.rs`：注册 `.plugin(tauri_plugin_dialog::init())`。
3. `desktop/src-tauri/capabilities/default.json`：追加 `"dialog:default"` 权限。
4. `desktop/src/lib/engineApi.ts`：封装与引擎 `/projects`、`/projects/{name}/materials`、`/generic` 的 API 交互。
5. `desktop/src/stores/project.ts`：Pinia store 管理活动项目、项目列表、资料列表、通用包状态及当前向导步骤。
6. `desktop/src/views/Home.vue` 与 `desktop/src/components/Step1Project.vue`：实现向导布局及 Step 1 项目/资料/通用包 UI。
7. `desktop/src/tests/project.test.ts`：新增单元测试。
8. `npm run build`：重建 `dist/`。

## 允许修改

- `desktop/**`
- `docs/dev-flow/tasks/V2-T9/**`

## 禁止修改

- `engine/**`、`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

## 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `cargo check`（workdir=`desktop/src-tauri`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）

## 停止条件

- 基线或工作树不符；
- 必须越界修改；
- 同一失败尝试两次未果；
- 依赖版本冲突或下载异常。

## 完成时

1. 只提交允许范围（`desktop/**` 候选提交）；
2. 完成说明写到 `docs/dev-flow/tasks/V2-T9/rounds/01/maker-completion.md`，单独提交；
3. 不 amend、不 rebase、不 push；
4. 冻结工作树交回。
