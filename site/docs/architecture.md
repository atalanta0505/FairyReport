# 系统架构与本地数据存储 🛡️

FairyReport 是一款开源、本地优先（Local-First）的智能报告编制桌面工具。整个系统建立在现代桌面混合架构与三源 RAG 检索体系之上，全部源码在 [GitHub (atalanta0505/FairyReport)](https://github.com/atalanta0505/FairyReport) 公开可查。

---

## 🏛️ 系统总体架构

FairyReport 采用轻量高效的 **Tauri 2 + 原生 Web 前端 + 独立高性能 Python 引擎** 架构：

<div class="fr-arch-diagram">
<div class="fr-arch-layer">
<div class="fr-arch-layer-title">🖥️ 用户桌面端（Tauri 2 + Vue 3）</div>
<div class="fr-arch-boxes two-col">
<div class="fr-arch-box">
<b>Vue 3 + TypeScript 现代化交互界面</b>
<span>五步端到端工作台 · 实时思维链 · 审阅抽屉</span>
</div>
<div class="fr-arch-box">
<b>Rust 原生安全底座与生命周期管理</b>
<span>本地回环安全通信 · 进程守护与文件定位</span>
</div>
</div>
</div>
<div class="fr-flow-arrow">⇅ 本地内部回环高速通信 (127.0.0.1)</div>
<div class="fr-arch-layer highlight">
<div class="fr-arch-layer-title">⚙️ 本地 Python 核心计算引擎（FastAPI）</div>
<div class="fr-arch-pipeline">
<div class="fr-arch-pipe-node"><b>1. 材料解析</b><small>PDF / Word / Excel</small></div>
<div class="fr-arch-pipe-node"><b>2. 离线向量化</b><small>FastEmbed 本机推理</small></div>
<div class="fr-arch-pipe-node"><b>3. 本地向量库</b><small>ChromaDB 持久化</small></div>
<div class="fr-arch-pipe-node"><b>4. 撰写与审阅</b><small>三源 RAG + 专家把关</small></div>
<div class="fr-arch-pipe-node"><b>5. 出版级导出</b><small>Word / Markdown</small></div>
</div>
</div>
<div class="fr-flow-arrow">⇅ 本地磁盘读写 &amp; 最小化摘要推理</div>
<div class="fr-arch-layer safe">
<div class="fr-arch-layer-title">🔒 本地物理隔离存储（用户本机磁盘 · 100% 不出机）</div>
<div class="fr-arch-boxes three-col">
<div class="fr-arch-box">
<b>原始项目底稿</b>
<span>.docx / .pdf / .xlsx 原件留存本机</span>
</div>
<div class="fr-arch-box">
<b>项目私有向量库</b>
<span>SQLite / Chroma 本地离线索引</span>
</div>
<div class="fr-arch-box">
<b>内置标准规程库</b>
<span>15 类报告模板与现行国标规范</span>
</div>
</div>
</div>
<div class="fr-arch-layer cloud">
<div class="fr-arch-layer-title">☁️ 外部大模型 API（仅按需最小化调用）</div>
<div class="fr-arch-box">
<b>DeepSeek 官方 API / 私有化算力接口</b>
<span>仅发送当前章节提示词与百字检索摘要片段 ←→ 返回流式正文与标准三线表</span>
</div>
</div>
</div>

---

## 🔒 纯本地物理隔离 · 数据安全保证

对于重大工程咨询、产业规划和企业投资决策，底稿数据往往涉及敏感商业机密。FairyReport 从底层架构上彻底拒绝“全云端黑盒”：

1. **原始文件零外泄**：
   - 导入的项目立项书、财务测算表、技术规范等文件全部存放在本机用户应用数据目录中（Windows 为 `%LOCALAPPDATA%\FairyReport\`）。
   - 系统绝不会将整份文档或原始压缩包上传至任何云端服务器。
2. **纯本地离线向量化**：
   - 文档的切片、分块（Chunking）与向量嵌入计算（Embedding）完全使用本地轻量化模型在用户本机 CPU/GPU 完成，不需要联网上传向量数据。
3. **极小化上下文交互原则**：
   - 当调用大模型进行流式撰写时，系统仅将与当前章节直接相关的**百余字参考文本碎片**与**行业规程写作要求**作为 Prompt 上下文发送给大模型，原始文档整体结构与全貌始终物理留存于本地。
4. **模型对接支持**：
   - 系统支持对接 DeepSeek 系列模型（推荐官方最新模型）；在保密私有算力环境下，支持直接指定局域网内对应的模型接口服务。

---

## 🧠 三源 RAG 智识矩阵

普通 RAG 仅从单一上传文档中做向量检索，容易陷入“无材料则言之无物，有材料则机械抄袭”的困局。FairyReport 独创**三源 RAG 智识矩阵**：

| 智识来源 | 物理存储方式 | 核心作用与能力 |
| :--- | :--- | :--- |
| **源 A · 项目私有材料** | 本地私有 Chroma 向量库 | 精准提取项目独有数据：建设地点、规模产能、工艺路线、投资估算指标。 |
| **源 B · 行业规程与规范库** | 内置只读 JSON 规程库 | 锚定现行标准体例、各专业技术规范、必备章节要素与审查指标。 |
| **源 C · 外部权威联网检索** | 按需实时轻量搜索引擎 | 动态补充最新宏观政策背景、行业碳排放基准、同类项目先进对标数据。 |

三路智识通过专有混合检索算法动态配比，既能确保工程报告的真实性与合规性，又赋予了针对前沿新型课题（如新质生产力、算力中心、低空经济）的敏锐洞察与实时建言能力。
