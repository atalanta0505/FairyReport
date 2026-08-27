# 任务合同 V2-T17 v1 — 项目资料向量化摄取模型本地化加载与异常容错增强

- 状态：ACCEPTED（2026-08-27 Checker 独立验收通过，锁定候选 SHA `3f84c2ddd9561fef1b80ecd6b349f85da33d55a5`）
- 依据：用户反馈 Step 1 上传资料时界面长时间卡在「正在向量化摄取...」与「文件解析与分块向量化入库中，请稍候...」。排查发现 FastEmbed 在 Windows Temp 临时目录中的 ONNX 模型文件下载中断导致 `NO_SUCHFILE` 损坏。
- 精确起始 SHA：`205b3003360b3911c48ceecc5c37f68e4279ddcb`
- 候选交付 SHA：`3f84c2ddd9561fef1b80ecd6b349f85da33d55a5`
- 验收报告：`docs/dev-flow/tasks/V2-T17/rounds/01/checker-report.md` (PASS)
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **本地嵌入模型离线加载与持久化路径优先 (`engine/app/embedding.py`)**：
   - 现已下载完整的 `paraphrase-multilingual-MiniLM-L12-v2` ONNX 模型（包含 224MB `model_optimized.onnx`、16MB `tokenizer.json`、14MB `unigram.json` 等全部 9 个完整文件）至 `data/fastembed_models/`；
   - `FastEmbedEmbedder` 升级 `_ensure_model` 逻辑：优先检测并使用本地 `data/fastembed_models`（或 `ENGINE_DATA_DIR/models/fastembed`）作为 `specific_model_path`，彻底杜绝首次运行联网卡顿或 Temp 目录被系统清理导致的问题；
   - 即使无本地目录，指定持久化 `cache_dir=str(Path(settings.engine_data_dir) / "models")`，并设定国内高速镜像源 `HF_ENDPOINT`。

2. **单文件摄取与向量化异常容错与局部回滚 (`engine/app/materials/router.py`)**：
   - 在 `_process_file` 中增加细致的 `try...except` 异常捕获与 `session.rollback()`；
   - 当遇到解析异常、分块异常或向量化异常时，安全返回 `IngestResult(status="error", error=f"摄取失败: {str(e)}")`，并在前端展示明确的错误文件名与原因，杜绝后端 500 抛错导致前端加载圈永久卡死。

3. **单元测试与门禁验证**：
   - 运行全部后端 Pytest（确保与现有打桩及真实模型完全兼容）；
   - 重新构建 `desktop/dist/**`；
   - 运行全量 A 级门禁（vitest, pytest, vue-tsc, build, cargo check）。

---

## 2. 允许修改

- `engine/app/embedding.py`
- `engine/app/materials/router.py`
- `engine/tests/**`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T17/**`

---

## 3. 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿。
- [ ] `npx vitest run`（`desktop/`）全绿。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：
  1. 打开应用进入 Step 1，选择或拖拽本地工程底稿（.docx / .xlsx / .csv / .md / .txt）；
  2. 摄取过程不再卡住，1~3 秒内完成向量化入库并展示「成功摄取 N 份文件并完成向量化！」。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
5. `cargo check`（workdir=`desktop/src-tauri`）
