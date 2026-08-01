"""
Exporter v1.0.5 — Markdown -> Word (.docx) export + three-tier reference list
- python-docx conversion, preserves 5 levels of headings
- Supports **bold**/*italic* inline formatting
- Supports Markdown table to native Word table
- Supports LaTeX formula ($...$ / $$...$$) extraction, preserved as italic formula regions
- PDF export not yet implemented (future iteration)
"""
import re
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from ref_manager import (
    _strip_ref_section,
    merge_global_refs,
    global_assign_ref_numbers,
    generate_global_ref_list,
)

# ── LaTeX formula regex ──
_LATEX_DISPLAY = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)
_LATEX_INLINE = re.compile(r'(?<!\$)\$(.+?)\$(?!\$)')


def _has_latex_formulas(text: str) -> bool:
    """Detect whether text contains LaTeX formulas."""
    return bool(_LATEX_INLINE.search(text)) or bool(_LATEX_DISPLAY.search(text))


def md_to_docx(md_content: str, output_path: str) -> str:
    """Convert Markdown content to a formatted Word document."""
    doc = Document()

    # ── Default style ──
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

    # ── Preprocessing: extract display formula ($$...$$) blocks, replace with placeholders to prevent line splitting ──
    display_formulas = {}
    _df_counter = [0]

    def _replace_display(m):
        _df_counter[0] += 1
        key = f"\x00LATEX_DISPLAY_{_df_counter[0]}\x00"
        display_formulas[key] = m.group(1).strip()
        return key

    processed = _LATEX_DISPLAY.sub(_replace_display, md_content)

    lines = processed.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]

        # ── Display formula placeholder -> insert formula paragraph ──
        if line.strip().startswith('\x00LATEX_DISPLAY_'):
            key = line.strip()
            if key in display_formulas:
                p = doc.add_paragraph()
                p.alignment = 1  # center
                run = p.add_run(f"${display_formulas[key]}$")
                run.italic = True
                run.font.size = Pt(11)
            i += 1
            continue

        # ── Table detection ──
        if line.strip().startswith('|') and line.strip().endswith('|') and '---' not in line:
            table_lines = [line]
            j = i + 1
            while j < len(lines):
                nl = lines[j].strip()
                if nl.startswith('|') and nl.endswith('|') and not nl.startswith('\x00'):
                    table_lines.append(nl)
                    j += 1
                else:
                    break
            if len(table_lines) >= 2:
                _add_table(doc, table_lines)
                i = j
                continue

        level, text, is_heading = _parse_md_line(line)

        if is_heading:
            doc.add_heading(text, level=level)
        elif text.strip():
            _add_formatted_paragraph(doc, text)

        i += 1

    doc.save(output_path)
    return output_path


def _add_table(doc, table_lines: list):
    """Add a native Word table."""
    rows = []
    for tl in table_lines:
        # Skip separator row (|---|---|)
        stripped = tl.strip()
        if re.match(r'^\|[\s\-:|]+\|$', stripped):
            continue
        # Split cells: strip leading/trailing | then split by |
        cells = [c.strip() for c in stripped[1:-1].split('|')]
        rows.append(cells)

    if not rows:
        return

    num_cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=num_cols, style='Table Grid')

    for ri, row_cells in enumerate(rows):
        for ci, cell_text in enumerate(row_cells):
            if ci < num_cols:
                cell = table.cell(ri, ci)
                # Clear the default paragraph before writing
                cell.paragraphs[0].clear()
                run = cell.paragraphs[0].add_run(cell_text)
                run.font.size = Pt(10)


def _add_formatted_paragraph(doc, text: str):
    """Add a paragraph with inline formatting (**bold**, *italic*) + inline LaTeX ($...$)."""
    p = doc.add_paragraph()
    # First split by inline LaTeX
    parts = _LATEX_INLINE.split(text)
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            # LaTeX inline formula -> italic
            run = p.add_run(f"${part}$")
            run.italic = True
        else:
            # Plain text -> apply bold/italic parsing
            segments = _parse_inline_formatting(part)
            for seg_text, is_bold, is_italic in segments:
                if not seg_text:
                    continue
                run = p.add_run(seg_text)
                if is_bold:
                    run.bold = True
                if is_italic:
                    run.italic = True


def _parse_inline_formatting(text: str) -> list:
    """Parse inline formatting, return [(text, is_bold, is_italic), ...]."""
    import re
    # Regex: **text** or *text*
    pattern = re.compile(r'(\*\*(.+?)\*\*|\*(.+?)\*)')
    result = []
    last_end = 0

    for m in pattern.finditer(text):
        # Preceding plain text
        if m.start() > last_end:
            result.append((text[last_end:m.start()], False, False))

        if m.group(2) is not None:
            # **bold**
            result.append((m.group(2), True, False))
        elif m.group(3) is not None:
            # *italic*
            result.append((m.group(3), False, True))
        last_end = m.end()

    # Trailing plain text
    if last_end < len(text):
        result.append((text[last_end:], False, False))

    return result if result else [(text, False, False)]


def _parse_md_line(line: str):
    """Parse a Markdown line into (level, text, is_heading)."""
    match = re.match(r'^(#{1,6})\s+(.*)', line)
    if match:
        return len(match.group(1)), match.group(2).strip(), True
    return 0, line, False


def generate_report_ref(chapters: dict, output_path: str, refs: list = None):
    """
    Generate the three-tier reference file report_ref.md (v1.0.2: merged from per-chapter 📎 sections)

    - Merge and dedupe references from each chapter's 📎 section to get a global list
    - Strip 📎, concatenate body, one-pass numbering on the full body
    - Sort by number and output references

    The `refs` parameter is kept for backward compatibility (no longer used in v1.0.2, ignored).
    """
    # v1.0.2: merge all chapter reference lists
    global_refs = merge_global_refs(chapters)

    # v1.0.2: strip 📎, concatenate body, one-pass numbering
    body_parts = []
    for ch_key in sorted(chapters.keys(),
                         key=lambda k: int(k) if str(k).lstrip('-').isdigit() else 0):
        content = chapters.get(ch_key, "")
        if content:
            body_parts.append(_strip_ref_section(content))
    full_body = "\n\n".join(body_parts)
    _, numbering = global_assign_ref_numbers(full_body)

    # Generate and write
    ref_content = generate_global_ref_list(global_refs, numbering)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ref_content)
    except IOError:
        pass
