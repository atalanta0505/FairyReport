"""
FairyReport v1.0.5 - TOC navigation component
"""
import re

import streamlit as st


def _build_toc_tree(outline_md: str) -> list:
    """Parse the hierarchical heading tree from outline MD, return [(level, text, anchor), ...]."""
    tree = []
    for line in outline_md.split('\n'):
        m = re.match(r'^(#{1,5})\s+(.+?)(?:\{.*\})?$', line.strip())
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            anchor = re.sub(r'[^\w\u4e00-\u9fff]', '_', text)[:30]
            tree.append((level, text, anchor))
    return tree


def render_toc(outline_md: str, key_prefix: str = "toc"):
    """Render the TOC navigation panel, return the clicked anchor (if any)."""
    tree = _build_toc_tree(outline_md)
    if not tree:
        st.caption("（无目录）")
        return None

    # Expand/collapse toggle
    if f'{key_prefix}_expanded' not in st.session_state:
        st.session_state[f'{key_prefix}_expanded'] = True

    expanded = st.session_state[f'{key_prefix}_expanded']
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption("📑 目录导航")
    with col2:
        if st.button("收起" if expanded else "展开", key=f"{key_prefix}_toggle", help="切换目录展开/收起"):
            st.session_state[f'{key_prefix}_expanded'] = not expanded
            st.rerun()

    clicked = None
    current_level = 0
    for level, text, anchor in tree:
        if not expanded and level > 1:
            continue
        indent = "  " * (level - 1)
        icon = {1: "📁", 2: "📄", 3: "•", 4: "◦", 5: "▸"}.get(level, "•")
        label = f"{indent}{icon} {text}"
        if st.button(label, key=f"{key_prefix}_{anchor}", help=f"跳转到「{text}」",
                     use_container_width=True):
            clicked = (level, text, anchor)
    return clicked
