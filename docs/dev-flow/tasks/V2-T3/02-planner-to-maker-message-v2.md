# 致 Maker 的转发消息 V2-T3 v2（架构 C 重制版）

你是当前唯一可写 Maker。

工作目录：D:\Repo\FairyReport_lite
精确起始 SHA：本合同提交后的 master HEAD（开工前 git rev-parse HEAD 核实，工作树须干净）
有效合同：docs/dev-flow/tasks/V2-T3/01-planner-task-contract-v2.md（注意是 v2；v1 已作废）

唯一主要行为：本地引擎（engine/，FastAPI，仅 127.0.0.1）可创建/列出/删除项目，按本地文件路径摄取资料（docx/xlsx/csv/md/txt）完成解析-分块-向量化入库，可列出资料并按来源删除（文件与向量同步删除）。

实现导航：
- 只读参考根目录 pipeline.py / kb.py / converters/ / config.py；移植而非 import
- 新建 engine/（独立自洽，不 import backend/ 与根目录模块）：app/main.py、config.py、db.py、models.py、projects/router.py、materials/{router,converters,chunking,vectorstore}.py、embedding.py
- 数据布局：ENGINE_DATA_DIR（默认 %LOCALAPPDATA%/FairyReport）/projects/<project>/files|vector
- 嵌入：fastembed paraphrase-multilingual-MiniLM-L12-v2，封装可打桩；测试用确定性假向量，不下载模型、不联网
- 语义：路径不存在/扩展名非法 → 4xx；重复摄取 upsert 覆盖；无认证（本机服务）

允许修改：
- engine/**、.gitignore（如需）、docs/dev-flow/tasks/V2-T3/**

禁止修改：
- backend/**（T1/T2 验收产物）、根目录现有产品文件、steps/、components/、converters/、generic_knowledge/、根 requirements.txt、.opencode/、AGENTS.md

快速验证顺序：
1. python -m pytest engine/tests -q
2. python -m pytest backend/tests -q（回归守卫，30 例须保持全绿）
3. python -c "from engine.app.main import app"

停止条件：
- 基线/工作树不符；需要新依赖；越界；同一失败两次；
- fastembed 与 Python 3.14 不兼容两次尝试无解 → 停止报告，不擅自换方案。

进度纪律：每完成一个阶段报告"已完成/当前在做/异常/是否仍在合同内"；预计超 3 分钟的命令不执行，标记移交。

完成时：
1. 只提交 engine/**（含小型测试 fixture）；
2. 创建本地候选提交；
3. 不 amend、不 rebase、不 push；
4. 按模板写完成说明到 docs/dev-flow/tasks/V2-T3/rounds/（轮次目录编号按合同 §12 核实后选择）；
5. 冻结工作树并交回。
