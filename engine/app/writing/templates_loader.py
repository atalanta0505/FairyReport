"""
模板加载 — 从已安装通用知识包目录读模板 JSON（替代根目录 config.py 的 _load_template）。

未安装通用包 → 抛 TemplatesNotInstalled，调用方映射 409。
模板缓存挂在已装版本上，版本变化自动失效。
"""
from __future__ import annotations

import json
from pathlib import Path

from ..generic.store import GenericStore
from .prompts import (
    DEFAULT_MAX_WORDS_PER_CHAPTER,
    DEFAULT_SUMMARY_CHAPTER_LIMIT,
    MAX_WORDS_PER_CHAPTER,
    REPORT_WORD_LIMITS,
    TEMPLATE_MAP,
)


class TemplatesNotInstalled(Exception):
    """通用知识包未安装，无法读取模板。"""


def _templates_dir() -> Path:
    """返回已安装通用包的 templates 目录；未装则抛异常。"""
    state = GenericStore._read_state()
    if not state or not state.get("version"):
        raise TemplatesNotInstalled("通用知识包未安装，请先 /generic/update")
    vdir = GenericStore._version_dir(state["version"])
    tdir = vdir / "templates"
    if not tdir.is_dir():
        raise TemplatesNotInstalled("通用知识包缺少 templates 目录")
    return tdir


# ── 模板缓存（按版本隔离，版本变化失效）──
_cache: dict[str, dict | None] = {}
_cache_version: str | None = None


def _current_version() -> str | None:
    state = GenericStore._read_state()
    return state.get("version") if state else None


def _ensure_cache_fresh() -> None:
    """版本变化时清缓存。"""
    v = _current_version()
    if v != _cache_version:
        _cache.clear()
        _cache_version_set(v)


def _cache_version_set(v: str | None) -> None:
    global _cache_version
    _cache_version = v


def load_template(report_type: str) -> dict | None:
    """加载指定报告类型的模板 JSON；未装返回 None 由调用方判定。

    注：未装时静默返回 None（与现版 _load_template 一致），由调用方决定是否报 409。
    """
    try:
        _ensure_cache_fresh()
    except Exception:
        return None

    if report_type in _cache:
        return _cache[report_type]

    filename = TEMPLATE_MAP.get(report_type)
    if not filename:
        _cache[report_type] = None
        return None

    try:
        tdir = _templates_dir()
    except TemplatesNotInstalled:
        _cache[report_type] = None
        return None

    tpath = tdir / filename
    if not tpath.exists():
        _cache[report_type] = None
        return None
    with open(tpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    _cache[report_type] = data
    return data


def get_word_limit(report_type: str) -> int:
    tmpl = load_template(report_type)
    if tmpl and tmpl.get("total_words_max"):
        return tmpl["total_words_max"]
    return 0


def get_chapter_word_limit(report_type: str) -> int:
    tmpl = load_template(report_type)
    if tmpl and tmpl.get("per_chapter_max"):
        return tmpl["per_chapter_max"]
    return 0


def get_summary_chapter_limit(report_type: str) -> int:
    tmpl = load_template(report_type)
    if tmpl and tmpl.get("summary_chapter_max"):
        return tmpl["summary_chapter_max"]
    return 0


def is_summary_chapter(report_type: str, chapter_seq: int) -> bool:
    tmpl = load_template(report_type)
    if not tmpl or "chapters" not in tmpl:
        return False
    for ch in tmpl["chapters"]:
        if ch.get("seq") == chapter_seq:
            return ch.get("is_summary", False)
    return False


def get_template_notes(report_type: str) -> str:
    tmpl = load_template(report_type)
    if not tmpl:
        return ""
    return tmpl.get("notes", "")


def get_template_outline_md(report_type: str) -> str:
    tmpl = load_template(report_type)
    if not tmpl:
        return ""
    return tmpl.get("outline_md", "")


def get_chapter_template_prompt(report_type: str) -> str:
    tmpl = load_template(report_type)
    if not tmpl or "chapters" not in tmpl:
        return ""
    chapters = tmpl["chapters"]
    lines = [f"**{report_type}必须严格遵循以下{len(chapters)}章结构：**\n"]
    for ch in chapters:
        title = ch["title"]
        desc = ch.get("description", "")
        if desc:
            lines.append(f"{title}（{desc}）")
        else:
            lines.append(f"{title}")
    lines.append("\n章标题可微调以适应具体项目，但章数和顺序须与以上模板一致。")
    return "\n".join(lines)


def get_chapter_word_budget(report_type: str, chapter_seq: int) -> int:
    tmpl = load_template(report_type)
    if tmpl and "chapters" in tmpl:
        for ch in tmpl["chapters"]:
            if ch.get("seq") == chapter_seq:
                return ch.get("word_budget", 0)
    return 0


def get_writing_order(report_type: str, total_chapters: int = 0) -> list[int]:
    """返回推荐章节写作顺序。优先取模板显式配置，其次按 is_summary 拓扑推导。"""
    tmpl = load_template(report_type)
    if tmpl and tmpl.get("writing_order"):
        return list(tmpl["writing_order"])

    if tmpl and "chapters" in tmpl and tmpl["chapters"]:
        chs = tmpl["chapters"]
        max_s = max(c.get("seq", 0) for c in chs)

        # 1. 提取首部综述章（如 seq == 1 且 is_summary）
        first_summary = [c["seq"] for c in chs if c.get("seq") == 1 and c.get("is_summary", False)]
        non_first = [c["seq"] for c in chs if c.get("seq") == 1 and not c.get("is_summary", False)]

        # 2. 提取尾部综述章（如 seq == max_s 且 is_summary）
        last_summary = [c["seq"] for c in chs if c.get("seq") == max_s and c.get("is_summary", False)]
        non_last = [c["seq"] for c in chs if c.get("seq") == max_s and not c.get("is_summary", False)]

        # 3. 中间主体章节（2 <= seq < max_s）
        body = [c["seq"] for c in chs if 1 < c.get("seq", 0) < max_s]

        order = non_first + body + non_last + first_summary + last_summary
        if order:
            return order

    if total_chapters > 0:
        return list(range(1, total_chapters + 1))
    return []


def get_writing_order_reason(report_type: str) -> str:
    """返回推荐写作顺序的逻辑说明。"""
    tmpl = load_template(report_type)
    if tmpl and tmpl.get("writing_order_reason"):
        return tmpl["writing_order_reason"]
    order = get_writing_order(report_type)
    if order and len(order) > 1 and order[0] != 1:
        return "先完成背景、需求、选址、工程方案及投资等主体论证章节，再汇总提炼第一章概述与综合结论，确保全书数据逻辑自洽与高效推演。"
    return "按照报告标准章节结构依次推进编写，确保各章节逻辑严密衔接。"


def require_installed() -> None:
    """显式要求通用包已安装；未装抛 TemplatesNotInstalled（路由映射 409）。"""
    state = GenericStore._read_state()
    if not state or not state.get("version"):
        raise TemplatesNotInstalled("通用知识包未安装，请先 /generic/update")
    if not GenericStore._version_dir(state["version"]).exists():
        raise TemplatesNotInstalled("通用知识包目录缺失")
