"""
Web Search — Tavily API wrapper
- Search web material by topic, return structured summaries
- Results use [网:title] tags, replaced with numeric numbers in post-processing
- Silent fallback on failure, does not break the main flow
"""
import logging
import os
import requests

_logger = logging.getLogger(__name__)

TAVILY_URL = "https://api.tavily.com/search"


def search(query: str, max_results: int = 15) -> str:
    """Search web material, return formatted reference text.

    Returns an empty string if the API key is not configured or the call fails.
    Results use [网:title] tags (numeric numbers are not used here).
    """
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return ""

    try:
        resp = requests.post(
            TAVILY_URL,
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "include_domains": [],
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        _logger.warning("Tavily search request failed: %s", e)
        return ""

    results = data.get("results", [])
    if not results:
        return ""

    lines = ["\n### 🌐 Web References (Tavily Search)\n"]
    for r in results:
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        content = r.get("content", "")
        # Truncate overly long content
        if len(content) > 300:
            content = content[:300] + "…"
        # v1.0.2: sanitize brackets in titles to avoid regex truncation; truncate overly long titles
        safe_title = title.replace('[', '(').replace(']', ')')
        safe_title = safe_title.replace('【', '「').replace('】', '」')
        if len(safe_title) > 50:
            safe_title = safe_title[:47] + "…"
        lines.append(f"【网:{safe_title}】\n  {url}\n  > {content}\n")

    return "\n".join(lines)
