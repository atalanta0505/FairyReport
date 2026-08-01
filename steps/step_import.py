"""
FairyReport v1.0.5 - Step 1: Import Materials
"""
import logging
import os
from datetime import datetime
from pathlib import Path

import streamlit as st

from project_store import save_project, load_project, load_chunks_on_demand
from utils import _pick_folder
from pipeline import scan_folder_with_pdf_warning, parse_single_file
from converters import get_format_name
from config import PROJECT_ROOT, PROJECTS_DIR

_logger = logging.getLogger(__name__)


def _compute_source_id(file_path: str, import_folder: str) -> str:
    """Compute a unique source_id from the file's relative path within the import folder.

    Falls back to basename if relative path computation fails.
    """
    try:
        rel = os.path.relpath(file_path, import_folder)
        return rel.replace(os.sep, '/')
    except (ValueError, OSError):
        return os.path.basename(file_path)


def _delete_kb_chunks(project_name: str, source_id: str):
    """从 ChromaDB 项目向量库中删除指定来源的文本块。
    仅在向量库目录存在时才执行（幂等操作）。
    """
    from pathlib import Path
    from config import PROJECTS_DIR
    vector_db_path = Path(PROJECTS_DIR) / project_name / "vector_db"
    if not vector_db_path.exists():
        return  # 向量库尚未创建，无需删除
    try:
        from kb import KnowledgeBase
        kb = KnowledgeBase(project_name, str(vector_db_path))
        kb.delete_by_source(source_id)
    except Exception as e:
        _logger.warning("删除项目 '%s' 的来源 '%s' 的文本块失败: %s", project_name, source_id, e)


def _ingest_chunks_now(project_name: str, chunks: list):
    """将文本块立即入库到项目向量知识库（feature spec 要求导入即入库）。

    同时设置 _project_ingested 标记，防止 step_outline 重复入库。
    """
    if not chunks:
        return
    from kb import KnowledgeBase
    vector_db_path = str(PROJECTS_DIR / project_name / "vector_db")
    kb_inst = KnowledgeBase.get_instance(project_name, vector_db_path)
    kb_inst.ingest_project(chunks)
    st.session_state['_project_ingested'] = True


def _update_parse_results_from_chunks():
    """从 imported_files + parse_all_chunks 重建每文件解析结果。

    使用 source_id（相对路径）进行匹配，避免同名文件在不同子目录互相污染。
    """
    results = {}
    imported = st.session_state.get('imported_files', [])
    import_folder = st.session_state.get('import_folder', '')
    for fobj in imported:
        fp = fobj.get("original", "")
        source_id = _compute_source_id(fp, import_folder)
        # 按 source_id 统计（优先），回退到 source（basename）兼容旧数据
        chunk_count = sum(1 for c in st.session_state.get('parse_all_chunks', [])
                          if c.get("source_id", c.get("source")) == source_id)
        real_status = fobj.get("status", "pending")
        if real_status == "ok" and chunk_count > 0:
            results[fp] = {"status": "ok", "chunks": chunk_count}
        elif real_status == "error":
            results[fp] = {"status": "error",
                           "error_msg": fobj.get("error", "未知错误"),
                           "chunks": 0}
    st.session_state.parse_results = results


