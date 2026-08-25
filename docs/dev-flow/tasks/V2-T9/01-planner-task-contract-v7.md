# 任务合同 V2-T9 v7 — 项目大纲与各步骤全链路持久化（后端存储 + 前端自动同步）

- 状态：ACCEPTED（第 7 轮 PASS；锁定候选 ab2a2d9b98634e46b947b2d70a0b0c166e2a0b48）
- 依据：用户实测截图反馈大纲生成后无法持久留存，要求每一步全链路持久化
- 精确起始 SHA：`72970f8087968536f98ef4ba021fb7a55ae58f0a`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

实现 Step 2 报告大纲与选定模板的全链路持久化（后端文件落盘 + 前端自动同步）：
1. **本地引擎大纲持久化端点 (`engine/app/writing/router.py`)**：
   - `GET /projects/{name}/outline`：读取 `%LOCALAPPDATA%/FairyReport/projects/<name>/outline.json`，返回 `{ report_type, outline_md, chapters, updated_at }`；文件不存在时返回安全默认值；
   - `POST /projects/{name}/outline`：将 `{ report_type, outline_md, chapters }` 写入对应项目根目录下的 `outline.json`；
   - 在 `POST /writing/outline` 生成大纲时，若 `req.project` 非空，自动完成一次落盘保存。
2. **桌面端 API 客户端与 Store 联动 (`desktop/src/lib/engineApi.ts` & `desktop/src/stores/project.ts`)**：
   - 增加 `getProjectOutline` 与 `saveProjectOutline` API；
   - Store 中增加 `loadOutline` 与 `saveOutline` 方法，并在 `selectProject` / `loadProjects` 时自动为当前活动项目加载其专属大纲与模板；
   - 增加 `localStorage` 双重本地备份机制（键名 `frl_outline_<projectName>`）；
   - 在用户手动编辑大纲文本（`setOutlineMd`）或切换模板（`setReportType`）时，自动防抖触发持久化保存。
3. **Step 2 UI 响应与自动回填 (`desktop/src/components/Step2Outline.vue`)**：
   - 监听活动项目切换与步骤切入，自动回填已保存的模板与大纲草稿，确保无论是刷新、重启客户端还是在各步骤间来回切换，大纲内容永不丢失。

---

## 2. 允许修改

- `engine/app/writing/router.py`
- `engine/tests/test_writing_router.py`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/stores/project.ts`
- `desktop/src/components/Step2Outline.vue`
- `desktop/src/tests/project.test.ts`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T9/**`

---

## 3. 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿（含大纲 GET/POST 持久化单测）。
- [ ] `npx vitest run`（`desktop/`）全绿（含前端大纲持久化/自动回填单测）。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：生成大纲后，退出应用重新打开或切换项目，已生成大纲 100% 自动回填且章节目录树正常呈现。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
