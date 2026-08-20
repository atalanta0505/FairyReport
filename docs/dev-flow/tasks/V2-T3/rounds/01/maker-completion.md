# Maker 完成说明 — V2-T3 第 1 轮（本地引擎骨架 + 资料处理）

## 合同与基线

- 有效合同：`tasks/V2-T3/01-planner-task-contract-v2.md`（v2，架构 C 重制版；v1 资料上云版已作废，未开工）
- 起始 SHA：`b97b7d73cf98a087c35702e827ff7334f1f59e28`（已核对：`git status --short` 干净，HEAD 与合同基线一致）
- 轮次目录选择：合同 §12 规定 rounds/01 预留给已作废的 v1 轮次；经核实 rounds/ 目录此前不存在、v1 未开工未产生任何 rounds 文件，故直接启用 rounds/01（非 02）。v1 的 01-planner-task-contract-v1.md 与 02-planner-to-maker-message-v1.md 仍作为历史记录保留于任务根目录，不属轮次产物。

## 唯一主要行为变化

新建本地引擎（`engine/`，FastAPI，仅绑定 127.0.0.1）：可创建/列出/删除项目，按本地文件路径摄取资料（docx/xlsx/csv/md/txt）完成解析-分块-向量化入库，可列出资料并按来源删除（文件与向量同步删除）。引擎独立自洽，不 import backend/ 与根目录模块；逻辑移植自根目录只读参考（pipeline.py / kb.py / converters/ / config.py）。

## 候选

