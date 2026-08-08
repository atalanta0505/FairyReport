"""
Reference-list management with numbering deferred to export.

Each chapter body embeds a 📎 Reference section at the end, in the format:
  ---
  ## 📎 Chapter References
  ### Project Material
  - filename — source path
  ### Web Links
  - title — URL
  ### AI Self-Knowledge
  - [Z] — general domain knowledge supplement

The 【源:xxx】/【网:xxx】 tags are kept intact during writing/modification phases; numeric numbers are not assigned.
Numbering is performed at export time by scanning the full body in order of first occurrence and assigning [1][2][3]... .
"""
import re


# ═══════════════════════════════════════════════
# Reference section sentinel
# ═══════════════════════════════════════════════

_REF_SECTION_MARKER = "\n\n---\n\n## 📎 本章参考资料"


# ═══════════════════════════════════════════════
# Cleaning & extraction (writing phase)
# ═══════════════════════════════════════════════

def strip_fabricated_labels(chapter_text: str, rag_context: str) -> str:
    """Strip fabricated source labels from the LLM: keep only labels that actually appear in rag_context.

    The LLM sometimes invents 【源:xxx】/【网:xxx】 tags (e.g. by formatting body sentences as labels).
    This function scans chapter_text; any label not found in rag_context is treated as fabricated
    and replaced with [Z].
    """
    if not rag_context or not chapter_text:
        return chapter_text

    # Extract all valid labels from rag_context
    valid_labels = set()
    for m in re.finditer(r'【(?:源|网):.+?】', rag_context):
        valid_labels.add(m.group(0))

    if not valid_labels:
        return chapter_text

    source_pat = re.compile(r'【(源|网):.+?】')

    def _clean(m):
        return m.group(0) if m.group(0) in valid_labels else '[Z]'

    return source_pat.sub(_clean, chapter_text)


def _extract_url_for_label(label: str, rag_context: str) -> str:
    """Extract the URL corresponding to a web reference label from rag_context.

    rag_context format: 【网:title】\n  url\n  > content
    """
    if not rag_context:
        return ""
    title_match = re.match(r'【网:(.+?)】', label)
    if not title_match:
        return ""
    title = re.escape(title_match.group(1).strip())
    pattern = rf'【网:{title}】\s*\n\s*(https?://\S+)'
    m = re.search(pattern, rag_context)
    if m:
        return m.group(1).strip()
    return ""


def extract_chapter_refs(body: str, rag_context: str = "") -> list:
    """Extract all reference tags and their source info from the chapter body.

    Returns [{"label": "【源:xxx】", "name": "...", "source": "...", "type": "项目资料"}, ...]
    Same label is deduped, ordered by first occurrence.
    [Z] references are categorized separately as AI self-knowledge.
    """
    refs = []
    seen_labels = set()

    # Project material: 【源:filename】
    for m in re.finditer(r'【源:(.+?)】', body):
        label = m.group(0)
        if label not in seen_labels:
            seen_labels.add(label)
            name = m.group(1).strip()
            refs.append({
                "label": label,
                "name": name,
                "source": name,
                "type": "项目资料"
            })

    # Web links: 【网:title】
    for m in re.finditer(r'【网:(.+?)】', body):
        label = m.group(0)
        if label not in seen_labels:
            seen_labels.add(label)
            name = m.group(1).strip()
            source = _extract_url_for_label(label, rag_context) or name
            refs.append({
                "label": label,
                "name": name,
                "source": source,
                "type": "网页链接"
            })

    # AI self-knowledge: [Z]
    if '[Z]' in body and '[Z]' not in seen_labels:
        refs.append({
            "label": "[Z]",
            "name": "[Z]",
            "source": "AI自有知识，请注意甄别内容真实性",
            "type": "AI自有知识"
        })

    return refs


