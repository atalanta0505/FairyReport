"""
hint_store.py — Writing hint persistence helpers

Storage location: data/projects/<project_name>/hints/chapter{N}_hint.md
"""
import os
from config import PROJECTS_DIR


def get_hints_dir(project_name: str) -> str:
    return os.path.join(PROJECTS_DIR, project_name, "hints")


def save_hint(project_name: str, ch_seq: int, hint_text: str):
    os.makedirs(get_hints_dir(project_name), exist_ok=True)
    path = os.path.join(get_hints_dir(project_name), f"chapter{ch_seq}_hint.md")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(hint_text)


def load_hint(project_name: str, ch_seq: int) -> str:
    path = os.path.join(get_hints_dir(project_name), f"chapter{ch_seq}_hint.md")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def get_predecessor_seqs(writing_order: list, current_ch_seq: int) -> list:
    """Return the list of chapter seqs that precede the current chapter in the writing order."""
    try:
        pos = writing_order.index(current_ch_seq)
        return writing_order[:pos]
    except ValueError:
        return []


def get_predecessor_hints(project_name: str, writing_order: list,
                          current_ch_seq: int) -> dict:
    """Return hints of predecessor chapters as {ch_seq: hint_text}."""
    result = {}
    for seq in get_predecessor_seqs(writing_order, current_ch_seq):
        hint = load_hint(project_name, seq)
        if hint:
            result[seq] = hint
    return result
