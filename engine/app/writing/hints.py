"""
章节提示持久化 — 移植自根目录 hint_store.py。

存储路径改挂 ENGINE_DATA_DIR：projects/<project_name>/hints/chapter{N}_hint.md
"""
import os

from ..config import settings


def get_hints_dir(project_name: str) -> str:
    """返回项目提示目录：ENGINE_DATA_DIR/projects/<project>/hints。"""
    return os.path.join(settings.projects_dir, project_name, "hints")


def save_hint(project_name: str, ch_seq: int, hint_text: str) -> str:
    """保存章节提示；返回文件路径。"""
    os.makedirs(get_hints_dir(project_name), exist_ok=True)
    path = os.path.join(get_hints_dir(project_name), f"chapter{ch_seq}_hint.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(hint_text)
    return path


def load_hint(project_name: str, ch_seq: int) -> str:
    """读取章节提示；不存在返回空串。"""
    path = os.path.join(get_hints_dir(project_name), f"chapter{ch_seq}_hint.md")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def get_predecessor_seqs(writing_order: list, current_ch_seq: int) -> list:
    """返回在写作顺序中先于当前章的章序号列表。"""
    try:
        pos = writing_order.index(current_ch_seq)
        return writing_order[:pos]
    except ValueError:
        return []


def get_predecessor_hints(project_name: str, writing_order: list,
                          current_ch_seq: int) -> dict:
    """返回前序章提示 {ch_seq: hint_text}。"""
    result = {}
    for seq in get_predecessor_seqs(writing_order, current_ch_seq):
        hint = load_hint(project_name, seq)
        if hint:
            result[seq] = hint
    return result
