"""
权威政务与智库联网检索 — 免 Key 国内高可用搜索调度与 .gov.cn 权威过滤。

1. 免 Key 高可用聚合检索（国内搜索引擎端点 / 公用接口 / 可选 TAVILY_API_KEY 回退）；
2. 权威信息源过滤：强制 .gov.cn / .edu.cn / .org.cn 及国家权威政务智库门户采信，严格剔除自媒体与非权威网站；
3. 文本清洗与格式化输出：【网:标题】\\n  URL\\n  > 摘要正文；
4. 严格 3.5s 超时与静默熔断保护（绝不抛出异常阻断写作主流程）。
"""
from __future__ import annotations

import html
import logging
import os
import re
from urllib.parse import parse_qs, quote, unquote, urlparse

import httpx

_logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 权威域名白名单与自媒体黑名单规则
# ═══════════════════════════════════════════════════════════════

WHITELIST_SUFFIXES = (
    ".gov.cn",
    ".edu.cn",
    ".org.cn",
)

WHITELIST_DOMAINS = {
    "gov.cn",
    "www.gov.cn",
    "news.cn",
    "xinhuanet.com",
    "people.com.cn",
    "cctv.com",
    "ce.cn",
    "chinanews.com.cn",
    "chinanews.com",
    "cac.gov.cn",
    "qstheory.cn",
    "scio.gov.cn",
    "std.samr.gov.cn",
    "stats.gov.cn",
    "ndrc.gov.cn",
    "mof.gov.cn",
    "mee.gov.cn",
    "miit.gov.cn",
    "mohurd.gov.cn",
    "mnr.gov.cn",
    "mot.gov.cn",
    "nea.gov.cn",
    "samr.gov.cn",
    "customs.gov.cn",
    "huanqiu.com",
}

BLACKLIST_DOMAINS = {
    "zhihu.com",
    "sohu.com",
    "163.com",
    "weibo.com",
    "baijiahao.baidu.com",
    "toutiao.com",
    "bilibili.com",
    "douban.com",
    "jianshu.com",
    "csdn.net",
    "xiaohongshu.com",
    "mp.weixin.qq.com",
    "weixin.qq.com",
    "tieba.baidu.com",
    "zhidao.baidu.com",
    "wenku.baidu.com",
    "kuaishou.com",
    "douyin.com",
    "tianya.cn",
    "360doc.com",
    "baidu.com",
    "bing.com",
    "sogou.com",
    "google.com",
    "so.com",
    "sm.cn",
}

# ═══════════════════════════════════════════════════════════════
# 可注入 HTTP 传输层（供单测使用 MockTransport）
# ═══════════════════════════════════════════════════════════════

_transport: httpx.BaseTransport | None = None


def set_transport(transport: httpx.BaseTransport | None) -> None:
    """设置可注入的 HTTP 传输层。"""
    global _transport
    _transport = transport


def get_transport() -> httpx.BaseTransport | None:
    return _transport


# ═══════════════════════════════════════════════════════════════
# 权威性校验与清洗格式化
# ═══════════════════════════════════════════════════════════════


def is_authoritative_domain(netloc: str) -> bool:
    """判定域名是否属于 .gov.cn 或权威政务/智库门户，且非黑名单自媒体。"""
    if not netloc:
        return False
    host = netloc.lower().split(":")[0].strip()
    if not host:
        return False

    # 1. 黑名单严格拦截（含子域名）
    for bad in BLACKLIST_DOMAINS:
        if host == bad or host.endswith("." + bad):
            return False

    # 2. 权威白名单顶级与二级后缀 (.gov.cn, .edu.cn, .org.cn)
    for suf in WHITELIST_SUFFIXES:
        if host.endswith(suf) or host == suf[1:]:
            return True

    # 3. 权威中央与行业官方门户域名
    for good in WHITELIST_DOMAINS:
        if host == good or host.endswith("." + good):
            return True

    return False


def is_authoritative_url(url: str) -> bool:
    """判定 URL 是否为权威政务或官方信息源。"""
    if not url or not url.startswith(("http://", "https://")):
        return False
    try:
        parsed = urlparse(url)
        return is_authoritative_domain(parsed.netloc)
    except Exception:
        return False


