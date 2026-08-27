# 任务合同 V2-T16 v1 — 免 Key 国内联网 RAG 检索集成与 .gov.cn 权威政务信息源过滤

- 状态：ACCEPTED（2026-08-27 独立 Checker 验收通过，锁定 204a06fb34b7194142954e524b0600e761ce9157）
- 依据：用户关于外部权威联网检索的要求：“优先免费免key的... ai-search-mcp：最推荐... 如果有外部RAG的话，请确保LLM查找的是“.gov”和权威消息来源的信息，不要查找未经过验证的公众号信息。”
- 精确起始 SHA：`549a1401008485bb3bd89186f2370ae1f9bb85d5`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **零 Key 国内权威搜索引擎驱动 (`engine/app/writing/web_search.py`)**：
   - 实现免 Key 国内高可用搜索调度通道（内置基于国内公用搜索引擎端点 / 免 Key 聚合搜索接口）；
   - 支持可选 `TAVILY_API_KEY` 作为回退通道；
   - 包含严格 3.5s 超时与静默异常捕获（网络不可达或超时不抛错，静默降级为空结果，绝不阻断写作/审阅）。
2. **`.gov.cn` 权威政务与智库信息源过滤与清洗**：
   - 检索时自动强化权威修饰词（如 `site:gov.cn` / 国家发改委 / 行业标准）；
   - 白名单域名优先采信：`*.gov.cn`、`*.edu.cn`、`*.org.cn`、`news.cn`、`people.com.cn` 等；
   - 排除非权威自媒体/论坛/博客（过滤 `zhihu.com`、`sohu.com`、`163.com`、`weibo.com`、`baijiahao.baidu.com`、普通微信公众号等）；
   - 网页标题规范化为 `【网:标题】`（清理括号、方括号与特殊 Markdown 标记，长度截断），内容摘要精简至 200~300 字。
3. **三源 RAG 融合检索与实时流水线指示 (`engine/app/writing/rag.py` & `router.py`)**：
   - 升级 `query_rag`：聚合 项目底稿（`【源:...】`）+ 通用规程（`[Z]`）+ 权威政务联网（`【网:...】`）；
   - 支持通过参数控制是否启用联网检索（默认开启，失败自动熔断）；
   - 升级流式写作 SSE 阶段提示：`🔍 正在三源检索：工程底稿库 + 行业规程库 + 权威政务联网信息(.gov.cn)...`。
4. **单测覆盖与快速验证**：
   - 新增 `engine/tests/test_web_search.py` 覆盖免 Key 联网搜索、`.gov.cn` 过滤、异常熔断降级、三源 RAG 融合格式断言；
   - 运行 5 项全量门禁（vitest, pytest, vue-tsc, build, cargo check）。

---

## 2. 允许修改

- `engine/app/writing/web_search.py`（新增）
- `engine/app/writing/rag.py`
- `engine/app/writing/router.py`
- `engine/app/writing/writer.py`
- `engine/tests/test_web_search.py`（新增）
- `engine/tests/**`
- `desktop/src/components/Step3Writing.vue`（若需同步心跳提示）
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T16/**`

---

## 3. 禁止修改

- `backend/**`、根目录除必要适配外的核心代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿（含新增 `test_web_search.py`）。
- [ ] `npx vitest run`、`npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] 零 Key 状态下可成功检索到 `.gov.cn` 权威政务信息并格式化为 `【网:xxx】`。
- [ ] 联网故障或超时能够 100% 静默降级，不阻断写作。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
5. `cargo check`（workdir=`desktop/src-tauri`）
