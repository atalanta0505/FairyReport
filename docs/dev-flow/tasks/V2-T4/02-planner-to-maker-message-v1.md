# 致 Maker 的转发消息 V2-T4 v1

你是当前唯一可写 Maker。

工作目录：D:\Repo\FairyReport_lite
精确起始 SHA：本合同提交后的 master HEAD（开工前 git rev-parse HEAD 核实，工作树须干净）
有效合同：docs/dev-flow/tasks/V2-T4/01-planner-task-contract-v1.md

唯一主要行为：引擎可凭服务器 URL+JWT 下载并安装通用知识包（sha256 校验、原子安装），安装后可本地检索；服务器凭 JWT 提供 manifest 与下载。

实现导航：
- 包格式 v1：zip（manifest.json + templates/ + vector_db/ chroma 目录，collection=generic_kb）
- 构建脚本 engine/tools/build_generic_pack.py：读根目录 generic_knowledge/（只读），文献走 engine chunking，嵌入默认真实 fastembed / --stub 假向量，打 zip + sha256
- backend 新增 pack/router.py：GET /api/pack/manifest、GET /api/pack/download（JWT 保护，FileResponse，PACK_DIR 配置，缺失 404）
- engine 新增 generic/：GET /generic/status、POST /generic/update（server_url+token，下载→校验→原子解压切换→加载）、GET /generic/query（未装 404；嵌入可注入）
- 测试：--stub 建包 + MockTransport 假下发；覆盖正常/篡改拒绝/未装 404/幂等/401/404；不联网、不下载真实模型
- 回归：engine 20 + backend 30 全绿

允许修改：
- engine/**、backend/**（仅新增 pack 端点与配置）、.gitignore（如需）、docs/dev-flow/tasks/V2-T4/**

禁止修改：
- 根目录产品文件、generic_knowledge/**（只读源）、steps/、components/、converters/、根 requirements.txt、.opencode/、AGENTS.md；既有测试不得删除或放宽

快速验证顺序：
1. python -m pytest engine/tests backend/tests -q
2. 两个 main 的 import 冒烟

停止条件：
- 基线/工作树不符；新依赖；越界；同一失败两次；Windows 文件锁致原子替换两次无解 → 停止报告。

进度纪律：每阶段报告"已完成/当前在做/异常/是否仍在合同内"；超 3 分钟命令不执行，标记移交。

完成时：
1. 只提交 engine/** 与 backend/**；
2. 创建本地候选提交；
3. 不 amend、不 rebase、不 push；
4. 完成说明写到 docs/dev-flow/tasks/V2-T4/rounds/01/maker-completion.md；
5. 冻结并交回。
