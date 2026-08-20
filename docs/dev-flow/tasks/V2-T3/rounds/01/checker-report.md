# Checker 验收报告 — V2-T3 第 1 轮

- 状态：**PASS**
- 精确候选 SHA：4839ec16674997985d928c83ff360653c2b97563
- 依据合同：`tasks/V2-T3/01-planner-task-contract-v2.md`
- 基线 SHA：b97b7d73cf98a087c35702e827ff7334f1f59e28

## 独立检查边界

- 独立重跑（Windows PowerShell 5.1，Python 3.14.2，工作目录 `D:\Repo\FairyReport_lite`，HEAD=0bc37a8 完成说明提交，其下 engine/ 与候选完全一致）：
  - `python -m pytest engine/tests -q` → exit 0：**20 passed, 2 warnings** in 4.75s
  - `python -m pytest backend/tests -q` → exit 0：**30 passed, 1 warning** in 6.27s（回归守卫全绿）
  - `python -c "from engine.app.main import app"` → exit 0：import ok
- 逐条核对合同 §8：阅读 engine/ 全部源码与 engine/tests/ 全部测试，见下表。
- 未重跑：真实嵌入模型冒烟（合同 §10 明示为日后人工项，本切片测试用确定性假向量，不下载、不联网）。

## 验收标准逐条核对

| 合同标准 | 证据等级(A/B/C/D) | 证据与结论 |
|---|---|---|
| §8.1 `GET /health` 200；配置仅绑定 127.0.0.1 | A | 独立重跑 `engine/tests/test_health.py:5/11` 全过；`engine/app/main.py:24` 定义 `/health` 返回 `{"status":"ok","host":settings.host}`；`engine/app/config.py:38` `host="127.0.0.1"`，`main.py:36` uvicorn 仅用 `settings.host`。符合。 |
| §8.2 建/列/删项目；删项目连文件与向量目录删除 | A | 独立重跑 `test_projects.py` 全过；`engine/app/projects/router.py:48` POST、`:69` GET、`:75` DELETE 调 `remove_project_data(name)`（`vectorstore.py:137`）先关向量库缓存再 `safe_rmtree` 整个项目目录（files+vector）。`test_delete_project_removes_dirs` 断言目录不存在。符合。 |
| §8.3 ingest .md 本地路径 → chunk_count>0；五格式各有用例 | A | `test_materials.py:17` `test_ingest_each_format_produces_chunks` 对 csv/docx/md/txt/xlsx 各一断言 `chunk_count>0`；`:32` `test_ingest_md_creates_chunks_and_file` 验证 md 分块>0 且文件已拷贝。`converters.py` 五格式转 Markdown，`chunking.py` 分块。符合。 |
| §8.4 同源重复 ingest → upsert 覆盖不累积 | A | `test_materials.py:45` 两次同源摄取断言 `store.count()==chunk_count` 且资料记录仍 1 条；`materials/router.py:139` ingest 先 `delete_by_source` 再 `upsert`；`vectorstore.py:71` ID 为 `f"{sid}_{i}"` 稳定 key。符合。 |
| §8.5 按 source 删除 → 文件+向量同删 | A | `test_materials.py:66` 删除后断言文件不存在、`store.count()==0`、资料记录空；`materials/router.py:199` 删向量+删拷贝文件+删 DB 记录。符合。 |
| §8.6 路径不存在 / 扩展名非法 → 4xx | A | `test_materials.py:104` 不存在路径断言 `400<=status<500`（实际 400）；`:113` `.pdf` 断言 4xx（实际 415）；`materials/router.py:93` 不存在路径 400、`:98` 扩展名白名单外 415。符合。 |
| §8.7 backend 既有 30 个测试保持全绿（回归守卫） | A | 独立重跑 `backend/tests`：30 passed。符合。 |
| §8.8 `python -c "from engine.app.main import app"` 通过 | A | 独立重跑 exit 0。符合。 |

## 修改范围复核

- `git diff b97b7d7..4839ec1` 是否严格落在允许路径内：**是**。共 27 个文件，全部为 `A`（新增）且均在 `engine/**` 下，无 `.gitignore` 改动、无 `docs/` 改动。
- 是否触碰禁止路径：**否**。无 `backend/**`、根目录产品文件、`steps/`、`components/`、`converters/`、`generic_knowledge/`、根 `requirements.txt`、`.opencode/`、`AGENTS.md`。
- 父链核对：`git log --oneline b97b7d7..4839ec1` 仅 4839ec1 一个提交；`4839ec1^ == b97b7d7`；完成说明提交 `0bc37a8` 父 == 4839ec1，其改动仅 `docs/dev-flow/tasks/V2-T3/rounds/01/maker-completion.md`（独立提交，符合 §12）。
- `git diff --check b97b7d7..4839ec1` → exit 0，无空白/冲突标记。

## 安全 / 约束

- 测试无真实模型下载、不联网：`conftest.py:34` 注入 `DeterministicStubEmbedder`（SHA-256 假向量，`embedding.py:43`）；全 engine/ 无 `requests.*`/`httpx.*`/`urllib`/`urlopen` 网络调用；`FastEmbedEmbedder`（`embedding.py:23`）懒加载且仅在 `requirements.txt` 登记依赖、测试不触发。符合。
- 无凭据入库：全 engine/ grep `api[-_]?key|secret|token|password|Bearer |sk-` 无命中。符合。
- engine 不 import backend/ 与根目录模块：全 engine/ 仅相对导入，grep `(from|import)\s+(backend|pipeline|kb|steps|components|converters|generic_knowledge)` 无命中。符合。
- 数据目录隔离：默认 `%LOCALAPPDATA%/FairyReport`（`config.py:13`），测试 monkeypatch 到 per-test `tmp_path`，不污染用户目录。

## 阻断项（仅 FAIL）

无。

## 非阻断风险

- 真实嵌入模型未冒烟：`FastEmbedEmbedder` 已封装但未用真实模型验证 encode 输出（dim=384 与实际模型一致性待验证）。已由合同 §10 界定为日后人工项，不阻塞本切片。
- `source_id` 取文件 basename：同 basename 不同路径会相互覆盖（合同未要求区分，幂等测试按"同源重复摄取"语义通过）。
- 第三方库弃用警告（starlette httpx 弃用、chromadb asyncio 弃用）：与本次任务无关，仅记录。
- Windows 下删除项目目录依赖 `safe_rmtree` 重试+`ignore_errors`，极端锁竞争下可能残留空目录（DB 记录已删，不影响逻辑）。

## 判定

- PASS：锁定 4839ec16674997985d928c83ff360653c2b97563；剩余人工项：真实嵌入模型冒烟（合同 §10，Evidence Runner 日后执行）。