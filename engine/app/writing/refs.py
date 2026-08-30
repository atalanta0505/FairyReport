"""
引用管理 — 项目底稿【源:...】+ 规程标准【标:...】+ 百度联网【网:...】标准化引用体系。

每章正文末尾内嵌 📎 参考资料段，格式：
  【源:filename】/【标:standard_name】/【网:title】
编号在导出时按首次出现顺序统一分配 [N]。
"""
from __future__ import annotations

import re

_REF_SECTION_MARKER = "\n\n---\n\n## 📎 本章参考资料"


def strip_fabricated_labels(chapter_text: str, rag_context: str) -> str:
    """剥离 LLM 编造的来源标签：只保留 rag_context 中实际出现的标签。

    不在 rag_context 中的虚构标签直接剥除，彻底消灭孤立 [Z]。
    """
    if not chapter_text:
        return ""
    if not rag_context:
        return re.sub(r"【(?:源|标|网):.+?】", "", chapter_text)

    valid_labels = set()
    for m in re.finditer(r"【(?:源|标|网):.+?】", rag_context):
        valid_labels.add(m.group(0))

    source_pat = re.compile(r"【(?:源|标|网):.+?】")

    def _clean(m):
        return m.group(0) if m.group(0) in valid_labels else ""

    return source_pat.sub(_clean, chapter_text)


def _extract_url_for_label(label: str, rag_context: str) -> str:
    """从 rag_context 提取网页标签对应的真实完整 URL。"""
    if not rag_context:
        return ""
    title_match = re.match(r"【网:(.+?)】", label)
    if not title_match:
        return ""
    title = re.escape(title_match.group(1).strip())
    pattern = rf"【网:{title}】[^\n]*\n?\s*(https?://[^\s\)]+)"
    m = re.search(pattern, rag_context)
    if m:
        return m.group(1).strip()
    pattern_fallback = rf"{title}[^\n]*\s+(https?://[^\s\)]+)"
    m2 = re.search(pattern_fallback, rag_context)
    if m2:
        return m2.group(1).strip()
    return ""


def extract_chapter_refs(body: str, rag_context: str = "") -> list:
    """提取正文中所有引用标签及其来源信息。

    返回 [{"label", "name", "source", "type"}, ...]；同标签去重，按首次出现排序。
    """
    if not body:
        return []

    refs = []
    seen_labels = set()

    for m in re.finditer(r"【源:(.+?)】", body):
        label = m.group(0)
        if label not in seen_labels:
            seen_labels.add(label)
            name = m.group(1).strip()
            refs.append({
                "label": label,
                "name": name,
                "source": name,
                "type": "项目资料",
            })

    for m in re.finditer(r"【标:(.+?)】", body):
        label = m.group(0)
        if label not in seen_labels:
            seen_labels.add(label)
            name = m.group(1).strip()
            refs.append({
                "label": label,
                "name": name,
                "source": name,
                "type": "规程标准",
            })

    for m in re.finditer(r"【网:(.+?)】", body):
        label = m.group(0)
        if label not in seen_labels:
            seen_labels.add(label)
            name = m.group(1).strip()
            source = _extract_url_for_label(label, rag_context) or name
            refs.append({
                "label": label,
                "name": name,
                "source": source,
                "type": "网页链接",
            })

    if "[Z]" in body and "[Z]" not in seen_labels:
        refs.append({
            "label": "[Z]",
            "name": "[Z]",
            "source": "通用领域行业标准与规程",
            "type": "规程标准",
        })

    return refs


def build_chapter_ref_section(refs: list) -> str:
    """根据引用列表生成「📎 本章参考资料」Markdown 段。按类型分组；无引用返回空串。"""
    if not refs:
        return ""

    project_items = [r for r in refs if r["type"] == "项目资料"]
    standard_items = [r for r in refs if r["type"] == "规程标准"]
    web_items = [r for r in refs if r["type"] == "网页链接"]
    ai_items = [r for r in refs if r["type"] == "AI自有知识"]

    lines = ["---", "", "## 📎 本章参考资料", ""]

    if project_items:
        lines.append("### 项目资料")
        for r in project_items:
            name = r["name"]
            source = r.get("source", "")
            if source and source != name:
                lines.append(f"- {name} — {source}")
            else:
                lines.append(f"- {name}")
        lines.append("")

    if standard_items:
        lines.append("### 规程标准")
        for r in standard_items:
            name = r["name"]
            source = r.get("source", "")
            if source and source != name:
                lines.append(f"- {name} — {source}")
            else:
                lines.append(f"- {name}")
        lines.append("")

    if web_items:
        lines.append("### 网页链接")
        for r in web_items:
            name = r["name"]
            source = r.get("source", "")
            if source and source != name:
                lines.append(f"- {name} — {source}")
            else:
                lines.append(f"- {name}")
        lines.append("")

    if ai_items:
        lines.append("### AI自有知识")
        lines.append("- [Z] — 通用领域知识补充")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _strip_ref_section(text: str) -> str:
    """剥离章末 📎 参考资料段，返回正文。"""
    idx = text.find(_REF_SECTION_MARKER)
    if idx != -1:
        return text[:idx]
    return text


