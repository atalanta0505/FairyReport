"""
Markdown -> Word (.docx) 导出 — 移植自根目录 exporter.py（v1.0.5）。

- python-docx 转换，保留 5 级标题
- 支持 **加粗**/*斜体* 行内格式
- 支持 Markdown 表格转原生 Word 表格
- 支持 LaTeX 公式（$...$ / $$...$$）检测与保留（斜体公式区）
- 引用函数复用 engine/app/writing/refs.py（global_assign_ref_numbers / generate_global_ref_list）
"""
import re

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

from ..writing.refs import (
    _strip_ref_section,
    generate_global_ref_list,
    global_assign_ref_numbers,
    merge_global_refs,
)

# ── LaTeX 公式正则 ──
_LATEX_DISPLAY = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)
_LATEX_INLINE = re.compile(r'(?<!\$)\$(.+?)\$(?!\$)')


def _has_latex_formulas(text: str) -> bool:
    """检测文本是否含 LaTeX 公式。"""
    return bool(_LATEX_INLINE.search(text)) or bool(_LATEX_DISPLAY.search(text))


def md_to_docx(md_content: str, output_path: str, title: str = "") -> str:
    """把 Markdown 内容转为带格式的 Word 文档。

    title 非空时在开头插入报告标题（Title 样式）。
    """
    doc = Document()

    # ── 默认样式 ──
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

    # ── 报告标题（Title 样式）──
    if title:
        doc.add_heading(title, level=0)

    # ── 预处理：提取块级公式（$$...$$），替换为占位防止行分割 ──
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

        # ── 块级公式占位 → 插入公式段 ──
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

        # ── 表格检测 ──
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
    """添加原生 Word 表格。"""
    rows = []
    for tl in table_lines:
        stripped = tl.strip()
        if re.match(r'^\|[\s\-:|]+\|$', stripped):
            continue
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
                cell.paragraphs[0].clear()
                run = cell.paragraphs[0].add_run(cell_text)
                run.font.size = Pt(10)


def _add_formatted_paragraph(doc, text: str):
    """添加含行内格式（**加粗**/*斜体*）+ 行内 LaTeX（$...$）的段落。"""
    p = doc.add_paragraph()
    parts = _LATEX_INLINE.split(text)
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            run = p.add_run(f"${part}$")
            run.italic = True
        else:
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
    """解析行内格式，返回 [(text, is_bold, is_italic), ...]。"""
    pattern = re.compile(r'(\*\*(.+?)\*\*|\*(.+?)\*)')
    result = []
    last_end = 0

    for m in pattern.finditer(text):
        if m.start() > last_end:
            result.append((text[last_end:m.start()], False, False))

        if m.group(2) is not None:
            result.append((m.group(2), True, False))
        elif m.group(3) is not None:
            result.append((m.group(3), False, True))
        last_end = m.end()

    if last_end < len(text):
        result.append((text[last_end:], False, False))

    return result if result else [(text, False, False)]


def _parse_md_line(line: str):
    """解析 Markdown 行为 (level, text, is_heading)。"""
    match = re.match(r'^(#{1,6})\s+(.*)', line)
    if match:
        return len(match.group(1)), match.group(2).strip(), True
    return 0, line, False


def generate_report_ref(chapters: dict, output_path: str, refs: list = None):
    """生成三层参考文献文件 report_ref.md（v1.0.2：从各章 📎 段合并去重）。

    - 合并去重各章 📎 段引用得全局列表
    - 剥离 📎、拼接正文、全文一次性编号
    - 按编号排序输出参考文献
    refs 参数保留向后兼容（v1.0.2 不再使用，忽略）。
    """
    global_refs = merge_global_refs(chapters)

    body_parts = []
    for ch_key in sorted(chapters.keys(),
                         key=lambda k: int(k) if str(k).lstrip('-').isdigit() else 0):
        content = chapters.get(ch_key, "")
        if content:
            body_parts.append(_strip_ref_section(content))
    full_body = "\n\n".join(body_parts)
    _, numbering = global_assign_ref_numbers(full_body)

    ref_content = generate_global_ref_list(global_refs, numbering)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ref_content)
    except IOError:
        pass


def build_merged_md(chapters: dict, include_refs: bool = True) -> str:
    """按 seq 合并各章正文；include_refs 时做全局编号并附参考文献表。

    chapters: {seq(可str/int): markdown}，按 seq 数值升序合并。
    """
    def _sort_key(k):
        try:
            return int(k)
        except (TypeError, ValueError):
            return 0

    ordered = sorted(chapters.keys(), key=_sort_key)

    # 各章正文（剥离 📎 段）
    body_parts = []
    for ch_key in ordered:
        content = chapters.get(ch_key, "")
        if content:
            body_parts.append(_strip_ref_section(content))
    full_body = "\n\n".join(body_parts)

    if not include_refs:
        return full_body

    # 全局编号 + 参考文献表
    global_refs = merge_global_refs(chapters)
    numbered_body, numbering = global_assign_ref_numbers(full_body)
    ref_md = generate_global_ref_list(global_refs, numbering)
    if ref_md.strip():
        return numbered_body + "\n\n" + ref_md
    return numbered_body
