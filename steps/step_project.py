"""
FairyReport v1.0.5 - Step 0: Project Information
"""
import streamlit as st
import re
import os

from project_store import save_project, load_project
from utils import _pick_folder, _update_env, _resolve_project_name
from config import REPORT_TYPES, PROFESSIONS, REPORT_WORD_LIMITS, get_word_limit, ENCOURAGED_INDUSTRIES, GENERIC_KB_DIR

# ── 产业多选的 Streamlit key，用于程序化控制选中值 ──
_INDUSTRY_KEY = "industry_select"


def _industries_to_topic(selected: list) -> str:
    """从选中的鼓励类产业自动生成项目主题。"""
    if not selected:
        return ""
    names = [re.sub(r'^[一二三四五六七八九十]+、', '', s).strip() for s in selected]
    return "、".join(names)


def _extract_industry_details(selected: list) -> str:
    """从产业结构调整指导目录 KB 中提取选中产业的详细子条目。

    返回精简摘要，如：
    **十九、轻工**：12.制革和毛皮加工清洁生产、皮革后整饰新技术开发及关键设备制造…
    """
    kb_path = os.path.join(GENERIC_KB_DIR, "产业结构调整指导目录（2024年版）.md")
    if not os.path.isfile(kb_path):
        return ""
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return ""

    results = []
    for ind in selected:
        parts = ind.split("、", 1)
        if len(parts) != 2:
            continue
        num, name = parts
        pattern = re.escape(f"**{num}、{name}**")
        m = re.search(pattern, content)
        if not m:
            continue
        start = m.end()
        next_m = re.search(r'\n\*\*[一二三四五六七八九十]+、', content[start:])
        section = content[start:start + next_m.start()] if next_m else content[start:]
        items = re.findall(r'^\d+\.\s*(.+?)$', section, re.MULTILINE)
        if items:
            summary = "；".join(items[:8])
            results.append(f"**{ind}**：{summary}")

    return "\n".join(results)


def _fallback_topic_from_report_name(report_name: str) -> str:
    """Derive a compact topic when the model returns explanatory prose."""
    topic = (report_name or "").strip()
    topic = re.sub(
        r'(?:可行性研究报告|可行性研究|项目建议书|资金申请报告|项目申请报告|实施方案|初步设计|研究报告|报告)$',
        '',
        topic,
    ).strip()
    topic = re.sub(r'^(?:[\u4e00-\u9fa5]{2,12}省)?(?:[\u4e00-\u9fa5]{2,12}市)?(?:[\u4e00-\u9fa5]{1,12}[县区])', '', topic)
    return topic.strip(" ：:，,。；;“”\"'")[:50]


def _clean_generated_topic(raw: str, report_name: str = "") -> str:
    """Normalize LLM output to a topic phrase instead of an explanation."""
    text = re.sub(r'\s+', ' ', (raw or "")).strip()
    text = re.sub(r'^```(?:\w+)?|```$', '', text).strip()
    text = re.sub(r'^[\-*•\d.、\s]+', '', text)

    extracted = re.search(
        r'(?:项目核心主题|核心主题|项目主题|主题关键词|主题)(?:应为|为|是|：|:)\s*[“"《]?([^”"》。；;，,\n]+)',
        text,
    )
    if extracted:
        text = extracted.group(1).strip()

    text = re.sub(r'^(?:项目核心主题|核心主题|项目主题|主题关键词|主题|答案)\s*[：:]\s*', '', text)

    if re.match(r'^(?:根据|结合|从|由|经分析|综合)', text):
        return _fallback_topic_from_report_name(report_name)

    text = re.split(r'[。；;\n]', text, maxsplit=1)[0]
    text = text.strip(" ：:，,。；;“”\"'`")

    if not text:
        text = _fallback_topic_from_report_name(report_name)
    return text[:50]


