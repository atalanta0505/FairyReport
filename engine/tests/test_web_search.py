"""
权威政务与智库联网检索单元测试 — 覆盖免 Key 搜索解析、域名白黑名单过滤、异常熔断降级与三源 RAG 融合。
"""
import httpx
import pytest

from engine.app.writing import web_search as ws_mod
from engine.app.writing.rag import query_rag
from engine.app.writing.refs import (
    _extract_url_for_label,
    extract_chapter_refs,
    strip_fabricated_labels,
)
from engine.app.writing.web_search import (
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
# 1. 域名与 URL 权威性白名单/黑名单判定
# ═══════════════════════════════════════════════════════════════


def test_is_authoritative_domain_whitelist_suffixes():
    # .gov.cn 各级政务网站
    assert is_authoritative_domain("www.gov.cn")
    assert is_authoritative_domain("ndrc.gov.cn")
    assert is_authoritative_domain("zcfb.ndrc.gov.cn")
    assert is_authoritative_domain("mof.gov.cn")
    assert is_authoritative_domain("mee.gov.cn")
    assert is_authoritative_domain("beijing.gov.cn")
    assert is_authoritative_domain("samr.gov.cn")

    # .edu.cn 高校智库
    assert is_authoritative_domain("tsinghua.edu.cn")
    assert is_authoritative_domain("pku.edu.cn")
    assert is_authoritative_domain("www.zju.edu.cn")

    # .org.cn 行业学会协会与标准组织
    assert is_authoritative_domain("cnea.org.cn")
    assert is_authoritative_domain("cnis.org.cn")
    assert is_authoritative_domain("csre.org.cn")


def test_is_authoritative_domain_whitelist_portals():
    assert is_authoritative_domain("news.cn")
    assert is_authoritative_domain("www.news.cn")
    assert is_authoritative_domain("people.com.cn")
    assert is_authoritative_domain("xinhuanet.com")
    assert is_authoritative_domain("cctv.com")
    assert is_authoritative_domain("ce.cn")
    assert is_authoritative_domain("chinanews.com.cn")
    assert is_authoritative_domain("qstheory.cn")
    assert is_authoritative_domain("scio.gov.cn")


def test_is_authoritative_domain_blacklist_rejections():
    # 自媒体/论坛/非权威网站必须严格剔除
    assert not is_authoritative_domain("zhihu.com")
    assert not is_authoritative_domain("www.zhihu.com")
    assert not is_authoritative_domain("zhuanlan.zhihu.com")
    assert not is_authoritative_domain("sohu.com")
    assert not is_authoritative_domain("163.com")
    assert not is_authoritative_domain("weibo.com")
    assert not is_authoritative_domain("baijiahao.baidu.com")
    assert not is_authoritative_domain("toutiao.com")
    assert not is_authoritative_domain("bilibili.com")
    assert not is_authoritative_domain("csdn.net")
    assert not is_authoritative_domain("xiaohongshu.com")
    assert not is_authoritative_domain("mp.weixin.qq.com")
    assert not is_authoritative_domain("tieba.baidu.com")
    assert not is_authoritative_domain("baidu.com")


def test_is_authoritative_url():
    assert is_authoritative_url("https://www.ndrc.gov.cn/xxgk/zcfb/tz/202303/t20230324_1352467.html")
    assert is_authoritative_url("http://www.gov.cn/zhengce/content/2022-01/24/content_5669984.htm")
    assert is_authoritative_url("https://www.news.cn/fortune/2023-01/01/c_123.htm")

    # 非法或自媒体 URL
    assert not is_authoritative_url("https://zhuanlan.zhihu.com/p/123456")
    assert not is_authoritative_url("https://baijiahao.baidu.com/s?id=987654")
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
    assert "site:gov.cn" in enhance_gov_query("节能减排技术方案")
    assert enhance_gov_query("第二章 项目建设背景") == "项目建设背景 site:gov.cn"
    # 已包含 site: 或 gov.cn 时不重复附加
    assert enhance_gov_query("ndrc.gov.cn 产业政策") == "ndrc.gov.cn 产业政策"


# ═══════════════════════════════════════════════════════════════
# 3. 免 Key 搜索引擎 HTML 解析测试
# ═══════════════════════════════════════════════════════════════


def test_bing_html_parsing_and_authority_filtering():
    fake_bing_html = """
    <html>
      <body>
        <ol id="b_results">
          <li class="b_algo">
            <h2><a href="https://www.ndrc.gov.cn/xxgk/zcfb/tz/202201/t20220124_1312520.html">十四五节能减排综合工作方案 - 国家发展改革委</a></h2>
            <div class="b_caption"><p>国家发改委关于印发十四五节能减排综合工作方案的通知，部署十大重点工程。</p></div>
          </li>
          <li class="b_algo">
            <h2><a href="https://zhuanlan.zhihu.com/p/123456">深度解读节能减排工作方案 - 知乎</a></h2>
            <div class="b_caption"><p>个人博客分析与解读节能减排细节。</p></div>
          </li>
          <li class="b_algo">
            <h2><a href="http://www.gov.cn/zhengce/2023-03/content.htm">国务院关于推进绿色低碳发展的指导意见 - 中国政府网</a></h2>
            <div class="b_caption"><p>推进产业结构绿色转型升级，加强资源节约集约利用。</p></div>
          </li>
        </ol>
      </body>
    </html>
    """

    def handler(request: httpx.Request):
        return httpx.Response(200, text=fake_bing_html)

    set_transport(httpx.MockTransport(handler))

    res = search_gov_web("节能减排", max_results=5)
    assert "【网:十四五节能减排综合工作方案" in res
    assert "https://www.ndrc.gov.cn/xxgk/zcfb/tz/202201/t20220124_1312520.html" in res
    assert "【网:国务院关于推进绿色低碳发展的指导意见" in res
    assert "http://www.gov.cn/zhengce/2023-03/content.htm" in res
    # 严格剔除知乎
    assert "zhihu.com" not in res


def test_duckduckgo_html_redirect_parsing():
    fake_ddg_html = """
    <div class="results">
      <div class="result results_links">
        <h2 class="result__title">
          <a class="result__url" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.mee.gov.cn%2Fzcwj%2Fzyygwj%2F202201%2Ft20220124_968032.shtml&rut=xxx">生态环境部关于印发方案的通知</a>
        </h2>
        <a class="result__snippet">生态环境保护综合规划要求...</a>
      </div>
    </div>
    """

    def handler(request: httpx.Request):
        if "bing.com" in str(request.url):
            return httpx.Response(200, text="<html><body></body></html>")
        return httpx.Response(200, text=fake_ddg_html)

    set_transport(httpx.MockTransport(handler))

    res = search_gov_web("生态环境规划", max_results=5)
    assert "【网:生态环境部关于印发方案的通知】" in res
    assert "https://www.mee.gov.cn/zcwj/zyygwj/202201/t20220124_968032.shtml" in res


# ═══════════════════════════════════════════════════════════════
# 4. 可选 TAVILY_API_KEY 通道测试
# ═══════════════════════════════════════════════════════════════


def test_tavily_api_channel(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-testkey-123456")

    fake_tavily_json = {
        "results": [
            {
                "title": "国家能源局关于组织开展新型储能试点示范工作的通知",
                "url": "https://www.nea.gov.cn/2023-12/27/c_1310757234.htm",
                "content": "新型储能试点示范项目申报要求与技术标准。",
            },
            {
                "title": "自媒体储能分析",
                "url": "https://baijiahao.baidu.com/s?id=123",
                "content": "非官方分析内容。",
            },
        ]
    }

    def handler(request: httpx.Request):
        if "api.tavily.com" in str(request.url):
            return httpx.Response(200, json=fake_tavily_json)
        return httpx.Response(500)

    set_transport(httpx.MockTransport(handler))

    res = search_gov_web("新型储能试点", max_results=5)
    assert "【网:国家能源局关于组织开展新型储能试点示范工作的通知】" in res
    assert "https://www.nea.gov.cn/2023-12/27/c_1310757234.htm" in res
    assert "baijiahao.baidu.com" not in res


# ═══════════════════════════════════════════════════════════════
# 5. 静默熔断降级与异常保护（超时/网络错误绝不阻断）
# ═══════════════════════════════════════════════════════════════


def test_search_gov_web_timeout_silent_fallback():
    def handler(request: httpx.Request):
        raise httpx.ReadTimeout("Stub Search Timeout", request=request)

    set_transport(httpx.MockTransport(handler))

    # 遇到超时应静默返回空字符串，绝不向外抛出异常
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
    # 打桩 search_gov_web
    fake_web_block = (
        "【网:国家发改委投资项目管理办法】\n"
        "  https://www.ndrc.gov.cn/xxgk/zcfb/tz/202303/t20230324_1352467.html\n"
        "  > 规范投资项目决策与审批管理程序。"
    )
    monkeypatch.setattr(ws_mod, "search_gov_web", lambda q, max_results=5, timeout=3.5: fake_web_block)

    # 1. 检索三源
    rag_out = query_rag(
        project_name="",
        query_text="投资管理与可行性研究",
        include_generic=False,
        include_web=True,
    )
    assert "【网:国家发改委投资项目管理办法】" in rag_out
    assert "https://www.ndrc.gov.cn/xxgk/zcfb/tz/202303/t20230324_1352467.html" in rag_out

    # 2. 禁用联网检索
    rag_no_web = query_rag(
        project_name="",
        query_text="投资管理与可行性研究",
        include_generic=False,
        include_web=False,
    )
    assert rag_no_web == "（无相关参考资料）"


# ═══════════════════════════════════════════════════════════════
# 7. 引用管理集成测试 (refs.py 配合)
# ═══════════════════════════════════════════════════════════════


def test_refs_integration_with_web_search():
    rag_context = (
        "【源:工程勘测底稿.docx】: 地质构造稳定。\n\n---\n\n"
        "【网:发改委规程】\n"
        "  https://www.ndrc.gov.cn/policy/123\n"
        "  > 建设标准规程正文。"
    )

    body = (
        "根据项目地质资料【源:工程勘测底稿.docx】，场地地基稳固。"
        "同时对照国家规程【网:发改委规程】，建设方案符合产业导向。"
        "另外存在编造标签【网:未检索自媒体】。"
    )

    # 1. 过滤编造标签：保留真实网页与底稿标签，编造转为 [Z]
    cleaned = strip_fabricated_labels(body, rag_context)
    assert "【源:工程勘测底稿.docx】" in cleaned
    assert "【网:发改委规程】" in cleaned
    assert "【网:未检索自媒体】" not in cleaned
    assert "[Z]" in cleaned

    # 2. 提取 URL 关联
    url = _extract_url_for_label("【网:发改委规程】", rag_context)
    assert url == "https://www.ndrc.gov.cn/policy/123"

    # 3. 提取章节引用列表
    refs = extract_chapter_refs(cleaned, rag_context)
    web_ref = next((r for r in refs if r["label"] == "【网:发改委规程】"), None)
    assert web_ref is not None
    assert web_ref["type"] == "网页链接"
    assert web_ref["source"] == "https://www.ndrc.gov.cn/policy/123"
