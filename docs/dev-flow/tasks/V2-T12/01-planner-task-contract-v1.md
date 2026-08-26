# 任务合同 V2-T12 v1 — 项目删除级联彻底清理资料分块与向量索引（杜绝重建项目残留历史资料）

- 状态：READY_FOR_MAKER（2026-08-26 产品负责人批准 V2-T12 实施方案）
- 依据：产品负责人反馈指示：
  “删除了的项目，新建后，项目资料的分块仍然存在。当项目删除后，所有的项目资料都应一并删除才对。通用知识包是保留的。”
- 精确起始 SHA：`453f0241cb9c0d65ca9a447247a174d35d7f80f1`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **SQLite 数据库连接开启外键级联支持 (`engine/app/db.py`)**：
   - 监听 SQLAlchemy Engine 的 `connect` 事件，为 SQLite 数据库连接执行 `PRAGMA foreign_keys=ON;`，确保外键约束与级联删除生效。
2. **ORM 模型级联配置 (`engine/app/models.py`)**：
   - 在 `Project` 模型中配置与 `Material` 的关系映射：
     ```python
     materials = relationship("Material", backref="project", cascade="all, delete-orphan", passive_deletes=True)
     ```
3. **项目路由删除与创建逻辑加固 (`engine/app/projects/router.py`)**：
   - `delete_project(name, session)`：
     - 显式执行 `session.execute(delete(models.Material).where(models.Material.project_id == proj.id))` 彻底清理 `materials` 表中的资料与分块记录；
     - 执行 `session.delete(proj)` 并 `session.commit()`；
     - 调用 `remove_project_data(name)` 关闭向量库缓存并删除包含文件、向量索引、大纲、章节的所有磁盘数据。
   - `create_project(body, session)`：
     - 在新建项目前，先行清理可能残留的同名旧目录与向量实例（`remove_project_data(body.name)`），确保新建项目处于绝对纯净状态。
4. **磁盘与向量库清理鲁棒性加固 (`engine/app/materials/vectorstore.py`)**：
   - `safe_rmtree(path, ignore_errors=True)`：增加 `os.path.exists(path)` 判断与 5 次重试退避（`time.sleep(0.1)` + `gc.collect()`），确保 Windows 下 ChromaDB 文件锁安全释放并彻底移除项目目录；
   - 保证仅清理项目专属目录（`settings.project_dir(name)`），绝不触碰通用知识包目录（`settings.generic_dir`）。
5. **前端 Store 状态与缓存清理 (`desktop/src/stores/project.ts`)**：
   - 在 `deleteProject` 与 `createProject` 中，确保清空当前活动项目的资料列表 `materials.value = []`、大纲及章节状态，并清理 `localStorage` 中对应的项目键值。
6. **单元测试与全量验证**：
   - 在 `engine/tests/test_projects.py` 中补充测试用例：
     - 验证项目创建、摄取资料、删除项目后，`materials` 表记录被清空，重新创建同名项目后资料列表完全为空，通用知识包状态未受影响。

---

## 2. 允许修改

- `engine/app/db.py`
- `engine/app/models.py`
- `engine/app/projects/router.py`
- `engine/app/materials/vectorstore.py`
- `desktop/src/stores/project.ts`
- `engine/tests/test_projects.py`
- `desktop/src/tests/**`（若需适配单测）
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T12/**`

---

## 3. 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿（含新增级联清理与重建验证测试）。
- [ ] `npx vitest run`（`desktop/`）全绿。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：
  1. 上传资料并生成分块 -> 删除该项目 -> 新建同名项目 -> 检查项目资料列表是否为空（分块数为 0）；
  2. 通用知识包状态依然为“已就绪”，不受项目删除影响。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