def render(llm):
    """Step 0: 项目信息——报告名称、类型、专业、主题"""
    st.header("项目信息")

    col_name, col_type, col_prof = st.columns([2, 1, 1])
    with col_name:
        st.session_state.report_name = st.text_input(
            "报告名称", value=st.session_state.report_name,
            placeholder="例如：XX市污水处理厂可行性研究报告")
    with col_type:
        idx = REPORT_TYPES.index(st.session_state.report_type) if st.session_state.report_type in REPORT_TYPES else 0
        st.session_state.report_type = st.selectbox("报告类型", options=REPORT_TYPES, index=idx)
    with col_prof:
        idx = PROFESSIONS.index(st.session_state.profession) if st.session_state.profession in PROFESSIONS else 0
        st.session_state.profession = st.selectbox("专业分类", options=PROFESSIONS, index=idx)

    # ═══════════════════════════════════════════════
    # Step 1: 鼓励类产业 — 智能推荐 + 手动选择
    # ═══════════════════════════════════════════════

    # 在 widget 渲染前注入待定的推荐值（绕过 Streamlit 不可后改 key 的限制）
    if st.session_state.get('_pending_industry_select'):
        st.session_state[_INDUSTRY_KEY] = st.session_state.pop('_pending_industry_select')

    col_ind, col_rec = st.columns([3, 1])
    with col_ind:
        selected = st.multiselect(
            "鼓励类产业（可多选）",
            options=ENCOURAGED_INDUSTRIES,
            key=_INDUSTRY_KEY,
            help="依据《产业结构调整指导目录（2024年本）》鼓励类，选择 1~N 个产业。",
            placeholder="🔍 搜索产业关键词，如「新能源」「人工智能」…",
        )
    with col_rec:
        st.caption("")
        if st.button("🔍 智能推荐", key="recommend_industries",
                     help="根据报告名称自动推荐匹配的鼓励类产业",
                     disabled=not st.session_state.report_name,
                     use_container_width=True):
            with st.spinner("正在分析报告名称，匹配鼓励类产业…"):
                try:
                    _industries_list = "\n".join(ENCOURAGED_INDUSTRIES)
                    result = llm.chat(
                        f"根据以下报告名称，从鼓励类产业列表中选出最相关的 1-3 个产业，"
                        f"只返回产业完整编号（如：十九、轻工），一行一个，不要解释：\n\n"
                        f"报告名称：{st.session_state.report_name}\n\n"
                        f"可选产业：\n{_industries_list}",
                        temperature=0.15)
                    # 解析 LLM 返回，验证是否在列表中
                    recommended = []
                    for line in result.strip().split("\n"):
                        line = line.strip().rstrip("。，,.")
                        if line in ENCOURAGED_INDUSTRIES:
                            recommended.append(line)
                    if recommended:
                        st.session_state['_pending_industry_select'] = recommended
                        st.session_state['_prev_selected_industries'] = list(recommended)
                        st.rerun()
                    else:
                        st.warning("未能匹配到产业，请手动选择。")
                except Exception as e:
                    st.error(f"推荐失败：{e}")

    # v13: 仅当产业选择发生变化时才自动更新 topic
    _prev = st.session_state.get('_prev_selected_industries', [])
    if selected != _prev:
        auto_topic = _industries_to_topic(selected)
        if auto_topic:
            st.session_state.topic = auto_topic
        st.session_state['_prev_selected_industries'] = list(selected)

    # ═══════════════════════════════════════════════
    # Step 2: 项目主题 — 结合产业条目生成精确关键词
    # ═══════════════════════════════════════════════
    col_topic, col_gen = st.columns([3, 1])
    with col_topic:
        st.session_state.topic = st.text_input(
            "项目主题",
            value=st.session_state.topic,
            placeholder="先选产业再点「✨ 生成主题」，或手动输入",
            help="💡 点击右侧按钮，结合报告名称和产业详细条目自动生成精确关键词。")
    with col_gen:
        st.caption("")
        if st.button("✨ 生成主题", key="generate_topic",
                     help="结合报告名称和已选产业的详细条目，智能生成核心主题关键词",
                     use_container_width=True):
            if not st.session_state.report_name:
                st.error("请先输入报告名称")
            elif not selected:
                # 未选产业时，仅从报告名称提取
                with st.spinner("正在分析…"):
                    try:
                        result = llm.chat(
                            f"请从以下报告名称中提取项目核心主题（10-30字），"
                            f"只描述项目本身的关键技术或产品方向。\n"
                            f"必须只返回主题本身，不要写“根据您提供的信息”等解释，不要加引号、标点或前缀：\n\n"
                            f"{st.session_state.report_name}",
                            temperature=0.3)
                        st.session_state.topic = _clean_generated_topic(result, st.session_state.report_name)
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成失败：{e}")
            else:
                with st.spinner("正在结合产业目录分析…"):
                    try:
                        _industry_detail = _extract_industry_details(selected)
                        _industry_names = "、".join(selected)
                        _detail_block = (
                            f"\n\n产业详细说明（摘自《产业结构调整指导目录（2024年版）》）：\n"
                            f"{_industry_detail}"
                        ) if _industry_detail else ""
                        result = llm.chat(
                            f"请从以下信息中提取项目核心主题（10-30字），"
                            f"只描述项目本身的关键技术或产品方向，优先从产业详细说明中提取关键词。\n"
                            f"必须只返回主题本身，不要写“根据您提供的信息”等解释，不要加引号、标点或前缀：\n\n"
                            f"报告名称：{st.session_state.report_name}\n"
                            f"已选鼓励类产业：{_industry_names}"
                            f"{_detail_block}",
                            temperature=0.3)
                        st.session_state.topic = _clean_generated_topic(result, st.session_state.report_name)
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成失败：{e}")

    st.divider()
    # 准备导入：补全 topic/project_name 后解锁并跳转到导入资料步骤
    if st.button("📂 准备导入资料", type="primary", disabled=not st.session_state.report_name):
        if not st.session_state.topic:
            st.session_state.topic = st.session_state.report_name
        if not st.session_state.get('project_name'):
            st.session_state.project_name = _resolve_project_name(st.session_state.report_name)
        from project_store import save_project
        save_project()
        st.session_state.max_step_reached = max(st.session_state.get('max_step_reached', 0), 1)
        st.session_state.step = 1
        st.rerun()
