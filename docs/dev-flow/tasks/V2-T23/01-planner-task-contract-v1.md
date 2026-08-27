# 任务合同 V2-T23 v1 — 免 Key 百度优先外部联网 RAG 深度改造、黑名单精准过滤、智能检索词提炼、标准引用体系规范化与 Step 4 导航对齐修复

- 状态：ACCEPTED（已由 Checker 验收通过，锁定候选提交 SHA `f4b29a12f6eb4b97bf96f849a87d170d0d0f2535`）
- 依据：用户关于外部联网 RAG 真实召回、国内公网必须第一优先走百度接口、废除白名单并严格拦截自媒体黑名单、消灭孤立 [Z]、Step 4 导航栏对齐 Step 3 与修复精准滚动/问题定位链接的指令
- 精确起始 SHA：`81205aea45ea8765d5c40483eae0584159c98448`
- 验收锁定 SHA：`f4b29a12f6eb4b97bf96f849a87d170d0d0f2535`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **国内公网第一优先走百度免 Key 检索与自媒体黑名单过滤 (`engine/app/writing/web_search.py`)**：
   - 实现 `_search_baidu`：第一优先级通过百度接口（`https://www.baidu.com/s?wd=...`）发起免 Key 搜索，解析真实标题、摘要与目标 URL；
   - 备用引擎：保留 Bing / DuckDuckGo 作为第 2、3 备用兜底；
   - 废除 `.gov.cn` 狭窄白名单限制（全面采信政府公报、行业协会、国家标准网、科研高校、企业公开公示、统计年鉴等真实权威源）；
   - 严格黑名单拦截：严格过滤知乎 (`zhihu.com`)、CSDN (`csdn.net`)、百家号 (`baijiahao.baidu.com`)、小红书 (`xiaohongshu.com`)、微信公众号 (`mp.weixin.qq.com`)、微博 (`weibo.com`)、贴吧 (`tieba.baidu.com`)、简书 (`jianshu.com`)、搜狐号/网易号等自媒体。

2. **智能提炼精简搜索词与三源 RAG 融合升级 (`engine/app/writing/rag.py`)**：
   - 实现 `extract_smart_web_query`：自动剥离“可行性研究报告”、“项目建议书”、“第X章”等冗余字样，提炼 `区域+产业主体词+章节主题`（如 `利辛县 牛皮革 产业政策 规划`），杜绝因搜索词过长导致 0 召回。

3. **规范引用标记体系（彻底消灭孤立 `[Z]`）(`engine/app/writing/refs.py`, `writer.py`, `prompts.py`, `markdown.ts`)**：
   - 规范三类引用标记：
     - `【源:项目文件名】` ➔ 项目底稿资料；
     - `【标:规程或标准全称】` ➔ 行业规程与国家强制标准（如 `【标:制革及毛皮加工工业水污染排放标准(GB 30486—2013)】`）；
     - `【网:政策标题】` ➔ 百度联网检索命中的政策、规划与统计数据；
   - 彻底废除后处理将未知来源替换为 `[Z]` 的逻辑，Prompt 严禁大模型输出孤立 `[Z]`。

4. **前端参考资料抽屉与外链可点击直达 (`desktop/src/components/Step3Writing.vue`, `Step4Review.vue`, `markdown.ts`)**：
   - 「📚 参考资料来源」抽屉中，对于 `【网:...】` 来源，渲染可直接点击的真实超链接（`<a :href="ref.url" target="_blank">`），方便用户直接查阅原始出处；
   - Step 3 写作前摇展示 `🌐 百度联网 RAG：已命中 N 条权威产业政策参考`。

5. **Step 4 导航栏与 Step 3 严格对齐、修复精准平滑滚动与问题角标直达 (`desktop/src/components/Step4Review.vue`)**：
   - Step 4 侧边栏顶部增加 `总章节` / `已审阅` / `总字数` 统计卡片，样式与 Step 3 100% 对齐；
   - 重构 `scrollToChapter` 与 `scrollToSubheading`：采用容器物理坐标直接滚动 `container.scrollTo({ top: el.offsetTop - 16, behavior: 'smooth' })`，并支持按标题文本模糊查找 DOM 元素，杜绝滚动失效；
   - 点击左侧小节预警角标（`⚠️ N`），立即滑出右侧专家诊断抽屉并定位至该小节的具体问题卡片（触发 2.5 秒呼吸闪烁）。

6. **单测覆盖与快速验证**：
   - 适配 `engine/tests/test_web_search.py`、`engine/tests/test_writing_rag.py`（或 `test_writing_unit.py`）与 `desktop/src/tests/`；
   - 运行 5 项全量门禁（pytest, vitest, vue-tsc, build, cargo check）。

---

## 2. 允许修改

- `engine/app/writing/web_search.py`
- `engine/app/writing/rag.py`
- `engine/app/writing/refs.py`
- `engine/app/writing/writer.py`
- `engine/app/writing/prompts.py`
- `engine/tests/**`
- `desktop/src/lib/markdown.ts`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T23/**`

---

## 3. 禁止修改

- `backend/**`、根目录除必要适配外的核心代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [x] `python -m pytest engine/tests -q` 全绿（含百度端点、黑名单过滤、智能搜索词与引用规范化单测）。
- [x] `npx vitest run`、`npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [x] 百度免 Key 检索通道正常调度，黑名单自媒体被 100% 拦截，正常行业权威源顺利召回。
- [x] 正文及参考资料抽屉中不再出现孤立的 `[Z]`，网络引用带真实外链。
- [x] Step 4 导航栏与 Step 3 视觉对齐，点击章节/子标题 100% 精准平滑滚动，点击问题角标能直达诊断抽屉。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
5. `cargo check`（workdir=`desktop/src-tauri`）
