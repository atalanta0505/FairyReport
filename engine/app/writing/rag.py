"""
三源 RAG 检索 — 项目库（materials vectorstore）+ 行业标准规程库（generic collection）+ 百度免 Key 外部联网 RAG（web_search）。

三类规范引用格式：
1. 项目底稿资料 → 【源:filename】: doc
2. 行业标准规程 → 【标:标准或规程名称】: doc
3. 权威联网检索 → 【网:title】\n  URL\n  > 摘要正文

嵌入走可注入接口（engine.app.embedding.get_embedder）。
"""
from __future__ import annotations

import logging
import re

from ..config import settings
from ..embedding import get_embedder
from ..generic.store import GenericStore
from ..materials.vectorstore import ProjectVectorStore
from . import web_search
from .prompts import RAG_RESULTS_PER_SOURCE

_logger = logging.getLogger(__name__)


def extract_smart_web_query(
    project_name: str,
    chapter_title: str = "",
    report_type: str = "",
) -> str:
    """智能提炼精简联网检索关键词，剥离冗余公文噪音，生成 2~4 个高命中率关键词。

    示例：
      - ("安徽省亳州市利辛县肉牛屠宰加工项目", "第二章 建设背景与产业政策符合性")
        ➔ "利辛县 肉牛屠宰 产业政策 规划"
      - ("制革工业污水治理技改项目", "第五章 环保与水污染排放方案")
        ➔ "制革工业 环保 排放标准"
    """
    # 1. 规范化与清洗章节标题
    clean_ch = (chapter_title or "").strip()
    clean_ch = re.sub(r"^#*\s*(?:第[一二三四五六七八九十百零\d]+章|\d+(?:\.\d+)*)\s*", "", clean_ch).strip()
    clean_ch = re.sub(r"[（\(].*?[）\)]", "", clean_ch).strip()

    # 2. 剥离报告类型与公文词汇噪音
    noise_patterns = [
        r"可行性研究报告", r"初步可行性研究报告", r"可行性研究", r"项目建议书",
        r"项目申请报告", r"项目申请书", r"资金申请报告", r"社会评价报告",
        r"后评价报告", r"特许经营方案", r"项目评估报告", r"专题研究报告",
        r"投资机会研究报告", r"产业发展规划报告", r"企业发展规划报告",
        r"园区发展规划报告", r"发展规划报告", r"实施方案", r"建设方案",
        r"规划报告", r"评估报告", r"研究报告", r"建议书", r"申请报告",
        r"项目", r"工程", r"报告", r"方案",
    ]

    p_clean = (project_name or "").strip()
    for np in noise_patterns:
        p_clean = re.sub(np, " ", p_clean)
    p_clean = re.sub(r"\s+", " ", p_clean).strip()

    # 3. 提取项目主体关键词（区域与产业核心词）
    words = []
    if p_clean:
        p_tokens = [t.strip() for t in p_clean.split() if t.strip()]
        words.extend(p_tokens[:2])

    # 4. 根据章节主题提炼针对性检索词
    topic_words = []
    if clean_ch:
        if any(kw in clean_ch for kw in ["背景", "必要性", "政策", "规划", "符合性", "战略"]):
            topic_words.extend(["产业政策", "规划"])
        elif any(kw in clean_ch for kw in ["环保", "生态", "环境", "水污染", "大气", "固体废物", "污水", "排放"]):
            topic_words.extend(["环保", "排放标准"])
        elif any(kw in clean_ch for kw in ["节能", "能耗", "资源", "碳达峰", "碳中和"]):
            topic_words.extend(["节能标准", "能耗"])
        elif any(kw in clean_ch for kw in ["安全", "消防", "职业卫生", "应急"]):
            topic_words.extend(["安全生产", "行业规程"])
        elif any(kw in clean_ch for kw in ["技术", "工艺", "设备", "工程", "装备"]):
            topic_words.extend(["技术规范", "标准"])
        elif any(kw in clean_ch for kw in ["市场", "需求", "产能", "前景"]):
            topic_words.extend(["市场需求", "前景"])
        elif any(kw in clean_ch for kw in ["投资", "财务", "资金", "经济效益"]):
            topic_words.extend(["投资估算", "指标"])
        else:
            for np in noise_patterns:
                clean_ch = re.sub(np, " ", clean_ch)
            clean_ch = re.sub(r"\s+", " ", clean_ch).strip()
            if clean_ch:
                topic_words.append(clean_ch)
            topic_words.append("产业政策")
    else:
        topic_words.append("产业政策")

    all_tokens = []
    seen = set()
    for tok in words + topic_words:
        if tok and tok not in seen:
            seen.add(tok)
            all_tokens.append(tok)

    query = " ".join(all_tokens[:4]).strip()
    return query or (project_name or chapter_title or "产业政策规划").strip()