- 候选 SHA：`4839ec16674997985d928c83ff360653c2b97563`
- 父提交：`b97b7d73cf98a087c35702e827ff7334f1f59e28`
- 提交标题：V2-T3 本地引擎骨架与资料处理（建/列/删项目 + 五格式摄取/分块/向量化）
- 精确修改文件（全部新建，共 27 项，均在 engine/**）：
  - `engine/__init__.py`、`engine/app/__init__.py`
  - `engine/app/config.py` — pydantic-settings：ENGINE_DATA_DIR（默认 %LOCALAPPDATA%/FairyReport，env 可覆盖）、CHUNK_SIZE=800/CHUNK_OVERLAP=100（含 FRL-003 钳制：overlap>=size 时降为 size//4）、嵌入模型名 paraphrase-multilingual-MiniLM-L12-v2、host=127.0.0.1/port=8001；database_url/projects_dir/files_dir/vector_dir 派生
  - `engine/app/db.py` — SQLAlchemy DeclarativeBase + make_engine（SQLite check_same_thread=False，内存库 StaticPool）+ SessionLocal + get_db + create_tables
  - `engine/app/models.py` — Project（name 唯一）、Material（project_id/source_id/filename/ext/chunk_count/size_bytes/created_at，(project_id,source_id) 唯一约束）
  - `engine/app/embedding.py` — Embedder 协议 + FastEmbedEmbedder（懒加载）+ DeterministicStubEmbedder（SHA-256 确定性假向量，dim=384）+ get_embedder/set_embedder（可注入/可打桩）
  - `engine/app/projects/router.py` — POST /projects、GET /projects、DELETE /projects/{name}（连 files+vector 目录删除，先关向量库缓存释放锁再 rmtree）；项目名防目录穿越校验
  - `engine/app/materials/router.py` — POST /projects/{name}/materials/ingest（file_paths 数组；路径不存在 400；扩展名白名单外 415）、GET /projects/{name}/materials、DELETE /projects/{name}/materials/{source_id}
  - `engine/app/materials/converters.py` — 移植五格式转 Markdown（docx 优先 pandoc 显式 utf-8 解码、回退 python-docx；xlsx openpyxl；csv 自动探测编码/分隔符；txt/md 多编码直读）
  - `engine/app/materials/chunking.py` — 移植分块（标题边界分段 + 固定大小重叠，含 FRL-003：size<=0 抛错、overlap>=size 钳制为 size//4、强制前进）
  - `engine/app/materials/vectorstore.py` — chromadb PersistentClient 每项目独立目录；collection 名合规化（3-512 字符、首尾字母数字，否则 md5 哈希为 proj_<hex>）；upsert 以 source_id 为键构建稳定 ID 幂等；delete_by_source 用 where 过滤；close_project 释放缓存+gc
  - `engine/app/main.py` — FastAPI 入口 + GET /health + include_router + create_tables + main()（uvicorn host=settings.host 仅 127.0.0.1）
  - `engine/requirements.txt` — 登记依赖（供打包切片）
  - 测试：`engine/tests/conftest.py`（per-test tmp 数据目录隔离 + 确定性假嵌入注入 + DB 表重置 + 向量库缓存清理）、test_health.py、test_projects.py、test_materials.py（五格式/幂等/删除/4xx/404）、test_chunking.py（FRL-003 边界保护）
  - fixtures：sample.md / sample.txt / sample.csv（文本）、sample.docx（手制最小 docx 1897B，_make_docx.py 生成脚本）、sample.xlsx（openpyxl 4995B）；各 <10KB

## 关键设计决策

- **引擎独立自洽**：engine/ 内部相对导入，绝不 import backend/ 或根目录 pipeline/kb/converters/config
- **嵌入可打桩**：routers 在请求时调用 get_embedder()，conftest 预先 set_embedder(DeterministicStubEmbedder())，测试不下载模型、不联网
- **幂等摄取**：ingest 时先 delete_by_source 删旧同源向量再 upsert，保证不累积（即便文件改动导致分块数变化也不残留旧向量）
- **测试隔离**：per-test tmp_path 作为 ENGINE_DATA_DIR（文件系统完全隔离，避免 chroma sqlite 锁导致跨用例残留向量），DB 表 drop/create 隔离关系数据
- **Windows 兼容**：pandoc 子进程显式 encoding=utf-8 解码（修默认 gbk locale 下 UTF-8 输出解码失败）；safe_rmtree 重试应对 chroma 短暂持锁
- **docx 小型 fixture**：python-docx 默认模板 ~35KB 超 10KB 限制，改用 zipfile 手制最小合法 docx（含 styles.xml，pandoc 与 python-docx 均可读，1897B）

## 验收标准对照

| 验收项（合同 §8） | 结果 | 证据 |
|---|---|---|
| GET /health 200；配置仅绑定 127.0.0.1 | ✅ | test_health_returns_200 / test_config_binds_localhost_only |
| 建/列/删项目；删项目连文件与向量目录删除 | ✅ | test_create_project / test_list_projects / test_delete_project_removes_dirs（断言目录不存在） |
| ingest .md → chunk_count>0；五格式各有用例 | ✅ | test_ingest_md_creates_chunks_and_file / test_ingest_each_format_produces_chunks（csv/docx/md/txt/xlsx 各一） |
| 同源重复 ingest → upsert 覆盖不累积 | ✅ | test_reingest_same_source_upsert_no_accumulation（count==chunk_count，资料记录仍 1 条） |
| 按 source 删除 → 文件+向量同删 | ✅ | test_delete_material_removes_file_and_vectors（文件不存在、count==0、记录空） |
| 路径不存在 / 扩展名非法 → 4xx | ✅ | test_ingest_nonexistent_path_returns_4xx（400）/ test_ingest_unsupported_extension_returns_4xx（415） |
| backend 30 测试保持全绿 | ✅ | 见下快速验证记录（30 passed） |
| `python -c "from engine.app.main import app"` | ✅ | 见下（import ok） |

## 快速验证记录（按合同 §9 顺序）

| 命令 | 结果 |
|---|---|
| `python -m pytest engine/tests -q` | exit 0：20 passed, 2 warnings |
| `python -m pytest backend/tests -q` | exit 0：30 passed, 1 warning（回归守卫全绿） |
| `python -c "from engine.app.main import app"` | exit 0：import ok |

首次失败记录：
- 一次：路由未注册（fixture 命名 `_isolated_state` 非注入式）→ 改名 `client` autouse 返回 TestClient
- 一次：chromadb collection 名 "p1" 仅 2 字符不满足 3-512 规则 → 强化 `_sanitize_collection_name` 校验首尾字母数字与长度，不满足则哈希
- 一次：chroma sqlite 锁致跨用例残留向量（rmtree ignore_errors 未清锁，下用例复用同目录带旧数据）→ 改 per-test tmp_path 数据目录，文件系统完全隔离不再依赖 rmtree 清锁
- 一次：pandoc 子进程默认 gbk 解码 UTF-8 输出失败 → 显式 encoding=utf-8/errors=replace
- 一次：test 写 bad.pdf 到 fixtures 目录泄漏 → 改用 tmp_path

均在合同范围内修复，未触停止条件。

## 明确保留（未改动）

- backend/**（T1/T2 验收产物）未动
- 根目录 pipeline.py / kb.py / converters/ / config.py / steps/ / components/ / generic_knowledge/ / 根 requirements.txt / .opencode/ / AGENTS.md 均未动
- .gitignore 未改（引擎运行时数据在 %LOCALAPPDATA% 与 tmp，不在仓库内）

## 未执行项（移交 Evidence Runner / 人工）

- 真实嵌入模型冒烟（fastembed paraphrase-multilingual-MiniLM-L12-v2 真实下载+encode）为日后人工项（合同 §10），本切片测试用确定性假向量不下载、不联网，不阻塞
- GUI / 人工验收项：无（合同 §11）

## 已知风险、未完成项与范围外发现

- 真实嵌入模型未冒烟：FastEmbedEmbedder 已封装但未用真实模型验证 encode 路径（dim=384 假定与模型一致）。Evidence Runner 日后下载模型后需冒烟真实 upsert/query 路径。
- source_id 采用文件 basename：同 basename 不同路径的文件会相互覆盖（合同未要求区分，幂等测试用同路径重复摄取验证不累积，符合"同源"语义）。如后续需区分，可改为含路径哈希的 source_id。
- chromadb 跨用例隔离依赖 per-test tmp 目录；生产环境删项目时 safe_rmtree 已重试+ignore_errors，但极端锁竞争下可能残留空目录（不影响逻辑，DB 记录已删）。
- 范围外发现：pytest 输出存在 starlette httpx 弃用警告与 chromadb asyncio 弃用警告（第三方库，与本任务无关，仅报告不处理）。

## 冻结声明

未 amend、未 rebase、未 push；候选 `4839ec16674997985d928c83ff360653c2b97563` 已冻结，本完成说明为独立提交，等待独立 Checker 对精确 SHA 验收。
