"""Project information step for the domain-neutral public edition."""

import streamlit as st

from config import CONSULTING_DOMAINS, REPORT_TYPES, get_word_limit
from project_store import save_project
from utils import _resolve_project_name


def render(llm):
    """Collect the report goal and scope without imposing a domain method."""
    st.header("项目信息")
    st.caption("定义报告要解决的问题；后续结构由目标、资料和受众共同决定。")

    st.session_state.report_name = st.text_input(
        "报告名称",
        value=st.session_state.report_name,
        placeholder="例如：客户体验改进研究报告",
    )

    col_type, col_domain = st.columns(2)
    with col_type:
        known_type = (
            st.session_state.report_type
            if st.session_state.report_type in REPORT_TYPES
            else "自定义"
        )
        selected_type = st.selectbox(
            "报告类型",
            options=REPORT_TYPES,
            index=REPORT_TYPES.index(known_type),
            help="这里只影响默认篇幅和表达方式，不绑定固定模板。",
        )
        if selected_type == "自定义":
            custom_type = st.text_input(
                "自定义报告类型",
                value=(
                    st.session_state.report_type
                    if st.session_state.report_type not in REPORT_TYPES
                    else ""
                ),
                placeholder="输入任意报告类型",
            )
            st.session_state.report_type = custom_type.strip() or "自定义"
        else:
            st.session_state.report_type = selected_type

    with col_domain:
        known_domain = (
            st.session_state.profession
            if st.session_state.profession in CONSULTING_DOMAINS
            else "其他"
        )
        selected_domain = st.selectbox(
            "咨询领域",
            options=CONSULTING_DOMAINS,
            index=CONSULTING_DOMAINS.index(known_domain),
            help="领域仅用于描述语境，不加载任何内置行业知识。",
        )
        if selected_domain == "其他":
            custom_domain = st.text_input(
                "自定义咨询领域",
                value=(
                    st.session_state.profession
                    if st.session_state.profession not in CONSULTING_DOMAINS
                    else ""
                ),
                placeholder="输入行业、职能或议题领域",
            )
            st.session_state.profession = custom_domain.strip() or "其他"
        else:
            st.session_state.profession = selected_domain

    st.session_state.topic = st.text_area(
        "报告目标与核心问题",
        value=st.session_state.topic,
        placeholder="说明报告面向谁、要回答什么问题、支持什么决策，以及已知范围或约束。",
        height=120,
    )

    st.caption(
        f"当前类型默认总篇幅约 {get_word_limit(st.session_state.report_type):,} 字；"
        "可在后续大纲阶段按实际需要调整。"
    )

    st.divider()
    if st.button(
        "📂 准备导入资料",
        type="primary",
        disabled=not st.session_state.report_name,
    ):
        if not st.session_state.topic:
            st.session_state.topic = st.session_state.report_name
        if not st.session_state.get("project_name"):
            st.session_state.project_name = _resolve_project_name(
                st.session_state.report_name
            )
        save_project()
        st.session_state.max_step_reached = max(
            st.session_state.get("max_step_reached", 0), 1
        )
        st.session_state.step = 1
        st.rerun()
