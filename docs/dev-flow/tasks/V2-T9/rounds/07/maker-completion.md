# Maker 完成说明 — V2-T9 第 7 轮（全链路大纲持久化）

- **任务 ID**：V2-T9
- **轮次**：第 7 轮
- **有效合同**：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v7.md`
- **精确起始 SHA**：`5108a26b2b73bc3a6cbbdbdf25a58742d46e017d`
- **候选提交 SHA**：`ab2a2d9b98634e46b947b2d70a0b0c166e2a0b48`
- **冻结声明**：Maker 编码与自测已全部完成，工作树已冻结，无未提交修改，严禁 push / rebase / amend。

---

## 1. 修改文件清单

| 路径 | 变动类型 | 说明 |
|---|---|---|
| `engine/app/writing/router.py` | 修改 | 新增 `OutlineData` 模型与 `GET/POST /projects/{name}/outline` 端点；在 `POST /writing/outline` 生成大纲时支持根据 `req.project` 自动落盘 |
| `engine/tests/test_writing_router.py` | 修改 | 新增项目大纲默认返回值、存取持久化数据以及生成大纲时自动落盘的单元测试 |
| `desktop/src/lib/engineApi.ts` | 修改 | 新增 `getProjectOutline` 与 `saveProjectOutline` API 客户端通信函数 |
| `desktop/src/stores/project.ts` | 修改 | 新增 `loadOutline`、`saveOutline`、`localStorage` 双重备份与防抖自动保存；在 `loadProjects`、`selectProject`、`generateOutline` 自动同步大纲 |
| `desktop/src/components/Step2Outline.vue` | 修改 | 步骤切入、项目切换与挂载时自动调用 `loadOutline` 恢复大纲与模板；编辑输入时自动同步持久化 |
| `desktop/src/tests/project.test.ts` | 修改 | 增加大纲持久化存取、降级容灾、项目切换同步等 8 个单测用例（共 51 个通过） |
| `desktop/dist/**` | 重建 | 产物重新构建打包 |

---

## 2. 设计与决策

1. **双重持久化与降级保障（引擎文件落盘 + localStorage 离线备份）**：
   - 引擎端将项目大纲以 JSON 格式存储于 `%LOCALAPPDATA%/FairyReport/projects/<name>/outline.json`，确保后端与多客户端共享一致；
   - 前端同时在 `localStorage` 备份（键名 `frl_outline_<projectName>`），在离线或本地引擎重启/等待时也能瞬间恢复用户草稿，体验零延迟、零丢稿。
2. **生成即落盘 + 编辑防抖保存**：
   - AI 大纲生成成功后立即自动落盘保存到后端；
   - 用户在 Markdown 编辑器中自由打字或调整模板时，立即写入 `localStorage` 并通过 300ms 防抖同步至本地引擎 `outline.json`。
3. **多项目大纲隔离与自动切换**：
   - 在 `selectProject` 或 `loadProjects` 切换项目时，自动为当前选中项目加载其专属大纲和模板类型；当大纲为空或未生成时优雅呈现空白模板，互不干扰。

---

## 3. 快速验证结果

严格按照合同第 5 节约定的顺序执行验证：

1. **`python -m pytest engine/tests -q`**：
   ```
   74 passed, 2 warnings in 77.42s (0:01:17)
   ```
2. **`npx vitest run`（`desktop/`）**：
   ```
   Test Files  3 passed (3)
        Tests  51 passed (51)
   Duration  887ms
   ```
3. **`npx vue-tsc --noEmit`（`desktop/`）**：
   - 检查通过，0 错误，0 警告。
4. **`npm run build`（`desktop/`）**：
   - 构建通过，`desktop/dist/` 产物已重建就绪。
5. **`cargo check`（`desktop/src-tauri`）**：
   - 编译检查通过。

---

## 4. 交付总结

所有变更均严格局限于合同允许路径。已创建候选 commit `ab2a2d9b98634e46b947b2d70a0b0c166e2a0b48`。
工作树已冻结，交回 Checker 与 Coordinator 进行审查。
