# FairyReport 冷启动推广与分发弹药库（Launch Kit）

本文件汇总了可直接复制使用的 **GitHub 仓库元数据配置、MCP 生态广场上架清单、开源周刊自荐文案、技术社区首发帖、以及短视频/图文种草脚本**。

---

## 一、 GitHub 仓库右上角（About 栏）1 分钟优化清单

打开 `https://github.com/atalanta0505/FairyReport` 右上角齿轮图标（**Edit repository details**），按以下内容填写：

- **Description（中英双语高检索命中版）**：
  ```text
  🧚‍♂️ 本地优先的智能工程咨询与智库报告工作台 & MCP Server（15 类可研/立项/专项债/专报标准大纲 · 三源深度 RAG · 跨章节经济指标自洽核验 · 出版级三线表 Word 导出）| Local-first AI consulting report workbench & MCP Server
  ```
- **Website**：
  ```text
  http://101.42.9.223/
  ```
- **Topics（复制逐个添加，覆盖工程报告、RAG 与 MCP 三大搜索流量池）**：
  ```text
  mcp-server
  model-context-protocol
  rag
  report-generation
  tauri
  vue3
  fastapi
  chromadb
  deepseek
  docx
  local-first
  feasibility-study
  ```

---

## 二、 MCP 市场与聚合仓库免费上架清单（自带精准搜索流量）

