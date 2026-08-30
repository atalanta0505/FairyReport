"""
权威政务与智库联网检索 — 免 Key 百度第一优先搜索调度与自媒体黑名单精准过滤。

1. 国内公网第一优先级免 Key 百度检索（https://www.baidu.com/s?wd=...）；
2. 备用兜底：保留 Bing 与 DuckDuckGo 作为第 2、3 备用通道；
3. 废除狭隘白名单（全面采信政府、高校、行业标准平台、协会智库、企业公示等权威源）；
4. 严格黑名单拦截：严格过滤自媒体、论坛、非权威博客（知乎、CSDN、百家号、小红书、微信公众号、微博等）；
5. 文本清洗与格式化输出：【网:标题】\\n  URL\\n  > 摘要正文；
6. 严格 3.5s 超时与静默熔断保护（绝不抛出异常阻断写作主流程）。
"""
from __future__ import annotations

import html
import json
import logging
import os
import re
from urllib.parse import quote, unquote, urlparse

import httpx

_logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 自媒体、论坛与非权威黑名单规则（全网严格拦截）
# ═══════════════════════════════════════════════════════════════

BLACKLIST_DOMAINS = {
    "zhihu.com",
    "csdn.net",
    "baijiahao.baidu.com",
    "xiaohongshu.com",
    "mp.weixin.qq.com",
    "weixin.qq.com",
    "weibo.com",
    "weibo.cn",
    "tieba.baidu.com",
    "zhidao.baidu.com",
    "wenku.baidu.com",
    "toutiao.com",
    "bilibili.com",
    "douban.com",
    "jianshu.com",
    "kuaishou.com",
    "douyin.com",
    "sohu.com",
    "163.com",
    "360doc.com",
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
    """判定域名是否属于真实合法网站，且严格非黑名单自媒体/论坛/非权威站点。"""
    if not netloc:
        return False
    host = netloc.lower().split(":")[0].strip()
    if not host or "." not in host:
        return False

    # 严格黑名单拦截（含子域名）
    for bad in BLACKLIST_DOMAINS:
        if host == bad or host.endswith("." + bad):
            return False

    return True


def is_authoritative_url(url: str) -> bool:
    """判定 URL 是否为合法且非黑名单的网页链接。"""
    if not url or not url.startswith(("http://", "https://")):
        return False
    try:
        parsed = urlparse(url)
        return is_authoritative_domain(parsed.netloc)
    except Exception:
        return False


# 常见繁体字到规范简体字映射表（覆盖法规、标准、政务与咨询报告常用字）
_T2S_MAP = str.maketrans({
    '製': '制', '業': '业', '污': '污', '染': '染', '標': '标', '準': '准',
    '華': '华', '國': '国', '生': '生', '態': '态', '環': '环', '境': '境',
    '發': '发', '展': '展', '規': '规', '劃': '划', '處': '处', '辦': '办',
    '項': '项', '總': '总', '產': '产', '設': '设', '備': '备', '質': '质',
    '量': '量', '題': '题', '經': '经', '濟': '济', '評': '评', '審': '审',
    '查': '查', '資': '资', '訊': '讯', '網': '网', '絡': '络', '關': '关',
    '於': '于', '報': '报', '範': '范', '疇': '畴', '類': '类', '統': '统',
    '計': '计', '認': '认', '證': '证', '實': '实', '施': '施', '測': '测',
    '驗': '验', '書': '书', '號': '号', '條': '条', '例': '例', '導': '导',
    '則': '则', '指': '指', '引': '引', '通': '通', '知': '知', '布': '布',
    '縣': '县', '區': '区', '鄉': '乡', '鎮': '镇', '農': '农', '漁': '渔',
    '商': '商', '稅': '税', '務': '务', '銀': '银', '險': '险', '券': '券',
    '投': '投', '融': '融', '預': '预', '決': '决', '風': '风', '應': '应',
    '急': '急', '監': '监', '估': '估', '論': '论', '優': '优', '節': '节',
    '減': '减', '綠': '绿', '體': '体', '係': '系', '廣': '广', '電': '电',
    '氣': '气', '機': '机', '構': '构', '運': '运', '營': '营', '協': '协',
    '會': '会', '聯': '联', '動': '动', '員': '员', '開': '开', '進': '进',
    '出': '出', '口': '口', '買': '买', '賣': '卖', '轉': '转', '換': '换',
    '選': '选', '擇': '择', '價': '价', '值': '值', '創': '创', '新': '新',
    '術': '术', '藝': '艺', '庫': '库', '專': '专', '門': '门', '戶': '户',
    '檢': '检', '督': '督', '籤': '签', '記': '记', '錄': '录', '線': '线',
    '路': '路', '橋': '桥', '梁': '梁', '鐵': '铁', '鋼': '钢', '鋁': '铝',
    '銅': '铜', '礦': '矿', '品': '品', '廢': '废', '棄': '弃', '置': '置',
    '循': '循', '綜': '综', '利': '利', '用': '用', '水': '水', '土': '土',
    '持': '持', '治': '治', '檔': '档', '案': '案', '測': '测', '算': '算',
})


def to_simplified_chinese(text: str) -> str:
    """将文本中的繁体字转换为规范简体汉字。"""
    if not text:
        return ""
    return text.translate(_T2S_MAP)


def strip_agency_suffix(text: str) -> str:
    """去除标题中尾随的部委/机构/平台名称后缀（如 中华人民共和国生态环境部、中国政府网等）。"""
    if not text:
        return ""
    agencies = [
        r"中华人民共和国生态环境部", r"生态环境部", r"国家发展和改革委员会", r"发展改革委",
        r"工业和信息化部", r"工信部", r"住房和城乡建设部", r"住建部", r"自然资源部",
        r"农业农村部", r"应急管理部", r"国家统计局", r"国家能源局", r"国家林业和草原局",
        r"中国政府网", r"新华网", r"人民网", r"央视网", r"光明网", r"中国网", r"政府门户网",
        r"全国标准信息公共服务平台", r"国家标准化管理委员会", r"行业标准信息服务平台"
    ]
    # 1. 匹配连接符修饰的后缀
    pat_suffix = rf"[-_–—|/]\s*(?:{'|'.join(agencies)})$"
    text = re.sub(pat_suffix, "", text, flags=re.IGNORECASE).strip()
    # 2. 匹配直接粘连在标题末尾的机构名称
    pat_tail = rf"(?:{'|'.join(agencies)})$"
    text = re.sub(pat_tail, "", text, flags=re.IGNORECASE).strip()
    return text


def clean_title(raw_title: str, max_len: int = 60) -> str:
    """清洗网页标题：繁简转换、去机构后缀、去除 HTML 标签、转义括号符号、长度截断。

    转义规则：
      [ ] ➔ ( )
      【 】 ➔ 「 」
    """
    if not raw_title:
        return "权威行业参考"

    text = html.unescape(raw_title)
    text = re.sub(r"<[^>]+>", "", text)
    # 转义方括号与中文黑体括号，防止污染 Markdown 引用语法
    text = text.replace("[", "(").replace("]", ")")
    text = text.replace("【", "「").replace("】", "」")

    # 繁简汉字规范转换
    text = to_simplified_chinese(text)

    # 去除常见搜索引擎、门户与机构后缀
    text = strip_agency_suffix(text)
    text = re.sub(r"[-_](?:中国政府网|国家发展改革委|新华网|人民网|百度.*|搜狗.*|必应.*|Bing)$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip("-_:：·| ")

    if len(text) > max_len:
        text = text[:max_len].rstrip("-_:：·| ")

    return text or "权威行业参考"


def clean_snippet(raw_snippet: str, max_len: int = 260) -> str:
    """清洗网页摘要：繁简转换、去除 HTML 标签、规范换行与空格、截断长度。"""
    if not raw_snippet:
        return ""

    text = html.unescape(raw_snippet)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("【", "「").replace("】", "」")
    text = to_simplified_chinese(text)
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
    """清理搜索词前缀，保持关键词精简有效。"""
    q = (query or "").strip()
    if not q:
        return ""
    # 去除冗余的章标题前缀如 "第一章 "，获取实质性主题
    q = re.sub(r"^#*\s*第[一二三四五六七八九十百\d]+章\s*", "", q).strip()
    return q or query.strip()


# ═══════════════════════════════════════════════════════════════
# 搜索引擎 HTML 解析与端点驱动
# ═══════════════════════════════════════════════════════════════


def _parse_baidu_html(html_text: str) -> list[dict]:
    """解析百度搜索结果 HTML。"""
    results: list[dict] = []
    if not html_text:
        return results

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")
        containers = soup.find_all(
            "div",
            class_=lambda c: c and ("result" in c or "c-container" in c),
        )
        if not containers:
            containers = soup.find_all("div", class_=["result", "c-container"])

        for item in containers:
            h3 = item.find("h3")
            if not h3:
                continue
            a = h3.find("a") or item.find("a")
            if not a:
                continue

            raw_title = a.get_text() or h3.get_text()
            title = clean_title(raw_title)

            # 提取 URL（支持 data-landurl、data-tools 及 href）
            url = a.get("data-landurl", "").strip() or a.get("href", "").strip()
            if not url and item.get("data-tools"):
                try:
                    dt = json.loads(item["data-tools"])
                    url = dt.get("url", "").strip()
                except Exception:
                    pass

            if not url or not url.startswith(("http://", "https://")):
                continue

            # 提取摘要正文
            snippet = ""
            snippet_el = (
                item.find("div", class_=lambda c: c and ("content-right" in c or "c-font-normal" in c or "c-abstract" in c or "abstract" in c or "content" in c))
                or item.find("span", class_=lambda c: c and ("content" in c or "c-font-normal" in c))
                or item.find("div", class_="c-span18")
                or item.find("div", class_="c-row")
                or item.find("p")
            )
            if snippet_el:
                snippet = snippet_el.get_text()
            else:
                full_text = item.get_text()
                h3_text = h3.get_text()
                if h3_text in full_text:
                    snippet = full_text.replace(h3_text, "", 1)
                else:
                    snippet = full_text

            snippet = clean_snippet(snippet)

            if title and is_authoritative_url(url):
                results.append({"title": title, "url": url, "snippet": snippet})
    except Exception as e:
        _logger.debug("Baidu HTML 解析失败: %s", e)

    return results


def _search_baidu(query: str, timeout: float, max_results: int = 5) -> list[dict]:
    """通过百度接口发起免 Key 搜索。"""
    results: list[dict] = []
    if not query or not query.strip():
        return results

    clean_q = enhance_gov_query(query)
    baidu_url = f"https://www.baidu.com/s?wd={quote(clean_q)}&ie=utf-8&rn={max_results * 2}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        with httpx.Client(transport=_transport, timeout=timeout, follow_redirects=True) as client:
            resp = client.get(baidu_url, headers=headers)
            if resp.status_code == 200:
                results = _parse_baidu_html(resp.text)
    except Exception as e:
        _logger.debug("百度搜索请求异常: %s", e)

    return results[:max_results]


def _parse_bing_html(html_text: str) -> list[dict]:
    """解析 Bing 搜索结果 HTML。"""
    results: list[dict] = []
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
                results.append({"title": clean_title(title), "url": url, "snippet": clean_snippet(snippet)})
    except Exception as e:
        _logger.debug("Bing HTML 解析失败: %s", e)

    return results


def _search_bing(query: str, timeout: float, max_results: int = 5) -> list[dict]:
    """通过 Bing 接口发起免 Key 搜索。"""
    results: list[dict] = []
    clean_q = enhance_gov_query(query)
    bing_url = f"https://cn.bing.com/search?q={quote(clean_q)}&mkt=zh-CN"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        with httpx.Client(transport=_transport, timeout=timeout, follow_redirects=True) as client:
            resp = client.get(bing_url, headers=headers)
            if resp.status_code == 200:
                results = _parse_bing_html(resp.text)
    except Exception as e:
        _logger.debug("Bing 搜索请求异常: %s", e)
    return results[:max_results]


def _parse_duckduckgo_html(html_text: str) -> list[dict]:
    """解析 DuckDuckGo HTML Lite 搜索结果。"""
    results: list[dict] = []
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
                results.append({"title": clean_title(title), "url": url, "snippet": clean_snippet(snippet)})
    except Exception as e:
        _logger.debug("DuckDuckGo HTML 解析失败: %s", e)

    return results


def _search_duckduckgo(query: str, timeout: float, max_results: int = 5) -> list[dict]:
    """通过 DuckDuckGo 接口发起免 Key 搜索。"""
    results: list[dict] = []
    clean_q = enhance_gov_query(query)
    ddg_url = f"https://html.duckduckgo.com/html/?q={quote(clean_q)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        with httpx.Client(transport=_transport, timeout=timeout, follow_redirects=True) as client:
            resp = client.get(ddg_url, headers=headers)
            if resp.status_code == 200:
                results = _parse_duckduckgo_html(resp.text)
    except Exception as e:
        _logger.debug("DuckDuckGo 搜索请求异常: %s", e)
    return results[:max_results]


def _search_tavily(query: str, api_key: str, timeout: float, max_results: int = 5) -> list[dict]:
    """调用 Tavily 搜索 API（若配置可选 Key）。"""
    results: list[dict] = []
    headers = {
        "Content-Type": "application/json",
    }
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results * 2,
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
                    results.append({"title": clean_title(title), "url": url, "snippet": clean_snippet(content)})
    return results


def _search_zero_key(query: str, timeout: float, max_results: int = 5) -> list[dict]:
    """执行国内免 Key 权威搜索聚合（百度第 1 优先，Bing/DuckDuckGo 备用兜底）。"""
    results: list[dict] = []
    seen_urls: set[str] = set()

    def _add_items(items: list[dict]):
        for it in items:
            u = it.get("url", "").strip()
            if u and u not in seen_urls and is_authoritative_url(u):
                seen_urls.add(u)
                results.append(it)

    # 1. 第一优先级：百度免 Key 检索
    try:
        baidu_items = _search_baidu(query, timeout=timeout, max_results=max_results)
        _add_items(baidu_items)
    except Exception as e:
        _logger.debug("百度检索尝试失败: %s", e)

    # 2. 第二优先级：Bing 备用通道
    if len(results) < max_results:
        try:
            bing_items = _search_bing(query, timeout=timeout, max_results=max_results)
            _add_items(bing_items)
        except Exception as e:
            _logger.debug("Bing 检索尝试失败: %s", e)

    # 3. 第三优先级：DuckDuckGo 备用通道
    if len(results) < max_results:
        try:
            ddg_items = _search_duckduckgo(query, timeout=timeout, max_results=max_results)
            _add_items(ddg_items)
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
    """免 Key 国内高可用权威联网检索（百度第一优先，严格黑名单拦截）。

    1. 第一优先级百度免 Key 调度，Bing / DuckDuckGo 备用兜底；
    2. 全面采信政府、高校智库、行业标准与企业公开信息，100% 拦截自媒体黑名单；
    3. 严格 3.5 秒超时控制与全异常静默熔断降级；
    4. 网页标题与内容清洗：转义括号符号，截断长标题与摘要；
    5. 格式化输出为：
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
        _logger.warning("权威联网检索降级: %s", e)
        return ""
