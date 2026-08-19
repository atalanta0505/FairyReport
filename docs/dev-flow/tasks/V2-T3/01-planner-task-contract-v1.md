# 任务合同 V2-T3 v1 — 资料 API：上传/解析/分块/向量化

- 状态：DRAFT（待产品负责人批准；批准即视为批准 §7 依赖清单）
- 产品决定来源：`00-product-decision-v2.md` 路线图 T3（D1 资料上云）
- 精确起始 SHA：本合同提交后的 master HEAD
- 工作树门禁：`git status --short` 必须干净

## 1. 背景与目标

桌面端用户的项目资料经后端统一处理：上传 → 解析为文本 → 分块 → 向量化入库，供后续 RAG 写作（T5）检索。本切片移植现有 `pipeline.py`（分块）与 `kb.py`（双库模式中的项目库部分）的核心逻辑到 backend，不依赖根目录 Streamlit 代码。

## 2. 唯一主要行为变化

**登录用户可创建项目、上传资料文件（docx/xlsx/csv/md/txt），后端解析-分块-向量化入库；可列出资料、按来源删除（向量同步删除）。**

## 3. 明确不做

- 不做 generic KB（T4）、不做检索接口（T5 随 RAG 一起）、不做写作/导出
- 不做 PDF（现有产品也不支持）
- 不做腾讯云部署（服务器未就位；本切片全部本地验证）
- 不改动根目录 Streamlit 产品代码（移植 = 复制改造，不是 import）

## 4. 实现导航

- 参考（只读）：根目录 `pipeline.py`（chunk_text 的标题边界+重叠分块逻辑、SUPPORTED_EXTENSIONS）、`kb.py`（chromadb collection/upsert/delete_by_source 模式、source_id 去重）、`converters/`（各格式转 markdown 的实现思路）
- 新建 `backend/app/materials/`：
  - `router.py` — 端点（全部 JWT 保护）：
    - `POST /api/projects`（建项目，名称唯一于该用户）/ `GET /api/projects` / `DELETE /api/projects/{id}`（连同文件与向量删除）
    - `POST /api/projects/{id}/materials`（multipart 上传；扩展名白名单 .docx/.xlsx/.csv/.md/.txt；单文件 ≤50MB，超限 413；非法扩展名 422）
    - `GET /api/projects/{id}/materials`（来源列表：文件名、chunk 数、上传时间）
    - `DELETE /api/projects/{id}/materials/{source_id}`（文件+向量删除）
  - `converters.py` — 五格式 → markdown/纯文本（移植根 converters/ 逻辑：python-docx、docx2txt、openpyxl、markdownify）
  - `chunking.py` — 移植 pipeline.chunk_text（标题边界、CHUNK_SIZE=800、CHUNK_OVERLAP=100 可配置）
  - `vectorstore.py` — chromadb PersistentClient，每项目独立目录（BACKEND_DATA_DIR 下 user_<id>/<project>/vector）；嵌入用 fastembed 的 `paraphrase-multilingual-MiniLM-L12-v2`（与现网模型一致，保证检索质量对齐）；upsert 幂等（source_id 为键，重复上传覆盖旧向量）
  - 权限隔离：用户只能访问自己的项目（他人项目 id → 404）
- 文件存储：BACKEND_DATA_DIR（环境变量，默认 ./backend_data）下 user_<id>/<project>/files/；该目录整体 gitignore
- 新增表：project（id、user_id、name、created_at）、material（id、project_id、source_id、filename、ext、chunk_count、size_bytes、created_at）

## 5. 允许修改

- `backend/**`
- `.gitignore`（如需为 backend_data/ 增补）
- `docs/dev-flow/tasks/V2-T3/**`

## 6. 禁止修改

- 根目录现有全部产品文件、steps/、components/、converters/、generic_knowledge/、根 requirements.txt、.opencode/、AGENTS.md

## 7. 新增依赖清单（随合同批准）

chromadb、fastembed、python-docx、docx2txt、openpyxl、markdownify（共 6 个，写入 backend/requirements.txt；由产品负责人安装）。嵌入模型权重（约 120MB）首次使用自动下载，属人工环境事项。

## 8. 验收标准

- [ ] 建项目/列项目/删项目正常；他人项目不可见（404）
- [ ] 上传 .md 测试文件 → 解析+分块+向量入库，material 记录 chunk_count>0
- [ ] 五种格式各有解析用例（小型 fixture 文件随测试提交）
- [ ] 重复上传同名文件 → upsert 覆盖，chunk 不重复累积
- [ ] 按 source 删除 → 向量与文件同删，列表更新
- [ ] 非法扩展名 → 422；超限 → 413；未认证 → 401
- [ ] 单元测试中嵌入打桩（确定性假向量），不依赖真实模型下载、不依赖网络
- [ ] T1/T2 既有 30 个测试保持全绿
- [ ] `python -c "from backend.app.main import app"` 通过

## 9. Maker 快速测试（按顺序）

1. `python -m pytest backend/tests -q`
2. `python -c "from backend.app.main import app"`

## 10. Evidence Runner 分级验证计划

- 真实嵌入模型冒烟（下载模型后对真实 docx 跑一次入库）：人工环境项，待模型下载完成后由产品负责人触发，不阻塞本切片验收。

## 11. GUI / 人工验收项

- 无（纯 API 切片）。

## 12. 候选提交与完成说明要求

- 候选只含 backend/**（及 .gitignore 如需）；完成说明单独提交到 rounds/01/maker-completion.md
- 不 amend、不 rebase、不 push
- 测试 fixture 小文件（每个 <10KB）随候选提交；backend_data/ 运行时产物绝不入库

## 13. 停止条件

- 基线/工作树不符；需要清单外依赖；必须越界修改；同一失败两次；
- fastembed 与 Python 3.14 不兼容且两次尝试无解 → 停止报告（备选：chromadb 自带 ONNX 嵌入，由 Planner 决定）。

## 14. 已知基线失败

- 无（T2 验收时 30 passed）。
