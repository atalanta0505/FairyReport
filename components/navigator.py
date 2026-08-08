"""Sidebar step navigator."""
import streamlit as st


def step_navigator(step_names: list):
    """Render the sidebar step navigator (locked while streaming)."""
    st.sidebar.divider()
    st.sidebar.caption("📌 步骤导航")

    current = st.session_state.get('step', -1)
    is_locked = st.session_state.get('_busy', False)
    max_reached = st.session_state.get('max_step_reached', current)
    max_step = max(max_reached, current) if current >= 0 else 0
    if max_step > st.session_state.get('max_step_reached', -1):
        st.session_state.max_step_reached = max_step

    # Once chapters are written, the outline stage is locked and cannot be rolled back
    has_written = bool(st.session_state.get('chapters', {}))
    outline_locked = has_written

    if is_locked:
        st.sidebar.warning("⏳ 任务进行中，导航已锁定")
    elif outline_locked:
        st.sidebar.info("📝 已有编写内容，大纲阶段已锁定")

    for i, label in enumerate(step_names):
        # Allow navigation to: completed steps, current step, or next step (current+1)
        allowed = max(max_step, current + 1)
        disabled = is_locked or (i > allowed) or (outline_locked and i == 2)
        is_current = i == current

        # Step icons: completed / current / inactive.
        if i < current:
            icon = "⚪"
        elif is_current:
            icon = "●"
        else:
            icon = "○"

        if st.sidebar.button(
            f"{icon} {label}",
            key=f"nav_step_{i}",
            use_container_width=True,
            disabled=disabled,
            type="primary" if is_current else "secondary",
        ):
            # Auto-save project state before switching steps
            from project_store import save_project
            save_project()
            st.session_state.step = i
            st.rerun()
