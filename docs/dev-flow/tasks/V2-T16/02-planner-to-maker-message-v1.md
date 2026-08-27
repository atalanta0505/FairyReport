# Planner 至 Maker 任务派发消息 — V2-T16 第 1 轮

Maker：

请严格按照任务合同 `docs/dev-flow/tasks/V2-T16/01-planner-task-contract-v1.md` 执行 V2-T16 第 1 轮开发工作。

### 核心实现要点：
1. **新建 `engine/app/writing/web_search.py`**：
   - 封装国内免 Key 权威搜索聚合器（可使用 Sogou/Bing/Baidu 等免 Key 公共搜索或轻量 HTTP 解析，配合 requests/urllib/httpx，带 3.5s 超时）；
   - 支持白名单与 `.gov.cn` 强化过滤，剔除自媒体；
   - 格式化输出为 `【网:标题】\n  url\n  > 摘要`；
   - 支持可选 `TAVILY_API_KEY` 作为备用通道。
2. **升级 `engine/app/writing/rag.py`**：
   - 在 `query_rag` 中融合项目资料库（`【源:...】`）、通用规程库（`[Z]`）与权威政务联网库（`【网:...】`）；
   - 异常全局捕获静默降级。
3. **升级 `engine/app/writing/router.py`**：
   - 更新 SSE 心跳事件：`🔍 正在三源检索：工程底稿库 + 行业规程库 + 权威政务联网信息(.gov.cn)...`。
4. **测试与快速验证**：
   - 编写 `engine/tests/test_web_search.py`；
   - 重跑 5 项门禁（pytest, vitest, vue-tsc, build, cargo check）；
   - 提交候选 commit，输出 `docs/dev-flow/tasks/V2-T16/rounds/01/maker-completion.md`，汇报候选 SHA。
