"""Chapter-writing, review, and reference workflow step."""
import streamlit as st
import time

from project_store import save_project, load_project
from utils import _sync_chapter_title_to_outline
from outline import OutlineGenerator
from writer import ChapterWriter, _count_chinese_chars, _count_content_chars
from config import get_word_limit, get_chapter_word_budget, is_summary_chapter, PROJECTS_DIR
import hint_store
import ref_manager
import web_search


def _render_word_count_info(ch_content: str, ch_key: str, report_type: str,
                             ch_title: str, ch_seq: int) -> None:
    """渲染字数提示信息（编写页和审阅页共用）。

    计数器包含全角标点，因此使用 85%/115% 阈值。
    """
    wc = _count_content_chars(ch_content)   # 正文（不含标题）
    budget = get_chapter_word_budget(report_type, ch_seq)
    if budget <= 0:
        return
    ratio = wc / budget
    if 0.85 <= ratio <= 1.15:
        pct = int(ratio * 100)
        st.caption(f"📊 正文字数 **{wc:,}** 字，计划 **{budget:,}** 字，"
                   f"实际为计划的 **{pct}%**，达标 ✓")
    elif ratio < 0.85:
        st.caption(f"📊 正文字数 **{wc:,}** 字，计划 **{budget:,}** 字，"
                   f"少于计划的 85%，建议充实内容")
    else:
        over = int((ratio - 1) * 100)
        st.warning(f"📊 正文字数 **{wc:,}** 字，计划 **{budget:,}** 字，"
                   f"超出计划 **{over}%**，请适当缩减篇幅")


def _render_writing_order_list(writing_order, chapter_titles, chapters, current_idx, disabled=False):
    """渲染可点击的写作顺序列表。返回被点击的章序号（或 None）。

    disabled=True 时所有按钮禁用（长耗时操作期间锁定章导航）。
    """
    clicked = None
    current_ch_num = writing_order[current_idx] if current_idx < len(writing_order) else None
    current_ch_title = chapter_titles.get(current_ch_num, f"第{current_ch_num}章") if current_ch_num else ""

    for i, ch_num in enumerate(writing_order):
        ch_key = str(ch_num)
        ch_title = chapter_titles.get(ch_num, f"第{ch_num}章")

        # 状态图标
        if ch_key in chapters:
            icon = "✅"
            status = ""
        elif i == current_idx:
            icon = "✍️"
            status = " ← 当前"
        else:
            icon = "○"
            status = ""

        label = f"{icon} {i+1}. {ch_title}{status}"

        # 已完成 → 点击在本页浏览（只读，不可编辑）
        if ch_key in chapters:
            if st.button(label, key=f"wo_done_{ch_key}", use_container_width=True,
                         disabled=disabled,
                         help=f"点击在本页浏览「{ch_title}」（只读模式，修改请至「审阅」标签页）"):
                clicked = ("view_completed", ch_num)
        else:
            btn_type = "primary" if i == current_idx else "secondary"
            btn_help = ""
            if i < current_idx:
                # 前面的未完成章（可能是跳过的）
                btn_help = f"点击开始编写「{ch_title}」"
            elif i > current_idx:
                btn_help = f"⚠️ 请按写作顺序依次编写各章，当前请先完成「{current_ch_title}」"
            if st.button(label, key=f"wo_{ch_key}", use_container_width=True,
                         type=btn_type, disabled=disabled, help=btn_help):
                if i > current_idx:
                    clicked = ("warning", ch_num, current_ch_title)
                else:
                    clicked = ("write", ch_num)

    return clicked


