# 致 Maker 的转发消息 V2-T5 v1

你是当前唯一可写 Maker。

工作目录：D:\Repo\FairyReport_lite
精确起始 SHA：本合同提交后的 master HEAD（开工前核实，工作树须干净）
有效合同：docs/dev-flow/tasks/V2-T5/01-planner-task-contract-v1.md

唯一主要行为：引擎凭请求携带的 llm_config（用户自带 Key，不存储）生成大纲、流式写作章节（双源 RAG + 字数预算 + 适用时技术分析框架）、技术审阅、修订，并管理章节提示；引用格式与现版一致。

实现导航：
- 只读移植根目录 outline.py / writer.py / hint_store.py / ref_manager.py / config.py 提示词资产（中文提示词原文不改写）
- 新建 engine/app/writing/：llm_client.py（httpx 直连 OpenAI 兼容，1+3 重试，5xx/超时→502/504，key 不落盘、日志脱敏）、templates_loader.py（读已安装通用包模板，未装→409）、outline.py、writer.py、hints.py、refs.py、router.py
- 端点：POST /writing/outline、/writing/chapter（stream SSE）、/writing/review、/writing/revise、/writing/hints（存/取）；llm_config 缺字段→422
- RAG：engine materials vectorstore + generic collection，【源:x】/[Z] 格式同 kb.py
- 测试：LLM MockTransport 打桩（含流式 chunks）+ 嵌入 stub；覆盖合同 §8 全部；不联网

允许修改：
- engine/**、docs/dev-flow/tasks/V2-T5/**、.gitignore（如需）

禁止修改：
- backend/**、根目录产品文件、generic_knowledge/**、steps/、components/、converters/、根 requirements.txt、.opencode/、AGENTS.md；既有测试不得删除或放宽

快速验证顺序：
1. python -m pytest engine/tests backend/tests -q（66 回归须全绿 + 新增）
2. python -c "from engine.app.main import app"

停止条件：
- 基线/工作树不符；新依赖；越界；同一失败两次；提示词移植两难 → 停止报告，不擅自简化。

进度纪律：每阶段报告"已完成/当前在做/异常/是否仍在合同内"；超 3 分钟命令不执行，标记移交。

完成时：
1. 只提交 engine/**；
2. 创建本地候选提交；
3. 不 amend、不 rebase、不 push；
4. 完成说明写到 docs/dev-flow/tasks/V2-T5/rounds/01/maker-completion.md；
5. 冻结并交回。
