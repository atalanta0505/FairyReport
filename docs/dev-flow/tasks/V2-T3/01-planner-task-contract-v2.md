# 任务合同 V2-T3 v2 — 本地引擎骨架 + 资料处理（架构 C 重制版）

- 状态：DRAFT（待产品负责人批准）
- 产品决定来源：`00-product-decision-v4.md`（D14 架构 C）
- 版本说明：v1（资料上云版）因架构转向作废，未开工；v2 为重制版本
- 精确起始 SHA：本合同提交后的 master HEAD
- 工作树门禁：`git status --short` 必须干净

## 1. 背景与目标

桌面端的本地 Python 引擎（sidecar）从零建立：本切片交付引擎服务骨架与资料处理能力（解析/分块/向量化），供后续通用知识（T4）、写作（T5）、导出（T6）叠加。引擎逻辑移植自根目录现有实现（只读参考），引擎是**本机服务**，不做云端上传语义。

## 2. 唯一主要行为变化

**本地引擎可创建/列出/删除项目，按本地文件路径摄取资料（docx/xlsx/csv/md/txt）完成解析-分块-向量化入库，可列出资料并按来源删除（文件与向量同步删除）。**

## 3. 明确不做

- 不做通用知识包（T4）、不做写作/导出（T5/T6）、不做 LLM 调用
- 不做认证（本机服务；通信安全见 O9，T8 合同再定）
- 不改动 backend/（云端认证服务，T1/T2 产物保持原样）
- 不改动根目录 Streamlit 遗留代码（只读参考）

## 4. 实现导航

- 只读参考：根目录 `pipeline.py`（标题边界分块）、`kb.py`（chromadb upsert/delete_by_source、source_id 幂等）、`converters/`（五格式转文本）、`config.py`（数据目录与 .env 覆盖模式）
- 新建 `engine/`（独立 FastAPI 应用，结构自洽，不 import backend/ 与根目录模块）：
  - `engine/app/main.py` — 入口 + `GET /health`；配置上仅绑定 127.0.0.1
  - `engine/app/config.py` — ENGINE_DATA_DIR（默认 `%LOCALAPPDATA%/FairyReport`，环境变量可覆盖）、CHUNK_SIZE=800/CHUNK_OVERLAP=100、嵌入模型名
  - `engine/app/db.py` + `engine/app/models.py` — SQLite + SQLAlchemy：project 表（name 唯一）、material 表（source_id、filename、ext、chunk_count、size_bytes、时间）
  - `engine/app/projects/router.py` — POST /projects、GET /projects、DELETE /projects/{name}（连同 files 目录与向量目录删除）
  - `engine/app/materials/router.py` — POST /projects/{name}/materials/ingest（body：file_paths 数组；路径不存在 4xx；扩展名白名单外 4xx）、GET /projects/{name}/materials、DELETE /projects/{name}/materials/{source_id}
  - `engine/app/materials/converters.py`、`chunking.py` — 移植（含 FRL-003 式边界保护：overlap>=size 时钳制）
  - `engine/app/materials/vectorstore.py` — chromadb PersistentClient 每项目独立目录；upsert 幂等（source_id 为键）；delete_by_source
  - `engine/app/embedding.py` — fastembed `paraphrase-multilingual-MiniLM-L12-v2` 封装，接口可注入/可打桩
- 数据布局：ENGINE_DATA_DIR/projects/<project>/files|vector
- 测试（engine/tests/）：嵌入打桩（确定性假向量）；数据目录 monkeypatch 到 tmp；五格式小型 fixture（各 <10KB）随候选提交；不下载真实模型、不联网
- 代码风格跟随现有仓库（简洁 docstring）

## 5. 允许修改

- `engine/**`（全部新建）
- `.gitignore`（如需为引擎运行时目录增补）
- `docs/dev-flow/tasks/V2-T3/**`

## 6. 禁止修改

- `backend/**`（T1/T2 验收产物）
- 根目录现有全部产品文件、steps/、components/、converters/、generic_knowledge/、根 requirements.txt、.opencode/、AGENTS.md

## 7. 依赖

无新增（chromadb/fastembed/python-docx/docx2txt/openpyxl/markdownify/fastapi/sqlalchemy/pydantic-settings/pytest/httpx 均已安装）。`engine/requirements.txt` 照实登记，供打包切片使用。

## 8. 验收标准

- [ ] `GET /health` 200；应用配置仅绑定 127.0.0.1
- [ ] 建/列/删项目；删项目连同文件与向量目录删除
- [ ] ingest .md 本地路径 → chunk_count>0；五格式各有用例
- [ ] 同源重复 ingest → upsert 覆盖不累积
- [ ] 按 source 删除 → 文件+向量同删
- [ ] 路径不存在 / 扩展名非法 → 4xx
- [ ] backend 既有 30 个测试保持全绿（回归守卫）
- [ ] `python -c "from engine.app.main import app"` 通过

## 9. Maker 快速测试（按顺序）

1. `python -m pytest engine/tests -q`
2. `python -m pytest backend/tests -q`（回归守卫）
3. `python -c "from engine.app.main import app"`

## 10. Evidence Runner 分级验证计划

- 真实嵌入模型冒烟为日后人工项（模型下载后），不阻塞本切片。

## 11. GUI / 人工验收项

- 无。

## 12. 候选提交与完成说明要求

- 候选只含 engine/**（及 .gitignore 如改）；完成说明单独提交到 rounds/02/maker-completion.md（rounds/01 预留给已作废的 v1 轮次，实际未产生文件则直接启用 rounds/01 亦可——Maker 核实后择一，说明中记录）
- 不 amend、不 rebase、不 push

## 13. 停止条件

- 基线/工作树不符；需要新依赖；越界修改；同一失败两次
- fastembed 与 Python 3.14 不兼容且两次尝试无解 → 停止报告

## 14. 已知基线失败

- 无（backend 30 passed）。
