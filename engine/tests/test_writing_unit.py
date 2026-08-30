"""写作链路单元测试：refs/writer/llm_client（不联网、不需通用包）。"""
import httpx
import pytest

from engine.app.writing import llm_client as llm_mod
from engine.app.writing.llm_client import LLMClient, LLMError, mask_key
from engine.app.writing.refs import strip_fabricated_labels
from engine.app.writing.writer import (
    _allocate_section_budgets,
    _build_section_quota_block,
    _count_chinese_chars,
    _count_content_chars,
    _parse_outline_hierarchy,
    _strip_markdown_headings,
    _strip_markdown_tables,
    parse_tech_review_result,
)


# ── refs.strip_fabricated_labels ──
def test_strip_fabricated_labels_keeps_valid_strips_fabricated():
    rag = "【源:policy.md】: 政策内容\n\n【网:示例】: 网页内容"
    body = "正文【源:policy.md】引用，【源:fake.docx】编造标签。"
    cleaned = strip_fabricated_labels(body, rag)
    assert "【源:policy.md】" in cleaned  # 保留有效
    assert "【源:fake.docx】" not in cleaned  # 剥离编造
    assert "[Z]" not in cleaned  # 彻底消灭孤立 [Z]


def test_strip_fabricated_labels_empty_rag():
    cleaned = strip_fabricated_labels("正文【源:fake.docx】", "")
    assert "【源:fake.docx】" not in cleaned
    assert "[Z]" not in cleaned


# ── writer._allocate_section_budgets（移植等价）──
def test_allocate_section_budgets_distributes_by_h3():
    hierarchy = {
        "chapter_title": "第二章 测试",
        "h2_sections": [
            {"title": "2.1 A", "level": 2, "h3_subsections": [
                {"title": "2.1.1 a", "level": 3},
                {"title": "2.1.2 b", "level": 3},
            ]},
            {"title": "2.2 B", "level": 2, "h3_subsections": [
                {"title": "2.2.1 c", "level": 3},
            ]},
        ],
    }
    allocation = _allocate_section_budgets(hierarchy, 5000)
    assert allocation["total_allocated"] == 5000
    h2s = allocation["h2_sections"]
    # 3 个 H3，per_h3_raw=1666.67 → 取整 1650
    assert h2s[0]["budget"] == 3350  # 1650*2 + 50 余数
    assert h2s[1]["budget"] == 1650
    assert h2s[0]["h3_subsections"][0]["budget"] == 1700  # 1650+50
    assert h2s[0]["h3_subsections"][1]["budget"] == 1650
    assert h2s[1]["h3_subsections"][0]["budget"] == 1650


def test_allocate_section_budgets_no_h3_split_by_h2():
    hierarchy = {
        "chapter_title": "第一章",
        "h2_sections": [
            {"title": "1.1 A", "level": 2, "h3_subsections": []},
            {"title": "1.2 B", "level": 2, "h3_subsections": []},
        ],
    }
    allocation = _allocate_section_budgets(hierarchy, 2000)
    assert allocation["total_allocated"] == 1000 * 2
    assert all(h2["budget"] == 1000 for h2 in allocation["h2_sections"])


def test_parse_outline_hierarchy_extracts_h2_h3():
    outline = (
        "# 第一章 概述\n## 1.1 项目概况\n## 1.2 编制依据\n# 第二章 背景\n## 2.1 建"
    )
    h = _parse_outline_hierarchy(outline, 1)
    assert h["chapter_title"] == "第一章 概述"
    assert len(h["h2_sections"]) == 2
    assert h["h2_sections"][0]["title"] == "1.1 项目概况"


