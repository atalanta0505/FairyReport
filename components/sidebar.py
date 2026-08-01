"""
FairyReport v1.0.5 - Settings page
"""
import logging
import os
from pathlib import Path

import streamlit as st

from config import (
    PROJECT_ROOT, GENERIC_KB_DIR, GENERIC_DB_DIR,
    DEFAULT_MODEL, DEFAULT_BASE_URL, EMBED_MODEL_NAME,
    CHUNK_SIZE, CHUNK_OVERLAP, RAG_RESULTS_PER_SOURCE,
)

_logger = logging.getLogger(__name__)

_MODEL_OPTIONS = [
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "deepseek-chat",
    "deepseek-reasoner",
    "自定义",
]


def render_settings(api_key, _update_env):
    """Render the Settings page."""
    st.header("⚙️ Settings")

    # Show save confirmation after a rerun so the user can actually see it.
    if st.session_state.pop("_settings_saved", False):
        st.success("✅ 设置已保存")
        st.info("保存后请重启应用生效")

    st.subheader("🔑 API 配置状态")
    if api_key:
        masked = api_key[:4] + "…" + api_key[-4:] if len(api_key) > 8 else "****"
        st.success(f"DEEPSEEK_API_KEY: `{masked}`")
    else:
        st.error("API Key 未配置")

    # ── Model platform configuration form ──
    st.subheader("🌐 模型平台配置")
    current_base_url = os.getenv("DEFAULT_BASE_URL", DEFAULT_BASE_URL)
    current_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    current_model = os.getenv("DEFAULT_MODEL", DEFAULT_MODEL)

    base_url = st.text_input("Base URL", value=current_base_url)
    api_key_input = st.text_input("API Key", value=current_api_key, type="password")

    if current_model in _MODEL_OPTIONS:
        model_index = _MODEL_OPTIONS.index(current_model)
        custom_model_value = ""
    else:
        model_index = _MODEL_OPTIONS.index("自定义")
        custom_model_value = current_model

    selected_model = st.selectbox("模型", options=_MODEL_OPTIONS, index=model_index)

    custom_model = ""
    if selected_model == "自定义":
        custom_model = st.text_input("自定义模型名", value=custom_model_value)

    if st.button("💾 保存设置", use_container_width=True):
        base_url_clean = base_url.strip()
        custom_model_clean = custom_model.strip()
        if not base_url_clean:
            st.error("⚠️ Base URL 不能为空")
        elif selected_model == "自定义" and not custom_model_clean:
            st.error("⚠️ 自定义模型名不能为空")
        else:
            final_model = custom_model_clean if selected_model == "自定义" else selected_model
            _update_env("DEEPSEEK_API_KEY", api_key_input)
            _update_env("DEFAULT_BASE_URL", base_url_clean)
            _update_env("DEFAULT_MODEL", final_model)
            # Update the running process environment so the next rerun picks up new values.
            os.environ["DEEPSEEK_API_KEY"] = api_key_input
            os.environ["DEFAULT_BASE_URL"] = base_url_clean
            os.environ["DEFAULT_MODEL"] = final_model
            st.session_state["_settings_api_key"] = api_key_input
            st.session_state["_settings_base_url"] = base_url_clean
            st.session_state["_settings_model"] = final_model
            st.session_state["_settings_saved"] = True
            st.rerun()

    st.subheader("📚 知识库")
    kb_files = list(GENERIC_KB_DIR.glob("*.md")) if GENERIC_KB_DIR.exists() else []
    if kb_files:
        st.success(f"通用知识库：{len(kb_files)} 篇文档")
    else:
        st.warning("知识库为空。将 `.md` 文件放入 `generic_knowledge/` 后运行 `python scripts/vectorize_kb.py`")

    if st.button("🔄 重建通用知识库", use_container_width=True):
        with st.spinner("正在重建通用知识库..."):
            try:
                from kb import KnowledgeBase
                from pipeline import chunk_text
                import json
                from datetime import datetime

                # Read _index.json (generic KB index and category management)
                index_path = GENERIC_KB_DIR / "_index.json"
                index_data = {}
                if index_path.exists():
                    try:
                        index_data = json.loads(index_path.read_text(encoding='utf-8'))
                    except (json.JSONDecodeError, IOError):
                        pass
                file_index = index_data.get("files", {})

                all_chunks = []
                skip_count = 0
                for mdf in sorted(GENERIC_KB_DIR.glob("*.md")):
                    text = mdf.read_text(encoding='utf-8')
                    if not text.strip():
                        continue

                    # Check file status in _index.json
                    fi = file_index.get(mdf.name, {})
                    status = fi.get("status", "active")
                    file_type = fi.get("type", "methodology")  # Default type

                    # Validate type field must be one of methodology/policy/standard
                    VALID_TYPES = {"methodology", "policy", "standard"}
                    if file_type not in VALID_TYPES:
                        st.warning(f"⚠️ _index.json 中 `{mdf.name}` 的 type 值 `{file_type}` 无效，"
                                   f"已回退为 methodology。有效值：{', '.join(sorted(VALID_TYPES))}")
                        file_type = "methodology"

                    # Files with status=archived are not vectorized or ingested
                    if status == "archived":
                        skip_count += 1
                        continue

                    chunks = chunk_text(text, mdf.name)
                    # Write type into each chunk's metadata
                    for c in chunks:
                        c["type"] = file_type
                    all_chunks.extend(chunks)

                if all_chunks:
                    import chromadb
                    gen_client = chromadb.PersistentClient(path=str(GENERIC_DB_DIR))
                    try:
                        gen_client.delete_collection("generic_kb")
                    except Exception as e:
                        _logger.debug("删除旧通用知识库集合失败: %s", e)
                    gen_coll = gen_client.create_collection("generic_kb")
                    kb_temp = KnowledgeBase("temp_rebuild", str(GENERIC_DB_DIR))
                    texts = [c["text"] for c in all_chunks]
                    embeddings = kb_temp.embedder.encode(texts, show_progress_bar=False).tolist()
                    gen_coll.add(
                        embeddings=embeddings, documents=texts,
                        metadatas=[{"source": c["source"], "type": c.get("type", "methodology")} for c in all_chunks],
                        ids=[f"kb_{c['source']}_{i}" for i, c in enumerate(all_chunks)],
                    )
                    # Update last_built in _index.json
                    index_data["last_built"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    index_path.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding='utf-8')
                    skip_msg = f"（跳过 {skip_count} 篇已归档）" if skip_count else ""
                    st.success(f"✅ 已重建：{len(all_chunks)} 个文本块 {skip_msg}")
                    st.rerun()
                else:
                    skip_msg = f"（{skip_count} 篇已归档）" if skip_count else "（知识库目录为空）"
                    st.warning(f"未找到可处理的内容 {skip_msg}")
            except Exception as e:
                st.error(f"重建失败：{e}")

    st.divider()
    st.subheader("🔧 高级设置")
    with st.expander("检索 & 模型参数", expanded=False):
        st.caption("⚠️ 如下参数仅供 IT 支持人员使用。")

        rerank_enabled = st.toggle("🔍 Rerank 增强检索",
            value=st.session_state.get("_rerank_enabled", False))
        if rerank_enabled != st.session_state.get("_rerank_enabled"):
            st.session_state["_rerank_enabled"] = rerank_enabled
            _update_env("RERANK_ENABLED", str(rerank_enabled))

        embed_model = st.text_input("Embedding 模型", value=st.session_state.get("_settings_embed", EMBED_MODEL_NAME))
        if embed_model != st.session_state.get("_settings_embed"):
            st.session_state["_settings_embed"] = embed_model
            _update_env("EMBED_MODEL_NAME", embed_model)

        col_cs, col_co = st.columns(2)
        with col_cs:
            chunk_size = st.number_input("切片大小（字符）", value=st.session_state.get("_settings_chunk_size", CHUNK_SIZE),
                                         min_value=200, max_value=3000, step=100)
            if chunk_size != st.session_state.get("_settings_chunk_size"):
                st.session_state["_settings_chunk_size"] = chunk_size
                _update_env("CHUNK_SIZE", str(chunk_size))
        with col_co:
            # FRL-003: clamp overlap max to chunk_size-1 to prevent infinite loop
            _cs = st.session_state.get("_settings_chunk_size", CHUNK_SIZE)
            _co_max = min(500, max(0, _cs - 100))
            chunk_overlap = st.number_input("切片重叠（字符）", value=st.session_state.get("_settings_chunk_overlap", CHUNK_OVERLAP),
                                            min_value=0, max_value=500, step=50)
            if chunk_overlap >= _cs:
                st.warning(f"⚠️ 重叠({chunk_overlap})不能大于等于切片大小({_cs})，已自动调整为 {max(0, _cs // 4)}")
                chunk_overlap = max(0, _cs // 4)
            if chunk_overlap != st.session_state.get("_settings_chunk_overlap"):
                st.session_state["_settings_chunk_overlap"] = chunk_overlap
                _update_env("CHUNK_OVERLAP", str(chunk_overlap))

        rag_results = st.number_input("RAG 检索条数", value=st.session_state.get("_settings_rag", RAG_RESULTS_PER_SOURCE),
                                      min_value=1, max_value=20, step=1)
        if rag_results != st.session_state.get("_settings_rag"):
            st.session_state["_settings_rag"] = rag_results
            _update_env("RAG_RESULTS_PER_SOURCE", str(rag_results))

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            temp_outline = st.slider("Temperature（大纲）", 0.0, 2.0,
                                     st.session_state.get("_settings_temp_outline", 0.2), 0.1)
            if temp_outline != st.session_state.get("_settings_temp_outline"):
                st.session_state["_settings_temp_outline"] = temp_outline
                _update_env("TEMPERATURE_OUTLINE", str(temp_outline))
        with col_t2:
            temp_chapter = st.slider("Temperature（章节）", 0.0, 2.0,
                                     st.session_state.get("_settings_temp_chapter", 0.2), 0.1)
            if temp_chapter != st.session_state.get("_settings_temp_chapter"):
                st.session_state["_settings_temp_chapter"] = temp_chapter
                _update_env("TEMPERATURE_WRITING", str(temp_chapter))

        st.caption("⚙️ 温度设置将在下次启动后生效")

    st.divider()
    if st.button("⬅️ 返回", use_container_width=True):
        st.session_state.settings_page = False
        st.rerun()
    st.stop()