仓库现已内置符合规范的 [server.json](file:///d:/Repo/FairyReport/server.json)、[pyproject.toml](file:///d:/Repo/FairyReport/pyproject.toml) 与 [MCP_GUIDE.md](file:///d:/Repo/FairyReport/docs/MCP_GUIDE.md)，建议依次提交至以下渠道：

1. **魔搭社区（ModelScope）MCP 广场**（国内流量最大，**Cherry Studio 客户端内置同步**）：
   - 地址：`https://www.modelscope.cn/mcp`
   - 亮点标签：`报告生成`、`工程咨询`、`Word 排版`、`三源 RAG`、`零 API Key`
2. **punkpeye/awesome-mcp-servers** & **appcypher/awesome-mcp-servers**（GitHub 高星 MCP 导航榜）：
   - 提交一行 PR 到 `Document / Knowledge & RAG` 分类：
     ```markdown
     - [atalanta0505/FairyReport](https://github.com/atalanta0505/FairyReport) 🐍 🏠 - Local-first structured consulting & engineering report MCP server with 15 authoritative report blueprints, 3-source RAG, deterministic cross-chapter financial/engineering metric verification, and publication-grade three-line-table DOCX export.
     ```
3. **Glama.ai MCP Directory**（`https://glama.ai/mcp/servers`）与 **MCP.so**（`https://mcp.so`）：
   - 直接提交 GitHub 仓库链接，系统会自动读取 [README_EN.md](file:///d:/Repo/FairyReport/README_EN.md) 与 [server.json](file:///d:/Repo/FairyReport/server.json) 进行质量评分与收录。
4. **tauri-apps/awesome-tauri**：
   - 提交 PR 到 `Applications` 分类，展示 Tauri 2 + FastAPI 本地 AI 生产力应用形态。

---

## 三、 开源周刊自荐文案（直接复制提交 Issue）

### 1. HelloGitHub 自荐（提交至 `https://github.com/521xueweihan/HelloGitHub/issues`）

- **项目名称**：FairyReport
- **项目地址**：https://github.com/atalanta0505/FairyReport
- **项目说明**：
  一款面向工程咨询、投资立项与智库研究的**本地优先 AI 报告编制工作台 & MCP Server**（基于 Tauri 2 + Vue 3 + FastAPI + ChromaDB）。
  它专门解决通用大模型写数万字专业报告（可行性研究报告、项目建议书、资金申请报告、特许经营方案、智库专报等 15 类）时的四大顽疾：
  1. **内置 15 类权威报告大纲与拓扑写作顺序**：骨架锁定防篡改，拒绝空洞套话；
  2. **三源深度 RAG 溯源**：融合本地 PDF/Word/Excel 工程底稿库、行业规程国标库与百度免 Key 权威联网检索，正文中实时生成绿色溯源胶囊；
  3. **跨章节工程经济指标自洽核验引擎**：自动比对前后章节的总投资、用地面积、建筑面积、工期、财务内部收益率（支持亿元/万元、公顷/亩自动换算），揪出前后数值打架；
  4. **出版级三线表 Word（`.docx`）一键导出**：自动拆分标题正文粘连、渲染 12 类标准工程经济三线表，并按出场顺序生成 `[1][2]` 参考文献章。
  提供 **Windows 绿色免安装便携版（解压即用、免注册）**，同时支持作为 **零额外 Key 的 MCP Server** 接入 Cherry Studio、Claude Desktop、Cursor 与 Trae。
- **推荐配图**：直接上传仓库内的 `docs/images/step3_writing.png` 与 `docs/images/step5_export.png`。

---

## 四、 V2EX / 掘金 / 知乎 / Linux.do 深度技术首发帖

### 标题备选
- **备选 A（痛点技术向）**：《大模型写万字可研报告总把投资额算串、Word 排版一团糟？我开源了一个带跨章量纲核验与三线表编译的本地工作台（支持 MCP）》
- **备选 B（桌面端 + Agent 向）**：《开源了 FairyReport：Tauri 2 + 三源 RAG 专业报告工作台，同时封装成了零 Key 可用的 MCP Server（适配 Cherry Studio / Claude / Trae）》

### 正文模板
> 平时在写或审阅**可行性研究报告、项目建议书、专项债资金申请报告、规划报告、智库专报**这类动辄两三万字的专业材料时，大家应该都试过直接扔给 ChatGPT、Claude 或 DeepSeek 网页端。
>
> 但实际用下来会发现四个非常头疼的工程问题：
> 1. **大纲失控**：写着写着就把发改委规定的核心比选章节漏了，或者擅自篡改多级标题；
> 2. **虚假出处**：顺口胡编一个国标号或政策文件，根本不敢直接往上交；
> 3. **前后章节数据打架（最致命）**：第一章《项目概述》写“总投资 1.2 亿元、建设期 24 个月”，写到第七章《投资估算》变成了“总投资 10,500 万元、工期 3 年”；
> 4. **Word 排版灾难**：Markdown 贴进 Word 后，多级标题和正文粘在一行、没有标准三线表、参考文献编号全乱。
>
> 为了彻底解决这几个问题，我开发并开源了 **FairyReport**（MIT 协议，纯本地存储，免注册开箱即用）：
> - 🔗 **GitHub 仓库**：https://github.com/atalanta0505/FairyReport
> - 🌐 **国内官方网站与 Windows 绿色便携版下载**：http://101.42.9.223/
>
> #### 核心做了哪几件硬核的事？
> 1. **15 类专业报告标准骨架与拓扑写作顺序**：内置可研、初可研、项目建议书、资金申请、PPP 特许经营、产业/园区/企业规划、智库专报等 15 套标准大纲与字数配额，先写主体技术与投资论证章，最后汇总生成首尾综述章。
> 2. **三源深度 RAG（底稿 `【源】` + 国标 `【标】` + 免 Key 权威联网 `【网】`）**：本地离线解析 PDF/Word/Excel 底稿入库 ChromaDB，联网检索内置自媒体黑名单，只采信权威公示信息。
> 3. **跨章节工程经济指标自洽核验引擎（`context_verifier.py`）**：纯确定性规则抽取各章的总投资、建设用地、建筑面积、工期、FIRR、营业收入，自动做单位换算（亿元 <-> 万元、公顷 <-> 亩、年 <-> 月），并区分基准方案与敏感性分析情景，毫秒级输出冲突诊断清单。
> 4. **出版级 `.docx` 与三线表编译器（`docx_builder.py`）**：自动清洗 50+ 种工程标题粘连，强制渲染 12 项规定动作标准三线表，并将全书引用按首次出现顺序重排为 `[1], [2], [3]...` 附于文末《参考文献》。
> 5. **双形态支持（独立 Tauri 2 桌面端 + 零 Key MCP Server）**：
>    - 不懂命令行的工程咨询/规划朋友，可以直接下载 `396 MB` 的 Windows 绿色便携包，解压双击 `FairyReport.exe` 即用；
>    - 习惯用 **Cherry Studio、Claude Desktop、Trae、Cursor、OpenClaw** 的开发者，只需配 5 行 JSON 挂载 `engine.mcp_server`，**无需在工具里额外配大模型 API Key**，直接让你客户端里现有的大模型获得上述全部专业报告能力！
>
> 欢迎大家试用、提 Issue 或点个 Star ⭐ 支持！

---

## 五、 小红书 / B站 60 秒破圈短视频分镜脚本（面向工程咨询 / 设计院 / 投研人群）

| 时间轴 | 画面内容（直接录屏） | 口播文案 / 字幕钩子 |
| :--- | :--- | :--- |
| **00:00 - 00:08** | 左边展示普通网页 AI 写可研报告：纯文字堆砌、前后投资额不一致；右边切入 FairyReport 清爽工作台 | “用普通 AI 写可研、立项、专项债报告，最怕什么？胡编数据、前后投资额打架、导进 Word 排版全乱！” |
| **00:08 - 00:22** | 展示 **Step 1 & Step 2**：拖入本地 PDF/Excel 底稿，点选《可行性研究报告》卡片，自动生成带推荐写作顺序的多级标准大纲 | “给大家分享一个完全免费开源、纯本地不泄密的智能报告工作台 **FairyReport**，内置 15 类标准工程与规划报告模板，底稿全部存在自己电脑里。” |
| **00:22 - 00:38** | 展示 **Step 3**（对应 `step3_writing.png`）：流式生成正文、绿色溯源胶囊 `【源/标/网】`、自动渲染漂亮的标准三线表 | “写作时自动锁定大纲骨架，每一处数据都带底稿、国标或官方网址溯源胶囊，工程经济指标自动排成标准三线表！” |
| **00:38 - 00:50** | 展示 **Step 4 & Step 5**（对应 `step4_review.png` & `step5_export.png`）：跨章节数据自洽核验 + 一键导出带封面目录的 Word 文档 | “最绝的是导出前会自动核验全书总投资、用地、收益率前后是否一致，一键导出带封面、目录、三线表和规范参考文献的出版级 Word 初稿！” |
| **00:50 - 01:00** | 展示 GitHub 仓库主页与绿色免安装便携包解压双击画面 | “提供 Windows 绿色免安装便携版，解压双击就能用，还能作为 MCP 插件接入 Cherry Studio 和 Claude。GitHub 搜 **FairyReport** 即可免费获取！” |
