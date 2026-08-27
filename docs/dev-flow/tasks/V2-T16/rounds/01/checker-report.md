# Checker 验收审查报告 — V2-T16 第 1 轮

- **任务 ID**：`V2-T16`
- **轮次**：第 1 轮（Round 01）
- **审查员（Checker）**：Checker Agent (cc96bcb4-d4dc-4181-9d30-7e3989eccfa3)
- **候选交付 SHA**：`204a06fb34b7194142954e524b0600e761ce9157`
- **父提交基线 SHA**：`33a4348b7ab146aeb112606363d12277c0fb54d6`
- **依据合同**：`docs/dev-flow/tasks/V2-T16/01-planner-task-contract-v1.md`
- **Maker 报告**：`docs/dev-flow/tasks/V2-T16/rounds/01/maker-completion.md`
- **审查结论**：**PASS（验收通过）**
- **审查时间**：2026-08-27

---

## 1. 变更范围与父链复核

### 1.1 Git 提交与父链核对
- 基线父提交：`33a4348b7ab146aeb112606363d12277c0fb54d6`（合同 v1 批准提交）
- 候选交付 SHA：`204a06fb34b7194142954e524b0600e761ce9157`
- 提交说明：`feat(writing): integrate zero-key domestic web search RAG with .gov.cn authoritative filtering`
- 审查期间工作区：干净（`git status` 无残留未跟踪或未提交代码）

### 1.2 修改文件清单核实
通过 `git diff --name-status 33a4348b7ab146aeb112606363d12277c0fb54d6..204a06fb34b7194142954e524b0600e761ce9157` 检查：

| 文件路径 | 变更状态 | 合同允许范围 | 判定 |
| :--- | :---: | :---: | :---: |
| `engine/app/writing/web_search.py` | A (新增) | 是 (`engine/app/writing/**`) | 合规 |
| `engine/app/writing/rag.py` | M | 是 (`engine/app/writing/**`) | 合规 |
| `engine/app/writing/router.py` | M | 是 (`engine/app/writing/**`) | 合规 |
| `desktop/src/components/Step3Writing.vue` | M | 是 (`desktop/src/**`) | 合规 |
| `desktop/src/stores/project.ts` | M | 是 (`desktop/src/**`) | 合规 |
| `engine/tests/test_web_search.py` | A (新增) | 是 (`engine/tests/**`) | 合规 |
| `desktop/dist/**` | R/M | 是 (`desktop/dist/**`) | 合规 |

**范围判定**：所有代码变更均严格限定在合同规定的 `engine/**`、`desktop/**` 范围内，未触及 `backend/**`、`generic_knowledge/**`、根目录配置文件或 `AGENTS.md` 等受保护区域。

---

## 2. A 级快速验证命令独立重跑记录

由 Checker Agent 在本地干净环境中独立逐项重跑合同规定的 5 项门禁命令：

| 顺序 | 验证命令 | 执行目录 | 独立实跑输出 / 耗时 | 判定 |
| :---: | :--- | :--- | :--- | :---: |
| 1 | `python -m pytest engine/tests -q` | 根目录 | **117 passed, 2 warnings (67.16s)** | ✅ PASS |
| 2 | `npx vitest run` | `desktop/` | **123 passed (5 files, 1.11s)** | ✅ PASS |
| 3 | `npx vue-tsc --noEmit` | `desktop/` | **0 errors, clean output** | ✅ PASS |
| 4 | `npm run build` | `desktop/` | **built in 1.02s (dist/ generated)** | ✅ PASS |
| 5 | `cargo check` | `desktop/src-tauri` | **Finished dev profile in 0.83s, 0 errors** | ✅ PASS |

所有 A 级快速验证命令 100% 通过。

---

## 3. 代码级逐项深度审查

### 3.1 零 Key 国内高可用权威政务检索调度 (`engine/app/writing/web_search.py`)
- **免 Key 驱动与解析**：
  - 实现 `_search_zero_key`，以国内高可用端点（基于国内 Bing 及 DuckDuckGo HTML Lite 备用通道）为底层驱动，附带现代浏览器标准 Header；
  - 正确解析 HTML 结果节点中的标题、URL 与摘要正文，并自动解密 URL 重定向。
- **权威白名单与自媒体黑名单过滤**：
  - `WHITELIST_SUFFIXES` 覆盖 `.gov.cn`、`.edu.cn`、`.org.cn`；
  - `WHITELIST_DOMAINS` 收录国家发改委 (`ndrc.gov.cn`)、生态环境部 (`mee.gov.cn`)、工信部 (`miit.gov.cn`)、新华网 (`news.cn`)、人民网 (`people.com.cn`)、央视网 (`cctv.com`)、国家标准委 (`std.samr.gov.cn`) 等 24+ 国家级权威门户与智库；
  - `BLACKLIST_DOMAINS` 严格排斥 `zhihu.com`、`sohu.com`、`163.com`、`weibo.com`、`baijiahao.baidu.com`、`toutiao.com`、`bilibili.com`、`csdn.net`、`xiaohongshu.com`、`mp.weixin.qq.com` 等未经验证自媒体与社区；
  - `is_authoritative_domain` 采取「黑名单优先拦截 -> 后缀匹配 -> 权威域名匹配」的三级校验逻辑，确保自媒体即使包含二级关键字亦被 100% 拦截。