def test_build_section_quota_block_unconstrained_depth_advice():
    hierarchy = {
        "chapter_title": "第二章 测试",
        "h2_sections": [
            {"title": "2.1 A", "level": 2, "h3_subsections": [
                {"title": "2.1.1 a", "level": 3, "budget": 1700}
            ], "budget": 1700},
        ],
    }
    block = _build_section_quota_block(hierarchy, {"h2_sections": hierarchy["h2_sections"], "total_allocated": 1700})
    assert "结构参考与小节篇幅建议" in block
    assert "2.1 A" in block
    assert "1,700" in block  # 逗号格式化
    assert "建议深度论证，参考篇幅约" in block
    assert "杜绝空洞简略与内容缩水" in block
    # 验证句数硬控制已彻底移除
    assert "句话以内" not in block
    assert "以中文句号『。』为准计" not in block
    assert "达到句数上限即行收尾" not in block


def test_pure_chinese_reasoning_constraint_in_prompts():
    from engine.app.writing.outline import OutlineGenerator, _build_outline_system_prompt
    from engine.app.writing.prompts import (
        COMPLIANCE_REVIEW_SYSTEM_PROMPT,
        FAST_REVIEW_SYSTEM_PROMPT,
        FULL_EXPERT_REVIEW_SYSTEM_PROMPT,
        NUMERICAL_REVIEW_SYSTEM_PROMPT,
        ORDER_SYSTEM_PROMPT,
        REASONING_CHINESE_DEFENSE_PROMPT,
        TECH_REVIEW_SYSTEM_PROMPT,
        _BASE_WRITING_PROMPT,
        _HINT_SYSTEM_PROMPT,
        _MODIFY_SYSTEM_PROMPT,
        _OUTLINE_BASE_PROMPT,
    )
    from engine.app.writing.writer import ChapterWriter

    # 1. 核心防御常量硬性规范核验
    assert "【思考链与语言规范（最高优先级·纯中文绝对纯化防线）】" in REASONING_CHINESE_DEFENSE_PROMPT
    assert "100% 使用规范中文进行投资项目与工程咨询专业论证" in REASONING_CHINESE_DEFENSE_PROMPT
    assert "绝对禁止夹杂任何英文思考句子、英文短语或英文分析单词" in REASONING_CHINESE_DEFENSE_PROMPT
    assert "'Okay', 'Let me', 'First', 'Next', 'I should', 'We need to'" in REASONING_CHINESE_DEFENSE_PROMPT

    # 2. 验证全部 10 个系统提示词资产均包含最高优先级纯中文绝对纯化防线
    all_system_prompts = [
        _BASE_WRITING_PROMPT,
        _OUTLINE_BASE_PROMPT,
        ORDER_SYSTEM_PROMPT,
        _HINT_SYSTEM_PROMPT,
        _MODIFY_SYSTEM_PROMPT.format(word_constraint="保持原文规模"),
        FAST_REVIEW_SYSTEM_PROMPT,
        FULL_EXPERT_REVIEW_SYSTEM_PROMPT,
        COMPLIANCE_REVIEW_SYSTEM_PROMPT,
        NUMERICAL_REVIEW_SYSTEM_PROMPT,
        TECH_REVIEW_SYSTEM_PROMPT,
    ]
    for prompt_text in all_system_prompts:
        assert REASONING_CHINESE_DEFENSE_PROMPT in prompt_text

    # 3. 验证 Outline 生成与排序的用户 Prompt 注入
    outline_gen = OutlineGenerator(llm=None, report_type="可行性研究报告")
    order_prompt = (
        f"已生成以下大纲：\n\n# 第一章 概述\n\n"
        f"请按从上到下的顺序为每个「第X章」编号（1,2,3...），"
        f"然后建议一个最优写作顺序。\n"
        f"只返回逗号分隔的数字序列，如 2,3,4,1,5\n\n"
        f"{REASONING_CHINESE_DEFENSE_PROMPT}"
    )
    assert REASONING_CHINESE_DEFENSE_PROMPT in order_prompt

    # 4. 验证 ChapterWriter 编写、修订、审阅等用户 Prompt 注入
    writer = ChapterWriter(llm=None, report_type="可行性研究报告")
    write_prompt, _ = writer._build_chapter_write_args(
        chapter_title="第一章 概述",
        outline_md="# 第一章 概述",
        predecessor_chapters={},
        rag_context="",
        topic="数字水利",
    )
    assert REASONING_CHINESE_DEFENSE_PROMPT in write_prompt

    modify_prompt, _ = writer._build_modify_args(
        original_content="原文内容",
        instruction="修改第1段",
        chapter_budget=2000,
    )
    assert REASONING_CHINESE_DEFENSE_PROMPT in modify_prompt

    review_prompt, _ = writer._build_expert_review_args(
        chapter_title="第一章 概述",
        chapter_text="正文段落",
        mode="fast",
    )
    assert REASONING_CHINESE_DEFENSE_PROMPT in review_prompt


