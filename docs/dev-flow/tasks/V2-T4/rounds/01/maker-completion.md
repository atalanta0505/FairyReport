# Maker 完成说明 — V2-T4 第 1 轮（通用知识包：构建 + 下发 + 引擎安装/检索）

## 合同与基线

- 有效合同：`tasks/V2-T4/01-planner-task-contract-v1.md`（v1）
- 起始 SHA：`7c6dab88a57b7ba15d91289ef7cedb727cf02eaf`（已核对：`git status --short` 干净，HEAD 与合同基线一致）
- 轮次目录：rounds/01（合同 §12 未规定预留；rounds/ 尚不存在，启用 01）

## 唯一主要行为变化

引擎可凭服务器 URL+JWT 下载并安装通用知识包（sha256 校验、原子安装），安装后可本地检索通用知识；服务器凭 JWT 提供知识包 manifest 与下载。

## 候选

- 候选 SHA：`3824433a33190254da9e1df346bba52bae25e584`
- 父提交：`7c6dab88a57b7ba15d91289ef7cedb727cf02eaf`
- 提交标题：V2-T4 通用知识包：构建脚本 + 服务器 JWT 下发 + 引擎下载安装/本地检索
- 精确修改文件（17 项，均在 engine/** 与 backend/**）：
  - `backend/app/config.py`：新增 `pack_dir` 配置（默认 "pack"，env PACK_DIR 可覆盖）
  - `backend/app/main.py`：挂载 pack_router
  - `backend/app/pack/__init__.py`、`backend/app/pack/router.py`：`GET /api/pack/manifest`（读 PACK_DIR/manifest.json，缺失 404）、`GET /api/pack/download`（FileResponse 返回 pack.zip，缺失 404）；均 JWT 保护（复用 `current_user`）
  - `engine/tools/__init__.py`、`engine/tools/build_generic_pack.py`：构建脚本，读 generic_knowledge/ → 文献走 engine chunking → 嵌入（默认真实 fastembed / `--stub` 确定性假向量）→ 写 chroma（collection=generic_kb）到临时目录 → 打 zip（manifest.json + templates/ + vector_db/）+ 计算 sha256 → 输出 pack.zip + manifest.json；CLI `python -m engine.tools.build_generic_pack --out <dir> [--stub] [--source <dir>]`
  - `engine/app/generic/__init__.py`、`engine/app/generic/store.py`：GenericStore（status/query/update/close/reset）+ 可注入 HTTP 传输层（set_transport，测试用 MockTransport）+ 异常（GenericNotInstalled/GenericTamperError/GenericServerError）；update 流程：拉 manifest → 幂等检查（同版本不重下）→ 下载 zip → sha256 校验（失败抛 GenericTamperError 不标记已装不留半装）→ 原子解压切换（临时目录解压后 os.replace 替换，清理旧版本目录）→ 写 state.json
  - `engine/app/generic/router.py`：`GET /generic/status`、`POST /generic/update`（body：server_url+token；4xx/5xx 映射）、`GET /generic/query?text=&n=`（未装 404；嵌入走 get_embedder 可注入接口）
  - `engine/app/main.py`：挂载 generic_router
  - `engine/tests/conftest.py`：autouse fixture 增 GenericStore.close() + set_transport(None) 清理（避免跨用例泄漏 MockTransport 与 chroma 锁）
  - `backend/tests/test_pack.py`：7 例（manifest/download 无 JWT 401、无效 JWT 401、缺失 404、有文件 manifest 200 / download 200）
  - `engine/tests/test_build_pack.py`：2 例（--stub 产出 zip+manifest 字段齐全 + sha256 匹配 + zip 内含 manifest/templates/vector_db；版本确定性）
  - `engine/tests/test_generic.py`：7 例（正常安装→status→query 命中、未装 query 404、篡改拒绝且不留半装、幂等不重下、服务器 401/404 转发、初始未装状态）
  - `engine/tests/fixtures/generic_source/`：小型构建 fixture（policy.md、terms.md、templates/feasibility.json，各 <1KB）

## 关键设计决策

- **sha256 自指循环**：manifest.json 同时作为独立文件（`--out/manifest.json`，权威 sha256 = sha256(pack.zip)）与 zip 内副本（解压后元数据用）。因 zip 内 manifest 的 sha256 字段无法精确等于其所在 zip 的哈希（自指循环），zip 内副本的 sha256 为构建时占位（空），**权威值以独立 manifest 为准**——引擎 update 拉取独立 manifest 的 sha256 与下载的 zip 字节比对。这与合同引擎流程"拉 manifest → 下载 → sha256 校验 → 解压"一致（校验在解压前，manifest 必须独立可取）。
- **原子安装**：解压到 `versions/<v>.tmp`，校验通过后 os.replace 替换为 `versions/<v>/`，再写 state.json；任意失败清理临时目录、state 不变，不留半装。
- **幂等**：update 先拉 manifest 比对已装 version，相同则直接返回 already_installed，不重下（测试验证第二次无 download 请求）。
- **嵌入一致性**：构建（--stub 用 DeterministicStubEmbedder）与引擎检索（conftest 注入同一 stub）走同一可注入接口，向量维度一致（384），测试不下载真实模型、不联网。
- **版本确定性**：version 基于内容哈希（chunks 文本 + 模板名），同内容→同版本，支撑幂等与版本比对。
- **JWT 复用**：backend pack 端点复用 `current_user(authorization, db)`（T1/T2 既有依赖），不新建认证逻辑；仅注册用户可下发。
- **引擎独立自洽**：generic 模块相对导入 engine 内部（config/embedding/materials.vectorstore.safe_rmtree），不 import backend/ 与根目录模块；构建脚本读根目录 generic_knowledge/（只读源，未改一字节，已 git 核实）。

## 验收标准对照

| 验收项（合同 §8） | 结果 | 证据 |
|---|---|---|
| `python -m engine.tools.build_generic_pack --out <tmp> --stub` 产出 zip+manifest，字段齐全 | ✅ | 验收步骤 3：620 chunks / 17 templates / version+sha256+built_at+chunk_count+templates 齐全；test_build_pack.py |
| engine update 正常路径：mock 下发 → 安装 → status 版本 → query 段落 | ✅ | test_update_install_status_query |
| sha256 篡改 → 拒绝且不标记已装；重复 update 幂等 | ✅ | test_tamper_rejected_no_half_install（422 + installed=False + 无半装目录）/ test_update_idempotent（第二次 already_installed 且无 download） |
| 未安装 query → 404 明确语义 | ✅ | test_not_installed_query_404（detail 含"未安装"） |
| backend：未带 JWT → 401；PACK_DIR 无文件 → 404；有文件 → manifest 200 / download 200 | ✅ | test_pack.py 7 例 |
| engine 20 + backend 30 回归全绿 | ✅ | engine 29 passed（20 既有 + 9 新增）/ backend 37 passed（30 既有 + 7 新增），既有测试未删未放宽 |
| 测试无真实模型下载、无联网 | ✅ | 构建与检索均用 DeterministicStubEmbedder；HTTP 走 MockTransport；无网络调用 |

## 快速验证记录（按合同 §9 顺序）

| 命令 | 结果 |
|---|---|
| `python -m pytest engine/tests backend/tests -q` | exit 0：66 passed, 2 warnings（engine 29 + backend 37） |
| `python -c "from engine.app.main import app"` | exit 0：engine ok |
| `python -c "from backend.app.main import app"` | exit 0：backend ok |
| 验收补充：`python -m engine.tools.build_generic_pack --out <tmp> --stub`（默认 generic_knowledge 源） | exit 0：620 chunks / 17 templates / sha256 完整 |

首次失败记录：无（一次通过；测试开发期出现的路由名/fixture 问题均在同轮内修复，未触停止条件）。

## 明确保留（未改动）

- 根目录产品文件、`generic_knowledge/**`（只读源，git 核实未改）、steps/、components/、converters/、根 requirements.txt、.opencode/、AGENTS.md 均未动
- backend 既有 auth/llm/smtp 端点与 T1/T2 行为未动；backend 既有 30 测试未删未放宽
- engine T3 既有 projects/materials 端点与 20 测试未动

## 未执行项（移交 Evidence Runner / 人工）

- 真实建包（合同 §10）：`python -m engine.tools.build_generic_pack --out <dir>`（无 --stub，首次自动下载 fastembed 模型 ~120MB，HF 镜像已配置）→ 产物上传服务器 PACK_DIR（运维步骤，部署切片 T7 一并落实）
- 真实端到端联调（真实服务器下发 + 引擎真实下载安装 + 真实嵌入检索）为日后人工项

## 已知风险、未完成项与范围外发现

- zip 内 manifest 的 sha256 为占位（空），权威 sha256 在独立 manifest.json（自指循环限制，已上文说明）；引擎校验用独立 manifest，不影响完整性。
- update 替换旧版本目录依赖先 GenericStore.close() 释放 chroma sqlite 锁再 safe_rmtree；Windows 极端锁竞争下 safe_rmtree 用 ignore_errors 兜底，极端情况或残留空目录（不影响逻辑，state 已更新指向新版本）。
- 范围外发现：pytest 输出存在 starlette httpx 弃用警告与 chromadb asyncio 弃用警告（第三方库，与本任务无关，仅报告不处理）。

## 冻结声明

未 amend、未 rebase、未 push；候选 `3824433a33190254da9e1df346bba52bae25e584` 已冻结，本完成说明为独立提交，等待独立 Checker 对精确 SHA 验收。
