# Checker 验收报告 — V2-T4 第 1 轮

- 状态：**PASS**
- 精确候选 SHA：3824433a33190254da9e1df346bba52bae25e584
- 依据合同：`tasks/V2-T4/01-planner-task-contract-v1.md`
- 基线 SHA：7c6dab88a57b7ba15d91289ef7cedb727cf02eaf

## 独立检查边界

- 独立重跑（Windows PowerShell 5.1，Python 3.14.2，工作目录 `D:\Repo\FairyReport_lite`，HEAD=7bf8f7c 完成说明提交，其下 engine/backend 与候选完全一致）：
  - `python -m pytest engine/tests backend/tests -q` → exit 0：**66 passed, 2 warnings**（engine 29 + backend 37）
  - `python -c "from engine.app.main import app"` → exit 0：engine ok
  - `python -c "from backend.app.main import app"` → exit 0：backend ok
  - `python -m engine.tools.build_generic_pack --out <tmp> --stub`（默认 generic_knowledge 源）→ exit 0：打包 `pack.zip`（3135125B）+ `manifest.json`（722B）；`version=v-e91b59bddd4f sha256=bf8a1fce22f58600… chunks=620 templates=17`；manifest 字段 version/sha256/built_at/chunk_count/templates 齐全。
- 逐条核对合同 §8：阅读 engine（generic/、tools/）与 backend（pack/）全部源码及新增测试，见下表。
- 未重跑：真实嵌入建包（合同 §10 明示为验收后人工项，`--stub` 用确定性假向量，不下载模型、不联网）。

## 验收标准逐条核对

| 合同标准 | 证据等级(A/B/C/D) | 证据与结论 |
|---|---|---|
| §8.1 `build_generic_pack --out <tmp> --stub` 产出 zip+manifest，字段齐全 | A | 独立重跑成功；`engine/tests/test_build_pack.py:13` 断言 version/sha256/built_at/chunk_count/templates 非空、`sha256(pack.zip)==manifest["sha256"]`、zip 内含 manifest/templates/vector_db；`build_generic_pack.py:168-180` 打 zip 后回填独立 manifest。符合。 |
| §8.2 engine update 正常路径：mock 下发→安装→status 版本→query 段落 | A | `engine/tests/test_generic.py:53` mock 安装后断言 status/version 正确、query 命中段落；`store.py:223` update、`:152` status、`:201` query 链路完整。符合。 |
| §8.3 sha256 篡改→拒绝且不标记已装；重复 update 幂等 | A | `test_tamper_rejected_no_half_install`（422+installed=False+versions 空）、`test_update_idempotent`（第二次 already_installed 且 0 download）；`store.py:238-251` 幂等检查在下载前、sha256 校验在解压前。符合。 |
| §8.4 未安装 query → 404 明确语义 | A | `test_not_installed_query_404`（detail 含"未安装"）；`generic/router.py:52` `GenericNotInstalled → 404 "通用知识未安装，请先 update"`。符合。 |
| §8.5 backend：未带 JWT→401；PACK_DIR 无文件→404；有文件→manifest 200/download 200 | A | `backend/tests/test_pack.py` 7 例（no_jwt 401×2、invalid_jwt 401、missing 404×2、200×2）；`pack/router.py:27/40` 每个端点先 `current_user(authorization, db)` JWT 门控，再查文件 404。符合。 |
| §8.6 engine 20 + backend 30 回归全绿 | A | 独立重跑 engine 29 passed + backend 37 passed；`git diff` 无任何既有 test 文件的 M/D，既有测试未删未放宽。符合。 |
| §8.7 测试无真实模型下载、无联网 | A | 构建脚本 `--stub` 走 `DeterministicStubEmbedder`（`build_generic_pack.py:145`）；检索走 conftest 注入的 stub 嵌入；HTTP 走 `httpx.MockTransport`（`store.py:67/85` 用可注入 `_transport` + `set_transport`）；全 engine/backend 无真实网络调用。符合。 |

## 修改范围复核

- `git diff 7c6dab8..3824433` 是否严格落在允许路径内：**是**。共 17 项，全部在 `engine/**` 与 `backend/**` 下（backend 5 项、engine 12 项）。
- 是否触碰禁止路径：**否**。`generic_knowledge/**` 零改动（git diff 无命中）；无根目录产品文件、steps/、components/、converters/、根 requirements.txt、.opencode/、AGENTS.md。
- 父链核对：`git log --oneline 7c6dab8..3824433` 仅 3824433 一个提交；`3824433^ == 7c6dab8`；完成说明提交 `7bf8f7c` 父 == 3824433，其改动仅 `docs/dev-flow/tasks/V2-T4/rounds/01/maker-completion.md`（独立提交，符合 §12）。
- `git diff --check 7c6dab8..3824433` → exit 0，无空白/冲突标记。

## 安全 / 约束

- 无凭据入库：新增源码无硬编码 token/secret/key；`store.py:70/88` 的 `Authorization: Bearer {token}` 仅取调用方传入的 token，无泄漏；JWT 门控复用 T1/T2 既有 `current_user`，未新建认证逻辑。
- manifest sha256 自指处理合理性：build 阶段 zip 内 manifest 的 sha256 为占位（空），权威 sha256 写入独立 `manifest.json`（`build_generic_pack.py:176-180`）；engine update 拉独立 manifest 的 sha256 与下载 zip 字节比对（`store.py:247`），校验发生在解压前。自指循环规避正确，且引擎不依赖 zip 内副本做完整性判定，无安全问题。
- engine 独立自洽：`engine/app/generic/store.py` 仅相对导入 engine 内部（config/embedding/materials.vectorstore.safe_rmtree），grep 确认不 import backend/ 与根目录模块。
- 原子性代码审查：`store.py:256-276` 解压到 `<version>.tmp`，`os.replace` 原子切换，写 state 在最后；任何异常 `safe_rmtree(tmp)` 且不写 state，不留半装。sha256 校验在临时目录创建之前，篡改直接拒绝、零落盘。

## 阻断项（仅 FAIL）

无。

## 非阻断风险

- `backend/app/config.py:43` 默认 `pack_dir = "pack"`（相对当前工作目录），与合同 §4 字面"默认 backend 数据目录下 pack/"存在措辞偏差；但与 backend 既有 `database_url="sqlite:///./backend_dev.db"` 相对路径约定一致，且 `PACK_DIR` 环境变量可覆盖（部署切片 T7 落实）。不影响本切片验收。
- zip 内 manifest 的 sha256 为占位（空）——权威值在独立 manifest.json，属自指循环的既定设计；打开 zip 内 manifest 会看到空 sha256，属预期而非缺陷。
- 更新替换旧版本目录依赖 `GenericStore.close()` 释放 sqlite 锁 + `safe_rmtree(ignore_errors=True)`；Windows 极端锁竞争下可能残留空目录（state 已指向新版本，不影响检索逻辑）。
- 第三方库弃用警告（starlette httpx、chromadb asyncio）：与本任务无关，仅记录。
- 真实建包（无 --stub）需下载 fastembed 模型，为合同 §10 人工项，本切片未执行（亦不阻塞）。

## 判定

- PASS：锁定 3824433a33190254da9e1df346bba52bae25e584；剩余人工项：真实建包与服务器上传部署（合同 §10，T7 落实）。