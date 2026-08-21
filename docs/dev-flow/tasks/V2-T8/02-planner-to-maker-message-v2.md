# 致 Maker 的转发消息 V2-T8 v2

你是当前唯一可写 Maker。

工作目录：D:\Repo\FairyReport_lite
精确起始 SHA：本合同提交后的 master HEAD（开工前核实 `git rev-parse HEAD` 与 `git status --short` 干净；起始 SHA 即合同 v2 提交）
有效合同：docs/dev-flow/tasks/V2-T8/01-planner-task-contract-v2.md（v2；v1 作历史，第 1 轮候选 a10e900 已 PASS）

唯一主要变化：desktop/package.json devDependencies 增补 @tauri-apps/cli（major=2），使 `npm run tauri dev` 开箱可用。无任何其他变化。

实现导航：
- `cd desktop && npm install -D @tauri-apps/cli@^2`（仅此一条产品变更；`"tauri": "tauri"` 脚本已存在，不改）
- package-lock.json 随 install 自动生成

允许修改：
- desktop/package.json、desktop/package-lock.json、docs/dev-flow/tasks/V2-T8/**

禁止修改：
- 上述以外一切（含 desktop/src/**、desktop/src-tauri/**、.gitignore、engine/**、backend/**、根目录产品文件、.opencode/、AGENTS.md）

快速验证顺序（合同 v2 §7）：
1. `npm run tauri -- --version`（workdir=desktop，须输出版本号）
2. `npx vitest run`（workdir=desktop，12 passed）
3. `cargo check`（workdir=desktop/src-tauri）
4. `npx vue-tsc --noEmit`（workdir=desktop）

停止条件：
- 基线/工作树不符；越界；同一失败两次；npm install 产生两文件之外的变更；npm 源/网络异常两次无解 → 停止报告。

进度纪律：每阶段报告"已完成/当前在做/异常/是否仍在合同内"；超 3 分钟命令不执行，标记移交。

完成时：
1. 候选提交只含 desktop/package.json + desktop/package-lock.json；
2. 不 amend、不 rebase、不 push；
3. 完成说明写到 docs/dev-flow/tasks/V2-T8/rounds/02/maker-completion.md 并单独提交；
4. 冻结并交回。
