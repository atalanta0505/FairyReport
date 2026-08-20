# 任务合同 V2-T4 v1 — 通用知识包：构建 + 服务端下发 + 引擎首启下载/本地检索

- 状态：DRAFT（待产品负责人批准）
- 产品决定来源：`00-product-decision-v4.md` D15、`00-product-decision-v5.md`；O8 由本合同落实（选址：认证服务器自带下发，不引入新存储）
- 精确起始 SHA：本合同提交后的 master HEAD
- 工作树门禁：`git status --short` 必须干净

## 1. 背景与目标

通用知识（generic_knowledge/：政策文献 + 模板 JSON + 预编译向量库）不进安装包；打包为"知识包"，由**认证服务器**凭 JWT 下发（登录门控、模板 IP 不外泄、零新增存储设施），引擎首次登录后下载、校验、本地加载，之后离线检索。

## 2. 唯一主要行为变化

**引擎可凭服务器 URL+JWT 下载并安装通用知识包（sha256 校验），安装后可本地检索通用知识；服务器凭 JWT 提供知识包 manifest 与下载。**

## 3. 明确不做

- 不做增量更新（v1 整包重下；版本变化罕见、包体小；增量列正式版前议题）
- 不用真实嵌入模型跑验收（构建脚本 --stub 路径被测；真实建包为验收后人工/运维项）
- 不做 COS/Gitee Release 托管（O8 定案：服务器自带下发）
- 不改 T1/T2/T3 既有行为（backend 仅新增 pack 端点；engine 仅新增 generic 模块）

## 4. 实现导航

- 只读参考：根目录 `generic_knowledge/`（templates/*.json + 政策文献 .md）、`engine/app/materials/{chunking,vectorstore}.py`、`engine/app/embedding.py`（可注入嵌入）、`backend/app/auth/security.py`（JWT 依赖）
- **包格式 v1**：zip，内含 `manifest.json`（version、sha256(zip 内容物)、built_at、chunk_count、templates 清单）、`templates/`（模板 JSON 原样）、`vector_db/`（chroma 持久化目录，collection 名 generic_kb）
- **构建脚本** `engine/tools/build_generic_pack.py`：读 generic_knowledge/ → 文献走 engine chunking → 嵌入（默认真实 fastembed；`--stub` 用确定性假向量）→ 写 chroma 到临时目录 → 打 zip + 计算 sha256 → 输出到指定目录；CLI：`python -m engine.tools.build_generic_pack --out <dir> [--stub]`
- **backend 新增**（`backend/app/pack/router.py`，JWT 保护）：
  - `GET /api/pack/manifest` → 读 PACK_DIR/manifest.json 返回
  - `GET /api/pack/download` → FileResponse 返回 PACK_DIR/pack.zip（流式）
  - 配置 `PACK_DIR`（环境变量，默认 backend 数据目录下 pack/）；文件缺失 → 404
- **engine 新增**（`engine/app/generic/`）：
  - `router.py` — `GET /generic/status`（已装版本/未装）；`POST /generic/update`（body：server_url、token；拉 manifest → 下载 zip → sha256 校验 → 解压到 ENGINE_DATA_DIR/generic/<version>/ → 原子切换（先解压临时目录再替换）→ 加载）；`GET /generic/query?text=&n=`（对已装 generic_kb 本地检索，返回段落列表；嵌入走可注入接口）
  - 未安装时 query → 404 + 明确错误码；校验失败 → 4xx/5xx 且**不**标记已装、不留半装状态
- 测试：构建脚本用 --stub + 小型 fixture 文献；update 流程用 httpx MockTransport 或本地 mock 服务提供假 zip；覆盖：正常安装/版本查询/检索命中、hash 篡改拒绝、下载中断不留半装（原子性）、未装 query 404、backend pack 端点 401/404/200（打桩文件）
- 回归：engine 20 例 + backend 30 例保持全绿

## 5. 允许修改

- `engine/**`、`backend/**`（仅新增 pack router + config 增 PACK_DIR + main 挂载）
- `.gitignore`（如需）
- `docs/dev-flow/tasks/V2-T4/**`

## 6. 禁止修改

- 根目录现有产品文件、`generic_knowledge/**`（只读源，不得改）、steps/、components/、converters/、根 requirements.txt、.opencode/、AGENTS.md
- backend/engine 既有测试不得删除或放宽

## 7. 依赖

无新增（zipfile/hashlib/shutil 均 stdlib）。

## 8. 验收标准

- [ ] `python -m engine.tools.build_generic_pack --out <tmp> --stub` 产出 zip+manifest，manifest 字段齐全
- [ ] engine update 正常路径：mock 下发 → 安装成功 → status 显示版本 → query 返回段落
- [ ] sha256 篡改 → 拒绝且不标记已装；重复 update 幂等
- [ ] 未安装 query → 404 明确语义
- [ ] backend：未带 JWT → 401；PACK_DIR 无文件 → 404；有文件 → manifest 200 / download 200
- [ ] engine 20 + backend 30 回归全绿
- [ ] 测试无真实模型下载、无联网

## 9. Maker 快速测试（按顺序）

1. `python -m pytest engine/tests backend/tests -q`
2. `python -c "from engine.app.main import app"` 与 `python -c "from backend.app.main import app"`

## 10. Evidence Runner / 人工项（验收后）

- 真实建包：`python -m engine.tools.build_generic_pack --out <dir>`（首次自动下载 fastembed 模型 ~120MB，HF 镜像已配置）→ 产物上传服务器 PACK_DIR（运维步骤，部署切片 T7 一并落实）

## 11. GUI / 人工验收项

- 无（纯 API 切片）。

## 12. 候选提交与完成说明要求

- 候选只含 engine/** 与 backend/**；完成说明单独提交到 rounds/01/maker-completion.md
- 不 amend、不 rebase、不 push

## 13. 停止条件

- 基线/工作树不符；需要新依赖；越界；同一失败两次；原子替换在 Windows 文件锁下两次尝试无解 → 停止报告

## 14. 已知基线失败

- 无（engine 20 + backend 30 passed）。
