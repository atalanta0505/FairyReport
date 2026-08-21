# 任务合同 V2-T8 v2 — 范围增补：@tauri-apps/cli（第 2 轮验收基线）

- 状态：READY_FOR_MAKER（产品负责人 2026-08-21 批准方案 B："批准"）
- 变更说明：v1 第 1 轮 Checker PASS（锁定 `a10e900605ace1d226a892ffe5d3237bd913439d`），但 B 级人工验证发现 `npm run tauri dev` 报 `'tauri' 不是内部或外部命令` —— `desktop/package.json` 仅含 `@tauri-apps/api`（前端绑定），缺 `@tauri-apps/cli`（v1 §7 "tauri" 被理解为运行时绑定，漏 CLI）。v2 将该窄修复合法化；其余条款不变，v1 保留作历史。
- 产品决定来源：2026-08-21 产品负责人对"项目完整性方案 B"的明确批准。
- 精确起始 SHA：本合同提交后的 master HEAD
- 工作树门禁：`git status --short` 必须干净

## 1. 唯一主要变化

`desktop/package.json` devDependencies 增补 `@tauri-apps/cli`（major=2，与 tauri crate 2 / `@tauri-apps/api ^2.1.0` 对齐），使 `npm run tauri dev` 开箱可用。**无任何其他行为变化。**

## 2. 明确不做

- 不改 `desktop/src/**`、`desktop/src-tauri/**` 任何源码与配置
- 不改测试与验收期望（vitest 12 例保持原样）
- 不引入 @tauri-apps/cli 之外的任何依赖
- 不触碰 engine/**、backend/**、根目录产品文件

## 3. 实现导航

- `cd desktop && npm install -D @tauri-apps/cli@^2`
- `package.json` 的 `"tauri": "tauri"` 脚本已存在，无需改动
- `package-lock.json` 锁定精确版本（随 install 自动生成）

## 4. 允许修改

- `desktop/package.json`、`desktop/package-lock.json`
- `docs/dev-flow/tasks/V2-T8/**`

## 5. 禁止修改

- 上述以外一切文件（含 desktop/src/**、desktop/src-tauri/**、.gitignore、engine/**、backend/**、generic_knowledge/**、.opencode/、AGENTS.md）

## 6. 验收标准

- [ ] `git diff <起始SHA>..<候选SHA>` 仅 `desktop/package.json` + `desktop/package-lock.json`
- [ ] `@tauri-apps/cli` major 版本 = 2；无清单外其他新依赖
- [ ] `npm run tauri -- --version` 正常输出版本号
- [ ] v1 §9 三项仍全绿：`npx vitest run`（12 passed）、`cargo check`（desktop/src-tauri）、`npx vue-tsc --noEmit`
- [ ] B 级人工三项（真实启动登录/引擎健康/设置持久化）改对本轮新候选 SHA 执行

## 7. 快速验证（按顺序）

1. `npm run tauri -- --version`（workdir=desktop）
2. `npx vitest run`（workdir=desktop）
3. `cargo check`（workdir=desktop/src-tauri）
4. `npx vue-tsc --noEmit`（workdir=desktop）

## 8. 停止条件

- 基线/工作树不符；越界；同一失败两次；
- npm install 产生两文件之外的变更（如源码被意外改动）→ 停止报告；
- npm 源/网络异常两次尝试无解 → 停止报告。

## 9. 候选提交与完成说明

- 候选只含 `desktop/package.json` + `desktop/package-lock.json`
- 完成说明写到 `docs/dev-flow/tasks/V2-T8/rounds/02/maker-completion.md`，单独提交
- 不 amend、不 rebase、不 push

## 10. 已知基线失败

- 无。
