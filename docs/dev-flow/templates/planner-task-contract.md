# 任务合同 <TASK-ID> v<N>

- 状态：DRAFT / READY_FOR_MAKER / MAKING / READY_FOR_CHECKER / ACCEPTED / CHANGES_REQUESTED
- 产品决定来源：<用户原话或 00-product-decision 引用>
- 精确起始 SHA：<base-sha>
- 工作树门禁：`git status --short` 必须干净（未跟踪用户数据除外，且不得纳入提交）

## 1. 背景与目标

<为什么做；解决什么问题>

## 2. 唯一主要行为变化

<本切片只改变这一个行为>

## 3. 明确不做

- <容易顺手扩张的内容，逐条列出>

## 4. 实现导航

- 入口/符号：<文件、函数、类>
- 调用链：<关键路径>
- 测试位置：<现有或需新建的测试文件>

## 5. 允许修改

- <paths>

## 6. 禁止修改

- <paths / 依赖 / 数据结构 / UI / 配置等>

## 7. 约束

- 数据/接口/安全/兼容性约束（含 .env 凭据纪律）

## 8. 验收标准

- [ ] <可验证标准 1>
- [ ] <可验证标准 2>

## 9. Maker 快速测试（按顺序）

1. `python -m pytest <目标用例>`
2. <其他快速命令>

## 10. Evidence Runner 分级验证计划

- <全量回归 / 构建 / GUI 人工项，标注由谁在何时执行>

## 11. GUI / 人工验收项

- <Streamlit 操作步骤与预期，或"无">

## 12. 候选提交与完成说明要求

- 本地候选提交，记录精确 SHA；不 amend、不 rebase、不 push；
- 完成说明按 `templates/maker-completion.md` 写入 `tasks/<TASK-ID>/rounds/<NN>/`。

## 13. 停止条件

- 基线或工作树不符；必须越界修改；需安装依赖；同一失败两次；需 GUI/凭据/权限/产品决定。

## 14. 已知基线失败

- <基线即存在的失败及判定方式，或"无">
