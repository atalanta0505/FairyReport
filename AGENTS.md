# FairyReport_lite 项目规则

## 项目
- FairyReport 智能报告编制应用：Tauri 2 + Vue 3（`desktop/`）+ FastAPI（`engine/` 本地引擎）+ 三源 RAG。
- 前端入口 `desktop/`；本地引擎入口 `engine/app/main.py`；数据目录开发模式 `data/`（可用 `ENGINE_DATA_DIR` 覆盖）。

## 硬规则
- **不许 push**：只能在本地提交。推送与打标签必须由产品负责人对精确 SHA 明确授权；禁止 force push。
- **单写入者**：同一时刻只有一个执行者改产品代码，其他人只读。
- **未跟踪文件是用户数据**：不清理、不覆盖、不提交。
- **凭据**：`.env` 永不提交、永不打印、永不写入工件；不硬编码密钥；API Key 只从 `.env` 读。
- **依赖**：安装或升级依赖先获批准，批准后同步 `requirements.txt`。

## 验证
- 全量门禁一条命令：`powershell -NoProfile -File scripts\verify.ps1`（5 项，约 90 秒；`-Fast` 跳过前端构建，`-Only <id>` 只跑指定项）。
- 行为变化补最小目标测试。交付时说明：改了什么、跑了什么、结果如何。

## 历史
- 早期 Planner-Maker-Checker 三角色流程与逐轮工件保留在 `docs/dev-flow/tasks/` 作记录，**不再是必须遵循的流程**。