def clean_title(raw_title: str, max_len: int = 50) -> str:
    """清洗网页标题：去除 HTML 标签、转义括号符号、长度截断。

    转义规则：
      [ ] ➔ ( )
      【 】 ➔ 「 」
    """
    if not raw_title:
        return "权威政务参考"

    text = html.unescape(raw_title)
    text = re.sub(r"<[^>]+>", "", text)
    # 转义方括号与中文黑体括号，防止污染 Markdown 引用语法
    text = text.replace("[", "(").replace("]", ")")
    text = text.replace("【", "「").replace("】", "」")

    # 去除常见搜索引擎与门户后缀
    text = re.sub(r"[-_](?:中国政府网|国家发展改革委|新华网|人民网|百度.*|搜狗.*|必应.*|Bing)$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip("-_:：·| ")

    if len(text) > max_len:
        text = text[:max_len].rstrip("-_:：·| ")

    return text or "权威政务参考"


def clean_snippet(raw_snippet: str, max_len: int = 260) -> str:
    """清洗网页摘要：去除 HTML 标签、规范换行与空格、截断长度。"""
    if not raw_snippet:
        return ""

    text = html.unescape(raw_snippet)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("【", "「").replace("】", "」")
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_len:
        text = text[:max_len] + "..."

    return text


def format_web_item(title: str, url: str, snippet: str) -> str:
    """按规范格式化单条联网检索参考条目：

    【网:标题】
      URL
      > 摘要正文
    """
    t = clean_title(title)
    s = clean_snippet(snippet)
    u = url.strip()
    return f"【网:{t}】\n  {u}\n  > {s}"


def enhance_gov_query(query: str) -> str:
    """增强关键词倾向，自动附加国家政策规程与 gov.cn 权威倾向。"""
    q = (query or "").strip()
    if not q:
        return ""
    # 去除冗余的章标题前缀如 "第一章 "，获取实质性主题
    q = re.sub(r"^第[一二三四五六七八九十百\d]+章\s*", "", q).strip()
    if not q:
        q = query.strip()

    # 如果未包含 site: 且未包含 gov.cn，增加权威政务倾向
    if "gov.cn" not in q and "site:" not in q:
        return f"{q} site:gov.cn"
    return q


# ═══════════════════════════════════════════════════════════════
# 搜索引擎 HTML 解析与端点驱动
# ═══════════════════════════════════════════════════════════════


def _parse_bing_html(html_text: str) -> list[dict]:
    """解析 Bing 搜索结果 HTML。"""
    results = []
    if not html_text:
        return results

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")
        items = soup.find_all("li", class_="b_algo")
        for item in items:
            h2 = item.find("h2")
            if not h2:
                continue
            a = h2.find("a")
            if not a:
                continue
            url = a.get("href", "").strip()
            title = a.get_text()

            # 提取摘要
            snippet = ""
            p = item.find("p")
            if p:
                snippet = p.get_text()
            else:
                caption = item.find("div", class_="b_caption")
                if caption:
                    snippet = caption.get_text()

            if url and title and is_authoritative_url(url):
                results.append({"title": title, "url": url, "snippet": snippet})
    except Exception as e:
        _logger.debug("Bing HTML 解析失败: %s", e)

    return results


def _parse_duckduckgo_html(html_text: str) -> list[dict]:
    """解析 DuckDuckGo HTML Lite 搜索结果。"""
    results = []
    if not html_text:
        return results

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")
        rows = soup.find_all("div", class_="result")
        for row in rows:
            h2 = row.find("h2", class_="result__title")
            title = ""
            url = ""
            if h2:
                a_h2 = h2.find("a")
                if a_h2:
                    title = a_h2.get_text()
                    raw_href = a_h2.get("href", "")
                    if "uddg=" in raw_href:
                        m = re.search(r"uddg=([^&]+)", raw_href)
                        if m:
                            url = unquote(m.group(1))
                    elif raw_href.startswith("http"):
                        url = raw_href

            snippet_el = row.find("a", class_="result__snippet") or row.find("div", class_="result__snippet")
            snippet = snippet_el.get_text() if snippet_el else ""

            if url and is_authoritative_url(url):
                results.append({"title": title, "url": url, "snippet": snippet})
    except Exception as e:
        _logger.debug("DuckDuckGo HTML 解析失败: %s", e)

    return results


def _search_tavily(query: str, api_key: str, timeout: float, max_results: int = 5) -> list[dict]:
    """调用 Tavily 搜索 API。"""
    results = []
    headers = {
        "Content-Type": "application/json",
    }
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results * 2,
        "include_domains": ["gov.cn", "edu.cn", "org.cn", "news.cn", "people.com.cn"],
    }
    with httpx.Client(transport=_transport, timeout=timeout) as client:
        resp = client.post("https://api.tavily.com/search", json=payload, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            raw_items = data.get("results") or []
            for item in raw_items:
                url = (item.get("url") or "").strip()
                title = item.get("title") or ""
                content = item.get("content") or ""
                if url and is_authoritative_url(url):
                    results.append({"title": title, "url": url, "snippet": content})
    return results


def _search_zero_key(query: str, timeout: float, max_results: int = 5) -> list[dict]:
    """执行国内免 Key 权威搜索聚合。"""
    results: list[dict] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # 1. 尝试 Bing 靶向搜索
    bing_query = enhance_gov_query(query)
    bing_url = f"https://cn.bing.com/search?q={quote(bing_query)}&mkt=zh-CN"

    with httpx.Client(transport=_transport, timeout=timeout, follow_redirects=True) as client:
        try:
            resp = client.get(bing_url, headers=headers)
            if resp.status_code == 200:
                bing_results = _parse_bing_html(resp.text)
                for item in bing_results:
                    if not any(r["url"] == item["url"] for r in results):
                        results.append(item)
        except Exception as e:
            _logger.debug("Bing 检索尝试失败: %s", e)

        # 若结果不足，尝试 DuckDuckGo 备用端点
        if len(results) < max_results:
            try:
                ddg_url = f"https://html.duckduckgo.com/html/?q={quote(bing_query)}"
                resp = client.get(ddg_url, headers=headers)
                if resp.status_code == 200:
                    ddg_results = _parse_duckduckgo_html(resp.text)
                    for item in ddg_results:
                        if not any(r["url"] == item["url"] for r in results):
                            results.append(item)
            except Exception as e:
                _logger.debug("DuckDuckGo 检索尝试失败: %s", e)

    return results[:max_results]


# ═══════════════════════════════════════════════════════════════
# 主对外调度接口（含静默熔断保护）
# ═══════════════════════════════════════════════════════════════


def search_gov_web(
    query: str,
    max_results: int = 5,
    timeout: float = 3.5,
) -> str:
    """免 Key 国内高可用权威政务检索。

    1. 自动强化权威政务检索意图并进行 .gov.cn 靶向过滤；
    2. 严格 3.5 秒超时控制与全异常静默熔断降级；
    3. 网页标题与内容清洗：转义括号符号，截断长标题与摘要；
    4. 格式化输出为：
       【网:标题】
         URL
         > 摘要正文
    """
    if not query or not query.strip():
        return ""

    try:
        items: list[dict] = []
        tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()

        if tavily_key:
            try:
                items = _search_tavily(query, tavily_key, timeout=timeout, max_results=max_results)
            except Exception as e:
                _logger.warning("Tavily 搜索失败，降级至免 Key 国内端点: %s", e)

        if not items:
            items = _search_zero_key(query, timeout=timeout, max_results=max_results)

        if not items:
            return ""

        # 去重、权威过滤与格式化
        seen_urls = set()
        formatted_blocks = []
        for it in items:
            url = it.get("url", "").strip()
            title = it.get("title", "").strip()
            snippet = it.get("snippet", "").strip()
            if not url or url in seen_urls:
                continue
            if not is_authoritative_url(url):
                continue
            seen_urls.add(url)
            block = format_web_item(title, url, snippet)
            formatted_blocks.append(block)
            if len(formatted_blocks) >= max_results:
                break

        return "\n\n".join(formatted_blocks)
    except Exception as e:
        _logger.warning("权威政务联网检索降级: %s", e)
        return ""
