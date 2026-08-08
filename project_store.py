"""FairyReport project persistence layer."""
import json
import gc
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st

from config import PROJECT_ROOT, PROJECTS_DIR

_logger = logging.getLogger(__name__)

# ── Persistence fields (saved to project.json) ──
# Note: parse_all_chunks is large, stored separately in chunks.json, not in project.json
PERSIST_KEYS = (
    'project_name', 'report_name', 'topic', 'report_type', 'profession',
    'import_folder', 'imported_files', 'outline_md', 'outline_json',
    'chapter_titles',
    'writing_order',         # writing order and button enable condition
    'step', 'max_step_reached',
    'current_order_idx',
    'writing_hints',       # persisted after automatic generation
    'chapter_notes',
    '_step3_active_tab',   # Keep the user's tab selection in Step 3
    '_project_ingested',   # avoid re-ingestion on reload
    '_quality_review_results',
    # Note: chapters (full chapter text) stored separately in chapters/*.md, not in project.json
    # Note: parse_all_chunks (text chunks) stored separately in chunks.json, not in project.json
)

# Fields that require special serialization (set -> list)
_SET_KEYS = set()


def _project_dir(name: str) -> Path:
    return PROJECTS_DIR / name


def init_session():
    """Initialize session_state."""
    defaults = {
        'step': -1,
        'project_name': '',
        'topic': '',
        'report_name': '',
        'report_type': '通用咨询报告',
        'profession': '综合',
        'import_folder': '',
        'imported_files': [],
        'outline_md': '',
        'chapter_titles': {},
        'writing_order': [],
        'chapters': {},
        '_busy': False,
        'current_order_idx': 0,
        'parse_done': True,
        'parse_idx': 0,
        'parse_results': {},
        'parse_all_chunks': [],
        'outline_json': {},
        'writing_hints': {},
        'chapter_notes': {},
        'max_step_reached': -1,
        '_review_tab': 'overview',
        '_step3_active_tab': 'write',
        '_project_ingested': False,  # Prevent duplicate ingestion in step_outline
        '_chunks_loaded': False,     # Distinguish "not loaded" from "emptied".
        '_quality_review_results': {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def save_project():
    """Persist current project state to disk atomically.

    - project.json: metadata (atomic write via temp file + os.replace)
    - chunks.json: text chunks (always synced; deleted when empty)
    - chapters/*.md: one file per chapter (stale files cleaned up)
    - outline.json: structured outline data
    """
    if not st.session_state.get('project_name'):
        return
    pdir = _project_dir(st.session_state.project_name)
    pdir.mkdir(parents=True, exist_ok=True)
    data = {}
    for k in PERSIST_KEYS:
        v = st.session_state.get(k)
        try:
            json.dumps(v)
            data[k] = v
        except (TypeError, ValueError):
            pass
    # Special serialization: set -> list
    for k in _SET_KEYS:
        v = st.session_state.get(k)
        if v is not None:
            if isinstance(v, set):
                data[k] = list(v)
            else:
                data[k] = v
    data['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data['chapters_done'] = len(st.session_state.get('chapters', {}))

    # Atomic write of project.json: temp file → os.replace
    proj_path = pdir / "project.json"
    tmp_proj = pdir / "project.json.tmp"
    if proj_path.exists():
        try:
            shutil.copy2(proj_path, pdir / "project.json.bak")
        except OSError:
            pass
    tmp_proj.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp_proj, proj_path)

    # Sync chunks.json: always reflect current state (write empty or delete)
    chunks = st.session_state.get('parse_all_chunks')
    chunks_path = pdir / 'chunks.json'
    if chunks:
        tmp_chunks = pdir / 'chunks.json.tmp'
        tmp_chunks.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp_chunks, chunks_path)
    elif chunks_path.exists():
        # Explicitly empty — delete stale chunks.json so load doesn't resurrect old data
        chunks_path.unlink(missing_ok=True)

    st.session_state['_chunks_loaded'] = True

    # Save chapter files and reconcile: delete stale .md files whose chapter was removed
    save_dir = pdir / "chapters"
    save_dir.mkdir(parents=True, exist_ok=True)
    current_ch_keys = set(str(k) for k in st.session_state.get('chapters', {}).keys())
    # Write current chapters
    for num, content in st.session_state.get('chapters', {}).items():
        (save_dir / f"{num}.md").write_text(content, encoding='utf-8')
    # Delete stale chapter files on disk that are no longer in memory
    for existing_md in save_dir.glob("*.md"):
        if existing_md.stem not in current_ch_keys:
            try:
                existing_md.unlink()
            except OSError:
                pass

    # Save outline.json
    ol = st.session_state.get('outline_json')
    if ol:
        (pdir / 'outline.json').write_text(
            json.dumps(ol, ensure_ascii=False, indent=2), encoding='utf-8')


def load_project(name: str) -> bool:
    """Load project from project.json into session_state.

    Returns True on success, False if project.json is corrupted and .bak recovery also fails.
    """
    import logging
    _logger = logging.getLogger(__name__)
    pdir = _project_dir(name)

    # Clear old state — reset identity fields first to prevent leakage from previous project
    for key in ('project_name', 'report_name', 'topic', 'report_type', 'profession',
                'parse_done', 'parse_idx', 'parse_results', 'parse_all_chunks',
                'outline_md', 'chapter_titles', 'writing_order', 'chapters',
                '_busy', 'current_order_idx', '_pending_review', '_editing_ch',
                '_stream_buffer', '_writing_order_reason',
                'outline_json', 'writing_hints', 'chapter_notes',
                '_review_tab', '_review_focus', '_step3_active_tab',
                '_project_ingested',
                '_pending_export_dir', '_prev_import_folder',
                '_stale_chapters', '_viewing_completed_chapter',
                'imported_files', 'import_folder',
                '_chunks_loaded'):
        st.session_state[key] = type(st.session_state.get(key, ''))()
    st.session_state['_stale_chapters'] = set()
    st.session_state['_chunks_loaded'] = False
    st.session_state.pop('_import_folder_fingerprint', None)

    pf = pdir / "project.json"
    data = None
    if pf.exists():
        try:
            data = json.loads(pf.read_text(encoding='utf-8'))
        except Exception as e:
            _logger.warning("Failed to load project.json for '%s': %s — trying .bak", name, e)
            # Try backup
            bak = pdir / "project.json.bak"
            if bak.exists():
                try:
                    data = json.loads(bak.read_text(encoding='utf-8'))
                    _logger.info("Recovered project '%s' from project.json.bak", name)
                except Exception as e2:
                    _logger.error("Failed to load project.json.bak for '%s': %s", name, e2)
                    return False
            else:
                return False

        if data is not None:
            # Schema validation: verify critical fields have correct types
            critical_str_fields = ('project_name', 'report_name', 'report_type')
            for f in critical_str_fields:
                if f in data and not isinstance(data[f], str):
                    _logger.warning("Project '%s' has invalid type for '%s', using default", name, f)
                    data.pop(f, None)

            for k in PERSIST_KEYS:
                if k in data:
                    st.session_state[k] = data[k]
            # Deserialization: list -> set
            for k in _SET_KEYS:
                if k in data:
                    if isinstance(data[k], list):
                        st.session_state[k] = set(data[k])
                    else:
                        st.session_state[k] = data[k]
            # Fix key-type issue caused by JSON serialization: chapter_titles keys become str after save, restore to int
            ct = st.session_state.get('chapter_titles')
            if ct:
                converted = {}
                for k, v in ct.items():
                    if isinstance(k, str) and k.lstrip('-').isdigit():
                        converted[int(k)] = v
                    else:
                        converted[k] = v
                st.session_state.chapter_titles = converted
    else:
        st.session_state.project_name = name
        st.session_state.report_name = name

    # Load outline.json
    ol_path = pdir / 'outline.json'
    if ol_path.exists():
        try:
            st.session_state.outline_json = json.loads(ol_path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, IOError):
            pass

    # Load chunks (separate file, avoid bloated project.json)
    # chunks.json is lazy-loaded on demand via load_chunks_on_demand()
    st.session_state.parse_all_chunks = []
    st.session_state['_chunks_loaded'] = False

    # Load chapter files
    ch_dir = pdir / "chapters"
    if ch_dir.exists():
        chapters = {}
        for f in sorted(ch_dir.glob("*.md")):
            chapters[f.stem] = f.read_text(encoding='utf-8')
        if chapters:
            st.session_state['chapters'] = chapters

    return True


def load_chunks_on_demand(project_name: str):
    """Lazy-load chunks.json on demand (only loaded from disk when chunk data is needed).

    Uses a _chunks_loaded sentinel to distinguish "not yet loaded" from "explicitly emptied".
    Once chunks have been loaded (or explicitly set empty), subsequent calls will not re-read
    from disk — preventing deleted data from resurrecting.

    Used for: step_import showing parse results, step_outline loading on ingest.
    """
    import streamlit as st
    # If already loaded in this session, return memory state without touching disk
    if st.session_state.get('_chunks_loaded', False):
        return st.session_state.get('parse_all_chunks', [])

    chunks = st.session_state.get('parse_all_chunks', [])
    if chunks:
        st.session_state['_chunks_loaded'] = True
        return chunks  # Already in memory, no need to reload

    pdir = _project_dir(project_name)
    chunks_path = pdir / 'chunks.json'
    if chunks_path.exists():
        try:
            chunks = json.loads(chunks_path.read_text(encoding='utf-8'))
            st.session_state.parse_all_chunks = chunks
        except (json.JSONDecodeError, IOError):
            pass
    st.session_state['_chunks_loaded'] = True
    return chunks


def delete_project(name: str):
    """Delete the project directory. Close the ChromaDB connection first to release file locks, then delete the files."""
    from kb import KnowledgeBase

    # 1. Explicitly close the KB instance to release the SQLite file lock
    if name in KnowledgeBase._instance_cache:
        try:
            KnowledgeBase._instance_cache[name].close()
        except Exception as e:
            _logger.warning("Failed to close KB instance for project '%s': %s", name, e)
    KnowledgeBase.close_instance(name)

    # 2. Clear the KB cache in session_state
    kb_cache_key = f"_kb_{name}"
    if kb_cache_key in st.session_state:
        try:
            del st.session_state[kb_cache_key]
            gc.collect()
        except Exception as e:
            _logger.warning("Failed to clear KB cache for project '%s': %s", name, e)

    pdir = _project_dir(name)
    if not pdir.exists():
        return

    # 3. Delete vector_db (ChromaDB data) first, then the entire project directory
    vector_db = pdir / "vector_db"
    if vector_db.exists():
        try:
            shutil.rmtree(vector_db)
        except OSError:
            # Retry once if file lock is not released
            import time
            time.sleep(0.5)
            try:
                shutil.rmtree(vector_db)
            except OSError:
                import warnings
                warnings.warn(f"Cannot delete vector DB of project {name}: file is occupied")

    # 4. Delete project directory
    shutil.rmtree(pdir, ignore_errors=True)


def list_projects() -> list:
    """List all existing projects."""
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    for d in sorted(PROJECTS_DIR.iterdir()):
        if d.is_dir():
            info = {
                'name': d.name,
                'report_type': '',
                'report_name': '',
                'profession': '',
                'step': 0,
                'updated_at': '',
                'chapters_done': 0,
                'chapters_total': 0,
            }
            pf = d / "project.json"
            if pf.exists():
                try:
                    data = json.loads(pf.read_text(encoding='utf-8'))
                    info['report_type'] = data.get('report_type', '')
                    info['report_name'] = data.get('report_name', d.name)
                    info['profession'] = data.get('profession', '')
                    info['step'] = data.get('step', 0)
                    info['updated_at'] = data.get('updated_at', '')
                    writing_order = data.get('writing_order', [])
                    info['chapters_total'] = len(writing_order)
                    info['chapters_done'] = data.get('chapters_done', 0)
                except Exception as e:
                    _logger.warning("Failed to read project.json of project '%s': %s", d.name, e)
            else:
                info['report_name'] = d.name
            projects.append(info)
    return projects


def reset_to_new_project():
    """Reset all state — close KB, clear session, re-init defaults."""
    from kb import KnowledgeBase

    # Clean up the KB singleton cache
    old_name = st.session_state.get('project_name')
    if old_name:
        KnowledgeBase.close_instance(old_name)

    for key in ('parse_done', 'parse_idx', 'parse_results', 'parse_all_chunks',
                'outline_md', 'chapter_titles', 'writing_order', 'chapters',
                '_busy', 'current_order_idx', '_pending_review', '_editing_ch',
                '_stream_buffer', '_writing_order_reason',
                'outline_json', 'writing_hints', 'chapter_notes',
                '_review_tab', '_review_focus', '_step3_active_tab',
                '_project_ingested',
                '_pending_export_dir', '_prev_import_folder',
                '_stale_chapters', '_viewing_completed_chapter',
                '_chunks_loaded'):
        st.session_state[key] = type(st.session_state.get(key, ''))()
    st.session_state['_stale_chapters'] = set()
    st.session_state['_chunks_loaded'] = False
    st.session_state.project_name = ''
    st.session_state.report_name = ''
    st.session_state.report_type = '通用咨询报告'
    st.session_state.topic = ''
    st.session_state.import_folder = ''
    st.session_state.imported_files = []
    st.session_state.step = -1
