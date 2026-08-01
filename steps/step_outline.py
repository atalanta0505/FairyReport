"""
FairyReport v1.0.5 - Step 2: Confirm Outline
"""
import re

import streamlit as st

from project_store import save_project, load_project, load_chunks_on_demand
from components.toc import render_toc
from outline import OutlineGenerator, _extract_chapter_titles
from config import REPORT_TYPES, PROFESSIONS, get_word_limit, PROJECTS_DIR


def render(llm):
    """Step 2: 确定大纲——大纲生成、编辑、写作顺序"""
    st.header("确定大纲")

    # 已有编写内容后禁止回到大纲阶段
    has_written = bool(st.session_state.get('chapters', {}))
    if has_written:
        st.warning("⚠️ 已有章节已编写，无法回到大纲阶段。如需修改大纲，请先清除已编写内容。\n\n请通过左侧导航栏返回编写页面。")
        st.stop()

    total_chunks = len(st.session_state.parse_all_chunks)
    outline_generated = bool(st.session_state.get('outline_md'))
    report_type = st.session_state.get("report_type", "")

    # ── v1.0.2 fix: 大纲已存在但关键数据缺失时自动恢复 ──
    if outline_generated:
        need_regen = False

        # 1. 恢复 chapter_titles（优先从 outline_json，其次从 outline_md 重新提取）
        chapter_titles = st.session_state.get('chapter_titles', {})
        if not chapter_titles:
            oj = st.session_state.get('outline_json')
            if oj and oj.get('chapters'):
                chapter_titles = {ch['chapter_seq']: ch['title'] for ch in oj['chapters'] if ch.get('title')}
                if chapter_titles:
                    st.session_state.chapter_titles = chapter_titles
                    need_regen = True

            if not chapter_titles:
                # 多层次正则提取
                titles = _extract_chapter_titles(st.session_state.outline_md)
                if not titles:
                    # 终极降级：匹配任何含"第X章"的行
                    raw = re.findall(r'第[一二三四五六七八九十百零\d]+章[^\n]*', st.session_state.outline_md)
                    titles = {i + 1: t.strip() for i, t in enumerate(raw)}
                if titles:
                    st.session_state.chapter_titles = titles
                    chapter_titles = titles
                    need_regen = True

        # 2. 恢复 writing_order — 优先从 outline_json 提取（不调 LLM）
        if not st.session_state.get('writing_order') and chapter_titles:
            oj = st.session_state.get('outline_json')
            if oj and oj.get('chapters') and oj.get('writing_order'):
                # outline.json 中已有写作顺序，直接提取
                st.session_state.writing_order = oj['writing_order']
                st.session_state._writing_order_reason = oj.get('writing_order_reason', '')
                need_regen = False
            elif oj and oj.get('chapters'):
                # 从各章 writing_order 排名重建
                ch_with_order = [ch for ch in oj['chapters'] if ch.get('writing_order', 0) > 0]
                if ch_with_order:
                    st.session_state.writing_order = [ch['chapter_seq'] for ch in sorted(ch_with_order, key=lambda c: c['writing_order'])]
                    need_regen = False
                else:
                    need_regen = True
            else:
                need_regen = True

        # 3. 仅在 outline.json 中也没有数据时才调 LLM
        if need_regen and not st.session_state.get('writing_order') and chapter_titles:
            st.session_state._busy = True
            with st.spinner("📋 正在补全写作顺序..."):
                gen = OutlineGenerator(llm, report_type=report_type, total_words=get_word_limit(report_type))
                try:
                    order, reason = gen.suggest_order(st.session_state.outline_md)
                except Exception as e:
                    st.warning(f"⚠️ 写作顺序分析失败：{e}，使用默认顺序")
                    order, reason = [], ""
                chapter_keys = list(chapter_titles.keys())
                if not order:
                    order = chapter_keys
                else:
                    all_nums = set(chapter_keys)
                    order = [n for n in order if n in all_nums] + [n for n in all_nums if n not in order]
                st.session_state.writing_order = order
                st.session_state._writing_order_reason = reason
                # 同步更新 outline_json
                oj = st.session_state.get('outline_json')
                if oj:
                    oj['writing_order'] = order
                    oj['writing_order_reason'] = reason
                save_project()
            st.session_state._busy = False
            st.rerun()

    if not outline_generated:
        # ── 两阶段：如果 busy，执行实际的大纲生成（UI 已锁定）──
        is_busy = st.session_state.get('_busy', False)
        if is_busy and st.session_state.get('_busy_reason') == 'gen_outline':
            st.session_state._busy_reason = None
            # 按需加载 chunks（仅在生成大纲入库时需要）
            load_chunks_on_demand(st.session_state.project_name)
            total_chunks = len(st.session_state.parse_all_chunks)
            st.info(f"📊 已解析 {total_chunks} 个文本块，准备入库并生成大纲。")

            outline_error = None
            try:
                with st.status("🗺️ 正在生成大纲…", expanded=True) as status:
                    st.write("🗃️ 正在建立项目知识库…")
                    from kb import KnowledgeBase

                    kb_inst = KnowledgeBase.get_instance(
                        st.session_state.project_name,
                        str(PROJECTS_DIR / st.session_state.project_name / "vector_db"))
                    # 幂等保护：如果导入阶段已入库，跳过重复入库
                    if not st.session_state.get('_project_ingested'):
                        kb_inst.ingest_project(st.session_state.parse_all_chunks)
                        st.session_state['_project_ingested'] = True
                        st.success(f"🗃️ 已入库 {total_chunks} 个文本块")
                    else:
                        st.info(f"🗃️ 资料已在导入阶段入库（{total_chunks} 个文本块），跳过重复入库")

                    st.write("🔍 正在检索项目资料库…")
                    context = kb_inst.query(st.session_state.report_name, n_results=5,
                                           include_generic=False)

                    gen = OutlineGenerator(llm, report_type=report_type, total_words=get_word_limit(report_type))
                    stream_placeholder = st.empty()
                    stream_buffer = [""]

                    def on_chunk(chunk):
                        stream_buffer[0] += chunk
                        stream_placeholder.markdown(
                            f"""<div style="
                                border: 1px solid rgba(128,128,128,0.3);
                                border-radius: 8px;
                                padding: 16px;
                                font-size: 14px;
                                width: 100%;
                                box-sizing: border-box;
                                max-height: 500px;
                                overflow-y: auto;
                                white-space: pre-wrap;
                                font-family: 'SF Mono', 'Fira Code', monospace;
                                background: rgba(128,128,128,0.05);
                            ">🗺️ **正在生成大纲...**

{stream_buffer[0]} ▌</div>""",
                            unsafe_allow_html=True
                        )

                    st.write("📝 正在调用 AI 生成大纲…")
                    outline_md = gen.generate_stream(st.session_state.report_name, context, callback=on_chunk)
                    st.session_state.outline_md = outline_md or ""
                    stream_placeholder.markdown(
                        f"""<div style="
                            border: 1px solid rgba(128,128,128,0.3);
                            border-radius: 8px;
                            padding: 16px;
                            font-size: 14px;
                            width: 100%;
                            box-sizing: border-box;
                            max-height: 500px;
                            overflow-y: auto;
                            white-space: pre-wrap;
                            font-family: 'SF Mono', 'Fira Code', monospace;
                            background: rgba(128,128,128,0.05);
                        ">{outline_md}</div>""",
                        unsafe_allow_html=True
                    )

                    # 提取章标题
                    chapter_titles = _extract_chapter_titles(outline_md)
                    st.session_state.chapter_titles = chapter_titles

                    # 写作顺序
                    st.write("📋 正在分析写作顺序…")
                    try:
                        order, reason = gen.suggest_order(outline_md)
                    except Exception as e:
                        st.warning(f"⚠️ 写作顺序分析失败：{e}，使用默认顺序")
                        order, reason = [], ""
                    chapter_keys = list(chapter_titles.keys())
                    if not order:
                        order = chapter_keys
                    else:
                        all_nums = set(chapter_keys)
                        order = [n for n in order if n in all_nums] + [n for n in all_nums if n not in order]
                    st.session_state.writing_order = order
                    st.session_state._writing_order_reason = reason

                    # v1.0.2: outline_json — writing_hint 初始化为空
                    outline_json = OutlineGenerator.build_outline_json(
                        outline_md, order, reason, chapter_titles, report_type)
                    outline_json["report_name"] = st.session_state.report_name
                    outline_json["report_type"] = report_type
                    st.session_state.outline_json = outline_json
                    st.session_state.writing_hints = {}
                    st.session_state.chapter_notes = {}

                    status.update(label="✅ 大纲生成完成！", state="complete")

            except ValueError as e:
                if "未配置 DeepSeek API Key" in str(e):
                    outline_error = str(e)
                else:
                    outline_error = f"大纲生成失败：{e}"
            except Exception as e:
                outline_error = f"大纲生成失败：{e}"
            finally:
                st.session_state._busy = False

            save_project()
            if outline_error:
                st.error(f"⚠️ {outline_error}")
            else:
                st.rerun()

        # Phase 1: 显示生成按钮
        load_chunks_on_demand(st.session_state.project_name)
        total_chunks = len(st.session_state.parse_all_chunks)
        st.info(f"📊 已解析 {total_chunks} 个文本块，准备入库并生成大纲。")

        if st.button("🗺️ 生成大纲", type="primary", disabled=(total_chunks == 0)):
            st.session_state._busy = True
            st.session_state._busy_reason = 'gen_outline'
            st.rerun()

    else:
        # ── 大纲已生成，审核编辑模式 ──
        st.success("📋 大纲已生成，可编辑调整后进入逐章编写")

        has_written = bool(st.session_state.get("chapters", {}))
        written_keys = set(st.session_state.get("chapters", {}).keys())

        # 大纲文本框：全宽，字体用等宽以对齐 Markdown 层级
        st.markdown("""
        <style>
        section[data-testid="stTextArea"] textarea {
            font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace !important;
            font-size: 14px !important;
            line-height: 1.6 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        new_outline = st.text_area(
            "大纲内容", value=st.session_state.outline_md, height=550,
            label_visibility="collapsed", disabled=has_written)
        if new_outline != st.session_state.outline_md and not has_written:
            st.session_state.outline_md = new_outline

        # 已写章锁定，未写章可编辑标题
        if has_written:
            st.warning("⚠️ 已编写章的标题已锁定（🔒）。未编写章的标题仍可编辑。")
            chapter_titles = st.session_state.get("chapter_titles", {})
            if chapter_titles:
                for num in sorted(chapter_titles.keys(), key=lambda x: int(x) if isinstance(x, (int, str)) and str(x).lstrip('-').isdigit() else 0):
                    old_title = chapter_titles[num]
                    if str(num) in written_keys:
                        st.caption("🛡️ 该章已编写，请在编写页面修改标题")
                    else:
                        new_title = st.text_input(f"第{num}章标题", value=old_title,
                                                  key=f"outline_ch_title_{num}", label_visibility="collapsed")
                        if new_title != old_title:
                            old_title_esc = re.escape(old_title)
                            st.session_state.outline_md = re.sub(
                                r'^#{1,2}\s+' + old_title_esc + r'$', f'# {new_title}',
                                st.session_state.outline_md, count=1, flags=re.MULTILINE)
                            st.session_state.chapter_titles[num] = new_title
                            oj = st.session_state.get('outline_json')
                            if oj:
                                OutlineGenerator.update_outline_json_title(oj, num, new_title)

        # 写作顺序（放在大纲下方，节省横向空间）
        st.divider()
        st.subheader("📋 写作顺序")
        writing_order = st.session_state.get("writing_order", [])
        chapter_titles = st.session_state.get("chapter_titles", {})
        reason = st.session_state.get("_writing_order_reason", "")

        if writing_order:
            if len(writing_order) <= 5:
                cols = st.columns(len(writing_order))
                for i, (col, num) in enumerate(zip(cols, writing_order)):
                    title = chapter_titles.get(num, f"第 {num} 章")
                    col.info(f"**{i+1}.** {title}")
            else:
                for i, num in enumerate(writing_order):
                    title = chapter_titles.get(num, f"第 {num} 章")
                    st.info(f"**{i+1}.** {title}")
        else:
            st.caption("⚠️ 写作顺序未生成")
        if reason:
            with st.expander("💡 顺序理由"):
                st.info(reason)

        col_reorder, _ = st.columns([1, 3])
        with col_reorder:
            if st.button("🔄 重新生成写作顺序"):
                with st.spinner("分析中..."):
                    gen = OutlineGenerator(llm, report_type=report_type, total_words=get_word_limit(report_type))
                    try:
                        order, reason = gen.suggest_order(st.session_state.outline_md)
                    except Exception as e:
                        st.warning(f"⚠️ 写作顺序分析失败：{e}，使用默认顺序")
                        order, reason = [], ""
                    chapter_keys = list(chapter_titles.keys())
                    if not order:
                        order = chapter_keys
                    else:
                        all_nums = set(chapter_keys)
                        order = [n for n in order if n in all_nums] + [n for n in all_nums if n not in order]
                    st.session_state.writing_order = order
                    st.session_state._writing_order_reason = reason
                    if st.session_state.get("outline_json"):
                        st.session_state.outline_json["writing_order"] = order
                        st.session_state.outline_json["writing_order_reason"] = reason
                st.rerun()

        # ── 进入编写 ──
        st.divider()
        if st.button("✍️ 准备逐章编写", type="primary", use_container_width=True,
                     disabled=not st.session_state.get("writing_order"),
                     help="逐章手动控制编写，可随时修改"):
            st.session_state.current_order_idx = 0
            save_project()
            st.session_state.max_step_reached = max(st.session_state.get('max_step_reached', 0), 3)
            st.session_state.step = 3
            st.rerun()
