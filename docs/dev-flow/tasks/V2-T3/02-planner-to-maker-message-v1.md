# 致 Maker 的转发消息 V2-T3 v1

你是当前唯一可写 Maker。

工作目录：D:\Repo\FairyReport_lite
精确起始 SHA：本合同提交后的 master HEAD（开工前 git rev-parse HEAD 核实，工作树须干净）
有效合同：docs/dev-flow/tasks/V2-T3/01-planner-task-contract-v1.md

唯一主要行为：登录用户可创建项目、上传资料（docx/xlsx/csv/md/txt），后端解析-分块-向量化入库；可列出资料、按来源删除（向量同步删除）。

实现导航：
- 只读参考根目录 pipeline.py（分块）、kb.py（chromadb 模式）、converters/（格式转换思路）；移植而非 import
- 新建 backend/app/materials/：router.py（项目 CRUD + 上传/列表/删除）、converters.py、chunking.py、vectorstore.py
- 向量库：chromadb 每项目独立目录；嵌入 fastembed paraphrase-multilingual-MiniLM-L12-v2；单测打桩嵌入（确定性假向量），不下载真实模型、不联网
- 存储：BACKEND_DATA_DIR（默认 ./backend_data，gitignore）；权限隔离（他人项目 404）
- 语义：白名单外扩展名 422；>50MB 413；未认证 401；重复上传 upsert 覆盖

允许修改：
- backend/**、.gitignore（如需）、docs/dev-flow/tasks/V2-T3/**

禁止修改：
- 根目录现有产品文件、steps/、components/、converters/、generic_knowledge/、根 requirements.txt、.opencode/、AGENTS.md

快速验证顺序：
1. python -m pytest backend/tests -q（T1/T2 的 30 例保持全绿 + 新增用例）
2. python -c "from backend.app.main import app"

停止条件：
- 基线/工作树不符；需要清单外依赖（chromadb/fastembed/python-docx/docx2txt/openpyxl/markdownify 之外）；越界；同一失败两次；
- fastembed 与 Python 3.14 不兼容两次尝试无解 → 停止报告，不擅自换方案。

完成时：
1. 只提交 backend/**（含小型测试 fixture）；
2. 创建本地候选提交；
3. 不 amend、不 rebase、不 push；
4. 按模板写完成说明到 docs/dev-flow/tasks/V2-T3/rounds/01/maker-completion.md；
5. 冻结工作树并交回。