# ── writer.parse_tech_review_result ──
def test_parse_tech_review_result_needs_supplement():
    # 使用解析器期望的冒号格式（移植自现版正则）
    raw = (
        "校核结果：需补充\n\n"
        "原因：缺少关键指标\n\n"
        "详情：未给出能耗指标\n\n"
        "建议：补充单位能耗\n\n"
        "资料清单：\n- 项目规模：1000吨\n- 技术路线：待定\n"
    )
    r = parse_tech_review_result(raw)
    assert r["status"] == "需补充"
    assert r["reason"] == "缺少关键指标"
    assert "能耗指标" in r["details"]
    assert r["parse_error"] is None
    assert len(r["data_gap_checklist"]) == 2


def test_parse_tech_review_result_pass():
    raw = "校核结果：通过\n\n原因：指标齐全"
    r = parse_tech_review_result(raw)
    assert r["status"] == "通过"
    assert r["data_gap_checklist"] == []


def test_parse_tech_review_result_empty():
    r = parse_tech_review_result("")
    assert r["status"] == "不适用"
    assert r["parse_error"]


# ── llm_client 脱敏 ──
def test_mask_key():
    assert mask_key("sk-abcdef123456") == "sk***3456"
    assert mask_key("") == "(empty)"
    assert mask_key("short") == "sh***"


# ── llm_client 502/504/重试 ──
@pytest.fixture
def fast_retries(monkeypatch):
    monkeypatch.setattr(llm_mod, "RETRY_DELAYS", [0, 0, 0])


def _make_client():
    return LLMClient({"api_key": "sk-test-123456", "base_url": "http://llm.stub/v1", "model": "m"})


def test_llm_chat_nonstream(fast_retries):
    stub_calls = []

    def handler(request):
        stub_calls.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello world"}}]})

    llm_mod.set_transport(httpx.MockTransport(handler))
    c = _make_client()
    assert c.chat("hi", system_prompt="sys") == "hello world"
    # 请求头含 Authorization 但不打印 key
    assert stub_calls[0].headers["authorization"].startswith("Bearer ")


def test_llm_chat_stream_iter(fast_retries):
    sse = "data: {\"choices\":[{\"delta\":{\"content\":\"段落\"}}]}\n\n" \
          "data: {\"choices\":[{\"delta\":{\"content\":\"内容\"}}]}\n\n" \
          "data: [DONE]\n\n"
    llm_mod.set_transport(httpx.MockTransport(lambda req: httpx.Response(
        200, text=sse, headers={"content-type": "text/event-stream"}
    )))
    c = _make_client()
    chunks = list(c.chat_stream_iter([{"role": "user", "content": "x"}], temperature=0.2))
    assert chunks == ["段落", "内容"]


def test_llm_502_on_upstream_5xx(fast_retries):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(500, text="upstream error")

    llm_mod.set_transport(httpx.MockTransport(handler))
    c = _make_client()
    with pytest.raises(LLMError) as ei:
        c.chat("hi")
    assert ei.value.status_code == 502
    assert len(calls) == 4  # 1 + 3 retries


def test_llm_504_on_timeout(fast_retries):
    def handler(request):
        raise httpx.ReadTimeout("stub timeout", request=request)

    llm_mod.set_transport(httpx.MockTransport(handler))
    c = _make_client()
    with pytest.raises(LLMError) as ei:
        c.chat("hi")
    assert ei.value.status_code == 504


