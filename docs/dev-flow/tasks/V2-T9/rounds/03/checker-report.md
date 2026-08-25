# Checker 验收报告 — V2-T9 第 3 轮（窄修复）

- **任务编号**：V2-T9（桌面端主流程向导 UI，第 3 轮窄修复）
- **任务目标**：根治 Windows 桌面端「📁 打开资料目录」失败问题，通过引擎后端原生系统调用（Windows `os.startfile`）直接唤起文件资源管理器
- **有效合同**：`docs/dev-flow/tasks/V2-T9/01-planner-task-contract-v3.md`
- **Maker 完成说明**：`docs/dev-flow/tasks/V2-T9/rounds/03/maker-completion.md`
- **基线父提交 SHA**：`a8ea5043e7222160ced2623254023ddef5ee14f6`
- **候选提交 SHA**：`e3a7d6e47f2ba78d47f522546a05dc09e3e4a343`
- **审查日期**：2026-08-25
- **验收结论**：**PASS**（全部通过）

---

## 1. 提交与范围核查

- **父提交链验证**：
  - `e3a7d6e47f2ba78d47f522546a05dc09e3e4a343^` 精确等于基线 SHA `a8ea5043e7222160ced2623254023ddef5ee14f6`（合同 v3 批准提交）。
- **文件变更边界核查**：
  - `git diff --name-status a8ea5043e7222160ced2623254023ddef5ee14f6..e3a7d6e47f2ba78d47f522546a05dc09e3e4a343`
  - 变更文件清单：
    - `desktop/dist/**`（构建产物一致同步）
    - `desktop/src/components/Step1Project.vue`
    - `desktop/src/lib/engineApi.ts`
    - `desktop/src/stores/project.ts`
    - `desktop/src/tests/project.test.ts`
    - `engine/app/projects/router.py`
    - `engine/tests/test_projects.py`
  - **合规判定**：严格限定在合同允许的 `desktop/**` 与 `engine/**` 范围内，无越界修改任何未授权文件。
- **工作区状态**：`git status --short` 干净。

---

## 2. 独立重跑 A 级快速验证

Checker 独立执行全部自动化测试与编译构建（未采信 Maker 口述），结果如下：

| 验证项 | 执行命令 / 路径 | 耗时 / 结果 | 判定 |
| :--- | :--- | :--- | :---: |
| **1. 引擎测试套件** | `python -m pytest engine/tests -q` | 71 passed, 2 warnings (36.81s) | ✅ PASS |
| **2. 前端单元测试** | `npx vitest run` (`desktop/`) | 3 test files, 37 passed (896ms) | ✅ PASS |
| **3. Rust 编译检查** | `cargo check` (`desktop/src-tauri/`) | Finished dev in 0.89s | ✅ PASS |
| **4. Vue 类型检查** | `npx vue-tsc --noEmit` (`desktop/`) | 0 errors | ✅ PASS |
| **5. 前端生产构建** | `npm run build` (`desktop/`) | Built in 729ms, dist 产物一致 | ✅ PASS |

---

## 3. 代码级与逻辑安全性审查

1. **引擎后端原生唤起端点 (`engine/app/projects/router.py`)**：
   - 提取公共 `_get_project(session, name)` 查询辅助函数，统一对不存在项目抛出标准 404 `HTTPException`。
   - `POST /projects/{name}/open-folder` 端点实现健全：
     - 查询项目存在性；
     - 通过 `settings.files_dir(proj.name)` 获取绝对路径，并调用 `fdir.mkdir(parents=True, exist_ok=True)` 确保物理目录必定存在；
     - 跨平台兼容性良好：Windows 下使用原生 `os.startfile(fpath)`，macOS 下使用 `subprocess.Popen(["open", fpath])`，Linux 下使用 `subprocess.Popen(["xdg-open", fpath])`；
     - 异常捕获完善，发生系统级异常时转换为 500 错误码与友好描述返回。
2. **前端与 Store 接入 (`desktop/src/lib/engineApi.ts` & `desktop/src/stores/project.ts` & `Step1Project.vue`)**：
   - `engineApi.openProjectDir` 重构为向本地引擎发送 `POST /projects/{encodeURIComponent(name)}/open-folder`；
   - Store 中规范管理状态并增加基础参数校验；
   - `Step1Project.vue` 增加 `engine.baseUrl` 就绪检查，统一捕获错误并提示，交互体验平滑。
3. **测试覆盖充分 (`engine/tests/test_projects.py` & `desktop/src/tests/project.test.ts`)**：
   - 引擎端对 200 正常唤起（含 mock 检查）和 404 不存在项目分别进行覆盖；
   - 前端对 API 与 Store 的请求路径、Method 与数据返回做了完整断言。

---

## 4. 判定结论与后续步骤

- **最终判定**：**PASS**
- **建议锁定 SHA**：`e3a7d6e47f2ba78d47f522546a05dc09e3e4a343`
- **阻断项**：无
- **非阻断风险与提示**：
  - 彻底规避了 Tauri 2 `@tauri-apps/plugin-shell` 在 Windows 上的 URL Scheme 白名单校验限制，系统集成度与稳定性大幅提升。
- **B 级人工验收建议（产品负责人）**：
  1. 启动本地桌面客户端与 Python 引擎；
  2. 在 Step 1（项目与资料）中选择或新建一个项目；
  3. 点击「📁 打开资料目录」按钮；
  4. 确认 Windows 文件资源管理器立即弹出并正确定位到 `%LOCALAPPDATA%\FairyReport\projects\<项目名>\files` 目录；
  5. 往该目录中拖入文件，点击「🔄 扫描本地资料」，确认文件被秒级索引并在左侧资料列表中呈现。