def _parse_ref_section(text: str) -> list:
    """从章文本解析 📎 参考资料段。返回引用列表；无段返回空列表。"""
    idx = text.find(_REF_SECTION_MARKER)
    if idx == -1:
        return []

    section = text[idx + len(_REF_SECTION_MARKER):]
    refs = []
    current_type = None

    for line in section.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("### 项目资料"):
            current_type = "项目资料"
        elif line.startswith("### 规程标准"):
            current_type = "规程标准"
        elif line.startswith("### 网页链接"):
            current_type = "网页链接"
        elif line.startswith("### AI自有知识"):
            current_type = "AI自有知识"
        elif line.startswith("- ") and current_type:
            item = line[2:].strip()
            if " — " in item:
                name, source = item.split(" — ", 1)
            else:
                name = item
                source = item

            if name.startswith("[Z]"):
                label = "[Z]"
            elif current_type == "项目资料":
                label = f"【源:{name}】"
            elif current_type == "规程标准":
                label = f"【标:{name}】"
            elif current_type == "网页链接":
                label = f"【网:{name}】"
            else:
                label = name

            refs.append({
                "label": label,
                "name": name,
                "source": source,
                "type": current_type,
            })

    return refs


def merge_global_refs(chapters: dict) -> list:
    """合并所有章引用列表，去重（同名+同类型保留首次出现章）。按章序扫描。"""
    seen = set()
    merged = []

    for ch_key in sorted(
        chapters.keys(),
        key=lambda k: int(k) if str(k).lstrip("-").isdigit() else 0,
    ):
        ch_text = chapters.get(ch_key, "")
        refs = _parse_ref_section(ch_text)
        if not refs:
            refs = extract_chapter_refs(ch_text)
        for ref in refs:
            key = (ref["name"], ref["type"])
            if key not in seen:
                seen.add(key)
                merged.append(ref)

    return merged


def global_assign_ref_numbers(full_body: str) -> tuple:
    """对全文一次性编号：扫描所有【源:xxx】/【标:xxx】/【网:xxx】标签，按首次出现分配 [N]。

    两阶段占位替换避免编号冲突：
      阶段1：标签 → \\x00REF_N\\x00（空字节哨兵，正文不可能出现）
      阶段2：\\x00REF_N\\x00 → [N]
    返回 (numbered_body, numbering_dict)。
    """
    label_pat = re.compile(r"【(?:源|标|网):.+?】")
    seen = []
    seen_set = set()

    for m in label_pat.finditer(full_body):
        label = m.group(0)
        if label not in seen_set:
            seen_set.add(label)
            seen.append(label)

    numbering = {label: i + 1 for i, label in enumerate(seen)}

    text = full_body
    for label, num in numbering.items():
        text = text.replace(label, f"\x00REF_{num}\x00")

    for num in range(1, len(seen) + 1):
        text = text.replace(f"\x00REF_{num}\x00", f"[{num}]")

    return text, numbering


def generate_global_ref_list(global_refs: list, numbering: dict) -> str:
    """根据合并引用 + 编号映射生成导出 _ref.md 内容（GB/T 7714 标准格式）。"""
    if not global_refs:
        return "# 参考文献\n\n（全书未引用外部参考资料）\n"

    sorted_refs = sorted(
        global_refs,
        key=lambda r: numbering.get(r.get("label", ""), 99999),
    )

    lines = ["# 参考文献\n", "> 依据 GB/T 7714 信息与文献 参考文献著录规则 自动汇总排序\n"]

    for r in sorted_refs:
        label = r.get("label", "")
        n = numbering.get(label, "?")
        name = r.get("name", "")
        source = r.get("source", "")
        ref_type = r.get("type", "项目资料")

        if ref_type in ("网页链接", "web"):
            url_part = f" 访问网址: {source}" if (source and source.startswith("http")) else ""
            lines.append(f"[{n}] [联网检索] {name}.{url_part}")
        elif ref_type in ("规程标准", "standard"):
            lines.append(f"[{n}] [规程标准] {name}.")
        elif ref_type == "AI自有知识":
            lines.append(f"[{n}] [领域知识] {name} — 通用领域工程专业知识补充.")
        else:
            source_part = f" — 来源: {source}" if (source and source != name) else ""
            lines.append(f"[{n}] [项目资料] {name}{source_part}.")

    return "\n".join(lines) + "\n"