def test_llm_4xx_not_retried(fast_retries):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(401, text="unauthorized")

    llm_mod.set_transport(httpx.MockTransport(handler))
    c = _make_client()
    with pytest.raises(LLMError) as ei:
        c.chat("hi")
    assert ei.value.status_code == 401
    assert len(calls) == 1  # 4xx 非 429 不重试


def test_llm_missing_config_raises_422():
    with pytest.raises(LLMError) as ei:
        LLMClient({"api_key": "", "base_url": "http://x", "model": "m"})
    assert ei.value.status_code == 422


# ── writer.normalize_chapter_markdown ──
def test_normalize_chapter_markdown_heading_separation_and_skeleton():
    from engine.app.writing.writer import normalize_chapter_markdown

    # 1. 骨架匹配与无标点粘连中文断行
    raw = "### 1.4.1 主要研究结论经系统论证，本项目符合国家重大基础设施建设规划。"
    sk = "# 第一章 概述\n### 1.4.1 主要研究结论"
    res = normalize_chapter_markdown(raw, skeleton=sk)
    assert res == "### 1.4.1 主要研究结论\n\n经系统论证，本项目符合国家重大基础设施建设规划。"

    # 2. 标点紧随拆分
    raw2 = "### 1.1.1 建设地点：本项目位于武汉市。"
    assert normalize_chapter_markdown(raw2) == "### 1.1.1 建设地点\n\n本项目位于武汉市。"

    # 3. 标题与加粗/表格粘连拆解
    raw3 = "### 1.1.2 编制依据**发改委文件**"
    assert normalize_chapter_markdown(raw3) == "### 1.1.2 编制依据\n\n**发改委文件**"

    # 4. 表格单行 || 拆分
    raw4 = "| 指标 | 数值 || --- | --- || 投资 | 5000 |"
    norm4 = normalize_chapter_markdown(raw4)
    assert "|\n|" in norm4

    # 5. 标题与正文单换行补空行
    raw5 = "### 1.1.3 建设内容\n本项目建设内容包含泵站与涵闸。"
    assert normalize_chapter_markdown(raw5) == "### 1.1.3 建设内容\n\n本项目建设内容包含泵站与涵闸。"


# ── rag.query_rag 智能检索词提炼 ──
def test_query_rag_composite_query(monkeypatch):
    from engine.app.writing.rag import query_rag
    from engine.app.writing import web_search

    captured_web_query = []

    def stub_search(q, max_results=5):
        captured_web_query.append(q)
        return "【网:权威报告】\n  http://gov.cn\n  > 摘要"

    monkeypatch.setattr(web_search, "search_gov_web", stub_search)

    res = query_rag(
        project_name="汉江水利枢纽建设工程可行性研究报告",
        query_text="第二章 项目建设背景与生态保护规划符合性",
        include_generic=False,
        include_web=True,
        topic="生态防洪保护",
        report_name="汉江水利枢纽",
    )
    assert len(captured_web_query) == 1
    q = captured_web_query[0]
    assert "汉江水利枢纽" in q
    # 验证公文噪音已被剥离
    assert "可行性研究报告" not in q
    assert "第二章" not in q
    assert "【网:权威报告】" in res


# ── templates_loader.get_writing_order & reason ──
def test_get_writing_order_derivation_from_template(monkeypatch):
    from engine.app.writing import templates_loader as tmpl

    # 模拟可研报告 11 章模板（第 1 章与第 11 章为 is_summary）
    mock_tmpl = {
        "report_type": "可行性研究报告",
        "chapters": [
            {"seq": 1, "title": "第一章 概述", "is_summary": True},
            {"seq": 2, "title": "第二章 项目建设背景和必要性", "is_summary": False},
            {"seq": 3, "title": "第三章 需求分析", "is_summary": False},
            {"seq": 4, "title": "第四章 选址", "is_summary": False},
            {"seq": 5, "title": "第五章 建设方案", "is_summary": False},
            {"seq": 6, "title": "第六章 运营方案", "is_summary": False},
            {"seq": 7, "title": "第七章 投融资方案", "is_summary": False},
            {"seq": 8, "title": "第八章 影响效果", "is_summary": False},
            {"seq": 9, "title": "第九章 风险管控", "is_summary": False},
            {"seq": 10, "title": "第十章 研究结论及建议", "is_summary": False},
            {"seq": 11, "title": "第十一章 附表附图", "is_summary": True},
        ]
    }
    monkeypatch.setattr(tmpl, "load_template", lambda rt: mock_tmpl)

    order = tmpl.get_writing_order("可行性研究报告")
    assert order == [2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 11]

    reason = tmpl.get_writing_order_reason("可行性研究报告")
    assert "先完成背景、需求、选址、工程方案及投资等主体论证章节" in reason


