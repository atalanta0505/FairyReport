# Maker 完成说明 — <TASK-ID> 第 <NN> 轮

## 合同与基线

- 有效合同：`tasks/<TASK-ID>/01-planner-task-contract-v<N>.md`
- 起始 SHA：<base-sha>（已核对一致 / 不符已停止）

## 候选

- 候选 SHA：<candidate-sha>
- 父提交：<parent-sha>
- 提交标题：<subject>
- 精确修改文件：
  - <path：改动摘要>

## 快速验证记录

| 命令 | 首次结果 | 修复后结果 |
|---|---|---|
| `python -m pytest <用例>` | <exit code / 摘要> | <如适用> |

首次失败记录（如有）：命令、退出码、错误摘要、当时 SHA。

## 未执行项（移交 Evidence Runner / 人工）

- <长测试 / 构建 / GUI / 人工项>

## 已知风险、未完成项与范围外发现

- <逐条列出；范围外发现只报告不处理>

## 冻结声明

未 amend、未 rebase、未 push；候选已冻结，等待独立 Checker 对 <candidate-sha> 验收。
