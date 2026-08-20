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
    _parse_outline_hierarchy,
    parse_tech_review_result,
)


# ── refs.strip_fabricated_labels ──
def test_strip_fabricated_labels_keeps_valid_replaces_fabricated():
    rag = "【源:policy.md】: 政策内容\n\n【网:示例】: 网页内容"
    body = "正文【源:policy.md】引用，【源:fake.docx】编造标签。"
    cleaned = strip_fabricated_labels(body, rag)
    assert "【源:policy.md】" in cleaned  # 保留有效
    assert "【源:fake.docx】" not in cleaned  # 剥离编造
    assert "[Z]" in cleaned  # 替换为 [Z]


def test_strip_fabricated_labels_empty_rag_noop():
    assert strip_fabricated_labels("正文【源:x】", "") == "正文【源:x】"


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


def test_build_section_quota_block_contains_budgets():
    hierarchy = {
        "chapter_title": "第二章 测试",
        "h2_sections": [
            {"title": "2.1 A", "level": 2, "h3_subsections": [
                {"title": "2.1.1 a", "level": 3, "budget": 1700}
            ], "budget": 1700},
        ],
    }
    block = _build_section_quota_block(hierarchy, {"h2_sections": hierarchy["h2_sections"], "total_allocated": 1700})
    assert "结构参考" in block
    assert "2.1 A" in block
    assert "1,700" in block  # 逗号格式化


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