def test_get_writing_order_explicit_config(monkeypatch):
    from engine.app.writing import templates_loader as tmpl

    mock_tmpl = {
        "report_type": "自定义报告",
        "writing_order": [3, 2, 1],
        "writing_order_reason": "自定义推荐顺序说明",
        "chapters": [
            {"seq": 1, "title": "第一章"},
            {"seq": 2, "title": "第二章"},
            {"seq": 3, "title": "第三章"},
        ]
    }
    monkeypatch.setattr(tmpl, "load_template", lambda rt: mock_tmpl)

    assert tmpl.get_writing_order("自定义报告") == [3, 2, 1]
    assert tmpl.get_writing_order_reason("自定义报告") == "自定义推荐顺序说明"


def test_get_writing_order_natural_fallback(monkeypatch):
    from engine.app.writing import templates_loader as tmpl

    monkeypatch.setattr(tmpl, "load_template", lambda rt: None)
    assert tmpl.get_writing_order("未知类型", total_chapters=5) == [1, 2, 3, 4, 5]
    assert "按照报告标准章节结构依次推进编写" in tmpl.get_writing_order_reason("未知类型")


def test_writer_build_prev_context_natural_order_and_lock():
    from engine.app.writing.writer import ChapterWriter

    writer = ChapterWriter(llm=None, report_type="可行性研究报告")
    predecessors = {
        "3": "第三章内容",
        "2": "第二章内容",
        "10": "第十章内容",
    }
    context = writer._build_prev_context(predecessors)
    # 应按 2, 3, 10 升序排列
    idx_2 = context.find("## 第 2 章")
    idx_3 = context.find("## 第 3 章")
    idx_10 = context.find("## 第 10 章")
    assert idx_2 != -1 and idx_3 != -1 and idx_10 != -1
    assert idx_2 < idx_3 < idx_10


def test_standard_three_line_table_rules_in_prompts_and_writer():
    from engine.app.writing.prompts import _BASE_WRITING_PROMPT
    from engine.app.writing.writer import _build_writing_system_prompt, ChapterWriter

    # 1. _BASE_WRITING_PROMPT 12 项规定动作三线表格检查
    assert "通用大纲 12 项规定动作标准三线表格强制规范" in _BASE_WRITING_PROMPT
    assert "主要技术经济指标表" in _BASE_WRITING_PROMPT
    assert "建设规模方案比选表" in _BASE_WRITING_PROMPT
    assert "场址方案比选表" in _BASE_WRITING_PROMPT
    assert "技术路线比选表" in _BASE_WRITING_PROMPT
    assert "关键设备比选表" in _BASE_WRITING_PROMPT
    assert "主要设备清单表" in _BASE_WRITING_PROMPT
    assert "工程方案比选表" in _BASE_WRITING_PROMPT
    assert "项目总投资与建设投资全要素估算表" in _BASE_WRITING_PROMPT
    assert "主要财务指标汇总表" in _BASE_WRITING_PROMPT
    assert "融资方案比选表" in _BASE_WRITING_PROMPT
    assert "债务清偿能力指标表" in _BASE_WRITING_PROMPT
    assert "风险评价与管控矩阵表" in _BASE_WRITING_PROMPT
    assert "对齐分隔线如 `| :--- | :---: | ---: |`" in _BASE_WRITING_PROMPT

    # 2. _build_writing_system_prompt 规则检查
    sys_prompt = _build_writing_system_prompt(report_type="可行性研究报告", chapter_title="第五章 建设方案")
    assert "12 项规定动作标准三线表" in sys_prompt

    # 3. ChapterWriter._build_chapter_write_args prompt 写作要求检查
    writer = ChapterWriter(llm=None, report_type="可行性研究报告")
    prompt, _ = writer._build_chapter_write_args(
        chapter_title="第一章 概述",
        outline_md="# 第一章 概述\n## 1.1 项目概况\n### 1.1.6 主要技术经济指标",
        predecessor_chapters={},
        rag_context="",
        topic="水利枢纽",
    )
    assert "12 项规定动作标准三线表格强制规范（最高优先级）" in prompt
    assert "严禁全篇纯文字堆砌" in prompt
    assert "内容深度与充实展开（极重要）" in prompt
    assert "全面展开实质性工程分析、技术论证" in prompt
    # 验证句数硬控制已彻底删除
    assert "句数与篇幅硬控制" not in prompt


