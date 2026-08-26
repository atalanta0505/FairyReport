# Maker 完成报告 — V2-T12 第 1 轮（项目删除级联彻底清理资料分块与向量索引，杜绝重建项目残留历史资料）

## 1. 基本信息

- 任务编号：V2-T12
- 轮次：第 1 轮
- 有效合同：`docs/dev-flow/tasks/V2-T12/01-planner-task-contract-v1.md`
- 转发消息：`docs/dev-flow/tasks/V2-T12/02-planner-to-maker-message-v1.md`
- 精确起始 SHA：`043de5dd2094f40a186b08c38771ecbd74f97d6b`
- 候选交付 SHA：`e4f92393486fbbc81b2f816d54e47b3dca5d461f`

---

## 2. 变更文件清单

- `engine/app/db.py`：为 SQLAlchemy Engine `connect` 注册监听器，针对 SQLite 连接自动执行 `PRAGMA foreign_keys=ON;`，开启数据库外键约束与级联删除。
- `engine/app/models.py`：在 `Project` ORM 模型中配置 `materials` 关系映射：`relationship("Material", backref="project", cascade="all, delete-orphan", passive_deletes=True)`。
- `engine/app/projects/router.py`：
  - `delete_project`：显式执行 `delete(models.Material).where(...)` 彻底清除 `materials` 表数据，调用 `session.delete(proj)`，并通过 `remove_project_data(name)` 清理项目磁盘文件与向量库；
  - `create_project`：在创建新项目入库前先行调用 `remove_project_data(body.name)`，确保可能存在的同名旧数据目录与向量实例完全重置清空。
- `engine/app/materials/vectorstore.py`：
  - 为 `ProjectVectorStore` 新增 `close()` 显式关闭 ChromaDB 客户端释放文件锁；并在 `close_project` 中触发 `close()`；
  - 加固 `safe_rmtree`：增加路径存在性判断与 5 次重试退避机制（`time.sleep(0.1)` + `gc.collect()`）；确认 `remove_project_data` 仅移除项目专属目录，不触碰通用知识包目录。
- `desktop/src/stores/project.ts`：在 `createProject` 与 `deleteProject` 中同步清空 `materials.value = []`、大纲与章节状态，并彻底移除 `localStorage` 中的旧缓存数据。
- `engine/tests/test_projects.py`：新增 `test_delete_project_cleans_materials_chunks_and_allows_clean_recreation` 单元测试，全面验证资料分块生成、项目删除、目录清理、通用包不受影响及同名重建后的绝对纯净状态。
- `desktop/src/tests/project.test.ts`：补充 `createProject` 同名重建重置本地缓存与资料状态的单测。
- `desktop/dist/**`：重新编译并更新前端分发产物。

---

## 3. 设计决策与核心实现

1. **多重保障的项目级联清理 (`engine/app/db.py`, `engine/app/models.py`, `engine/app/projects/router.py`)**：
   - 在 SQLite 底层启用 `PRAGMA foreign_keys=ON;`，结合 ORM `cascade="all, delete-orphan"`；
   - 在路由 `delete_project` 中再加一层显式 `session.execute(delete(models.Material)...)` 确保无论何种模式下均能彻底清除 `materials` 关联记录；
   - 在路由 `create_project` 中，创建前主动调用 `remove_project_data(body.name)`，杜绝同名项目重建时磁盘残留历史资料分块与向量索引。
2. **Windows 下 ChromaDB 文件锁安全释放与清理 (`engine/app/materials/vectorstore.py`)**：
   - 解决 Windows 环境下 SQLite 文件句柄在客户端未显式 close 时无法被 rmtree 删除的问题；
   - `safe_rmtree` 采用 5 次指数/退避重试结合垃圾回收与文件存在性检查，确保项目专属目录彻底被物理移除。
3. **前端状态与持久化缓存完全一致性 (`desktop/src/stores/project.ts`)**：
   - 在 Pinia store 中，创建与删除项目均清空当前 `materials`、`outlineMd`、`outlineChapters`、`chapters` 并同步清理 `localStorage`，杜绝前端残留状态。

---

## 4. 验证记录

严格按照合同规定的快速验证顺序执行并通过：

1. `python -m pytest engine/tests -q`
   - 结果：`82 passed, 2 warnings in 43.09s`（全绿，含新增的级联清理与重建验证测试）。
2. `npx vitest run`（`desktop/`）
   - 结果：`4 passed (4), 92 passed (92)`（全绿，含新增的前端缓存清理单测）。
3. `npx vue-tsc --noEmit`（`desktop/`）
   - 结果：通过（退出码 0，无任何 TypeScript 类型错误）。
4. `npm run build`（`desktop/`）
   - 结果：通过（成功构建前端静态资源至 `desktop/dist/`）。
5. `cargo check`（`desktop/src-tauri/`）
   - 结果：通过（`Finished dev profile in 0.90s`）。

---

## 5. 已知风险与后续建议

- 无向后兼容风险，所有修改均严格限制在任务合同允许范围内，所有禁止修改文件（如 `generic_knowledge/**`、`backend/**`、`AGENTS.md` 等）均未受影响。
- 通用知识包路径独立于项目目录，测试已验证在项目删除与重建过程中通用知识包不受任何干扰。

---

## 6. 冻结声明

Maker 本轮编码与测试工作已全部完成，代码、静态资源与测试均已验证通过并冻结，特此交付候选 commit SHA `e4f92393486fbbc81b2f816d54e47b3dca5d461f`。
