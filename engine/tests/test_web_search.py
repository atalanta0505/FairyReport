"""
权威政务与智库联网检索单元测试 — 覆盖百度第一优先搜索解析、自媒体黑名单精准过滤、智能检索词提炼与标准引用体系。
"""
import httpx
import pytest

from engine.app.writing import web_search as ws_mod
from engine.app.writing.rag import extract_smart_web_query, query_rag
from engine.app.writing.refs import (
    _extract_url_for_label,
    build_chapter_ref_section,
    extract_chapter_refs,
    global_assign_ref_numbers,
    strip_fabricated_labels,
)
from engine.app.writing.web_search import (
    BLACKLIST_DOMAINS,
    _parse_baidu_html,
    _search_baidu,
    clean_snippet,
    clean_title,
    enhance_gov_query,
    format_web_item,
    is_authoritative_domain,
    is_authoritative_url,
    search_gov_web,
    set_transport,
)


@pytest.fixture(autouse=True)
def reset_transport():
    """每个测试前后重置 transport。"""
    set_transport(None)
    yield
    set_transport(None)


# ═══════════════════════════════════════════════════════════════
# 1. 域名与 URL 黑名单严格拦截与广泛采信判定
# ═══════════════════════════════════════════════════════════════


def test_is_authoritative_domain_accepted_sources():
    # 1. 政府与公共机构
    assert is_authoritative_domain("www.gov.cn")
    assert is_authoritative_domain("ndrc.gov.cn")
    assert is_authoritative_domain("mee.gov.cn")
    assert is_authoritative_domain("samr.gov.cn")

    # 2. 高校与智库
    assert is_authoritative_domain("tsinghua.edu.cn")
    assert is_authoritative_domain("pku.edu.cn")
    assert is_authoritative_domain("www.zju.edu.cn")

    # 3. 行业协会与国家标准组织
    assert is_authoritative_domain("cnea.org.cn")
    assert is_authoritative_domain("cnis.org.cn")
    assert is_authoritative_domain("std.samr.gov.cn")

    # 4. 行业权威平台、企业公示与门户
    assert is_authoritative_domain("news.cn")
    assert is_authoritative_domain("people.com.cn")
    assert is_authoritative_domain("chinanews.com")
    assert is_authoritative_domain("industry-standard.cn")
    assert is_authoritative_domain("enterprise-portal.com")


def test_is_authoritative_domain_blacklist_rejections():
    # 严格过滤自媒体、论坛与非权威博客
    for bad in BLACKLIST_DOMAINS:
        assert not is_authoritative_domain(bad)
        assert not is_authoritative_domain(f"www.{bad}")
        assert not is_authoritative_domain(f"sub.{bad}")

    assert not is_authoritative_domain("zhihu.com")
    assert not is_authoritative_domain("zhuanlan.zhihu.com")
    assert not is_authoritative_domain("csdn.net")
    assert not is_authoritative_domain("blog.csdn.net")
    assert not is_authoritative_domain("baijiahao.baidu.com")
    assert not is_authoritative_domain("xiaohongshu.com")
    assert not is_authoritative_domain("mp.weixin.qq.com")
    assert not is_authoritative_domain("tieba.baidu.com")
    assert not is_authoritative_domain("zhidao.baidu.com")
    assert not is_authoritative_domain("wenku.baidu.com")
    assert not is_authoritative_domain("toutiao.com")
    assert not is_authoritative_domain("jianshu.com")
    assert not is_authoritative_domain("sohu.com")
    assert not is_authoritative_domain("163.com")


def test_is_authoritative_url():
    assert is_authoritative_url("https://www.ndrc.gov.cn/xxgk/zcfb/tz/202303/t20230324_1352467.html")
    assert is_authoritative_url("http://www.gov.cn/zhengce/content/2022-01/24/content_5669984.htm")
    assert is_authoritative_url("https://std.samr.gov.cn/gb/search/gbDetailed?id=123")
    assert is_authoritative_url("https://www.cnea.org.cn/reports/2023.pdf")

    # 非法或黑名单 URL
    assert not is_authoritative_url("https://zhuanlan.zhihu.com/p/123456")
    assert not is_authoritative_url("https://baijiahao.baidu.com/s?id=987654")
    assert not is_authoritative_url("https://blog.csdn.net/user/article/123")
    assert not is_authoritative_url("ftp://ndrc.gov.cn/file.pdf")
    assert not is_authoritative_url("")
    assert not is_authoritative_url("invalid_url")


