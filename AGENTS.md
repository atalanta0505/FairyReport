# AGENTS.md — FairyReport_lite 项目级规则

所有在本仓库工作的 Agent（人或 AI）每次都必须遵守以下规则。
开发流程见 `docs/dev-flow/PROCESS.md`（Planner-Maker-Checker 模式，基于《可移植的 AI 协作开发手册》）。

## 项目概况

- FairyReport v1.0.5：基于 Streamlit + LLM + RAG 的工程咨询报告生成工具（12 类投前咨询交付物）。
- 技术栈：Python 3.10+、streamlit、openai 兼容 API、chromadb、sentence-transformers、python-docx、openpyxl。
- 入口：`app.py`（`streamlit run app.py`）。
- 核心模块：`pipeline.py`（解析/分块）、`kb.py`（向量库）、`outline.py`（大纲）、`writer.py`（写作）、`exporter.py`（导出）、`ref_manager.py`、`hint_store.py`、`web_search.py`、`steps/`（UI 步骤）、`components/`、`converters/`（格式转换）、`generic_knowledge/`（只读资源与模板 JSON）。
- 全局配置：`config.py`（支持 `.env` 覆盖）。数据目录：开发模式为仓库根目录下 `data/`；打包后为 `%LOCALAPPDATA%\FairyReport`（可用 `FRL_DATA_DIR` 覆盖）。

## 单写入者规则

- 同一时刻只有当前 Maker 可修改产品代码；Planner 与 Checker 对产品代码只读。
- 未跟踪文件视为用户数据：不擅自清理、覆盖、暂存、提交或推送。

## 测试与验证

- 测试框架：pytest + pytest-bdd（requirements.txt）。运行：`python -m pytest`。
- 本仓库当前没有测试用例：任务合同涉及行为变化时，Planner 必须要求 Maker 先补能证明主要行为的最小目标测试。
- 已知保护逻辑（基线事实）：`config.py` 中 FRL-003（`CHUNK_OVERLAP >= CHUNK_SIZE` 时钳制，防止 `_chunk_segment` 死循环）。

## 凭据与安全

- API Key 从 `.env` 读取（如 `DEEPSEEK_API_KEY`、可选 SiliconFlow rerank key）。
- `.env` 永不提交、永不打印、永不写入任何工件；代码中不得硬编码密钥。
- 人工动作交接（HUMAN_ACTION_REQUIRED）不得包含 Token、密码或含凭据截图。

## 发布边界

- Maker 只创建本地候选提交，不 push。
- 发布需要产品负责人对**精确已验收 SHA** 的明确授权；禁止 force push；推送前后都要精确比对远端 SHA。

## 依赖纪律

- 安装新依赖或升级版本必须先获产品负责人批准；批准后同步更新 `requirements.txt`。

## Git 纪律

- 每轮开始读取 `git rev-parse HEAD` 与 `git status --short`。
- 候选提交只包含合同允许的文件；验收针对精确 SHA；任何新提交都需要重新验收。
