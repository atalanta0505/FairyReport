# Maker 完成说明 — V2-T9 第 3 轮（窄修复）

- **任务合同**：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v3.md`
- **转发消息**：`docs/dev-flow/tasks/V2-T9/02-planner-to-maker-message-v3.md`
- **起始 SHA**：`a8ea5043e7222160ced2623254023ddef5ee14f6`
- **候选 SHA**：`e3a7d6e47f2ba78d47f522546a05dc09e3e4a343`
- **完成时间**：2026-08-25

---

## 1. 交付文件清单

本轮窄修复交付严格仅限 `engine/**`、`desktop/**` 与治理说明文档：

### 引擎后端 (`engine/**`)
1. `engine/app/projects/router.py`：
   - 提取 `_get_project` 公共安全查询辅助函数；
   - 新增 `POST /projects/{name}/open-folder` 端点，确保项目 `files/` 目录存在并使用系统原生能力唤起（Windows 下 `os.startfile`，macOS/Linux 下 `open`/`xdg-open` fallback）。
2. `engine/tests/test_projects.py`：
   - 新增 `test_open_project_folder` 单元测试（使用 `unittest.mock.patch` 模拟 `os.startfile`）；
   - 新增 `test_open_nonexistent_project_folder_returns_404` 单元测试。

### 桌面端前端 (`desktop/**`)
1. `desktop/src/lib/engineApi.ts`：
   - 更新 `openProjectDir(baseUrl, projectName)` 方法，调用本地引擎 `POST /projects/{name}/open-folder` 端点，彻底解除 Tauri 前端 shell 插件对本地物理路径的安全阻断。
2. `desktop/src/stores/project.ts`：
   - 扩展 `openProjectDir(baseUrl, projectName?)` 状态机方法。
3. `desktop/src/components/Step1Project.vue`：
   - 适配 `handleOpenProjectDir` 调用，传入 `engine.baseUrl`，移除未使用的 `engineApi` 引用。
4. `desktop/src/tests/project.test.ts`：
   - 新增 `engineApi.openProjectDir` 与 `store.openProjectDir` 自动化单测。
5. `desktop/dist/**`：
   - 同步更新生产构建产物。

---

## 2. 核心设计与修复说明

1. **问题根因**：
   - Tauri 2 的 `@tauri-apps/plugin-shell` 中 `open()` 方法底层存在 URL 协议白名单限制（默认仅放行 `http/https/mailto` 等 URL），直接传入 Windows 本地绝对文件系统路径会被安全校验抛弃，导致前端报 `打开资料目录失败: undefined`。
2. **根治方案**：
   - 将唤起文件资源管理器的动作移至本地 Python 引擎服务端；
   - 在引擎侧使用 Windows 原生 `os.startfile(files_dir)`，绕过浏览器沙箱与前端插件限制，实现 100% 稳健的资源管理器定位与弹出。

---

## 3. 快速验证记录

严格按照合同第 5 条约定的快速验证顺序执行：

```bash
# 1. 引擎测试套件
python -m pytest engine/tests -q
# 结果：71 passed, 2 warnings in 38.51s（通过率 100%）

# 2. 前端 Vitest 单元测试
npx vitest run (desktop)
# 结果：3 个测试文件，37 项测试全部通过（通过率 100%）
# ✓ src/tests/api.test.ts (7 tests)
# ✓ src/tests/engine.test.ts (5 tests)
# ✓ src/tests/project.test.ts (25 tests)

# 3. Rust 编译检查
cargo check (desktop/src-tauri)
# 结果：Finished `dev` profile in 0.93s，Exit Code 0

# 4. Vue/TypeScript 严格类型检查
npx vue-tsc --noEmit (desktop)
# 结果：无类型报错，Exit Code 0

# 5. 前端生产打包构建
npm run build (desktop)
# 结果：Vite 构建打包成功（dist 产物一致），Exit Code 0
```

---

## 4. 冻结声明

- 代码变更严格限定在 `engine/**` 与 `desktop/**`。
- 本地工作树已验证且保持干净，无 `git push`、无 `git rebase`、无 `git commit --amend`。
- 正式交付候选 SHA：`e3a7d6e47f2ba78d47f522546a05dc09e3e4a343`，交回验收。