def build_chapter_ref_section(refs: list) -> str:
    """Generate a 「📎 Chapter References」 Markdown section from the reference list.

    Grouped by type: project material / web links / AI self-knowledge.
    Returns an empty string if there are no references.
    """
    if not refs:
        return ""

    project_items = [r for r in refs if r["type"] == "项目资料"]
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


# ═══════════════════════════════════════════════
# 📎 Section parsing & stripping
# ═══════════════════════════════════════════════

def _strip_ref_section(text: str) -> str:
    """Strip the 📎 Reference section at the end of chapter text, return body only."""
    idx = text.find(_REF_SECTION_MARKER)
    if idx != -1:
        return text[:idx]
    return text


def _parse_ref_section(text: str) -> list:
    """Parse the 📎 Reference section from chapter text.

    Returns [{"label": "...", "name": "...", "source": "...", "type": "..."}, ...]
    Returns an empty list if the section is not found.
    """
    idx = text.find(_REF_SECTION_MARKER)
    if idx == -1:
        return []

    section = text[idx + len(_REF_SECTION_MARKER):]
    refs = []
    current_type = None

    for line in section.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('### 项目资料'):
            current_type = '项目资料'
        elif line.startswith('### 网页链接'):
            current_type = '网页链接'
        elif line.startswith('### AI自有知识'):
            current_type = 'AI自有知识'
        elif line.startswith('- ') and current_type:
            item = line[2:].strip()
            if ' — ' in item:
                name, source = item.split(' — ', 1)
            else:
                name = item
                source = item

            if name.startswith('[Z]'):
                label = '[Z]'
            elif current_type == '项目资料':
                label = f'【源:{name}】'
            elif current_type == '网页链接':
                label = f'【网:{name}】'
            else:
                label = name

            refs.append({
                "label": label,
                "name": name,
                "source": source,
                "type": current_type
            })

    return refs


# ═══════════════════════════════════════════════
# Reference Tab display data
# ═══════════════════════════════════════════════

def get_chapter_refs_display(chapters: dict, chapter_titles: dict = None) -> list:
    """Generate chapter-grouped reference data for the References Tab, with cross-chapter first-occurrence annotation.

    Returns [{"chapter": "1", "title": "第一章 xxx",
              "refs": [{"name": "...", "source": "...", "type": "...",
                        "first_in": "第一章 xxx"}, ...]}, ...]
    Cross-chapter duplicate references are annotated as ↗ first seen in chapter X.
    """
    if not chapter_titles:
        chapter_titles = {}

    # First pass: determine the first-occurrence chapter for each (name, type)
    first_occurrence = {}
    all_chapter_refs = []

    for ch_key in sorted(chapters.keys(),
                         key=lambda k: int(k) if str(k).lstrip('-').isdigit() else 0):
        ch_text = chapters.get(ch_key, "")
        refs = _parse_ref_section(ch_text)
        # Chapter-title keys may be integers or strings.
        try:
            int_key = int(ch_key)
        except (ValueError, TypeError):
            int_key = None
        title = (chapter_titles.get(ch_key) or
                 (chapter_titles.get(int_key) if int_key is not None else None) or
                 chapter_titles.get(str(ch_key)) or
                 f"第{ch_key}章")
        all_chapter_refs.append((ch_key, title, refs))

        for ref in refs:
            # [Z] AI self-knowledge does not participate in cross-chapter first-occurrence tracking
            if ref['type'] != 'AI自有知识':
                key = (ref['name'], ref['type'])
                if key not in first_occurrence:
                    first_occurrence[key] = title

    # Second pass: annotate
    result = []
    for ch_key, title, refs in all_chapter_refs:
        annotated = []
        for ref in refs:
            r = dict(ref)
            if ref['type'] == 'AI自有知识':
                r['first_in'] = title  # General knowledge, do not annotate first-occurrence chapter
            else:
                key = (ref['name'], ref['type'])
                r['first_in'] = first_occurrence.get(key, title)
            annotated.append(r)
        if annotated:
            result.append({
                "chapter": ch_key,
                "title": title,
                "refs": annotated
            })

    return result


