# Checker 验收报告 — V2-T7 第 2 轮

- 状态：**PASS**
- 精确候选 SHA：0dab11da3c1aefd7d7cecef7669cc65737061084（T7 代码候选）
- 依据合同：`tasks/V2-T7/01-planner-task-contract-v2.md`（v2；v1 作历史）
- 基线 SHA：21b04dc2f0d3c42e9737d6a067f8f9700f456e97

## 独立检查边界

- 独立重跑（本轮）：
  - `python -m pytest engine/tests backend/tests -q` → exit 0：**101 passed, 2 warnings**（73s）
  - `git diff 21b04dc..0dab11d` 逐行核对 engine/ 变更
  - 公网黑盒：health / pack 401 / login / manifest / download sha256（下载到临时目录取 SHA256）
  - SSH frl-server 只读抽查：docker compose ps / free -h / ss -tlnp
- 对第 1 轮证据的审查（非本轮重跑）：v1 合同条款定义、第 1 轮 checker-report（仅作线索，不采信其结论）；E2E 注册全链路（send-code→register）仍为产品负责人邮箱依赖，本轮未重跑，以第 1 轮 + 完成说明记录作 B 级佐证。

## 验收标准逐条核对

### v2 §8 增补条目

| 合同标准 | 证据等级(A/B/C/D) | 证据与结论 |
|---|---|---|
| f774f39 diff 逐行核实仅为 3 行前缀修改，无其他 engine 变更 | A | `git diff 21b04dc..0dab11d -- engine/` 仅两文件：`config.py` 一行 `embed_model_name` 默认值、`embedding.py` 两行（模块 docstring + `FastEmbedEmbedder.__init__` 默认参数），三处均为 `paraphrase-multilingual-MiniLM-L12-v2` → `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`，无任何其他 engine 改动。符合 v2 §1 边界。 |
| 前缀修复后 101 测试全绿 | A | 本轮独立重跑 **101 passed**（engine 64 + backend 37）。 |
| 真实建包/检索同模型一致性（pack version 由前缀后模型建成） | A | 公网 manifest `version=v-e91b59bddd4f`、`sha256=b3464203…ffb29fe`；download 实测 bytes sha256=`b3464203fd80f050f7f19852e4961a967e6047abfaa63be4288fe66d0ffb29fe`，与 manifest 及预期值精确一致，证 patched 嵌入模型建包产物一致。 |
| rounds/01/maker-completion.md 已提交 | A | `git ls-files docs/dev-flow/tasks/V2-T7/rounds/` 含 `maker-completion.md` 与 `checker-report.md`。 |

### v1 §8 抽查复核（§2 维持条款）

| 合同标准 | 证据等级(A/B/C/D) | 证据与结论 |
|---|---|---|
| `curl /api/health` → 200 | A | 本轮自执行 `{"status":"ok"}` [200]。 |
| 无 JWT pack → 401 | A | 本轮自执行 `{"detail":"未提供认证凭据"}` [401]。 |
| 带 JWT manifest 200 且 version 一致；download sha256 一致 | A | login（13476526@qq.com）→ token；manifest 200 `version=v-e91b59bddd4f`；download 200 size=4013820、sha256 匹配。 |
| `free -h` >300MB；现有端口仍在 | A | available **777Mi**（>300MB）；`:7000`(frps)/`:8000`(python3)/`:18789`(openclaw-gatewa) 均在。 |
| backend 101 本地全绿 | A | 本轮 **101 passed**。 |
| 两容器 Up | A | `docker compose ps`：`backend-api-1`、`backend-nginx-1` 均 Up。 |

## 修改范围复核

- `git diff --name-status 21b04dc..0dab11d`：
  - backend/**：`backend/Dockerfile`(M)、`backend/docker-compose.yml`(M)、`backend/nginx/nginx.conf`(A) —— v2 §5 允许。
  - engine/**：`engine/app/config.py`(M)、`engine/app/embedding.py`(M) —— v2 §5 增补允许（仅前缀 3 行，逐行核实无越界）。
- 完整范围 `21b04dc..4818e76` 另含 `docs/dev-flow/tasks/V2-T7/**`（合同 v2 + rounds/01 两份报告）——v1/v2 §5 允许。
- 父链：`21b04dc → 5da16c0 → f774f39 → 0dab11d → 60c5256(第1轮报告) → 4818e76(合同v2+完成说明)`；`git status --short` 干净；`git branch -vv` master 无 upstream（未 push）。

## 阻断项（仅 FAIL）

无。

## 非阻断风险

- HTTP 明文（合同 §3 已知悉临时风险，跑通模式；HTTPS 留待发布前自签+客户端固定）。
- 测试账号 `13476526@qq.com` 明文密码存于完成说明（已交产品负责人处置，非凭据泄漏入仓问题，但建议后续轮换）。
- E2E 注册全链路（send-code→邮箱收码）本轮未独立重跑，为产品负责人邮箱依赖；完成说明记录为"REGISTER/LOGIN/ME 全过"，建议发布前人工复跑一次。
- 未做备份/监控脚本（合同 §3 明确不做，发布前议题）。

## 判定

- **PASS**：锁定 `0dab11da3c1aefd7d7cecef7669cc65737061084` 为 T7 代码候选（范围 21b04dc..0dab11d 含 v2 §5 合法化的窄修复）。剩余人工项：HTTPS、备份、E2E 注册复跑（发布前）。