def render(llm):
    """Step 3: 编写 & 审阅——Tab 切换式布局"""
    st.header("编写 & 审阅")

    # ── 全局样式：允许按钮内文字换行，解决长章标题被截断问题 ──
    st.markdown("""
    <style>
    div[data-testid="stButton"] button {
        white-space: normal !important;
        word-wrap: break-word !important;
        text-align: left !important;
        height: auto !important;
        min-height: 2.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    writer = ChapterWriter(llm, report_type=st.session_state.report_type,
                           total_words=get_word_limit(st.session_state.report_type))
    from kb import KnowledgeBase
    # 首次加载提示：embedding 模型 + ChromaDB 初始化约需 10-30 秒
    is_first = st.session_state.project_name not in KnowledgeBase._instance_cache
    if is_first:
        load_placeholder = st.empty()
        load_placeholder.info(
            "⏳ **正在加载知识库**（首次打开约需 10-30 秒），请耐心等待，不是卡住了喔^_^\n\n"
            "> 加载内容：embedding 模型 + 向量数据库索引\n"
            "> 后续打开将直接命中缓存，无需等待。"
        )
        t0 = time.time()

    kb = KnowledgeBase.get_instance(
        st.session_state.project_name,
        str(PROJECTS_DIR / st.session_state.project_name / "vector_db"))

    if is_first:
        elapsed = time.time() - t0
        load_placeholder.success(
            f"✅ 知识库加载完成（耗时 {elapsed:.1f} 秒），后续打开将秒开。"
        )


    # ── 状态变量 ──
    writing_order = st.session_state.get('writing_order', [])
    chapter_titles = st.session_state.get("chapter_titles", {})
    chapters = st.session_state.chapters
    total = len(writing_order)
    done = len(chapters)
    current_order_idx = st.session_state.get('current_order_idx', 0)

    # 提前计算 is_streaming（Tab 命名和锁定需要）
    is_streaming = st.session_state.get('_busy', False)

    # ── 顶部进度条 ──
    if total > 0:
        progress = done / total
        st.progress(progress, text=f"📝 进度：{done}/{total} 章已完成 | 写作顺序已定")
    else:
        st.info("暂无大纲，请先返回「确定大纲」步骤生成大纲。")
        st.stop()

    # ── Tab 布局（session-state 控制，避免 st.tabs() 跨 rerun 丢失选中状态）──
    if '_step3_active_tab' not in st.session_state:
        st.session_state['_step3_active_tab'] = 'write'
    active_tab = st.session_state['_step3_active_tab']

    tab_options = ["🖊️ 编写", "📋 审阅", "📚 参考资料"]
    if is_streaming:
        tab_options = ["🖊️ 编写中…", "📋 审阅 (暂不可用)", "📚 参考资料 (暂不可用)"]

    tab_index = 0 if active_tab == 'write' else 1 if active_tab == 'review' else 2
    selected_tab_label = st.radio(
        "视图切换", tab_options, index=tab_index,
        horizontal=True, label_visibility="collapsed",
        key="_step3_tab_radio",
        disabled=is_streaming
    )
    # 同步 radio 选择到 session state
    if "编写" in selected_tab_label and "暂不可用" not in selected_tab_label:
        st.session_state['_step3_active_tab'] = 'write'
    elif "审阅" in selected_tab_label and "暂不可用" not in selected_tab_label:
        st.session_state['_step3_active_tab'] = 'review'
    elif "参考资料" in selected_tab_label and "暂不可用" not in selected_tab_label:
        st.session_state['_step3_active_tab'] = 'references'
    active_tab = st.session_state['_step3_active_tab']

    # AI 修改在顶层分发，避免审阅页锁定时死锁。
    if is_streaming:
        busy_reason = st.session_state.get('_busy_reason', '')

        # mod_gen_hint: AI 修改 — 生成新提示词
        if busy_reason == 'mod_gen_hint':
            st.session_state._busy_reason = None
            ch_num = st.session_state.pop('_busy_ch', None)
            if ch_num is not None:
                ch_key = str(ch_num)
                ch_title = chapter_titles.get(ch_num, f"第{ch_num}章")
                mod_key = f"_review_mod_{ch_key}"
                modify_instr = st.session_state.get(f"_mod_instr_{ch_key}", "")
                try:
                    with st.spinner("💡 正在生成新提示词…"):
                        pred_hints = hint_store.get_predecessor_hints(
                            st.session_state.project_name, writing_order, ch_num)
                        existing_hint = hint_store.load_hint(
                            st.session_state.project_name, ch_num)
                        new_hint = writer.generate_hint(
                            ch_title, ch_num,
                            st.session_state.outline_md, writing_order,
                            predecessor_hints=pred_hints,
                            report_name=st.session_state.report_name,
                            user_instruction=modify_instr,
                            existing_hint=existing_hint)
                        st.session_state[f"_mod_hint_pending_{ch_key}"] = new_hint
                        st.session_state[mod_key] = False
                except Exception as e:
                    st.error(f"提示词生成失败：{e}")
                    st.session_state[mod_key] = False
                finally:
                    st.session_state._busy = False
                st.rerun()

        # mod_regen_hint: AI 修改 — 重新生成提示词
        elif busy_reason == 'mod_regen_hint':
            st.session_state._busy_reason = None
            ch_num = st.session_state.pop('_busy_ch', None)
            if ch_num is not None:
                ch_key = str(ch_num)
                ch_title = chapter_titles.get(ch_num, f"第{ch_num}章")
                modify_instr = st.session_state.get(f"_mod_instr_{ch_key}", "")
                try:
                    with st.spinner("💡 正在重新生成…"):
                        pred_hints = hint_store.get_predecessor_hints(
                            st.session_state.project_name, writing_order, ch_num)
                        existing_hint = hint_store.load_hint(
                            st.session_state.project_name, ch_num)
                        new_hint = writer.generate_hint(
                            ch_title, ch_num,
                            st.session_state.outline_md, writing_order,
                            predecessor_hints=pred_hints,
                            report_name=st.session_state.report_name,
                            user_instruction=modify_instr,
                            existing_hint=existing_hint)
                        st.session_state[f"_mod_hint_pending_{ch_key}"] = new_hint
                except Exception as e:
                    st.error(f"提示词生成失败：{e}")
                finally:
                    st.session_state._busy = False
                st.rerun()

        # mod_stream: AI 修改 — 执行重写（完整编写流水线）
        elif busy_reason == 'mod_stream':
            st.session_state._busy_reason = None
            ch_num = st.session_state.pop('_busy_ch', None)
            if ch_num is not None:
                ch_key = str(ch_num)
                if st.session_state.get(f"_mod_confirmed_{ch_key}"):
                    confirmed_hint = st.session_state.pop(f"_mod_confirmed_{ch_key}")
                    ch_title = chapter_titles.get(ch_num, f"第{ch_num}章")
                    ch_seq = ch_num if isinstance(ch_num, int) else int(ch_num) if str(ch_num).isdigit() else 0

                    with st.status("✍️ 正在按新提示词重写本章…", expanded=True) as write_status:
                        st.write("🔍 检索项目资料库…")
                        rag_context = kb.query(
                            ch_title + " " + st.session_state.report_name, n_results=5,
                            include_generic=False)
                        st.write("🌐 搜索网络参考资料…")
                        web_context = web_search.search(
                            ch_title + " " + st.session_state.report_name)
                        if web_context:
                            rag_context += "\n\n" + web_context

                        st.session_state['_stream_buffer'] = ""
                        mod_stream_placeholder = st.empty()

                        def on_mod_rewrite_chunk(delta):
                            st.session_state['_stream_buffer'] += delta
                            mod_stream_placeholder.markdown(
                                f'<div style="border: 1px solid #ddd; border-radius: 8px; '
                                f'padding: 16px; font-size: 0.92em; background: #fafafa; '
                                f'line-height: 1.7; max-height: 600px; max-width: 900px; '
                                f'margin: 0 auto; overflow-y: auto; min-height: 200px;">'
                                f'{st.session_state["_stream_buffer"]}</div>',
                                unsafe_allow_html=True)

                        st.write("📝 AI 正在按新提示词重写…")
                        try:
                            pred_seqs = hint_store.get_predecessor_seqs(writing_order, ch_num)
                            pred_chapters = {
                                str(s): chapters[str(s)]
                                for s in pred_seqs if str(s) in chapters
                            }
                            new_content = writer.write_chapter_with_control(
                                ch_title, st.session_state.outline_md,
                                pred_chapters, rag_context,
                                st.session_state.topic,
                                callback=on_mod_rewrite_chunk,
                                writing_hint=confirmed_hint,
                                report_name=st.session_state.report_name)
                            # 清洗模型编造的来源标签。
                            new_content = ref_manager.strip_fabricated_labels(new_content, rag_context)
                            # 提取引用标签并生成参考资料区块。
                            ch_refs = ref_manager.extract_chapter_refs(new_content, rag_context)
                            if ch_refs:
                                ref_section = ref_manager.build_chapter_ref_section(ch_refs)
                                new_content = new_content + "\n\n" + ref_section
                            mod_stream_placeholder.markdown(
                                f'<div style="border: 1px solid #ddd; border-radius: 8px; '
                                f'padding: 16px; font-size: 0.92em; background: #fafafa; '
                                f'line-height: 1.7; max-width: 900px; margin: 0 auto;">'
                                f'{new_content}</div>',
                                unsafe_allow_html=True)
                            chapters[ch_key] = new_content
                            st.session_state.chapters = chapters
                            _stale = st.session_state.get('_stale_chapters', set())
                            _stale.discard(ch_key)
                            # 标记写作顺序中排在本章之后的所有章为“过期”。
                            writing_order = st.session_state.get('writing_order', [])
                            if ch_num in writing_order:
                                pos = writing_order.index(ch_num)
                                downstream = writing_order[pos + 1:]
                                for ds_num in downstream:
                                    ds_key = str(ds_num)
                                    if ds_key in chapters and ds_key != ch_key:
                                        _stale.add(ds_key)
                            st.session_state['_stale_chapters'] = _stale
                            save_project()
                        except Exception as e:
                            st.session_state._busy = False
                            st.error(f"重写失败：{e}")
                            st.stop()
                        write_status.update(label="✅ 重写完成", state="complete")
                    st.session_state._busy = False
                    st.rerun()

        # quality_review: execute the domain-neutral method review
        elif busy_reason == 'quality_review':
            st.session_state._busy_reason = None
            ch_num = st.session_state.pop('_busy_ch', None)
            if ch_num is not None:
                ch_key = str(ch_num)
                ch_title = chapter_titles.get(ch_num, f"第{ch_num}章")
                ch_content = chapters.get(ch_key, "")
                try:
                    with st.spinner("🔍 正在进行方法质量校核…"):
                        from config import QUALITY_REVIEW_SYSTEM_PROMPT
                        from writer import parse_quality_review_result
                        review_prompt = (
                            f"# 章节标题\n{ch_title}\n\n"
                            f"# 章节正文\n{ch_content}\n\n"
                            f"# 报告类型\n{st.session_state.report_type}\n\n"
                            f"请按照方法质量校核规则，对以上章节进行校核。"
                        )
                        result = llm.chat(
                            review_prompt,
                            system_prompt=QUALITY_REVIEW_SYSTEM_PROMPT,
                            temperature=0.15,
                        )
                        # Parse and validate the quality-review output.
                        parsed = parse_quality_review_result(result)
                        if parsed.get("parse_error"):
                            # Retry once on parse failure
                            result2 = llm.chat(
                                review_prompt + "\n\n⚠️ 上次输出格式有误，请务必按指定格式输出：状态、原因、详情、建议。",
                                system_prompt=QUALITY_REVIEW_SYSTEM_PROMPT,
                                temperature=0.1,
                            )
                            parsed = parse_quality_review_result(result2)
                        st.session_state[f"_quality_review_result_{ch_key}"] = result
                        st.session_state[f"_quality_review_parsed_{ch_key}"] = parsed
                        st.session_state[f"_quality_review_pending_{ch_key}"] = False
                        # Persist the structured result for save/load.
                        st.session_state.setdefault('_quality_review_results', {})[ch_key] = {
                            "status": parsed.get("status", ""),
                            "reason": parsed.get("reason", ""),
                            "details": parsed.get("details", ""),
                            "suggestions": parsed.get("suggestions", ""),
                            "data_gap_checklist": parsed.get("data_gap_checklist", []),
                        }
                        save_project()
                except Exception as e:
                    st.error(f"质量校核失败：{e}")
                    st.session_state[f"_quality_review_pending_{ch_key}"] = False
                finally:
                    st.session_state._busy = False
                st.rerun()

        # 安全阀：未匹配任何已知 busy_reason → 重置 _busy 避免死锁
        _KNOWN_REASONS = {'gen_hint', 'regen_hint', 'stream_write',
                          'gen_outline',
                          'mod_gen_hint', 'mod_regen_hint', 'mod_stream',
                          'quality_review'}
        if busy_reason not in _KNOWN_REASONS:
            st.session_state._busy = False
            st.rerun()

    # ═══════════════════════════════════════
    # Tab 1：编写视图（100% 宽度）
    # ═══════════════════════════════════════
    if active_tab == 'write':
        col_wo, col_content = st.columns([1, 4])

        # ── 写作顺序列表 ──
        with col_wo:
            with st.container(border=True):
                st.caption("写作顺序（点击跳转）")
                clicked = _render_writing_order_list(
                    writing_order, chapter_titles, chapters, current_order_idx,
                    disabled=is_streaming)

                if clicked:
                    action = clicked[0]
                    target = clicked[1]
                    if action == "view_completed":
                        # 在编写页浏览已完成章（只读），不跳审阅
                        st.session_state['_viewing_completed_chapter'] = target
                        st.rerun()
                    elif action == "warning":
                        ch_num = target
                        current_ch_title = clicked[2]
                        st.toast(f"⚠️ 请按写作顺序依次编写各章，当前请先完成「{current_ch_title}」", icon="⚠️")
                    elif action == "write":
                        # 找到该章在 writing_order 中的位置
                        try:
                            new_idx = writing_order.index(target)
                            st.session_state.current_order_idx = new_idx
                            st.session_state['_step3_active_tab'] = 'write'
                        except ValueError:
                            pass
                        save_project()
                        st.rerun()

        # ── 当前章内容（宽区域）──
        with col_content:
            # 检查是否正在浏览已完成章（只读模式）
            viewing_ch = st.session_state.pop('_viewing_completed_chapter', None)
            if viewing_ch is not None and str(viewing_ch) in chapters:
                v_key = str(viewing_ch)
                v_title = chapter_titles.get(viewing_ch, f"第{viewing_ch}章")
                v_content = chapters[v_key]

                st.subheader(f"📖 {v_title}")
                v_seq = viewing_ch if isinstance(viewing_ch, int) else int(viewing_ch) if str(viewing_ch).isdigit() else 0
                _render_word_count_info(v_content, v_key, st.session_state.report_type, v_title, v_seq)
                st.caption("🔒 **只读浏览** — 本章已在当前进度之前完成。如需修改，请切换到「📋 审阅」标签页操作。")
                st.markdown(
                    f'<div style="border: 1px solid #ddd; border-radius: 8px; '
                    f'padding: 16px; font-size: 0.92em; background: #fafafa; '
                    f'line-height: 1.7; max-height: 600px; max-width: 900px; '
                    f'margin: 0 auto; overflow-y: auto;">'
                    f'{v_content}</div>',
                    unsafe_allow_html=True
                )
                st.divider()
                col_v1, col_v3 = st.columns([1, 2])
                with col_v1:
                    if st.button("🔄 返回当前章", key="back_to_current", use_container_width=True, type="primary"):
                        st.rerun()

            elif current_order_idx >= total:
                # 全部章节都过了一遍
                remaining = [n for n in writing_order if str(n) not in chapters]

                if remaining:
                    st.info(f"还有 {len(remaining)} 章未处理，请在写作顺序列表中点击开始编写。")
                else:
                    st.success("🎉 全部章节编写完成！无需额外操作，可在下方导航栏进入导出，或切换到「📋 审阅」标签查看全文。")

            else:
                # 当前章
                ch_num = writing_order[current_order_idx]
                ch_key = str(ch_num)
                ch_title = chapter_titles.get(ch_num, f"第 {ch_num} 章")
                ch_seq = ch_num if isinstance(ch_num, int) else int(ch_num) if ch_num.isdigit() else 0
                budget = get_chapter_word_budget(st.session_state.report_type, ch_seq)
                is_summary = is_summary_chapter(st.session_state.report_type, ch_seq)

                st.subheader(f"{ch_title}")
                if budget > 0:
                    tag = "综述章" if is_summary else "普通章"
                    st.caption(f"💰 正文字数建议：{budget:,} 字 ({tag})，标题不计入")

                # writing_hint
                hint = OutlineGenerator.get_hint(st.session_state.get('outline_json', {}), ch_num)
                if hint:
                    with st.expander("💡 编写提示", expanded=False):
                        st.info(hint)

                # 流式输出占位
                stream_placeholder = st.empty()

                # 已编写 → 显示已有内容
                if ch_key in chapters:
                    ch_content = chapters[ch_key]
                    # 字数提示
                    _render_word_count_info(ch_content, ch_key, st.session_state.report_type, ch_title, ch_seq)
                    _stale = st.session_state.get('_stale_chapters', set())
                    if ch_key in _stale:
                        st.info("💡 本章的上下文已过期（前序章被修改或新资料导入），建议重写。")

                    # 流式输出样式容器（全宽居中优化）
                    st.markdown(
                        f'<div style="border: 1px solid #ddd; border-radius: 8px; '
                        f'padding: 16px; font-size: 0.92em; background: #fafafa; '
                        f'line-height: 1.7; max-height: 600px; max-width: 900px; '
                        f'margin: 0 auto; overflow-y: auto;">'
                        f'{ch_content}</div>',
                        unsafe_allow_html=True
                    )

                    st.divider()

                    col_b1, col_b2 = st.columns([1, 1])
                    with col_b1:
                        if st.button("🔄 重新生成", key=f"regen_{ch_key}", use_container_width=True,
                                     disabled=is_streaming):
                            # 删除已有内容，重新生成
                            if ch_key in chapters:
                                del chapters[ch_key]
                            stream_placeholder.empty()
                            save_project()
                            st.rerun()
                    with col_b2:
                        is_last = (current_order_idx + 1 >= total)
                        label = "✅ 全部完成 ✓" if is_last else "➡️ 下一章"
                        if st.button(label, key=f"next_{ch_key}", use_container_width=True,
                                     type="primary" if is_last else "secondary",
                                     disabled=is_streaming):
                            old_t, new_t = _sync_chapter_title_to_outline(ch_key, ch_content)
                            st.session_state.current_order_idx += 1
                            save_project()
                            st.rerun()

                else:
                    # ── 三阶段编写流程 ──
                    hint_generated_key = f"_write_hint_pending_{ch_key}"
                    hint_confirmed_key = f"_write_confirmed_{ch_key}"

                    # 阶段 3：提示词已确认 → 执行编写（两阶段：先锁 UI，再流式）
                    if st.session_state.get(hint_confirmed_key):
                        if is_streaming and st.session_state.get('_busy_reason') == 'stream_write':
                            st.session_state._busy_reason = None
                            confirmed_hint = st.session_state.pop(hint_confirmed_key)
                            with st.status("✍️ 正在编写…", expanded=True) as write_status:
                                st.write("🔍 检索知识库…")
                                rag_context = kb.query(
                                    ch_title + " " + st.session_state.report_name, n_results=5)

                                st.write("🌐 搜索网络参考资料…")
                                web_context = web_search.search(
                                    ch_title + " " + st.session_state.report_name)
                                if web_context:
                                    rag_context += "\n\n" + web_context

                                st.session_state['_stream_buffer'] = ""
                                # _busy 已在 Phase 1 设为 True，此处不重复设置

                                def on_chunk(delta):
                                    st.session_state['_stream_buffer'] += delta
                                    stream_placeholder.markdown(
                                        f'<div style="border: 1px solid #ddd; border-radius: 8px; '
                                        f'padding: 16px; font-size: 0.92em; background: #fafafa; '
                                        f'line-height: 1.7; max-height: 600px; max-width: 900px; '
                                        f'margin: 0 auto; overflow-y: auto; min-height: 200px;">'
                                        f'{st.session_state["_stream_buffer"]}</div>',
                                        unsafe_allow_html=True
                                    )

                                st.write("📝 AI 正在生成内容…")
                                try:
                                    pred_seqs = hint_store.get_predecessor_seqs(writing_order, ch_num)
                                    pred_chapters = {
                                        str(s): chapters[str(s)]
                                        for s in pred_seqs if str(s) in chapters
                                    }
                                    content = writer.write_chapter_with_control(
                                        ch_title, st.session_state.outline_md,
                                        pred_chapters, rag_context,
                                        st.session_state.topic, callback=on_chunk,
                                        writing_hint=confirmed_hint,
                                        report_name=st.session_state.report_name)
                                    # 清洗模型编造的来源标签。
                                    content = ref_manager.strip_fabricated_labels(content, rag_context)
                                    # 提取引用标签并生成参考资料区块。
                                    ch_refs = ref_manager.extract_chapter_refs(content, rag_context)
                                    if ch_refs:
                                        ref_section = ref_manager.build_chapter_ref_section(ch_refs)
                                        content = content + "\n\n" + ref_section
                                    stream_placeholder.markdown(
                                        f'<div style="border: 1px solid #ddd; border-radius: 8px; '
                                        f'padding: 16px; font-size: 0.92em; background: #fafafa; '
                                        f'line-height: 1.7; max-width: 900px; margin: 0 auto;">'
                                        f'{content}</div>',
                                        unsafe_allow_html=True
                                    )
                                except Exception as e:
                                    st.session_state._busy = False
                                    st.error(f"❌ 编写失败：{e}")
                                    st.stop()
                                write_status.update(label="✅ 编写完成", state="complete")
                            st.session_state._busy = False
                            chapters[ch_key] = content
                            # 标记写作顺序中排在本章之后的所有已存在章为“过期”。
                            writing_order = st.session_state.get('writing_order', [])
                            if ch_num in writing_order:
                                pos = writing_order.index(ch_num)
                                downstream = writing_order[pos + 1:]
                                _stale = st.session_state.get('_stale_chapters', set())
                                _stale.discard(ch_key)
                                for ds_num in downstream:
                                    ds_key = str(ds_num)
                                    if ds_key in chapters:
                                        _stale.add(ds_key)
                                st.session_state['_stale_chapters'] = _stale
                            save_project()
                            st.rerun()
                        else:
                            # Phase 1: 设置 busy 并 rerun，让 UI 先锁定
                            st.session_state._busy = True
                            st.session_state._busy_reason = 'stream_write'
                            st.rerun()

                    # 阶段 2：提示词已生成 → 展示并等待确认
                    elif st.session_state.get(hint_generated_key):
                        pending_hint = st.session_state[hint_generated_key]
                        st.info("💡 编写提示词（可编辑后确认）")
                        edited_hint = st.text_area(
                            "提示词内容", value=pending_hint, height=240,
                            key=f"write_hint_edit_{ch_key}", label_visibility="collapsed",
                            disabled=is_streaming)
                        col_h1, col_h2 = st.columns([2, 1])
                        with col_h1:
                            if st.button("✍️ 确认提示词并开始编写",
                                         key=f"confirm_write_hint_{ch_key}",
                                         type="primary", use_container_width=True,
                                         disabled=is_streaming):
                                hint_store.save_hint(st.session_state.project_name, ch_num, edited_hint)
                                OutlineGenerator.update_outline_json_hint(
                                    st.session_state.outline_json, ch_num, edited_hint)
                                st.session_state.pop(hint_generated_key)
                                st.session_state[hint_confirmed_key] = edited_hint
                                save_project()
                                st.session_state._busy = True
                                st.session_state._busy_reason = 'stream_write'
                                st.rerun()
                        with col_h2:
                            # ── 两阶段：UI 已锁定，执行重新生成 ──
                            if is_streaming and st.session_state.get('_busy_reason') == 'regen_hint':
                                st.session_state._busy_reason = None
                                try:
                                    with st.spinner("💡 正在重新生成提示词…"):
                                        try:
                                            pred_hints = hint_store.get_predecessor_hints(
                                                st.session_state.project_name,
                                                writing_order, ch_num)
                                            new_hint = writer.generate_hint(
                                                ch_title, ch_num,
                                                st.session_state.outline_md,
                                                writing_order,
                                                predecessor_hints=pred_hints,
                                                report_name=st.session_state.report_name)
                                            st.session_state[hint_generated_key] = new_hint
                                        except Exception as e:
                                            st.error(f"提示词生成失败：{e}")
                                finally:
                                    st.session_state._busy = False
                                st.rerun()

                            if st.button("🔄 重新生成", key=f"regen_write_hint_{ch_key}",
                                         use_container_width=True, disabled=is_streaming):
                                st.session_state._busy = True
                                st.session_state._busy_reason = 'regen_hint'
                                st.rerun()

                    # 阶段 1：未生成提示词 → 显示生成按钮
                    else:
                        # ── 防御：刷新后 session_state 丢失，磁盘可能已有提示词 ──
                        existing_hint = hint_store.load_hint(st.session_state.project_name, ch_num)
                        if existing_hint:
                            st.session_state[hint_generated_key] = existing_hint
                            st.rerun()

                        # ── 两阶段：UI 已锁定，执行实际操作 ──
                        if is_streaming and st.session_state.get('_busy_reason') == 'gen_hint':
                            st.session_state._busy_reason = None
                            try:
                                with st.spinner("💡 正在生成编写提示词…"):
                                    try:
                                        pred_hints = hint_store.get_predecessor_hints(
                                            st.session_state.project_name,
                                            writing_order, ch_num)
                                        hint = writer.generate_hint(
                                            ch_title, ch_num,
                                            st.session_state.outline_md,
                                            writing_order,
                                            predecessor_hints=pred_hints,
                                            report_name=st.session_state.report_name)
                                        st.session_state[hint_generated_key] = hint
                                    except Exception as e:
                                        st.error(f"提示词生成失败：{e}")
                            finally:
                                st.session_state._busy = False
                            st.rerun()

                        btn_disabled = is_streaming
                        if st.button("💡 生成编写提示词", key=f"gen_hint_{ch_key}",
                                     type="primary", use_container_width=True,
                                     disabled=btn_disabled):
                            st.session_state._busy = True
                            st.session_state._busy_reason = 'gen_hint'
                            st.rerun()

    # ═══════════════════════════════════════
    # Tab 2：审阅视图（100% 宽度）
    # ═══════════════════════════════════════
    elif active_tab == 'review':
        # 流式输出期间，审阅 Tab 锁定
        if is_streaming:
            st.info("⏳ 当前章节正在编写中，完成后可切换审阅")
        else:
            # ── 审阅子 Tabs（也用 radio 保持状态）──
            review_tab = st.session_state.get('_review_tab', 'overview')
            sub_tab_options = ["📋 章节总览", "📄 全文预览", "📊 字数分布"]
            sub_index = 0
            if review_tab == 'preview':
                sub_index = 1
            elif review_tab == 'stats':
                sub_index = 2

            selected_sub = st.radio(
                "审阅视图", sub_tab_options, index=sub_index,
                horizontal=True, label_visibility="collapsed",
                key="_step3_review_sub_radio"
            )
            if "章节总览" in selected_sub:
                st.session_state['_review_tab'] = 'overview'
            elif "全文预览" in selected_sub:
                st.session_state['_review_tab'] = 'preview'
            elif "字数分布" in selected_sub:
                st.session_state['_review_tab'] = 'stats'
            review_tab = st.session_state['_review_tab']

            # ── 章节总览（可编辑 + AI 修改）──
            if review_tab == 'overview':
                st.session_state['_review_tab'] = 'overview'

                if not chapters:
                    st.info("暂无已完成的章节。编写完成后会出现在这里。")
                else:
                    st.caption(f"共 {len(chapters)} 章，可展开编辑")

                    # 自动聚焦
                    focus_key = st.session_state.pop('_review_focus', None)

                    for num in sorted(chapter_titles.keys(),
                                      key=lambda x: int(x) if isinstance(x, (int, str)) and str(x).lstrip('-').isdigit() else 0):
                        ch_key = str(num)
                        if ch_key not in chapters:
                            continue

                        ch_title = chapter_titles.get(num, f"第 {num} 章")
                        ch_content = chapters.get(ch_key, "")

                        _stale = st.session_state.get('_stale_chapters', set())
                        stale_badge = " 🟡 上下文已过期" if ch_key in _stale else ""
                        title_text = f"**{ch_title}{stale_badge}**"

                        expanded = (focus_key == ch_key)
                        with st.expander(title_text, expanded=expanded):

                            mod_key = f"_review_mod_{ch_key}"
                            is_modifying = st.session_state.get(mod_key)

                            if is_modifying:
                                # ── 修改面板：输入修改意图 ──
                                # 展示原文，方便用户对照写修改意见
                                with st.container(border=True):
                                    st.caption("📖 原文内容（修改后将基于新提示词重写本章）")
                                    st.markdown(
                                        f'<div style="border: 1px solid #ddd; border-radius: 8px; '
                                        f'padding: 16px; font-size: 0.92em; background: #fafafa; '
                                        f'line-height: 1.7; max-height: 400px; max-width: 900px; '
                                        f'margin: 0 auto; overflow-y: auto;">'
                                        f'{ch_content}</div>',
                                        unsafe_allow_html=True)

                                modify_instr = st.text_area(
                                    "修改意见", key=f"review_instr_{ch_key}",
                                    height=80, placeholder="输入修改意见…")
                                cr1, cr2 = st.columns(2)
                                with cr1:
                                    # ── 两阶段：UI 已锁定，执行 AI 修改提示词生成 ──
                                    if is_streaming and st.session_state.get('_busy_reason') == 'mod_gen_hint':
                                        st.session_state._busy_reason = None
                                        ch_num_saved = st.session_state.pop('_busy_ch', num)
                                        ch_key_saved = str(ch_num_saved)
                                        modify_instr = st.session_state.get(f"_mod_instr_{ch_key_saved}", "")
                                        try:
                                            with st.spinner("💡 正在生成新提示词…"):
                                                try:
                                                    pred_hints = hint_store.get_predecessor_hints(
                                                        st.session_state.project_name,
                                                        writing_order, ch_num_saved)
                                                    existing_hint = hint_store.load_hint(
                                                        st.session_state.project_name, ch_num_saved)
                                                    new_hint = writer.generate_hint(
                                                        ch_title, ch_num_saved,
                                                        st.session_state.outline_md,
                                                        writing_order,
                                                        predecessor_hints=pred_hints,
                                                        report_name=st.session_state.report_name,
                                                        user_instruction=modify_instr,
                                                        existing_hint=existing_hint)
                                                    st.session_state[f"_mod_hint_pending_{ch_key_saved}"] = new_hint
                                                    st.session_state[f"_mod_instr_{ch_key_saved}"] = modify_instr
                                                    st.session_state[mod_key] = False
                                                except Exception as e:
                                                    st.error(f"提示词生成失败：{e}")
                                                    st.session_state[mod_key] = False
                                        finally:
                                            st.session_state._busy = False
                                        st.rerun()

                                    if st.button("💡 生成新提示词", key=f"review_apply_{ch_key}",
                                                 disabled=not modify_instr.strip() or is_streaming):
                                        st.session_state._busy = True
                                        st.session_state._busy_reason = 'mod_gen_hint'
                                        st.session_state._busy_ch = num
                                        st.session_state[f"_mod_instr_{ch_key}"] = modify_instr
                                        st.rerun()
                                with cr2:
                                    if st.button("❌ 取消", key=f"review_cancel_{ch_key}"):
                                        st.session_state[mod_key] = False
                                        st.rerun()

                            # ── 修改提示词确认面板 ──
                            elif st.session_state.get(f"_mod_hint_pending_{ch_key}"):
                                new_hint = st.session_state[f"_mod_hint_pending_{ch_key}"]
                                modify_instr = st.session_state.get(f"_mod_instr_{ch_key}", "")
                                st.info(f"💡 AI 修改提示词（基于：{modify_instr}）")
                                edited_hint = st.text_area(
                                    "提示词内容", value=new_hint, height=240,
                                    key=f"mod_hint_edit_{ch_key}", label_visibility="collapsed")
                                col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
                                with col_h1:
                                    if st.button("✍️ 确认提示词并重写本章",
                                                 key=f"confirm_mod_hint_{ch_key}",
                                                 type="primary", use_container_width=True,
                                                 disabled=is_streaming):
                                        # 保存新提示词，覆盖旧 hint.md
                                        hint_store.save_hint(st.session_state.project_name, num, edited_hint)
                                        OutlineGenerator.update_outline_json_hint(
                                            st.session_state.outline_json, num, edited_hint)
                                        st.session_state.pop(f"_mod_hint_pending_{ch_key}")
                                        st.session_state.pop(f"_mod_instr_{ch_key}", None)
                                        st.session_state[f"_mod_confirmed_{ch_key}"] = edited_hint
                                        save_project()
                                        st.session_state._busy = True
                                        st.session_state._busy_reason = 'mod_stream'
                                        st.session_state._busy_ch = num
                                        st.rerun()
                                with col_h2:
                                    # ── 两阶段：UI 已锁定，重新生成 AI 修改提示词 ──
                                    if is_streaming and st.session_state.get('_busy_reason') == 'mod_regen_hint':
                                        st.session_state._busy_reason = None
                                        ch_num_saved = st.session_state.pop('_busy_ch', num)
                                        ch_key_saved = str(ch_num_saved)
                                        modify_instr = st.session_state.get(f"_mod_instr_{ch_key_saved}", "")
                                        try:
                                            with st.spinner("💡 正在重新生成…"):
                                                try:
                                                    pred_hints = hint_store.get_predecessor_hints(
                                                        st.session_state.project_name,
                                                        writing_order, ch_num_saved)
                                                    existing_hint = hint_store.load_hint(
                                                        st.session_state.project_name, ch_num_saved)
                                                    new_hint2 = writer.generate_hint(
                                                        ch_title, ch_num_saved,
                                                        st.session_state.outline_md,
                                                        writing_order,
                                                        predecessor_hints=pred_hints,
                                                        report_name=st.session_state.report_name,
                                                        user_instruction=modify_instr,
                                                        existing_hint=existing_hint)
                                                    st.session_state[f"_mod_hint_pending_{ch_key_saved}"] = new_hint2
                                                except Exception as e:
                                                    st.error(f"提示词生成失败：{e}")
                                        finally:
                                            st.session_state._busy = False
                                        st.rerun()

                                    if st.button("🔄 重新生成", key=f"regenerate_mod_hint_{ch_key}",
                                                 use_container_width=True, disabled=is_streaming):
                                        st.session_state._busy = True
                                        st.session_state._busy_reason = 'mod_regen_hint'
                                        st.session_state._busy_ch = num
                                        st.rerun()
                                with col_h3:
                                    if st.button("↩ 放弃修改", key=f"abandon_mod_{ch_key}"):
                                        st.session_state.pop(f"_mod_hint_pending_{ch_key}")
                                        st.session_state.pop(f"_mod_instr_{ch_key}", None)
                                        st.rerun()

                            else:
                                # ── 正常状态：显示 text_area + 按钮 ──
                                ch_seq_review = int(num) if not isinstance(num, int) else num
                                _render_word_count_info(ch_content, ch_key, st.session_state.report_type, ch_title, ch_seq_review)
                                last_instr = st.session_state.get(f"_last_mod_instr_{ch_key}", "")
                                if last_instr:
                                    st.caption(f"📝 上轮修改意见：{last_instr}")

                                edited = st.text_area(
                                    f"内容 #{num}", value=ch_content, height=300,
                                    key=f"review_edit_{ch_key}", label_visibility="collapsed")
                                if edited != ch_content:
                                    chapters[ch_key] = edited

                                col_btn1, col_btn2, col_btn3 = st.columns(3)
                                with col_btn1:
                                    if st.button("💾 保存", key=f"review_save_{ch_key}"):
                                        save_project()
                                        st.toast("✅ 已保存")
                                with col_btn2:
                                    if st.button("🔧 AI 修改", key=f"review_mod_btn_{ch_key}"):
                                        st.session_state[mod_key] = True
                                        st.rerun()
                                with col_btn3:
                                    if st.button("🔍 质量校核", key=f"quality_review_btn_{ch_key}"):
                                        st.session_state[f"_quality_review_pending_{ch_key}"] = True
                                        st.session_state._busy = True
                                        st.session_state._busy_reason = 'quality_review'
                                        st.session_state._busy_ch = num
                                        st.rerun()

                                # Keep the quality-review result visible until dismissed.
                                review_result = st.session_state.get(f"_quality_review_result_{ch_key}")
                                if review_result:
                                    st.divider()
                                    with st.container(border=True):
                                        st.markdown("### 🔍 方法质量校核结果")
                                        st.markdown(review_result)
                                    col_r1, col_r2 = st.columns([1, 1])
                                    with col_r1:
                                        if st.button("🔄 重新校核", key=f"requality_{ch_key}"):
                                            st.session_state.pop(f"_quality_review_result_{ch_key}", None)
                                            st.session_state[f"_quality_review_pending_{ch_key}"] = True
                                            st.session_state._busy = True
                                            st.session_state._busy_reason = 'quality_review'
                                            st.session_state._busy_ch = num
                                            st.rerun()
                                    with col_r2:
                                        if st.button("✕ 关闭", key=f"close_quality_{ch_key}"):
                                            st.session_state.pop(f"_quality_review_result_{ch_key}", None)
                                            st.rerun()

            # ── 全文预览（只读拼接）──
            elif review_tab == 'preview':
                st.session_state['_review_tab'] = 'preview'

                if not chapters:
                    st.info("暂无内容可预览。")
                else:
                    full_text_parts = []
                    for num in sorted(chapter_titles.keys(),
                                      key=lambda x: int(x) if isinstance(x, (int, str)) and str(x).lstrip('-').isdigit() else 0):
                        ch_key = str(num)
                        content = chapters.get(ch_key, "")
                        if content:
                            full_text_parts.append(content)

                    full_text = "\n\n---\n\n".join(full_text_parts)
                    st.caption(f"📊 共 {len(chapters)} 章，{len(full_text):,} 字符")
                    with st.container(height=700, border=True):
                        st.markdown(full_text)

            # ── 字数分布（可视化）──
            elif review_tab == 'stats':
                st.session_state['_review_tab'] = 'stats'

                if not chapters:
                    st.info("暂无内容可统计。")
                else:
                    for num in sorted(chapter_titles.keys(),
                                      key=lambda x: int(x) if isinstance(x, (int, str)) and str(x).lstrip('-').isdigit() else 0):
                        ch_key = str(num)
                        ch_title = chapter_titles.get(num, f"第 {num} 章")
                        ch_seq = num if isinstance(num, int) else int(num) if str(num).isdigit() else 0
                        budget = get_chapter_word_budget(st.session_state.report_type, ch_seq)

                        if ch_key in chapters:
                            wc = _count_chinese_chars(chapters[ch_key])
                            ratio = wc / budget if budget > 0 else 0
                            over = int((ratio - 1) * 100) if ratio > 1 else 0
                            bar = min(ratio, 1.0)  # st.progress 上限 1.0
                            label = f"{ch_title}: {wc:,} / {budget:,} 字"
                            if ratio <= 0.95:
                                st.text(label)
                                st.progress(bar, text=f"{int(ratio*100)}%")
                            elif ratio <= 1.2:
                                st.text(label)
                                st.progress(bar, text=f"超出 {over}%")
                            else:
                                st.text(label)
                                st.progress(bar, text=f"⚠️ 超出 {over}%")
                        else:
                            st.caption(f"○ {ch_title} — 未开始（预算 {budget:,} 字）")

    # ═══════════════════════════════════════
    # Tab 3：参考资料
    # ═══════════════════════════════════════
    elif active_tab == 'references':
        if is_streaming:
            st.info("⏳ 当前章节正在编写中，完成后可查看参考资料")
        else:
            display_data = ref_manager.get_chapter_refs_display(
                st.session_state.chapters,
                st.session_state.get("chapter_titles", {})
            )
            if not display_data:
                st.info("暂无引用。编写章节后，正文中引用的资料将自动出现在这里。")
            else:
                total_refs = sum(len(d['refs']) for d in display_data)
                st.caption(f"共 {len(display_data)} 章引用，{total_refs} 条（含跨章重复）")
                for ch_data in display_data:
                    with st.expander(f"{ch_data['title']}引用（{len(ch_data['refs'])} 条）", expanded=False):
                        for ref in ch_data['refs']:
                            icon = {"项目资料": "📄", "网页链接": "🌐", "AI自有知识": "🤖"}.get(ref['type'], "📎")
                            line = f"{icon} {ref['name']}"
                            if ref.get('source') and ref['source'] != ref['name']:
                                line += f" — {ref['source']}"
                            if ref.get('first_in') and ref['first_in'] != ch_data['title']:
                                line += f"  ↗ 首见于{ref['first_in']}"
                            st.markdown(line)
                st.caption("💡 [Z] 为 AI 自有知识。导出时系统将按全文首次出现顺序统一生成数字编号。")

    # ── 底部导航（居中）──
    st.divider()

    col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
    with col_b2:
        if st.button("✅ 进入合并导出 →", type="primary", use_container_width=True,
                     key="bottom_export", disabled=is_streaming):
            st.session_state.step = 4
            save_project()
            st.rerun()
