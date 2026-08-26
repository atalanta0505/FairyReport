# Planner -> Maker 指派消息 — V2-T12 第 1 轮

Maker 请注意：

请严格依据 [`docs/dev-flow/tasks/V2-T12/01-planner-task-contract-v1.md`](file:///D:/Repo/FairyReport_lite/docs/dev-flow/tasks/V2-T12/01-planner-task-contract-v1.md) 执行项目删除级联彻底清理资料与向量、杜绝重建项目残留历史分块的编码与测试任务。

## 1. 核心实现要点

1. **`engine/app/db.py`**：
   - 监听 SQLAlchemy Engine 的 `connect` 事件，执行 `PRAGMA foreign_keys=ON;`。
2. **`engine/app/models.py`**：
   - `Project` 模型添加 `materials = relationship("Material", backref="project", cascade="all, delete-orphan", passive_deletes=True)`。
3. **`engine/app/projects/router.py`**：
   - `delete_project`：
     - 显式执行 `session.execute(delete(models.Material).where(models.Material.project_id == proj.id))`；
     - `session.delete(proj)` 并 `session.commit()`；
     - `remove_project_data(name)`；
   - `create_project`：
     - 在创建前先调用 `remove_project_data(body.name)` 确保清理可能残留的同名旧目录；
4. **`engine/app/materials/vectorstore.py`**：
   - 加固 `safe_rmtree`（`os.path.exists` 检查、重试 5 次并退避与 gc.collect）；
   - 确保 `remove_project_data` 彻底关闭项目实例并安全删除项目数据目录。
5. **`desktop/src/stores/project.ts`**：
   - `deleteProject` 与 `createProject` 确保清空当前活动项目的资料列表 `materials.value = []`，重置本地状态与 localStorage 缓存。
6. **`engine/tests/test_projects.py`**：
   - 新增 `test_delete_project_cleans_materials_chunks_and_allows_clean_recreation`。

## 2. 快速验证

- `python -m pytest engine/tests -q`
- `npx vitest run`（`desktop/`）
- `npx vue-tsc --noEmit`（`desktop/`）
- `npm run build`（`desktop/`）
- `cargo check`（`desktop/src-tauri/`）

完成后提交候选 commit 并编写 `docs/dev-flow/tasks/V2-T12/rounds/01/maker-completion.md`，交回候选 SHA。