# ═══════════════════════════════════════════════
# Export phase: global merge & numbering
# ═══════════════════════════════════════════════

def merge_global_refs(chapters: dict) -> list:
    """Merge all chapter reference lists, dedupe (same name+type keeps the first-occurrence chapter).

    Returns [{"label": "...", "name": "...", "source": "...", "type": "..."}, ...]
    Scans in chapter-order, first occurrence wins.
    """
    seen = set()
    merged = []

    for ch_key in sorted(chapters.keys(),
                         key=lambda k: int(k) if str(k).lstrip('-').isdigit() else 0):
        ch_text = chapters.get(ch_key, "")
        refs = _parse_ref_section(ch_text)
        for ref in refs:
            key = (ref['name'], ref['type'])
            if key not in seen:
                seen.add(key)
                merged.append(ref)

    return merged


def global_assign_ref_numbers(full_body: str) -> tuple:
    """One-pass numbering on the full body: scan all 【源:xxx】/【网:xxx】 tags, assign [N] by first occurrence.

    Uses a two-phase placeholder substitution to avoid number collisions:
      Phase 1: tag → \x00REF_N\x00 (null-byte sentinel, cannot appear in body text)
      Phase 2: \x00REF_N\x00 → [N]

    Returns (numbered_body, numbering_dict)
      numbering_dict: {"【源:xxx】": 1, "【网:xxx】": 2, ...}
    """
    label_pat = re.compile(r'【(?:源|网):.+?】')
    seen = []
    seen_set = set()

    for m in label_pat.finditer(full_body):
        label = m.group(0)
        if label not in seen_set:
            seen_set.add(label)
            seen.append(label)

    numbering = {label: i + 1 for i, label in enumerate(seen)}

    # Phase 1: tag → sentinel placeholder
    text = full_body
    for label, num in numbering.items():
        text = text.replace(label, f"\x00REF_{num}\x00")

    # Phase 2: sentinel → [N]
    for num in range(1, len(seen) + 1):
        text = text.replace(f"\x00REF_{num}\x00", f"[{num}]")

    return text, numbering


def generate_global_ref_list(global_refs: list, numbering: dict) -> str:
    """Generate the export _ref.md content from merged references + numbering map.

    global_refs: output of merge_global_refs()
    numbering: second return value of global_assign_ref_numbers()
    """
    if not global_refs:
        return "# 参考资料清单\n\n（未检测到引用标记）\n"

    # Sort by assigned number
    sorted_refs = sorted(global_refs,
                         key=lambda r: numbering.get(r['label'], 99999))

    project_items = [r for r in sorted_refs if r['type'] == '项目资料']
    web_items = [r for r in sorted_refs if r['type'] == '网页链接']
    ai_items = [r for r in sorted_refs if r['type'] == 'AI自有知识']

    lines = ["# 参考资料清单\n", "> 自动生成于报告导出时\n"]

    if project_items:
        lines.append("## 项目资料\n")
        for r in project_items:
            n = numbering.get(r['label'], '?')
            name = r.get('name', '')
            source = r.get('source', '')
            if source and source != name:
                lines.append(f"- [{n}] {name} — 来源: {source}")
            else:
                lines.append(f"- [{n}] {name}")
        lines.append("")

    if web_items:
        lines.append("## 网页链接\n")
        for r in web_items:
            n = numbering.get(r['label'], '?')
            name = r.get('name', '')
            source = r.get('source', '')
            if source and source != name:
                lines.append(f"- [{n}] {name} — {source}")
            else:
                lines.append(f"- [{n}] {name}")
        lines.append("")

    if ai_items:
        lines.append("## AI自有知识\n")
        lines.append("（由 AI 在编写过程中补充的通用领域知识）\n")

    return '\n'.join(lines)