def query_rag(
    project_name: str,
    query_text: str,
    n_results: int = None,
    include_generic: bool = True,
    include_web: bool = True,
    topic: str = "",
    report_name: str = "",
    report_type: str = "",
) -> str:
    """三源 RAG 检索，返回格式化字符串。

    项目库 → 【源:filename】: doc
    标准规程库 → 【标:标准全称】: doc
    权威联网库 → 【网:title】\n  URL\n  > 摘要正文
    无结果 → "（无相关参考资料）"
    """
    if n_results is None:
        n_results = RAG_RESULTS_PER_SOURCE

    results: list[str] = []
    emb = None

    rep_name = report_name or project_name or ""
    # 构造项目/通用向量库精确检索词
    search_parts = []
    if rep_name:
        search_parts.append(rep_name)
    if topic and topic != rep_name:
        search_parts.append(topic)
    if query_text and query_text not in (rep_name, topic):
        search_parts.append(query_text)

    vector_query = " ".join(search_parts) if search_parts else query_text

    # ── 1. 项目底稿资料库 ──
    try:
        if project_name and settings.vector_dir(project_name).exists():
            store = ProjectVectorStore.get(
                project_name, settings.vector_dir(project_name)
            )
            if store.count() > 0:
                emb = get_embedder().encode([vector_query])[0]
                res = store.collection.query(query_embeddings=[emb], n_results=n_results)
                docs = (res.get("documents") or [[]])[0]
                metas = (res.get("metadatas") or [[]])[0]
                for doc, meta in zip(docs, metas):
                    meta = meta or {}
                    source = meta.get("source", "项目底稿")
                    results.append(f"【源:{source}】: {doc}")
    except Exception as e:
        _logger.warning("项目库检索失败: %s", e)

    # ── 2. 行业标准与规程库 ──
    if include_generic:
        try:
            gen_col = GenericStore._get_collection()
            if gen_col and gen_col.count() > 0:
                if emb is None:
                    emb = get_embedder().encode([vector_query])[0]
                res = gen_col.query(query_embeddings=[emb], n_results=n_results)
                docs = (res.get("documents") or [[]])[0]
                metas = (res.get("metadatas") or [[]])[0]
                for idx, doc in enumerate(docs):
                    meta = metas[idx] if idx < len(metas) and metas[idx] else {}
                    title = meta.get("title") or meta.get("name") or meta.get("source") or "行业标准与技术规程"
                    results.append(f"【标:{title}】: {doc}")
        except Exception as e:
            _logger.warning("通用规程库检索失败: %s", e)

    # ── 3. 百度免 Key 外部联网 RAG 检索库 ──
    if include_web:
        smart_query = extract_smart_web_query(
            project_name=rep_name,
            chapter_title=topic or query_text,
            report_type=report_type,
        )
        if smart_query:
            try:
                web_content = web_search.search_gov_web(smart_query, max_results=n_results, project_name=project_name)
                if web_content and web_content.strip():
                    results.append(web_content.strip())
            except Exception as e:
                _logger.warning("百度免 Key 外部联网检索失败: %s", e)

    return "\n\n---\n\n".join(results) if results else "（无相关参考资料）"
