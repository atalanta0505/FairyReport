"""Merge-and-export workflow step."""
import os

import streamlit as st

from project_store import save_project
from utils import _pick_folder
import re

from exporter import md_to_docx
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from outline import parse_chapter_seq
from config import get_word_limit
from ref_manager import (
    _strip_ref_section,
    global_assign_ref_numbers,
    merge_global_refs,
    generate_global_ref_list,
)


def render(llm):
    """Step 5: 合并导出——MD/DOCX 导出"""
    st.header("合并导出")

    chapter_titles = st.session_state.get("chapter_titles", {})
    chapters = st.session_state.get("chapters", {})

    # ── 第一步：合并正文（切除各章 📎 区块）──
    st.subheader("① 合并文本")
    body_parts = []
    for ch_num in sorted(chapter_titles.keys(),
                         key=lambda x: int(x) if isinstance(x, (int, str)) and str(x).lstrip('-').isdigit() else 0):
        content = chapters.get(str(ch_num), "")
        if content:
            ch_title = chapter_titles.get(ch_num, f"第 {ch_num} 章")
            stripped = _strip_ref_section(content)
            # 如果正文已自带章标题（`# 第一章 概述`），不再重复添加
            if stripped.lstrip().startswith(f"# {ch_title}"):
                body_parts.append(stripped)
            else:
                body_parts.append(f"# {ch_title}\n\n{stripped}")

    if not body_parts:
        st.error("没有已完成的章节可导出。至少需完成一章。请通过左侧导航栏返回编写步骤。")
        st.stop()

    full_body = f"# {st.session_state.report_name}\n\n" + "\n\n".join(body_parts)
    total_chars = len(full_body)
    st.caption(f"📊 共 {len(chapters)} 章，{total_chars:,} 字符（正文，不含参考资料区）")

    st.divider()

    # ── 第二步：选择格式 ──
    st.subheader("② 选择格式")
    export_format = st.radio("导出格式", options=["docx", "md"],
                             format_func=lambda x: "📄 Word 文档 (.docx)" if x == "docx" else "📝 Markdown (.md)",
                             horizontal=True)

    # 引用标记选项
    keep_ref_markers = st.checkbox("是否保留引用标记", value=True,
                                   help="保留正文中的 [1][2]...[Z] 引文标记；取消勾选则全部删除")

    st.divider()

    # ── 第三步：选择文件夹导出 ──
    st.subheader("③ 导出到本地文件夹")

    # 在 text_input 渲染之前注入 picked 路径
    if st.session_state.get('_pending_export_dir'):
        st.session_state['export_dir_input'] = st.session_state.pop('_pending_export_dir')

    col_path, col_browse = st.columns([3, 1])
    with col_path:
        export_dir = st.text_input("目标文件夹",
                                   placeholder="选择导出文件夹...",
                                   label_visibility="collapsed",
                                   key="export_dir_input")
    with col_browse:
        if st.button("📁 浏览...", use_container_width=True):
            picked = _pick_folder()
            if picked:
                st.session_state['_pending_export_dir'] = picked
                st.rerun()
            else:
                st.toast("⚠️ 无法弹出文件夹选择对话框（可能运行在无桌面环境）。请手动输入或粘贴路径。", icon="⚠️")

    col_exp, col_new, col_back = st.columns([1, 1, 1])
    with col_exp:
        if st.button("📥 导出", type="primary",
                     disabled=not (export_dir and os.path.isdir(export_dir))):
            out_path = os.path.join(export_dir, f"{st.session_state.project_name}.{export_format}")
            try:
                with st.spinner("正在导出..."):
                    # 若不保留引用标记，先清除标签
                    export_body = full_body
                    if not keep_ref_markers:
                        export_body = _strip_citation_markers(full_body)

                    # 全文一次性编号（标签 → [N]）。
                    numbered_body, numbering = global_assign_ref_numbers(export_body)

                    if export_format == "docx":
                        md_to_docx(numbered_body, out_path)
                        # v13: 在标题后插入 Word TOC 域
                        _insert_toc_after_title(out_path)
                    else:
                        with open(out_path, 'w', encoding='utf-8') as f:
                            f.write(numbered_body)

                # 合并所有章引用清单，生成全局参考资料。
                ref_path = None
                if keep_ref_markers:
                    ref_path = os.path.join(export_dir, f"{st.session_state.project_name}_ref.md")
                    global_refs = merge_global_refs(st.session_state.chapters)
                    ref_content = generate_global_ref_list(global_refs, numbering)
                    with open(ref_path, 'w', encoding='utf-8') as f:
                        f.write(ref_content)

                st.success(f"✅ 已导出到 `{out_path}`")
                if ref_path:
                    st.caption(f"📎 参考资料清单已保存至 `{ref_path}`")
            except Exception as e:
                st.error(f"导出失败：{e}")

    with col_new:
        if st.button("✨ 完成，开始新项目", use_container_width=True):
            save_project()
            from project_store import reset_to_new_project
            reset_to_new_project()
            st.rerun()

    with col_back:
        st.caption("📌 通过左侧导航栏返回其他步骤")


def _insert_toc_after_title(docx_path: str):
    """在 Word 文档标题后插入 TOC 域（Word 打开后右击 → 更新域即可生成目录）。"""
    from docx import Document as _Doc
    doc = _Doc(docx_path)
    if not doc.paragraphs:
        return

    # 构建 TOC 域段落
    toc_para = OxmlElement('w:p')
    toc_run = OxmlElement('w:r')

    # 域开始标记
    fld_begin = OxmlElement('w:fldChar')
    fld_begin.set(qn('w:fldCharType'), 'begin')
    toc_run.append(fld_begin)

    # 域指令：TOC，取 1-5 级标题
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = ' TOC \\o "1-5" \\h \\z \\u '
    toc_run.append(instr)

    # 分隔符
    fld_sep = OxmlElement('w:fldChar')
    fld_sep.set(qn('w:fldCharType'), 'separate')
    toc_run.append(fld_sep)

    # 域结束标记
    fld_end = OxmlElement('w:fldChar')
    fld_end.set(qn('w:fldCharType'), 'end')
    toc_run.append(fld_end)

    toc_para.append(toc_run)

    # 插入到第一个段落（标题）之后
    doc.paragraphs[0]._element.addnext(toc_para)
    doc.save(docx_path)


def _strip_citation_markers(text: str) -> str:
    """删除正文中所有引文标记：【源:xxx】、【网:xxx】、[Z]、【Z】"""
    text = re.sub(r'【(?:源|网):.+?】', '', text)
    text = text.replace('[Z]', '')
    text = text.replace('【Z】', '')
    return text