# ═══════════════════════════════════════════════════════════════
# 2. 标题与摘要清洗格式化
# ═══════════════════════════════════════════════════════════════


def test_clean_title_bracket_escaping_and_truncation():
    raw = "【国家发改委】关于印发[十四五节能减排综合工作方案]的通知_中国政府网"
    cleaned = clean_title(raw, max_len=40)
    assert "「国家发改委」" in cleaned
    assert "(十四五节能减排综合工作方案)" in cleaned
    assert "【" not in cleaned and "】" not in cleaned
    assert "[" not in cleaned and "]" not in cleaned
    assert "_中国政府网" not in cleaned


def test_clean_snippet_stripping_and_truncation():
    raw = "<p>本方案<b>明确</b>了十四五时期节能减排的主要目标与重点任务。</p>"
    cleaned = clean_snippet(raw, max_len=30)
    assert "<p>" not in cleaned and "<b>" not in cleaned
    assert "本方案明确了十四五时期节能减排的主要目标" in cleaned


def test_format_web_item_standard_structure():
    item_str = format_web_item(
        title="国家发展改革委关于印发可研大纲的通知",
        url="https://www.ndrc.gov.cn/xxgk/zcfb/tz/202303/t20230324_1352467.html",
        snippet="本大纲适用于各类投资项目可行性研究报告编制。",
    )
    expected = (
        "【网:国家发展改革委关于印发可研大纲的通知】\n"
        "  https://www.ndrc.gov.cn/xxgk/zcfb/tz/202303/t20230324_1352467.html\n"
        "  > 本大纲适用于各类投资项目可行性研究报告编制。"
    )
    assert item_str == expected


def test_enhance_gov_query():
    assert enhance_gov_query("第二章 项目建设背景与必要性") == "项目建设背景与必要性"
    assert enhance_gov_query("第1章 概述") == "概述"
    assert enhance_gov_query("节能减排技术方案") == "节能减排技术方案"


# ═══════════════════════════════════════════════════════════════
# 3. 百度第 1 优先免 Key 搜索与 HTML 解析测试
# ═══════════════════════════════════════════════════════════════


