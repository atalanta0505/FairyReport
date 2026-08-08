"""FairyReport home page."""
import streamlit as st

from project_store import list_projects, load_project, delete_project, reset_to_new_project
from utils import _resolve_project_name
from config import CONSULTING_DOMAINS, REPORT_TYPES, STEP_NAMES


def render(llm):
    """Step -1: 开始页——新建项目 / 已有项目列表"""
    st.title("开始页")
    st.caption("面向咨询报告工作流的开源编制助手 — FairyReport")
    st.divider()

    st.subheader("✨ 新建项目")
    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_a:
        new_name = st.text_input("报告名称", placeholder="例如：客户体验改进研究报告", key="new_report_name")
    with col_b:
        new_type = st.selectbox("报告类型", options=REPORT_TYPES, index=0, key="new_report_type")
    with col_c:
        new_profession = st.selectbox(
            "咨询领域",
            options=CONSULTING_DOMAINS,
            index=0,
            help="仅用于描述项目语境，不绑定行业模板或内置知识。",
            key="new_profession",
        )
    if st.button("🚀 创建并进入", type="primary", disabled=not new_name):
        # ── 清除旧项目的导入状态，防止残留污染新项目 ──
        st.session_state.imported_files = []
        st.session_state.import_folder = ''
        st.session_state.pop('_import_folder_fingerprint', None)
        # 清除旧 per-file 导入标记
        for k in list(st.session_state.keys()):
            if k.startswith('_per_file_imported_'):
                del st.session_state[k]

        st.session_state.report_name = new_name
        st.session_state.report_type = new_type
        st.session_state.profession = new_profession
        st.session_state.project_name = _resolve_project_name(new_name)
        st.session_state.step = 0
        st.rerun()

    st.divider()
    st.subheader("📂 已有项目")
    projects = list_projects()
    if not projects:
        st.info("暂无项目，请新建。")
    else:
        for proj in projects:
            prof_tag = f"｜{proj['profession']}" if proj.get('profession') else ''
            with st.expander(
                f"**{proj['report_name']}** — {proj['report_type']} {prof_tag}  "
                f"{'| 已更新 ' + proj['updated_at'] if proj['updated_at'] else ''}",
                expanded=False,
            ):
                if proj['chapters_total'] > 0:
                    st.progress(proj['chapters_done'] / proj['chapters_total'],
                                text=f"章节进度 {proj['chapters_done']}/{proj['chapters_total']}")
                step_idx = proj['step']
                label = STEP_NAMES[step_idx] if 0 <= step_idx < len(STEP_NAMES) else '初始'
                st.caption(f"当前步骤：{label}")
                col_open, col_del = st.columns([1, 1])
                with col_open:
                    if st.button("📂 打开项目", key=f"open_{proj['name']}"):
                        with st.spinner("正在加载项目..."):
                            load_project(proj['name'])
                        st.rerun()
                with col_del:
                    if st.button("🗑️ 删除", key=f"del_{proj['name']}"):
                        st.session_state[f"_confirm_delete_{proj['name']}"] = True
                        st.rerun()
                if st.session_state.get(f"_confirm_delete_{proj['name']}"):
                    st.warning(f"⚠️ 确认删除「{proj['report_name']}」？")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("✅ 确认删除", key=f"del_ok_{proj['name']}", type="primary"):
                            with st.spinner("正在删除项目..."):
                                delete_project(proj['name'])
                            st.session_state[f"_confirm_delete_{proj['name']}"] = False
                            # 删除后清除 session_state 中的对应 KB 缓存
                            kb_cache_key = f"_kb_{proj['name']}"
                            st.session_state.pop(kb_cache_key, None)
                            import gc
                            gc.collect()
                            st.rerun()
                    with cc2:
                        if st.button("❌ 取消", key=f"del_cancel_{proj['name']}"):
                            st.session_state[f"_confirm_delete_{proj['name']}"] = False
                            st.rerun()
