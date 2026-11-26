# FairyReport MCP Server 多客户端接入指南

**FairyReport MCP Server** 将原本内置于桌面工作台的四大核心专业能力封装为标准 **Model Context Protocol (MCP)** 工具，使国内外主流桌面端办公与开发 AI Agent（**Cherry Studio、腾讯 WorkBuddy、豆包电脑版、千问桌面端 / Qoder、Claude Desktop / Cowork、Trae、Cursor、Windsurf、Antigravity、OpenClaw / QClaw** 等）能够直接调用。

> [!TIP]
> **零额外 API Key 设计（Host-LLM Mode）**
> 挂载 FairyReport MCP Server 后，默认**不需要额外配置任何大模型 API Key**——由你当前使用的桌面客户端自带大模型（如 Claude、DeepSeek、GPT、Gemini、Qwen）负责推理与正文写作，FairyReport 负责提供 **15 类权威报告大纲蓝图、本地+国标+权威联网三源检索、跨章节工程经济指标自洽核验、以及出版级三线表 Word（`.docx`）编译导出**。

---

## 一、 环境准备（两种方式任选其一）

### 方式 A：零 Python 环境直接使用 Windows 绿色便携包（推荐）

下载并解压 `FairyReport-Local-v1.6.5-Windows-x64.zip` 至任意本地目录（例如 `D:/Tools/FairyReport`），无需安装 Python 或 `pip` 依赖，包内自带的 `fairyreport-engine.exe` 已内置完整 MCP Server、离线向量模型与 15 类标准报告模板：

```json
{
  "mcpServers": {
    "fairyreport": {
      "command": "D:/Tools/FairyReport/fairyreport-engine.exe",
      "args": ["--mcp"]
    }
  }
}
```

> **便携数据自动互通**：便携包同级自带 `.portable` 标记，直接运行 `fairyreport-engine.exe --mcp` 时会自动将项目数据库、向量索引与导出的 Word 保存在 `<解压目录>/data/` 下，与 `FairyReport.exe` 桌面端共享数据（也可通过 `env.ENGINE_DATA_DIR` 自定义数据目录）。  
> 如需以 Streamable HTTP 模式启动，直接执行：
> ```bash
> D:/Tools/FairyReport/fairyreport-engine.exe --mcp --transport streamable-http --host 127.0.0.1 --port 8002
> ```

### 方式 B：开发者从源码安装（Windows / macOS / Linux）

在本地克隆仓库并安装依赖（推荐 Python `>= 3.10`）：

```bash
git clone https://github.com/atalanta0505/FairyReport.git
cd FairyReport

# 可选：创建虚拟环境
python -m venv .venv
# Windows 激活：
.venv\Scripts\activate
# macOS / Linux 激活：
source .venv/bin/activate

# 安装依赖（含官方 mcp SDK）
pip install -r requirements.txt

# 可选：以可编辑包形式安装，即可在任意路径直接调用 `fairyreport-mcp` 命令
pip install -e .
```

---

## 二、 各主流桌面端 AI Agent 配置方法

### 1. Cherry Studio（国内首选开源桌面客户端）

1. 打开 **Cherry Studio** ➔ 点击左下角 **「设置」** ➔ **「MCP 服务器」** ➔ **「添加服务器」**（或点击「编辑 JSON」）。
2. 选择类型为 `STDIO`，填入以下 JSON 配置（请将 `D:/Repo/FairyReport` 替换为你本地实际路径）：

```json
{
  "mcpServers": {
    "fairyreport": {
      "command": "python",
      "args": ["-m", "engine.mcp_server"],
      "cwd": "D:/Repo/FairyReport",
      "env": {
        "ENGINE_DATA_DIR": "D:/Repo/FairyReport/data"
      }
    }
  }
}
```

> 若使用了虚拟环境，可将 `"command"` 设为虚拟环境 Python 绝对路径（例如 `"D:/Repo/FairyReport/.venv/Scripts/python.exe"`）；若已执行 `pip install -e .` 或通过 PyPI 安装，可直接设置 `"command": "fairyreport-mcp", "args": []`。

---

### 2. Claude Desktop（含 Claude Cowork 桌面模式）

打开 Claude Desktop 配置文件：
- **Windows**：`%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**：`~/Library/Application Support/Claude/claude_desktop_config.json`

添加 `fairyreport` 服务节点并重启 Claude Desktop：

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

---

### 3. Trae / Cursor / Windsurf / Antigravity（AI IDE 与智能工作台）

在 IDE 的全局或项目级 MCP 配置文件（如 `.cursor/mcp.json`、Trae MCP 设置或 `mcp_config.json`）中添加：

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

---

### 4. 国内桌面办公 Agent（腾讯 WorkBuddy / 豆包电脑版 / 千问桌面端 / Qoder）

- **腾讯 WorkBuddy**：打开侧边栏 **「专家·技能·连接器 ➔ 连接器 ➔ 自定义连接器」**（或编辑用户目录下的 `~/.workbuddy/mcp.json`），填入上方相同的 `mcpServers` 配置后点击 **「信任」** 并启用。
- **豆包电脑版**：进入桌面客户端的 **「技能 / 自定义连接器」**，添加本地 `stdio` 启动命令（如 `uvx --from git+https://github.com/atalanta0505/FairyReport.git fairyreport-mcp` 或本地便携包 `fairyreport-engine.exe --mcp`）。
- **阿里 Qoder / 千问桌面端**：按 `Ctrl+Shift+,` 打开设置 ➔ **MCP ➔ My Servers ➔ + Add**（或从魔搭社区 MCP 广场搜索 **「斐语报告 / FairyReport」** 一键导入）。

