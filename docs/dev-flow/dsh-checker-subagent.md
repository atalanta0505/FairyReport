# DSH 环境：Checker 子代理实例（V2-T50 §7）

- 状态：已注入 DSH profile patch（2026-10-06），**待重启后生效**
- 位置：`%USERPROFILE%\.dsh\profiles\desktop\cordis.patch.yml`（DSH 环境配置，**不属于本仓库**）
- 备份：`cordis.patch.yml.bak-v2t50-2026-10-06T06-58-17-306Z`（同目录）

## 1. 它解决什么问题

PMC 的"独立验收"此前只是文档条款：Maker 与 Checker 由同一个模型（deepseek-flash）在人工切换的两个会话里扮演，独立性既不可机制保证，也不可审计。本配置把该角色落成运行时机制。

## 2. 注入内容

在 `preset-standard` 与 `preset-ptc` 的 `delegation` 组内各插入一行（`- id: tool-checker`）：

```yaml
- id: tool-checker
  name: '@deepseek-ai/dsh-tool-subagent'
  config:
    provider: spawn
    toolName: checker
    backgroundMode: one-shot
    maxDepth: 0
    agentOptions:
      provider: deepseek-official
      model: deepseek-v4-pro
    persona: |
      You are the Checker of this repository's Planner-Maker-Checker flow.
      Product code is read-only for you: never modify, create or delete tracked files.
      Verify only the exact candidate SHA you are given; never treat the Maker's summary as evidence.
      Re-run scripts/verify.ps1 yourself and report per-gate status with the exact command and observed result.
      End your report with git rev-parse HEAD and git status --short; a changed worktree is a FAIL.
      FAIL reports blockers only; PASS locks the SHA.
    toolFilter:
      deny:
        - write
        - edit
```

| 参数 | 值 | 作用 |
|---|---|---|
| `agentOptions.model` | `deepseek-v4-pro` | 与 Maker（`deepseek-flash`）**强制不同模型**，不依赖当场手选，且可审计 |
| `toolFilter.deny` | `write`, `edit` | 关掉直接改文件的工具；被过滤的工具从子代理提示词中消失且执行被拒 |
| `maxDepth` | `0` | Checker 不能再往下委派，杜绝套娃 |
| `backgroundMode` | `one-shot` | 前台等待，符合"一轮一验" |
| `persona` | 见上 | 只读、只认精确 SHA、报告前后 git 状态 |

写入方式是**按 id 覆盖 bundle 里的 preset 行**——这正是 preset 文件自身注释记载的 Web 编辑器保存路径（"Edits saved from the Web editor override this row's `config.plugins` by id from the profile patch"）。除新增的 `tool-checker` 行外，plugins 列表与 bundle 逐字一致。

## 3. 生效与回滚

- **生效**：重启 DSH 桌面端（profile 在启动时组装），然后在新会话中确认工具列表出现 `checker`。
- **回滚**：`Copy-Item "<备份文件>" "<原文件>" -Force`，再重启。
- 若启动异常，先回滚再排查：本次变更已通过 YAML 解析与结构断言（两个 preset 的 delegation 组各 10 个子行，含 `tool-checker`），但**运行时组装未经验证**（无法在不重启的前提下验证）。

## 4. 已知局限

1. `toolFilter` 只能按工具名屏蔽，而 `pwsh` 本身可以写文件——所以这不是硬隔离。补偿机制：Checker 报告必须以 `git rev-parse HEAD` 与 `git status --short` 开头和结尾，工作树变化即判 FAIL；`scripts/verify.ps1` 也会在结果里带 `worktreeStable`。
2. `deepseek-v4-pro` 单价高于 `deepseek-flash`，成本随验收轮次上升；建议只对档 2/档 3 切片使用。
3. 该配置不随仓库版本管理；DSH 升级若改动 bundle preset 结构，需按 §2 的规则重新生成覆盖行。

## 5. 与其他 scheme 的关系

- 本轮（V2-T50）只交付 `scripts/verify.ps1` 与文档修正；`checker` 的**首次实跑**留给下一轮，届时用它验收 V2-T50 之后的第一个切片，即可同时验证该机制。
