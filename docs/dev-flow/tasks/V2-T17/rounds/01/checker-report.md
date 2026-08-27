# Checker 验收报告 — V2-T17 第 1 轮

- **任务 ID**：`V2-T17`
- **轮次**：第 1 轮（Round 01）
- **审查人**：Checker Agent
- **有效合同**：`docs/dev-flow/tasks/V2-T17/01-planner-task-contract-v1.md`
- **Maker 完成说明**：`docs/dev-flow/tasks/V2-T17/rounds/01/maker-completion.md`
- **精确基线 SHA**：`205b3003360b3911c48ceecc5c37f68e4279ddcb`
- **候选交付 SHA**：`3f84c2ddd9561fef1b80ecd6b349f85da33d55a5`
- **验收结论**：**PASS（验收通过）**

---

## 1. 变更范围与父链核对

### 1.1 提交链核验
- **基线父提交**：`205b3003360b3911c48ceecc5c37f68e4279ddcb`（docs(dev-flow): V2-T17 合同 v1 批准）
- **候选提交**：`3f84c2ddd9561fef1b80ecd6b349f85da33d55a5`（fix(materials): prioritize local fastembed model and add ingestion error handling with rollback）
- 提交链连续，无分叉或漂移。

### 1.2 文件变更范围审查 (`git diff --name-status`)
```text
M	engine/app/embedding.py
M	engine/app/materials/router.py
A	engine/tests/test_embedding.py
M	engine/tests/test_materials.py
```
- **允许范围**：`engine/app/embedding.py`, `engine/app/materials/router.py`, `engine/tests/**`, `desktop/dist/**`, `docs/dev-flow/tasks/V2-T17/**`。
- **禁止修改范围**：`backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore` 等均未受任何侵入。
- **工作区状态**：干净（除 dev-flow 文档外无未暂存残留）。

---

## 2. 代码级设计审查

### 2.1 本地嵌入模型离线优先与持久化缓存路径 (`engine/app/embedding.py`)
- `FastEmbedEmbedder._ensure_model` 逻辑：
  - 优先检测仓库本地预置模型目录 `data/fastembed_models`（包含完整的 `model_optimized.onnx`、`tokenizer.json`、`unigram.json` 等全部 9 个完整文件）；
  - 其次检测数据目录 `settings.engine_data_dir / "models" / "fastembed"`；
  - 若检测到 `model_optimized.onnx` 存在，直接调用 `TextEmbedding(model_name=..., specific_model_path=specific_path)`，实现 100% 离线秒级载入与推理；
  - 备用路径指定持久化 `cache_dir=str(Path(settings.engine_data_dir) / "models")` 并设置国内镜像源 `HF_ENDPOINT`，彻底消除 Windows `Temp` 临时目录被清理导致损坏的问题。
- 保持 `DeterministicStubEmbedder` 与 `get_embedder()` / `set_embedder()` 接口不变，单元测试可零依赖快速运行。

### 2.2 资料摄取异常容错与局部事务回滚 (`engine/app/materials/router.py`)
- `_process_file` 函数全流程（文件格式转换、分块切片、向量编码、向量库 upsert、本地文件拷贝、SQLite 资料记录 upsert）包裹于完备的 `try...except Exception as e` 异常捕获中；
- 发生任何异常时，触发 `session.rollback()`，并安全返回 `IngestResult(status="error", error=f"摄取失败: {str(e)}")`；
- 单个文件格式解析错误或损坏不会扩散为 HTTP 500，保障前端摄取批量接口正常返回清晰的逐文件摄取状态，彻底消除前端加载圈无限卡死的问题。

### 2.3 单元测试覆盖
- 新增 `engine/tests/test_embedding.py`：测试 `DeterministicStubEmbedder`、`FastEmbedEmbedder` 本地目录优先载入与降级逻辑、`get/set_embedder` 切换；
- 新增 `engine/tests/test_materials.py`：`test_ingest_exception_returns_error_result_and_rolls_back`（模拟向量化编码异常并验证回滚与错误返回）、`test_ingest_empty_file_returns_error_result`（验证空文件摄取错误返回）。

---

## 3. 独立重跑 A 级验证记录

Checker Agent 在本地环境独立执行全部快速验证命令，结果如下：

| 验证项 | 执行命令 | 执行工作目录 | 执行结果 |
| :--- | :--- | :--- | :--- |
| **Python 后端测试** | `python -m pytest engine/tests -q` | 根目录 | **101 passed**, 2 warnings in 56.85s (100% PASS) |
| **前端单元测试** | `npx vitest run` | `desktop/` | **5 files passed, 123 passed (100% PASS)** |
| **TypeScript 类型检查** | `npx vue-tsc --noEmit` | `desktop/` | **0 errors, clean output** |
| **生产打包构建** | `npm run build` | `desktop/` | **built in 1.18s, dist/** generated successfully** |
| **Rust Tauri 检查** | `cargo check` | `desktop/src-tauri/` | **Finished `dev` profile in 0.85s, 0 errors** |
| **离线推理实测** | `python -c "from engine.app.embedding import FastEmbedEmbedder; ..."` | 根目录 | **离线模型加载成功，输出 dim=384 向量** |

---

## 4. 判定结论与待办建议

- **判定结论**：**PASS（全部验收标准均达标，予以通过）**
- **阻断项（Blockers）**：0 项
- **非阻断风险（Risks）**：0 项

### 待产品负责人执行的 B 级人工验证项
1. 启动桌面端应用，进入 Step 1（项目管理与工程底稿资料库）；
2. 拖入或选取多种格式的资料底稿（`.docx` / `.xlsx` / `.csv` / `.md` / `.txt`）；
3. 点击「开始向量化摄取」，确认资料在 1~3 秒内完成向量化入库，界面提示「成功摄取 N 份文件并完成向量化！」，不再出现长时间卡顿或损坏异常。