def render(llm):
    """Step 1: 导入资料——文件扫描、解析、入库"""
    st.header("导入资料")

    st.info("💡 **资料处理说明**：所有资料将统一转为 Markdown 格式。\n"
            "• docx / xlsx / csv → 自动转换  • txt / md → 直接使用  • **PDF → 请先用 MinerU 转为 Markdown**")

    st.markdown("**资料文件夹路径**")
    col_input, col_browse = st.columns([4, 1])
    with col_input:
        folder_path = st.text_input("资料文件夹路径", value=st.session_state.import_folder,
                                    placeholder="例如：E:\\Projects\\资料", label_visibility="collapsed")
    with col_browse:
        st.caption("")
        if st.button("📁 浏览...", use_container_width=True):
            picked = _pick_folder()
            if picked:
                st.session_state.import_folder = picked
                st.rerun()
            else:
                st.toast("⚠️ 无法弹出文件夹选择对话框（可能运行在无桌面环境）。请手动输入或粘贴路径。", icon="⚠️")
    st.session_state.import_folder = folder_path

    # 检测资料文件夹路径是否变化
    prev_folder = st.session_state.get('_prev_import_folder', '')
    if prev_folder and folder_path != prev_folder:
        st.session_state._import_folder_fingerprint = ''
        if st.session_state.get('chapters'):
            _stale = st.session_state.get('_stale_chapters', set())
            for ch_key in st.session_state.chapters:
                _stale.add(ch_key)
            st.session_state['_stale_chapters'] = _stale
    st.session_state['_prev_import_folder'] = folder_path

    from pipeline import SUPPORTED_EXTENSIONS

    if folder_path and os.path.isdir(folder_path):
        all_files, pdf_files = scan_folder_with_pdf_warning(folder_path)
        ext_names = sorted(set(SUPPORTED_EXTENSIONS.keys()))
        st.caption(f"找到 {len(all_files)} 个文件（支持格式：{', '.join(ext_names)}）")

        if pdf_files:
            st.warning(f"⚠️ 发现 {len(pdf_files)} 个 PDF 文件（已跳过），请先用 MinerU 转为 .md")

        if all_files:
            st.success(f"✅ 可处理 {len(all_files)} 个文件")

            old_fp = getattr(st.session_state, '_import_folder_fingerprint', '')
            new_fp = '|'.join(sorted(all_files))
            if new_fp != old_fp:
                st.session_state._import_folder_fingerprint = new_fp
                st.session_state.parse_done = True
                st.session_state.parse_results = {}
                st.session_state.parse_idx = 0
                # 仅清理已移除文件的 chunks（使用 source_id 匹配）
                current_source_ids = set(
                    _compute_source_id(fp, folder_path) for fp in all_files)
                st.session_state.parse_all_chunks = [
                    c for c in st.session_state.get('parse_all_chunks', [])
                    if c.get("source_id", c.get("source")) in current_source_ids
                ]

                # ── 合并旧 imported_files 与新扫描结果，保留已导入状态 ──
                old_imported = {f["original"]: f for f in st.session_state.get('imported_files', [])}
                new_imported = []
                for i, fp in enumerate(all_files):
                    if fp in old_imported:
                        entry = dict(old_imported[fp])
                        entry["doc_id"] = i + 1
                        new_imported.append(entry)
                    else:
                        new_imported.append({
                            "doc_id": i + 1, "original": fp, "converted": None,
                            "status": "pending", "chunks": 0, "error": None,
                            "imported_at": datetime.now().isoformat(),
                        })
                st.session_state.imported_files = new_imported
                # 文件夹内容已变化，标记所有已编写章为"过期"
                if st.session_state.get('chapters'):
                    _stale = st.session_state.get('_stale_chapters', set())
                    for ch_key in st.session_state.chapters:
                        _stale.add(ch_key)
                    st.session_state['_stale_chapters'] = _stale
            # 指纹未变 → 保留现有 imported_files，不重置
            elif st.session_state.get('imported_files'):
                # 回访导入页面：确保能正常显示导入表格
                st.session_state.parse_done = True
                st.session_state.parse_results = {}
        else:
            st.info("文件夹中没有受支持的资料文件。")
            st.session_state.imported_files = []
            if st.session_state.get('chapters'):
                _stale = st.session_state.get('_stale_chapters', set())
                for ch_key in st.session_state.chapters:
                    _stale.add(ch_key)
                st.session_state['_stale_chapters'] = _stale
    elif folder_path:
        st.error(f"文件夹不存在：`{folder_path}`")
        st.session_state.imported_files = []
        if st.session_state.get('chapters'):
            _stale = st.session_state.get('_stale_chapters', set())
            for ch_key in st.session_state.chapters:
                _stale.add(ch_key)
            st.session_state['_stale_chapters'] = _stale

    imported = st.session_state.imported_files
    if not imported:
        st.stop()

    # v1.0.2: 文件导入即解析入库，无需额外处理步骤
    st.session_state.parse_done = True
    _update_parse_results_from_chunks()

    if st.session_state.parse_done:
        st.divider()
        st.subheader("📂 待处理文件")

        # ── 每文件导入状态跟踪（每次从 imported_files 权威同步）──
        per_file_key = f"_per_file_imported_{st.session_state.project_name}"
        st.session_state[per_file_key] = {}
        for f in imported:
            is_ok = (f.get("status") == "ok" and f.get("chunks", 0) > 0)
            st.session_state[per_file_key][f["original"]] = is_ok

        sel_key = f"_file_selected_{st.session_state.project_name}"
        if sel_key not in st.session_state:
            st.session_state[sel_key] = {f["original"]: True for f in imported}
            st.session_state._file_sel_version = 0
        selections = st.session_state[sel_key]

        # ── 表头：批量操作按钮 ──
        col_all, col_none, col_batch_import, col_batch_delete, col_refresh = st.columns(5)
        with col_all:
            if st.button("☑️ 全选", use_container_width=True):
                for f in imported:
                    selections[f["original"]] = True
                st.session_state._file_sel_version += 1
                st.rerun()
        with col_none:
            if st.button("☐ 全不选", use_container_width=True):
                for f in imported:
                    selections[f["original"]] = False
                st.session_state._file_sel_version += 1
                st.rerun()
        with col_batch_import:
            if st.button("📥 批量导入", use_container_width=True):
                sel_files = [f for f in imported if selections.get(f["original"], False)]
                md_output_dir = str(PROJECTS_DIR / st.session_state.project_name / "converted_md")
                import_folder = st.session_state.import_folder
                batch_new_chunks = []
                for fobj in sel_files:
                    fp = fobj["original"]
                    if st.session_state[per_file_key].get(fp):
                        continue  # 已导入，跳过
                    source_id = _compute_source_id(fp, import_folder)
                    result = parse_single_file(fp, output_dir=md_output_dir,
                                               doc_id=fobj["doc_id"],
                                               source_id=source_id)
                    if result["status"] == "ok":
                        new_chunks = result.pop("_chunks", [])
                        st.session_state.parse_all_chunks.extend(new_chunks)
                        batch_new_chunks.extend(new_chunks)
                        fobj["status"] = "ok"
                        fobj["chunks"] = len(new_chunks)
                        fobj["error"] = None
                    else:
                        fobj["status"] = result["status"]
                        fobj["error"] = result.get("error_msg")
                        fobj["chunks"] = 0
                # 批量入库到项目向量知识库
                if batch_new_chunks:
                    _ingest_chunks_now(st.session_state.project_name, batch_new_chunks)
                    if st.session_state.get('chapters'):
                        _stale = st.session_state.get('_stale_chapters', set())
                        for ch_key in st.session_state.chapters:
                            _stale.add(ch_key)
                        st.session_state['_stale_chapters'] = _stale
                # FRL-005: immediately persist after import
                save_project()
                st.rerun()
        with col_batch_delete:
            sel_to_del = [f for f in imported if selections.get(f["original"], False)
                          and st.session_state[per_file_key].get(f["original"])]
            if st.button("🗑️ 批量删除", use_container_width=True,
                         disabled=(len(sel_to_del) == 0)):
                import_folder = st.session_state.import_folder
                for fobj in sel_to_del:
                    fp = fobj["original"]
                    source_id = _compute_source_id(fp, import_folder)
                    st.session_state[per_file_key][fp] = False
                    fobj["status"] = "pending"
                    fobj["chunks"] = 0
                    # 移除对应 chunks（按 source_id 匹配）
                    st.session_state.parse_all_chunks = [
                        c for c in st.session_state.parse_all_chunks
                        if c.get("source_id", c.get("source")) != source_id]
                    # 同步从 ChromaDB 项目向量库中删除
                    _delete_kb_chunks(st.session_state.project_name, source_id)
                if sel_to_del and st.session_state.get('chapters'):
                    _stale = st.session_state.get('_stale_chapters', set())
                    for ch_key in st.session_state.chapters:
                        _stale.add(ch_key)
                    st.session_state['_stale_chapters'] = _stale
                # FRL-005: immediately persist after delete
                save_project()
                st.rerun()
        with col_refresh:
            if st.button("🔄 刷新", use_container_width=True):
                st.session_state._import_folder_fingerprint = ''
                st.rerun()

        st.caption("")

        sel_version = st.session_state._file_sel_version
        selected_count = 0
        for fobj in imported:
            fp = fobj["original"]
            fname = os.path.basename(fp)
            fmt = get_format_name(fp)
            is_imported = st.session_state[per_file_key].get(fp, False)

            # ── 5 列表格：checkbox | seq | name | status | action ──
            col_cb, col_seq, col_name, col_status, col_action = st.columns(
                [0.5, 0.5, 3.5, 1.2, 1.5])

            with col_cb:
                selected = st.checkbox(
                    "选", value=selections.get(fp, True),
                    key=f"chk_{fp}_v{sel_version}", label_visibility="collapsed")
                selections[fp] = selected
                if selected:
                    selected_count += 1

            with col_seq:
                st.caption(f"`{fobj['doc_id']}`")

            with col_name:
                st.markdown(f"**{fname}** `({fmt})`")

            with col_status:
                if is_imported:
                    st.success("✅ 已导入")
                else:
                    st.caption("⏳ 未导入")

            with col_action:
                if is_imported:
                    if st.button("🗑️ 删除", key=f"del_{fp}_v{sel_version}",
                                 use_container_width=True):
                        import_folder = st.session_state.import_folder
                        source_id = _compute_source_id(fp, import_folder)
                        st.session_state[per_file_key][fp] = False
                        fobj["status"] = "pending"
                        fobj["chunks"] = 0
                        # 移除对应 chunks（按 source_id 匹配）
                        st.session_state.parse_all_chunks = [
                            c for c in st.session_state.parse_all_chunks
                            if c.get("source_id", c.get("source")) != source_id]
                        # 同步从 ChromaDB 项目向量库中删除
                        _delete_kb_chunks(st.session_state.project_name, source_id)
                        if st.session_state.get('chapters'):
                            _stale = st.session_state.get('_stale_chapters', set())
                            for ch_key in st.session_state.chapters:
                                _stale.add(ch_key)
                            st.session_state['_stale_chapters'] = _stale
                        # FRL-005: immediately persist after delete
                        save_project()
                        st.rerun()
                else:
                    if st.button("📥 导入", key=f"import_{fp}_v{sel_version}",
                                 use_container_width=True):
                        import_folder = st.session_state.import_folder
                        source_id = _compute_source_id(fp, import_folder)
                        md_output_dir = str(PROJECTS_DIR / st.session_state.project_name / "converted_md")
                        result = parse_single_file(fp, output_dir=md_output_dir,
                                                   doc_id=fobj["doc_id"],
                                                   source_id=source_id)
                        if result["status"] == "ok":
                            new_chunks = result.pop("_chunks", [])
                            st.session_state.parse_all_chunks.extend(new_chunks)
                            _ingest_chunks_now(st.session_state.project_name, new_chunks)
                            if st.session_state.get('chapters'):
                                _stale = st.session_state.get('_stale_chapters', set())
                                for ch_key in st.session_state.chapters:
                                    _stale.add(ch_key)
                                st.session_state['_stale_chapters'] = _stale
                            fobj["status"] = "ok"
                            fobj["chunks"] = len(new_chunks)
                            fobj["error"] = None
                        else:
                            fobj["status"] = result["status"]
                            fobj["error"] = result.get("error_msg")
                            fobj["chunks"] = 0
                        # FRL-005: immediately persist after import
                        save_project()
                        st.rerun()

        st.caption(f"已选 {selected_count} / {len(imported)} 个文件")

    # ── 解析结果（v1.0.2:文件导入即解析，无需批量处理）──
    results = st.session_state.parse_results
    st.subheader("📂 文件转换结果")

    ok_count = sum(1 for r in results.values() if r["status"] == "ok")
    err_count = sum(1 for r in results.values() if r["status"] == "error")
    skip_count = sum(1 for r in results.values() if r["status"] == "skip")

    for fobj in imported:
        f_name = os.path.basename(fobj["original"])
        result_key = fobj["original"]
        result = results.get(result_key)
        if result is None:
            # 不在 parse_results 中 → 未处理（pending）或已删除
            st.markdown(f"⏳ **{f_name}** — 未处理")
        elif result["status"] == "ok":
            st.markdown(f"✅ **{f_name}** — {result['chunks']} 个文本块")
        elif result["status"] == "error":
            st.markdown(f"❌ **{f_name}** — {result.get('error_msg', '未知错误')}")
        else:
            st.markdown(f"⏭️ **{f_name}** — {result.get('error_msg', '已跳过')}")

    # 按需加载 chunks（仅用于统计和后续入库）
    load_chunks_on_demand(st.session_state.project_name)
    total_chunks = len(st.session_state.parse_all_chunks)
    if ok_count > 0:
        st.success(f"📊 {ok_count} 成功，共 {total_chunks} 个文本块")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔄 重新解析全部", disabled=(err_count == 0)):
                st.session_state.parse_done = False
                st.session_state.parse_idx = 0
                st.session_state.parse_results = {}
                st.session_state.parse_all_chunks = []
                st.rerun()
        with col2:
            if st.button("✅ 确认结果", type="primary", disabled=(total_chunks == 0)):
                from project_store import save_project
                save_project()
                st.session_state.max_step_reached = max(st.session_state.get('max_step_reached', 0), 2)
                st.session_state.step = 2
                st.rerun()
