# MCP Server 多客户端接入指南

**FairyReport** 除提供独立 Tauri 2 桌面工作台外，还内置了标准的 **Model Context Protocol (MCP) Server**（`engine.mcp_server`），可被 **Cherry Studio、Claude Desktop / Cowork、Trae、Cursor、Windsurf、Antigravity、OpenClaw / QClaw** 等国内外主流桌面端 AI Agent 直接挂载调用。

::: tip 零额外 API Key（Host-LLM Mode）
挂载 FairyReport MCP Server 后，默认**无需额外配置大模型 API Key**——由你当前使用的桌面客户端自身大模型负责推理与撰文，FairyReport 负责提供 **15 类权威报告标准蓝图、三源深度 RAG 检索、跨章节工程经济指标自洽核验、以及出版级三线表 Word（`.docx`）编译导出**。
:::

---

## 一、 快速接入配置（JSON）

在本地克隆仓库并安装依赖（`pip install -r requirements.txt`）后，在你的桌面 Agent 客户端（如 Cherry Studio「设置 -> MCP 服务器」、Claude Desktop `claude_desktop_config.json`、Trae / Cursor MCP 设置）中添加：

```json
{
  "mcpServers": {
    "fairyreport": {
      "command": "python",
      "args": ["-m", "engine.mcp_server"],
      "cwd": "D:/Repo/FairyReport"
    }
  }
}
```

*(请将 `D:/Repo/FairyReport` 替换为你本地实际仓库目录；若已执行 `pip install -e .`，可直接设置 `"command": "fairyreport-mcp", "args": []`。)*

---

## 二、 核心 MCP 工具一览

| 工具名称 | 是否需额外 Key | 功能说明 |
| :--- | :---: | :--- |
| `list_report_templates` | **否** | 列出支持的全部 15 类专业报告名称、字数上限与拓扑推荐写作顺序 |
| `get_report_blueprint` | **否** | 获取指定报告类型的权威标准大纲骨架、各章配额与 12 项标准三线表规范 |
| `ingest_project_materials` | **否** | 将本地 PDF / Word / Excel / TXT 工程底稿切片向量化入库本地 ChromaDB |
| `retrieve_report_evidence` | **否** | 执行三源深度 RAG（底稿 `【源:...】` + 国标 `【标:...】` + 免 Key 权威联网 `【网:...】`） |
| `verify_report_consistency` | **否** | 跨章节核验总投资、建设用地、建筑面积、工期、FIRR、营业收入量纲自洽性 |
| `export_consulting_docx` | **否** | 一键编译带封面、自动目录、标准三线表、标题防粘连与自动编号《参考文献》的 `.docx` |
| `draft_chapter_with_engine` | 可选 | 当 `.env` 配有大模型 Key 时，支持将超长单章卸载至后台引擎生成 |

---

## 三、 推荐对话指令模板

挂载成功后，直接在客户端对话框发送：

> “请调用 `fairyreport` 工具获取《可行性研究报告》标准大纲蓝图，结合 `retrieve_report_evidence` 检索‘算力基础设施 绿电协同 产业政策’，按规范起草第一章《项目概述》与第七章《投资估算与资金筹措》（包含标准三线表与行内引用），随后调用 `verify_report_consistency` 核验前后章节总投资等指标是否自洽，最后调用 `export_consulting_docx` 导出出版级 Word 初稿。”