def test_baidu_html_parsing_and_blacklist_filtering():
    fake_baidu_html = """
    <html>
      <body>
        <div id="content_left">
          <div class="result c-container xpath-log" data-tools='{"title":"制革及毛皮加工工业水污染排放标准","url":"https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/shjbh/gwjhb/201312/t20131230_265691.shtml"}'>
            <h3 class="c-title t">
              <a href="https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/shjbh/gwjhb/201312/t20131230_265691.shtml">
                <em>制革</em>及毛皮加工工业水污染物排放标准(GB 30486-2013)
              </a>
            </h3>
            <div class="c-abstract">
              本标准规定了制革及毛皮加工工业企业水污染物排放限值、监测和监控要求。
            </div>
          </div>

          <div class="result c-container" data-tools='{"title":"制革废水处理知乎讨论","url":"https://zhuanlan.zhihu.com/p/888999"}'>
            <h3 class="c-title t">
              <a href="https://zhuanlan.zhihu.com/p/888999">制革废水深度处理经验分享 - 知乎</a>
            </h3>
            <div class="c-abstract">知乎个人专栏文章...</div>
          </div>

          <div class="result c-container">
            <h3 class="c-title t">
              <a href="https://baijiahao.baidu.com/s?id=123456">百家号皮革产业分析</a>
            </h3>
            <div class="c-abstract">自媒体营销号文章...</div>
          </div>

          <div class="result c-container" data-tools='{"title":"利辛县国民经济和社会发展第十四个五年规划纲要","url":"http://www.lixin.gov.cn/content/detail/1234.html"}'>
            <h3 class="c-title t">
              <a href="http://www.lixin.gov.cn/content/detail/1234.html">利辛县国民经济和社会发展第十四个五年规划纲要</a>
            </h3>
            <div class="c-abstract">
              利辛县围绕现代轻纺服装、牛皮革及肉牛全产业链打造产业集群。
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    def handler(request: httpx.Request):
        assert "baidu.com/s" in str(request.url)
        return httpx.Response(200, text=fake_baidu_html)

    set_transport(httpx.MockTransport(handler))

    res = search_gov_web("利辛县 牛皮革 环保标准", max_results=5)
    assert "【网:制革及毛皮加工工业水污染物排放标准(GB 30486-2013)】" in res
    assert "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/shjbh/gwjhb/201312/t20131230_265691.shtml" in res
    assert "【网:利辛县国民经济和社会发展第十四个五年规划纲要】" in res
    assert "http://www.lixin.gov.cn/content/detail/1234.html" in res

    # 严格拦截知乎与百家号
    assert "zhihu.com" not in res
    assert "baijiahao.baidu.com" not in res


def test_search_zero_key_fallback_to_bing_and_ddg():
    # 百度返回空，降级由 Bing / DuckDuckGo 提供
    fake_bing_html = """
    <html><body><ol id="b_results">
      <li class="b_algo">
        <h2><a href="https://www.samr.gov.cn/policy/samr_1.html">国家市场监督管理总局标准化指导意见</a></h2>
        <div class="b_caption"><p>全面加强国家标准建设与行业规范管理。</p></div>
      </li>
    </ol></body></html>
    """

    def handler(request: httpx.Request):
        url_str = str(request.url)
        if "baidu.com" in url_str:
            return httpx.Response(200, text="<html><body></body></html>")
        if "bing.com" in url_str:
            return httpx.Response(200, text=fake_bing_html)
        return httpx.Response(200, text="<html><body></body></html>")

    set_transport(httpx.MockTransport(handler))

    res = search_gov_web("国家标准建设", max_results=5)
    assert "【网:国家市场监督管理总局标准化指导意见】" in res
    assert "https://www.samr.gov.cn/policy/samr_1.html" in res


# ═══════════════════════════════════════════════════════════════
# 4. 智能精简搜索词提炼测试
# ═══════════════════════════════════════════════════════════════


def test_extract_smart_web_query():
    # 1. 复杂长项目名称与公文噪音剥离
    q1 = extract_smart_web_query(
        project_name="安徽省亳州市利辛县年产50万张高档牛皮革深加工及肉牛屠宰综合产业园项目可行性研究报告",
        chapter_title="第二章 项目建设背景与产业政策符合性分析",
        report_type="可行性研究报告",
    )
    assert "可行性研究报告" not in q1
    assert "第二章" not in q1
    assert "利辛县" in q1
    assert "产业政策" in q1

    # 2. 环保排放章节
    q2 = extract_smart_web_query(
        project_name="制革工业清洁生产技术改造项目",
        chapter_title="第五章 环境保护与水污染治理技术方案",
        report_type="可行性研究报告",
    )
    assert "环保" in q2 or "排放标准" in q2
    assert "制革工业" in q2

    # 3. 节能减碳章节
    q3 = extract_smart_web_query(
        project_name="分布式光伏电站项目建议书",
        chapter_title="第七章 能源消耗与碳达峰碳中和利用分析",
        report_type="项目建议书",
    )
    assert "项目建议书" not in q3
    assert "节能" in q3 or "能耗" in q3


# ═══════════════════════════════════════════════════════════════
# 5. 静默熔断降级与异常保护（超时/网络错误绝不阻断）
# ═══════════════════════════════════════════════════════════════


def test_search_gov_web_timeout_silent_fallback():
    def handler(request: httpx.Request):
        raise httpx.ReadTimeout("Stub Search Timeout", request=request)

    set_transport(httpx.MockTransport(handler))

    res = search_gov_web("技术方案与投资估算", timeout=1.0)
    assert res == ""


def test_search_gov_web_network_error_silent_fallback():
    def handler(request: httpx.Request):
        raise httpx.ConnectError("Connection refused", request=request)

    set_transport(httpx.MockTransport(handler))

    res = search_gov_web("水利工程规划", timeout=1.0)
    assert res == ""


def test_search_gov_web_empty_query():
    assert search_gov_web("") == ""
    assert search_gov_web("   ") == ""


# ═══════════════════════════════════════════════════════════════
# 6. 三源 RAG 融合格式断言
# ═══════════════════════════════════════════════════════════════


def test_query_rag_tri_source_fusion(monkeypatch):
    fake_web_block = (
        "【网:国家发改委投资项目管理办法】\n"
        "  https://www.ndrc.gov.cn/xxgk/zcfb/tz/202303/t20230324_1352467.html\n"
        "  > 规范投资项目决策与审批管理程序。"
    )
    monkeypatch.setattr(ws_mod, "search_gov_web", lambda q, max_results=5, timeout=3.5: fake_web_block)

    rag_out = query_rag(
        project_name="水利投资示范项目",
        query_text="投资管理与可行性研究",
        include_generic=False,
        include_web=True,
    )
    assert "【网:国家发改委投资项目管理办法】" in rag_out
    assert "https://www.ndrc.gov.cn/xxgk/zcfb/tz/202303/t20230324_1352467.html" in rag_out

    rag_no_web = query_rag(
        project_name="",
        query_text="投资管理与可行性研究",
        include_generic=False,
        include_web=False,
    )
    assert rag_no_web == "（无相关参考资料）"


# ═══════════════════════════════════════════════════════════════
# 7. 规范引用标记体系集成测试（消灭孤立 [Z]）
# ═══════════════════════════════════════════════════════════════


def test_refs_standardization_and_no_isolated_z():
    rag_context = (
        "【源:工程勘测底稿.docx】: 地质构造稳定。\n\n---\n\n"
        "【标:制革工业水污染物排放标准(GB 30486—2013)】: 排放限值。\n\n---\n\n"
        "【网:发改委可研编制大纲】\n"
        "  https://www.ndrc.gov.cn/policy/123\n"
        "  > 建设标准规程正文。"
    )

    body = (
        "根据项目地质资料【源:工程勘测底稿.docx】，场地地基稳固。"
        "同时对照国家标准【标:制革工业水污染物排放标准(GB 30486—2013)】与政策【网:发改委可研编制大纲】，建设方案合规。"
        "另外存在编造标签【网:未检索自媒体】和【源:虚假底稿.pdf】。"
    )

    # 1. 过滤编造标签：保留真实标签，虚构标签直接剥离，严禁替换为孤立 [Z]
    cleaned = strip_fabricated_labels(body, rag_context)
    assert "【源:工程勘测底稿.docx】" in cleaned
    assert "【标:制革工业水污染物排放标准(GB 30486—2013)】" in cleaned
    assert "【网:发改委可研编制大纲】" in cleaned
    assert "【网:未检索自媒体】" not in cleaned
    assert "【源:虚假底稿.pdf】" not in cleaned
    assert "[Z]" not in cleaned

    # 2. 提取 URL 关联
    url = _extract_url_for_label("【网:发改委可研编制大纲】", rag_context)
    assert url == "https://www.ndrc.gov.cn/policy/123"

    # 3. 提取章节引用列表分类
    refs = extract_chapter_refs(cleaned, rag_context)
    types = {r["type"] for r in refs}
    assert "项目资料" in types
    assert "规程标准" in types
    assert "网页链接" in types

    # 4. 生成本章参考资料 Markdown 段
    sec_md = build_chapter_ref_section(refs)
    assert "### 项目资料" in sec_md
    assert "### 规程标准" in sec_md
    assert "### 网页链接" in sec_md
    assert "- 工程勘测底稿.docx" in sec_md
    assert "- 制革工业水污染物排放标准(GB 30486—2013)" in sec_md
    assert "https://www.ndrc.gov.cn/policy/123" in sec_md

    # 5. 全文编号分配 [1], [2], [3]
    numbered_body, numbering = global_assign_ref_numbers(cleaned)
    assert "[1]" in numbered_body
    assert "[2]" in numbered_body
    assert "[3]" in numbered_body
    assert "【源:" not in numbered_body
    assert "【标:" not in numbered_body
    assert "【网:" not in numbered_body