def test_strip_markdown_tables_and_count_content_chars():
    md = (
        "# 第一章 概述\n\n"
        "## 1.1 项目概况\n\n"
        "### 1.1.1 建设地点\n\n"
        "本项目位于湖北省武汉市江夏区。\n\n"
        "### 1.1.6 主要技术经济指标\n\n"
        "| 序号 | 指标名称 | 单位 | 目标值 |\n"
        "| :--- | :---: | ---: | :--- |\n"
        "| 1 | 总库容 | 万m³ | 1500 |\n"
        "| 2 | 防洪标准 | 年一遇 | 100 |\n\n"
        "各项规划指标均符合发改委与水利行业编制规范要求。"
    )

    stripped = _strip_markdown_tables(md)
    assert "| 序号 |" not in stripped
    assert "| :--- |" not in stripped
    assert "| 1 |" not in stripped
    assert "本项目位于湖北省武汉市江夏区。" in stripped
    assert "各项规划指标均符合发改委与水利行业编制规范要求。" in stripped

    # 正文：
    # "本项目位于湖北省武汉市江夏区。" (15 中文/标点字符)
    # "各项规划指标均符合发改委与水利行业编制规范要求。" (24 中文/标点字符)
    # 共 15 + 24 = 39 字符
    wc = _count_content_chars(md)
    assert wc == 39


def test_ndrc_financial_table_prompt_full_elements():
    """验证发改委教材标准全要素财务报表强化提示词规范。"""
    from engine.app.writing.prompts import _BASE_WRITING_PROMPT
    from engine.app.writing.writer import _build_writing_system_prompt

    # 1. 验证基础提示词中的全要素财务报表要求
    assert "项目总投资与建设投资全要素估算表" in _BASE_WRITING_PROMPT
    assert "建筑工程费、设备及工器具购置费、安装工程费" in _BASE_WRITING_PROMPT
    assert "基本预备费、涨价预备费、建设期利息、流动资金" in _BASE_WRITING_PROMPT
    assert "主要财务指标汇总表" in _BASE_WRITING_PROMPT
    assert "FIRR" in _BASE_WRITING_PROMPT
    assert "FNPV" in _BASE_WRITING_PROMPT
    assert "ROI" in _BASE_WRITING_PROMPT
    assert "ROE" in _BASE_WRITING_PROMPT
    assert "利息备付率（ICR）" in _BASE_WRITING_PROMPT
    assert "偿债备付率（DSCR）" in _BASE_WRITING_PROMPT

    # 2. 验证写入系统提示词中的全要素规则
    sys_prompt = _build_writing_system_prompt(report_type="可行性研究报告", chapter_title="第七章 投资估算与财务分析")
    assert "项目总投资与建设投资估算表/分年度资金计划" in sys_prompt
    assert "主要财务指标汇总" in sys_prompt
    assert "债务清偿能力指标" in sys_prompt


