# 任务合同 V2-T9 v3 — 窄修复：本地项目资料文件夹系统级唤起（os.startfile 通路）

- 状态：READY_FOR_MAKER（2026-08-25 协调者发现 Tauri shell open 对本地目录 URL pattern 限制，改走引擎端系统级 os.startfile 通路）
- 依据：用户实测截图反馈 `打开资料目录失败: undefined`
- 精确起始 SHA：`f6137f394142f1cf1b4cfc24d3fe3a4f6be59299`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

根治「📁 打开资料目录」在 Windows 桌面端的调用失败问题：
- **根因**：Tauri 2 的 `@tauri-apps/plugin-shell` 中 `open()` 方法底层受限于 URL 正则白名单校验（默认仅放行 `http/https/mailto`），传入 Windows 本地物理绝对路径会被安全策略阻断并返回 `undefined`。
- **解决方案**：在本地 Python 引擎新增 `POST /projects/{name}/open-folder` 端点，在服务端使用 Windows 原生 `os.startfile(files_dir)`，由本地引擎直接拉起系统文件资源管理器定位到项目 `files/` 文件夹。
- **前端适配**：`engineApi.openProjectDir` 改为调用引擎 `/projects/{name}/open-folder`，彻底解除 Tauri 前端沙箱限制，实现 100% 稳健的系统资源管理器唤起。

---

## 2. 允许修改

- `engine/app/projects/router.py`
- `engine/tests/test_projects.py`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/stores/project.ts`
- `desktop/src/components/Step1Project.vue`
- `desktop/src/tests/project.test.ts`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T9/**`

---

## 3. 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿。
- [ ] `npx vitest run`（`desktop/`）全绿。
- [ ] `cargo check`、`npx vue-tsc --noEmit`、`npm run build` 全绿。
- [ ] B 级实跑：点击「📁 打开资料目录」，Windows 文件资源管理器立即弹出并定位到当前项目 `files` 目录。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`
3. `npx vue-tsc --noEmit`
4. `npm run build`
