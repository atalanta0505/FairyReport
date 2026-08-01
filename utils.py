"""
FairyReport v1.0.5 - Utility functions
"""
import io
import logging
import re
import time
from pathlib import Path

from dotenv import set_key
from dotenv.parser import parse_stream
import streamlit as st

from config import PROJECT_ROOT, PROJECTS_DIR, DATA_ROOT
from outline import OutlineGenerator

_logger = logging.getLogger(__name__)


def _pick_folder() -> str:
    """Open a folder selection dialog (Linux: zenity, Windows: tkinter)."""
    import sys
    try:
        if sys.platform.startswith('linux'):
            import subprocess
            result = subprocess.run(
                ['zenity', '--file-selection', '--directory', '--title=选择文件夹'],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return ""
        else:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder = filedialog.askdirectory(title="选择文件夹")
            root.destroy()
            return folder if folder else ""
    except Exception as e:
        _logger.warning("Failed to open folder selection dialog: %s", e)
        return ""


def _sanitize_project_name(name: str) -> str:
    """Sanitize report_name for filesystem-safe use."""
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    sanitized = sanitized.strip('. ')
    return sanitized or "未命名项目"


def _resolve_project_name(name: str) -> str:
    """Detect project directory conflicts, append (2) (3) suffix as needed. Project name truncated to 50 characters."""
    base = _sanitize_project_name(name)
    # Truncate to 50 characters (feature requirement: length must not exceed 50 characters)
    if len(base) > 50:
        base = base[:50]
    candidate = base
    n = 2
    while (PROJECTS_DIR / candidate).exists():
        candidate = f"{base}({n})"
        n += 1
    return candidate


def _update_env(key: str, value: str):
    """Update a key-value pair in the .env file using python-dotenv for robust quoting.

    On Windows, python-dotenv's atomic replace (os.replace) can fail with
    PermissionError when the target .env file is locked by another process.
    In that case, fall back to a direct in-place write that preserves the
    existing file structure.
    """
    env_path = DATA_ROOT / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)

    # Retry a few times in case the lock is transient (antivirus, file watcher).
    last_error = None
    for _ in range(3):
        try:
            set_key(str(env_path), key, value)
            return
        except PermissionError as e:
            last_error = e
            time.sleep(0.3)

    # Fallback: write directly without atomic replace.
    _update_env_direct_write(env_path, key, value)


def _update_env_direct_write(env_path: Path, key: str, value: str):
    """Write a key-value pair directly to the .env file.

    This bypasses python-dotenv's atomic replace, which can fail on Windows
    when the .env file is locked. The quoting logic matches python-dotenv's
    default "always" quote mode.
    """
    quote = "'"
    escaped_quote = "\\'"
    line_out = f"{key}={quote}{value.replace(quote, escaped_quote)}{quote}\n"

    if env_path.exists():
        source = io.StringIO(env_path.read_text(encoding="utf-8"))
    else:
        source = io.StringIO("")

    lines = []
    replaced = False
    missing_newline = False

    for mapping in parse_stream(source):
        if mapping.key == key:
            lines.append(line_out)
            replaced = True
        else:
            lines.append(mapping.original.string)
            missing_newline = not mapping.original.string.endswith("\n")

    if not replaced:
        if missing_newline:
            lines.append("\n")
        lines.append(line_out)

    env_path.write_text("".join(lines), encoding="utf-8")


def _sync_chapter_title_to_outline(ch_key: str, chapter_content: str):
    """Extract title from chapter body; if it differs, force-sync to outline_md / outline_json / chapter_titles."""
    match = re.search(r'^#\s+(第[一二三四五六七八九十百零\d]+章.+)', chapter_content, re.MULTILINE)
    if not match:
        return None, None
    new_title = match.group(1).strip()

    ch_num = int(ch_key) if ch_key.lstrip('-').isdigit() else None
    if ch_num is None:
        return None, None

    old_title = st.session_state.chapter_titles.get(ch_num, '')
    if not old_title or new_title == old_title:
        return None, None

    st.session_state.chapter_titles[ch_num] = new_title

    old_md = st.session_state.get('outline_md', '')
    if old_md:
        escaped = re.escape(old_title)
        new_md = re.sub(r'^#{1,2}\s+' + escaped + r'$', f'# {new_title}', old_md, count=1, flags=re.MULTILINE)
        if new_md != old_md:
            st.session_state.outline_md = new_md

    oj = st.session_state.get('outline_json')
    if oj:
        OutlineGenerator.update_outline_json_title(oj, ch_num, new_title)

    return old_title, new_title
