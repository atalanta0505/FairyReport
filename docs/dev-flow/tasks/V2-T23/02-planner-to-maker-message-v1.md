# Planner -> Maker 派发消息：V2-T23 第 1 轮

Maker 您好！请按合同执行任务 **V2-T23 第 1 轮**（免 Key 百度优先外部联网 RAG 深度改造、黑名单精准过滤、智能检索词提炼、标准引用体系规范化与 Step 4 导航对齐修复）。

---

### 一、任务基础信息
- **有效合同**：`docs/dev-flow/tasks/V2-T23/01-planner-task-contract-v1.md`
- **精确起始 SHA**：`9942aec52e1f9abf2818c440fc13bf20c3f6c1c3`
- **目标分支**：`master`

---

### 二、核心交付范围与实现要点
1. **百度优先免 Key 检索与自媒体黑名单过滤 (`engine/app/writing/web_search.py`)**：
   - 实现 `_search_baidu(query, timeout, max_results)` 作为第一优先级引擎；
   - 废除 `.gov.cn` 狭窄白名单限制；
   - 严格拦截知乎、CSDN、百家号、小红书、微信公众号、微博、贴吧、简书等自媒体黑名单。
2. **智能提炼精简搜索词 (`engine/app/writing/rag.py`)**：
   - 剥离项目标题中的长串报告噪音，提取 `区域 + 产业核心词 + 章节主题` 生成 2~4 元精炼搜索词。
3. **规范引用标记（消灭孤立 [Z]）(`engine/app/writing/refs.py`, `writer.py`, `prompts.py`, `markdown.ts`)**：
   - 【源:文件名】（底稿）、【标:规程或标准全称】（国家/行业标准）、【网:政策标题】（百度搜索政策）；
   - 彻底废除将未知标签洗涤为 `[Z]` 的行为，Prompt 严禁输出孤立 `[Z]`。
4. **前端参考资料抽屉展示 URL 超链接 (`desktop/src/components/Step3Writing.vue`, `Step4Review.vue`, `markdown.ts`)**：
   - 网页来源渲染 `<a :href="ref.url" target="_blank">`；
   - Step 3 写作前摇展示百度联网检索命中状态。
5. **Step 4 导航栏对齐与精准平滑滚动/问题直达 (`desktop/src/components/Step4Review.vue`)**：
   - 顶部增加统计卡片对齐 Step 3；
   - 采用 `container.scrollTo({ top: el.offsetTop - 16, behavior: 'smooth' })` 物理坐标精准滚动，支持标题文本模糊查找；
   - 点击左侧小节预警角标（`⚠️ N`）直达专家诊断抽屉对应问题卡片。
6. **单测覆盖与快速验证**：
   - 适配单测并确保 5 项全量门禁通过；
   - 提交候选 commit，输出 `docs/dev-flow/tasks/V2-T23/rounds/01/maker-completion.md`，交回候选 SHA。
