"""FairyReport Streamlit application and five-step workflow."""
import sys
import os
import logging
import threading

_logger = logging.getLogger(__name__)

from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from llm import LLMClient
from config import STEP_NAMES, DEFAULT_MODEL, DEFAULT_BASE_URL, SOURCE_URL
from project_store import init_session, save_project, reset_to_new_project
from utils import _update_env
from components.navigator import step_navigator
from components.sidebar import render_settings

# ── Step renderers ──
from steps.step_home import render as render_step_home
from steps.step_project import render as render_step_project
from steps.step_import import render as render_step_import
from steps.step_outline import render as render_step_outline
from steps.step_write_review import render as render_step_write_review
from steps.step_export import render as render_step_export

# ── Page config ──
st.set_page_config(page_title="FairyReport", layout="wide")

# ── Initialization ──
init_session()

api_key = os.getenv("DEEPSEEK_API_KEY", "")

# ── Always allow app entry; warn if API key is missing ──
if not api_key:
    st.warning("⚠️ 未配置 DeepSeek API Key，AI 功能不可用。请进入侧边栏 ⚙️ Settings 配置 API Key、Base URL 和模型。")

# Read latest config from environment so Settings changes can take effect after a rerun.
_current_model = os.getenv("DEFAULT_MODEL", DEFAULT_MODEL)
_current_base_url = os.getenv("DEFAULT_BASE_URL", DEFAULT_BASE_URL)
llm = LLMClient(api_key=api_key, model=_current_model, base_url=_current_base_url)

# ── Background warming of the embedding model ──
def _warmup_embedder():
    try:
        from kb import KnowledgeBase
        KnowledgeBase._get_embedder()
    except Exception as e:
        _logger.warning("后台预热 embedding 模型失败: %s", e)

if api_key and "embedder_warmed" not in st.session_state:
    st.session_state.embedder_warmed = True
    threading.Thread(target=_warmup_embedder, daemon=True).start()

# ── Sidebar + Settings ──
if st.session_state.get("settings_page"):
    if st.sidebar.button("⬅️ 返回", use_container_width=True):
        st.session_state.settings_page = False
        st.rerun()
else:
    is_busy = st.session_state.get('_busy', False)
    if st.session_state.step != -1:
        if st.sidebar.button("🏠 返回首页", use_container_width=True, disabled=is_busy):
            save_project()
            reset_to_new_project()
            st.rerun()

    if st.session_state.step >= 0:
        step_navigator(STEP_NAMES)

    if st.session_state.step >= 0 and st.session_state.get('project_name'):
        st.sidebar.divider()
        st.sidebar.caption("📁 当前项目")
        st.sidebar.markdown(f"**{st.session_state.project_name}**")
        if st.session_state.get('report_type'):
            st.sidebar.caption(f"类型：{st.session_state.report_type}")

    st.sidebar.divider()
    if st.sidebar.button("⚙️ Settings", use_container_width=True, disabled=is_busy):
        st.session_state.settings_page = True
        st.rerun()

st.sidebar.divider()
st.sidebar.caption("FairyReport · AGPL-3.0-only")
if SOURCE_URL:
    st.sidebar.markdown(f"[获取对应源码]({SOURCE_URL})")

if st.session_state.get("settings_page"):
    render_settings(api_key, _update_env)

# ── Step dispatch ──
if st.session_state.step == -1:
    render_step_home(llm)
elif st.session_state.step == 0:
    render_step_project(llm)
elif st.session_state.step == 1:
    render_step_import(llm)
elif st.session_state.step == 2:
    render_step_outline(llm)
elif st.session_state.step == 3:
    render_step_write_review(llm)
elif st.session_state.step == 4:
    render_step_export(llm)