---

### 5. OpenCode / DeepSeek Harness（终端 CLI Agent 运行时）

- **OpenCode（`~/.config/opencode/opencode.json` 或项目根目录 `opencode.json`）**：
  ```json
  {
    "$schema": "https://opencode.ai/config.json",
    "mcp": {
      "fairyreport": {
        "type": "local",
        "command": ["C:/Python314/python.exe", "-m", "engine.mcp_server"],
        "enabled": true,
        "environment": {
          "PYTHONPATH": "D:/Repo/FairyReport",
          "ENGINE_DATA_DIR": "D:/Repo/FairyReport/data"
        }
      }
    }
  }
  ```
- **DeepSeek Harness（`dsh` / `~/.dsh/cordis.patch.yml`）**：
  ```yaml
  - insert:
      - id: mcp-fairyreport
        name: '@deepseek-ai/dsh-mcp-client'
        config:
          serverName: fairyreport
          transport: stdio
          command: C:/Python314/python.exe
          args:
            - '-m'
            - 'engine.mcp_server'
          cwd: D:/Repo/FairyReport
          env:
            ENGINE_DATA_DIR: D:/Repo/FairyReport/data
  ```

---

### 6. OpenClaw / QClaw / 远程 Agent（Streamable HTTP 模式）

对于需要通过 HTTP 端点挂载的本地网关或远程 Agent 容器，可将 FairyReport MCP Server 启动为 `streamable-http` 或 `sse` 服务：

```bash
python -m engine.mcp_server --transport streamable-http --host 127.0.0.1 --port 8002
```

---

## 三、 工具清单与参数速查

| 工具名称 | 核心用途 | 关键输入参数 |
| :--- | :--- | :--- |
| `list_report_templates` | 查看支持的全部 15 类专业报告名称、总字数上限与推荐写作顺序 | 无参数 |
| `get_report_blueprint` | 获取指定报告类型的权威标准章节骨架（`outline_md`）、单章配额及三线表规范 | `report_type`（如 `"可行性研究报告"`） |
| `ingest_project_materials` | 将本地 `.pdf` / `.docx` / `.xlsx` / `.txt` / `.md` 底稿切片并建立项目向量库 | `project`、`file_paths`（文件**或文件夹**路径列表，传文件夹自动递归扫描） |
| `retrieve_report_evidence` | 执行三源深度 RAG 检索（底稿 `【源:...】` + 国标 `【标:...】` + 免 Key 权威联网 `【网:...】`） | `query`、`project`、`chapter_title`、`report_type` |
| `verify_report_consistency` | 跨章节核验总投资、用地面积、建筑面积、建设工期、FIRR、营业收入自洽性（自动换算亿元/万元、公顷/亩） | `chapters`（如 `{"1": "# 第一章...", "7": "# 第七章..."}`） |
| `export_consulting_docx` | 将各章 Markdown 一键编译为带封面、目录、标准三线表、标题防粘连与自动编号《参考文献》的 `.docx` | `chapters`、`title`、`project`、`report_type`、`author_org` |
| `draft_chapter_with_engine` | *(可选)* 当 `.env` 配有 `DEEPSEEK_API_KEY` 时，将超长单章卸载给本地引擎后台生成 | `report_type`、`outline_md`、`chapter_seq`、`chapter_title`、`topic` |

---

## 四、 开箱即用的对话指令示例（无需敲英文工具名，直接说大白话）

挂载成功后，你无需记忆任何英文工具名称，在 Cherry Studio / WorkBuddy / 豆包电脑版 / Trae 中直接用自然语言交流，大模型会在后台自动匹配调度工具：

### 场景 0：纯自然语言对话（甩整个文件夹路径一键开写）
> “项目资料都放在 `D:/我的项目底稿` 这个文件夹里了，你帮我全部读进去看看，然后按《可行性研究报告》标准拟一份大纲出来，报告标题叫《长三角智能算力中心建设项目可行性研究报告》。”
>
> *(确认大纲后继续说)*：“大纲没问题，帮我先写出第一章和第七章，核对一下两章的投资额有没有前后打架，最后导出成标准三线表 Word 文档放到桌面。”

### 场景 1：带本地底稿的《可行性研究报告》全闭环指令（精确指定步骤）
> “请调用 `fairyreport` 工具：
> 1. 先查看《可行性研究报告》的标准大纲蓝图与推荐写作顺序；
> 2. 将我本地的 `D:/资料/算力中心立项批复.pdf` 导入到项目 `长三角智算中心`；
> 3. 结合三源证据（`retrieve_report_evidence`）帮我按规范撰写第一章《项目概述》和第七章《投资估算与资金筹措》（严格包含标准三线表与 `【源:...】【标:...】【网:...】` 行内引用）；
> 4. 调用 `verify_report_consistency` 核验这两章的总投资、用地、工期等指标是否 100% 自洽；
> 5. 最后调用 `export_consulting_docx` 导出出版级 Word 初稿并告诉我保存路径。”

### 场景 2：零底稿快速起草《智库专报》或《资金申请报告》
> “请使用 FairyReport 的 `get_report_blueprint` 获取《智库专报》蓝图，并调用 `retrieve_report_evidence` 检索‘全国一体化算力网 绿电协同 产业政策’权威资料，按规范起草一篇完整专报，核验自洽后导出为 Word 文档。”
