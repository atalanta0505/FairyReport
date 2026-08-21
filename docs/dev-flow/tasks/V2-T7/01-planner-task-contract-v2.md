# 任务合同 V2-T7 v2 — 范围增补（第 2 轮验收基线）

- 状态：READY_FOR_CHECKER（第 2 轮）
- 变更说明：v1 第 1 轮 FAIL，阻断项 = 提交 f774f39 修改 engine/** 越界。v2 将该窄修复合法化并修正导航措辞；其余条款不变。v1 保留作历史。
- 产品决定来源：2026-08-20 产品负责人对窄修复的明确指令（"修复"）；原因：新版 fastembed 要求完整模型 ID，同模型、零质量变化
- 代码候选（不变）：`0dab11d`；仓库 diff 范围：`21b04dc..0dab11d` + 完成说明提交（本轮新增）

## 1. v2 增补条款

- §5 允许修改增补：`engine/app/config.py`、`engine/app/embedding.py` —— **仅限**嵌入模型 ID 补 `sentence-transformers/` 前缀（共 3 行：config 默认值、FastEmbedEmbedder 默认参数、模块 docstring）；engine/** 其余仍禁止
- §4 导航修正：Dockerfile 基础镜像为 `python:3.14-slim`（与本地 Python 3.14 及依赖兼容一致；v1 误写 3.12）；compose 环境变量命名 `SMTP_*`（与 T1 config 字段名一致）
- §8 增补验收条目：
  - [ ] f774f39 的 diff 逐行核实仅为上述 3 行前缀修改，无其他 engine 变更
  - [ ] 前缀修复后 101 测试全绿（已两次验证）
  - [ ] 真实建包与检索同模型一致性：pack version=v-e91b59bddd4f 由前缀后模型建成（证据见第 1 轮报告与 E2E sha256 匹配）
  - [ ] `rounds/01/maker-completion.md` 已提交（补第 1 轮非阻断项）

## 2. 不变条款

v1 §1-§3、§7-§14 全部维持；第 1 轮已通过的验收条目（health/注册 E2E/pack JWT/401/内存/现有服务）由第 2 轮 Checker 抽查复核。

## 3. 两轮规则说明

第 1 轮 FAIL 为范围文档问题，非实现缺陷；v2 为范围合法化，不触发"停止自动修复"升级。若第 2 轮再 FAIL，交产品负责人再决策。