- **标题清洗与语法防污染**：
  - `clean_title` 将 `[` `]` 替换为 `(` `)`，将 `【` `】` 替换为 `「` `」`，去除搜索引擎与门户网站后缀，并截断至合理长度；
  - 格式化输出严格符合 `【网:标题】\n  URL\n  > 摘要正文` 规范，杜绝污染 Markdown 正文语法及后续 `refs.py` 的标签提取。
- **严格超时与静默熔断保护**：
  - 设置 3.5 秒严格超时；
  - `search_gov_web` 内部完整捕获所有网络异常、DNS 解析异常和解析错误，记录 `warning` 日志并静默返回 `""`，100% 保障写作主流程在离线或弱网下稳定运行。
- **可测试性注入**：
  - 提供 `set_transport` / `get_transport`，完整支持单测中使用 `httpx.MockTransport` 进行端到端离线测试。
- **扩展性通道**：
  - 检测到环境变量 `TAVILY_API_KEY` 时自动调用 `_search_tavily`，并在异常时平滑降级至国内免 Key 通道。

### 3.2 三源 RAG 融合检索 (`engine/app/writing/rag.py`)
- **多源聚合机制**：
  - `query_rag` 正确聚合：
    1. **项目底稿库**：`【源:filename】: doc`
    2. **通用规程库**：`[Z]: doc`
    3. **权威政务联网库**：`【网:title】\n  URL\n  > 摘要正文`
- **参数控制与异常保护**：
  - 新增 `include_web: bool = True` 控制参数，默认开启；
  - 联网检索模块被独立 try-catch 包裹，出现异常仅打 warning，不影响项目库与通用库检索结果。

### 3.3 路由与流式写作集成 (`engine/app/writing/router.py`)
- **端点支持**：
  - `chapter` 非流式端点与 `_stream_chapter` SSE 流式生成器均调用 `query_rag(..., include_web=True)`；
  - SSE 心跳第一阶段（`stage: "rag"`）提示文案精准更新为：
    `"🔍 正在三源检索：工程底稿库 + 行业规程库 + 权威政务联网信息(.gov.cn)..."`。

### 3.4 前端流转状态与 UI 同步 (`desktop/src/components/Step3Writing.vue` & `desktop/src/stores/project.ts`)
- `desktop/src/stores/project.ts` 中 `writingProgress` 初始化文案同步为三源检索描述；
- `desktop/src/components/Step3Writing.vue` 中动态构思步进指示器标题更新为「三源知识检索」，副标题更新为「底稿数据 + 行业规程 + 权威政务」。

### 3.5 单元测试覆盖率 (`engine/tests/test_web_search.py`)
- 全量包含 16 个专项测试，覆盖：
  - 权威域名后缀（`.gov.cn`, `.edu.cn`, `.org.cn`）与门户白名单测试；
  - 自媒体与社交网络黑名单拦截测试；
  - URL 合法性与权威性校验；
  - 标题括号转义与摘要清洗测试；
  - 关键词政务修饰强化测试；
  - Bing HTML 解析与知乎过滤测试；
  - DuckDuckGo 重定向解密测试；
  - Tavily API 通道与自媒体过滤测试；
  - 超时与网络故障静默降级熔断测试；
  - 空查询静默返回测试；
  - 三源 RAG 融合检索格式与禁用联网检索测试；
  - `refs.py` 对接：编造标签剥离、URL 提取与章节引用分类集成测试。

---

## 4. 待产品负责人执行的 B 级人工核验清单

虽然自动化 A 级门禁已全部通过，建议产品负责人启动应用后进行以下界面交互体验验证：

1. **联网流式写作体验核验**：在网络连通状态下进入步骤 3，触发单章或全书流式写作，观察顶部等待指示器是否顺畅展现「三源知识检索：底稿数据 + 行业规程 + 权威政务」；
2. **权威政务引用呈现核验**：写作完成后，查看生成的正文段落是否在引用发改委政策、环保标准等条文时包含类似 `【网:国家发展改革委关于...】` 标签；
3. **右侧参考资料抽屉核验**：点击「📚 参考资料」，确认权威网页链接是否被正确归类为「网页链接」，并能正确查看其对应政务来源 URL；
4. **离线/弱网静默降级核验**：拔掉网线或断开 Wi-Fi 重新触发章节写作，确认系统是否在 3.5 秒内自动静默降级为纯本地底稿 + 规程库写作，不会抛出网络错误弹窗或中断流程。

---

## 5. 验收判定结论

- **判定**：**PASS（验收通过）**
- **阻断项（Blockers）**：无
- **非阻断风险（Non-blocking Risks）**：公用搜索引擎 HTML 结构若在未来发生重大改版，可通过更新正则表达式或配置专用 Tavily API Key / 私有检索代理保证长期可用性，当前代码已实现多源回退与全面异常熔断。
- **结论与建议**：候选提交 `204a06fb34b7194142954e524b0600e761ce9157` 架构设计优雅、白名单过滤严格、容错保护完善、单测与快速验证 100% 通过，建议 Coordinator 予以合入锁定。
