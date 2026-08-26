# Checker 验收报告 — V2-T12 第 1 轮（项目删除级联彻底清理资料与向量索引，杜绝重建项目残留历史资料）

- **任务 ID**：V2-T12
- **轮次**：第 1 轮
- **审查时间**：2026-08-26
- **有效合同**：[`docs/dev-flow/tasks/V2-T12/01-planner-task-contract-v1.md`](file:///d:/Repo/FairyReport_lite/docs/dev-flow/tasks/V2-T12/01-planner-task-contract-v1.md)
- **候选 SHA**：`e4f92393486fbbc81b2f816d54e47b3dca5d461f`
- **基线（父提交）SHA**：`043de5dd2094f40a186b08c38771ecbd74f97d6b`
- **验收结论**：**PASS**（全部 A 级自动化测试独立重跑通过，SQLite 外键 PRAGMA 与 ORM 级联配置完备，后端路由双重清理保障与创建前纯净化重置设计严密，Windows 下 ChromaDB 文件锁安全释放与 safe_rmtree 退避重试健全，通用知识包物理隔离安全无损，建议锁定合并）

---

## 1. 提交与修改范围审查

### 1.1 父提交链复核
- 候选提交 `e4f92393486fbbc81b2f816d54e47b3dca5d461f` 的父提交确为 `043de5dd2094f40a186b08c38771ecbd74f97d6b`（V2-T12 合同 v1 批准提交），提交历史链合法连续。

### 1.2 变动文件列表与范围边界
通过 `git diff --name-status 043de5dd2094f40a186b08c38771ecbd74f97d6b..e4f92393486fbbc81b2f816d54e47b3dca5d461f` 审查，修改文件清单如下：
- `engine/app/db.py` (M) — 注册 SQLAlchemy Engine `connect` 监听器，为 SQLite 连接开启 `PRAGMA foreign_keys=ON;`。
- `engine/app/models.py` (M) — 在 `Project` 模型中配置 `materials` 关系映射：`relationship("Material", backref="project", cascade="all, delete-orphan", passive_deletes=True)`。
- `engine/app/projects/router.py` (M) — `delete_project` 显式清除 `materials` 表数据与项目磁盘/向量索引；`create_project` 创建新项目前先行调用 `remove_project_data(body.name)` 纯净化重置同名旧数据。
- `engine/app/materials/vectorstore.py` (M) — 为 `ProjectVectorStore` 新增 `close()` 显式释放 ChromaDB 客户端与集合句柄；`close_project` 触发 `close()` 并调用 `gc.collect()`；`safe_rmtree` 增加路径存在性判断与 5 次退避重试（`time.sleep(0.1)` + `gc.collect()`）。
- `desktop/src/stores/project.ts` (M) — `createProject` 与 `deleteProject` 彻底清理 Pinia store 状态（`materials`、`outlineMd`、`outlineChapters`、`chapters`、`chapterStatuses`）及 `localStorage` 缓存。
- `engine/tests/test_projects.py` (M) — 新增 `test_delete_project_cleans_materials_chunks_and_allows_clean_recreation` 单元测试，全面覆盖资料分块摄取、项目删除、目录清理、通用包状态隔离以及同名重建后完全纯净的验证。
- `desktop/src/tests/project.test.ts` (M) — 新增 `createProject: 重建同名项目前彻底清理本地资料与大纲缓存` 单元测试。
- `desktop/dist/**` (M / R) — 重新构建的前端静态资源分发产物。

所有变动文件严格限定在合同允许范围（`engine/**`、`desktop/**`、`docs/dev-flow/tasks/V2-T12/**`），未触碰任何受保护的路径（`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md` 等），无越界修改。

---

## 2. 独立重跑 A 级验证（切勿采信自述）

独立审查员在干净工作区独立重新执行了全套快速自动化验证：

| 验证项 | 执行命令 | 结果 | 耗时/详情 |
| :--- | :--- | :---: | :--- |
| **后端引擎单元测试** | `python -m pytest engine/tests -q` | **PASS** | 82 passed, 2 warnings (40.06s) |
| **桌面端单元测试** | `npx vitest run` (`desktop/`) | **PASS** | 4 文件全部通过, 92 用例通过 (1.04s) |
| **桌面端 TypeScript 检查** | `npx vue-tsc --noEmit` (`desktop/`) | **PASS** | 退出码 0，零类型错误 |
| **桌面端生产构建** | `npm run build` (`desktop/`) | **PASS** | 成功输出至 `desktop/dist/` (866ms) |
| **Rust / Tauri 编译检查** | `cargo check` (`desktop/src-tauri/`) | **PASS** | `dev` profile 编译检查通过 (0.82s) |

---

## 3. 合同逐项比对与代码审查细节

### 3.1 SQLite 外键级联与 ORM 模型映射 (`engine/app/db.py`, `engine/app/models.py`)
- `engine/app/db.py`：通过 `@event.listens_for(Engine, "connect")` 拦截底层 SQLite 连接，每次连接建立时执行 `PRAGMA foreign_keys=ON;`，从数据库内核层面激活外键约束与级联支持。
- `engine/app/models.py`：`Project.materials` 显式声明 `cascade="all, delete-orphan"` 与 `passive_deletes=True`，与底层数据库外键级联完美配合。

### 3.2 路由层双保险清理与重建纯净化 (`engine/app/projects/router.py`)
- **`delete_project`**：
  - 显式执行 `session.execute(delete(models.Material).where(models.Material.project_id == proj.id))` 进行防御性显式清理，杜绝因 SQLite 驱动或会话差异导致的分块记录孤立残留；
  - 调用 `session.delete(proj)` 并 `session.commit()`；
  - 触发 `remove_project_data(name)`，先释放向量库句柄再彻底删除项目专属目录。
- **`create_project`**：
  - 在创建新项目前主动执行 `remove_project_data(body.name)`，消除以往可能因异常终止或磁盘手动残留的文件/向量库，确保新建或重建同名项目时环境处于 100% 纯净初始态。

### 3.3 ChromaDB 文件锁安全释放与通用知识包物理隔离 (`engine/app/materials/vectorstore.py`)
- `ProjectVectorStore.close()` 妥善关闭 `client` 与删除 `collection` 引用；
- `safe_rmtree` 增加 `p.exists()` 检查，并在 Windows 环境下提供 5 次 `gc.collect()` + `time.sleep(0.1)` 退避重试，有效解决 Windows 下 SQLite/Chroma 文件占用导致的删除失败；
- 物理路径隔离：项目专属目录为 `ENGINE_DATA_DIR/projects/{name}`，通用知识包目录为 `ENGINE_DATA_DIR/generic`，`remove_project_data` 仅针对 `project_dir` 操作，绝不波及通用知识包。

### 3.4 前端状态与持久化缓存重置 (`desktop/src/stores/project.ts`)
- `createProject` 与 `deleteProject` 均清理当前项目在 `localStorage` 中的大纲与章节缓存键值（`frl_outline_{name}`、`frl_chapters_{name}`）；
- 重置 Pinia 中 `materials`、`outlineMd`、`outlineChapters`、`chapters`、`chapterStatuses` 状态，避免前端界面残留上一项目的资料与大纲。

### 3.5 单元测试覆盖
- `engine/tests/test_projects.py` 新增 `test_delete_project_cleans_materials_chunks_and_allows_clean_recreation`：
  - 完整模拟创建项目 -> 摄取资料生成分块 -> 录入大纲与章节 -> 记录通用包状态基线 -> 删除项目 -> 断言磁盘目录已移除 -> 断言通用包状态一致未受影响 -> 重建同名项目 -> 断言资料列表为空、向量库 count=0、大纲与章节均为空对象。
- `desktop/src/tests/project.test.ts` 新增 `createProject` 清理历史大纲/章节本地缓存及资料状态的断言测试。

---

## 4. 判定结论与建议

- **最终判定**：**PASS**
- **锁定候选 SHA**：`e4f92393486fbbc81b2f816d54e47b3dca5d461f`
- **阻断项（Blockers）**：无
- **非阻断风险**：无

### 待产品负责人执行的 B 级人工验证项
1. **项目删除与同名重建资料纯净化验证**：
   - 在桌面端新建项目并上传资料文件，等待摄取并确认分块数；
   - 删除该项目；
   - 重新创建同名的项目，进入项目资料管理页面，检查资料列表是否完全为空（分块数为 0），确认无历史残留数据。
2. **通用知识包独立性验证**：
   - 检查项目删除与重建前后，顶部通用知识包状态均保持为“已就绪”，通用检索功能正常运作。
