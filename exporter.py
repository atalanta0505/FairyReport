"""
Exporter — Markdown -> Word (.docx) 导出 + 三层参考文献规范化。
- 符合国家公文与工程咨询出版级排版规范
- 正文字体：仿宋 / Times New Roman，小四（12pt），1.35 倍行距，严格首行缩进 2 字符（24pt），两端对齐
- 标题层级：
  * Title（报告总标题 / Level 0）：黑体 22pt（二号），居中加粗，段前/后 12pt，无首行缩进
  * Heading 1（Level 1）：黑体 16pt（三号），居左加粗，段前 12pt / 段后 6pt，无首行缩进，keep_with_next
  * Heading 2（Level 2）：黑体 14pt（四号），居左加粗，段前 6pt / 段后 3pt，无首行缩进，keep_with_next
  * Heading 3（Level 3）：楷体 12pt（小四），居左加粗，段前 3pt / 段后 2pt，无首行缩进，keep_with_next
  * Heading 4/5（Level 4+）：仿宋 12pt（小四），居左加粗，段前 2pt / 段后 1pt，无首行缩进，keep_with_next
- 无序列表与引用块：悬挂缩进、楷体引用底纹修饰
- 国家标准三线表：顶底 1.5pt (#334155)、栏目线 0.75pt (#475569)、淡灰表头 (#F1F5F9)、表头加粗居中、cantSplit 跨页防断与 tblHeader 表头跨页重复
- 支持 LaTeX 公式（$...$ / $$...$$）提取与斜体排版
"""
import re

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor

from ref_manager import (
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


def _format_run(
    run,
    font_name: str = 'Times New Roman',
    east_asia: str = '仿宋',
    font_size: Pt = Pt(12),
    bold: bool = False,
    italic: bool = False,
    color: RGBColor = None,
):
    """为 run 设置西文字体、中文字体、字号、粗体、斜体与颜色。"""
    run.font.name = font_name
    run.font.size = font_size
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color

    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn('w:eastAsia'), east_asia)
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)


def _init_document_styles(doc: Document):
    """初始化出版级页面设置与基础样式。"""
    for section in doc.sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(2.8)
        section.right_margin = Cm(2.6)

    normal_style = doc.styles['Normal']
    normal_font = normal_style.font
    normal_font.name = 'Times New Roman'
    normal_font.size = Pt(12)
    normal_font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

    rFonts = normal_style.element.rPr.get_or_add_rFonts()
    rFonts.set(qn('w:eastAsia'), '仿宋')
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')

    normal_style.paragraph_format.line_spacing = 1.35
    normal_style.paragraph_format.space_before = Pt(0)
    normal_style.paragraph_format.space_after = Pt(2)
    normal_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def md_to_docx(md_content: str, output_path: str, title: str = "") -> str:
    """把 Markdown 内容转为符合出版级排版规范的 Word 文档。"""
    doc = Document()
    _init_document_styles(doc)

    if title:
        _add_heading(doc, title, level=0)

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
        stripped = line.strip()

        if stripped.startswith('\x00LATEX_DISPLAY_'):
            key = stripped
            if key in display_formulas:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(6)
                p.paragraph_format.first_line_indent = Pt(0)
                run = p.add_run(f"${display_formulas[key]}$")
                _format_run(run, font_name='Times New Roman', east_asia='仿宋', font_size=Pt(11), italic=True)
            i += 1
            continue

        if stripped.startswith('|') and stripped.endswith('|') and '---' not in stripped:
            table_lines = [stripped]
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

        level, heading_text, is_heading = _parse_md_line(line)
        if is_heading:
            _add_heading(doc, heading_text, level=level)
            i += 1
            continue

        if stripped.startswith('>'):
            quote_text = re.sub(r'^>\s*', '', stripped)
            if quote_text:
                _add_blockquote(doc, quote_text)
            i += 1
            continue

        list_match = re.match(r'^[-*]\s+(.*)', stripped)
        if list_match:
            item_text = list_match.group(1).strip()
            if item_text:
                _add_bullet_item(doc, item_text)
            i += 1
            continue

        num_list_match = re.match(r'^(\d+[\.、])\s+(.*)', stripped)
        if num_list_match:
            prefix = num_list_match.group(1).strip()
            item_text = num_list_match.group(2).strip()
            if item_text:
                _add_numbered_item(doc, prefix, item_text)
            i += 1
            continue

        if stripped:
            _add_formatted_paragraph(doc, stripped)

        i += 1

    doc.save(output_path)
    return output_path


def _add_heading(doc: Document, text: str, level: int):
    """添加符合国家工程咨询出版级规范的各级标题。"""
    style_name = 'Title' if level == 0 else f'Heading {min(level, 9)}'
    try:
        p = doc.add_paragraph(style=style_name)
    except KeyError:
        p = doc.add_paragraph()

    p.paragraph_format.keep_with_next = True
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.left_indent = Pt(0)
    p.paragraph_format.right_indent = Pt(0)

    if level == 0:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(12)
        east_asia = '黑体'
        font_size = Pt(22)
        bold = True
        color = RGBColor(0x0F, 0x17, 0x2A)
    elif level == 1:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)
        east_asia = '黑体'
        font_size = Pt(16)
        bold = True
        color = RGBColor(0x0F, 0x17, 0x2A)
    elif level == 2:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(3)
        east_asia = '黑体'
        font_size = Pt(14)
        bold = True
        color = RGBColor(0x1E, 0x29, 0x3B)
    elif level == 3:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(2)
        east_asia = '楷体'
        font_size = Pt(12)
        bold = True
        color = RGBColor(0x1E, 0x29, 0x3B)
    else:  # level >= 4
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(1)
        east_asia = '仿宋'
        font_size = Pt(12)
        bold = True
        color = RGBColor(0x33, 0x41, 0x55)

    parts = _LATEX_INLINE.split(text)
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            run = p.add_run(f"${part}$")
            _format_run(run, font_name='Times New Roman', east_asia=east_asia, font_size=font_size, bold=bold, italic=True, color=color)
        else:
            segments = _parse_inline_formatting(part)
            for seg_text, is_bold, is_italic in segments:
                if not seg_text:
                    continue
                run = p.add_run(seg_text)
                _format_run(
                    run,
                    font_name='Times New Roman',
                    east_asia=east_asia,
                    font_size=font_size,
                    bold=True if bold else is_bold,
                    italic=is_italic,
                    color=color,
                )


def _set_three_line_table_borders(table, has_header: bool = True):
    """为 Word 表格应用出版级三线表格式。"""
    tblPr = table._tbl.tblPr
    old_tblBorders = tblPr.find(qn('w:tblBorders'))
    if old_tblBorders is not None:
        tblPr.remove(old_tblBorders)

    tblBorders = parse_xml(
        r'<w:tblBorders %s>'
        r'  <w:top w:val="single" w:sz="12" w:space="0" w:color="334155"/>'
        r'  <w:bottom w:val="single" w:sz="12" w:space="0" w:color="334155"/>'
        r'  <w:left w:val="none"/>'
        r'  <w:right w:val="none"/>'
        r'  <w:insideH w:val="none"/>'
        r'  <w:insideV w:val="none"/>'
        r'</w:tblBorders>' % nsdecls('w')
    )
    tblPr.append(tblBorders)

    old_tblCellMar = tblPr.find(qn('w:tblCellMar'))
    if old_tblCellMar is not None:
        tblPr.remove(old_tblCellMar)
    tblCellMar = parse_xml(
        r'<w:tblCellMar %s>'
        r'  <w:top w:w="120" w:type="dxa"/>'
        r'  <w:bottom w:w="120" w:type="dxa"/>'
        r'  <w:left w:w="160" w:type="dxa"/>'
        r'  <w:right w:w="160" w:type="dxa"/>'
        r'</w:tblCellMar>' % nsdecls('w')
    )
    tblPr.append(tblCellMar)

    if len(table.rows) > 0 and has_header:
        for cell in table.rows[0].cells:
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = parse_xml(
                r'<w:tcBorders %s>'
                r'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="475569"/>'
                r'  <w:top w:val="none"/>'
                r'  <w:left w:val="none"/>'
                r'  <w:right w:val="none"/>'
                r'</w:tcBorders>' % nsdecls('w')
            )
            tcPr.append(tcBorders)
            shd = parse_xml(r'<w:shd %s w:fill="F1F5F9"/>' % nsdecls('w'))
            tcPr.append(shd)


def _add_table(doc: Document, table_lines: list):
    """添加三线表格。"""
    raw_rows = []
    alignments = []

    for tl in table_lines:
        stripped = tl.strip()
        if re.match(r'^\|[\s\-:|]+\|$', stripped):
            sep_cells = [c.strip() for c in stripped[1:-1].split('|')]
            alignments = []
            for c in sep_cells:
                if c.startswith(':') and c.endswith(':'):
                    alignments.append(WD_ALIGN_PARAGRAPH.CENTER)
                elif c.endswith(':'):
                    alignments.append(WD_ALIGN_PARAGRAPH.RIGHT)
                elif c.startswith(':'):
                    alignments.append(WD_ALIGN_PARAGRAPH.LEFT)
                else:
                    alignments.append(None)
            continue
        cells = [c.strip() for c in stripped[1:-1].split('|')]
        raw_rows.append(cells)

    if not raw_rows:
        return

    num_cols = max(len(r) for r in raw_rows)
    table = doc.add_table(rows=len(raw_rows), cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    has_header = len(raw_rows) > 1
    _set_three_line_table_borders(table, has_header=has_header)

    for ri, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(r'<w:cantSplit %s/>' % nsdecls('w')))
        if ri == 0 and has_header:
            trPr.append(parse_xml(r'<w:tblHeader %s/>' % nsdecls('w')))

    for ri, row_cells in enumerate(raw_rows):
        is_header = (ri == 0 and has_header)
        for ci, cell_text in enumerate(row_cells):
            if ci < num_cols:
                cell = table.cell(ri, ci)
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

                p = cell.paragraphs[0]
                p.clear()
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.first_line_indent = Pt(0)

                if is_header:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    col_align = alignments[ci] if ci < len(alignments) and alignments[ci] is not None else None
                    if col_align is not None:
                        p.alignment = col_align
                    elif re.match(r'^-?\d+(?:\.\d+)?%?$', cell_text):
                        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    else:
                        p.alignment = WD_ALIGN_PARAGRAPH.LEFT

                east_asia = '黑体' if is_header else '仿宋'
                font_size = Pt(10.5) if is_header else Pt(10)
                parts = _LATEX_INLINE.split(cell_text)
                for idx, part in enumerate(parts):
                    if idx % 2 == 1:
                        run = p.add_run(f"${part}$")
                        _format_run(
                            run,
                            font_name='Times New Roman',
                            east_asia=east_asia,
                            font_size=font_size,
                            bold=is_header,
                            italic=True,
                        )
                    else:
                        segments = _parse_inline_formatting(part)
                        for seg_text, is_b, is_i in segments:
                            if not seg_text:
                                continue
                            run = p.add_run(seg_text)
                            _format_run(
                                run,
                                font_name='Times New Roman',
                                east_asia=east_asia,
                                font_size=font_size,
                                bold=True if is_header else is_b,
                                italic=is_i,
                            )


def _add_formatted_paragraph(doc: Document, text: str):
    """添加出版级正文段落。"""
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(24)
    p.paragraph_format.line_spacing = 1.35
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    parts = _LATEX_INLINE.split(text)
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            run = p.add_run(f"${part}$")
            _format_run(run, font_name='Times New Roman', east_asia='仿宋', font_size=Pt(12), italic=True)
        else:
            segments = _parse_inline_formatting(part)
            for seg_text, is_bold, is_italic in segments:
                if not seg_text:
                    continue
                run = p.add_run(seg_text)
                _format_run(
                    run,
                    font_name='Times New Roman',
                    east_asia='仿宋',
                    font_size=Pt(12),
                    bold=is_bold,
                    italic=is_italic,
                )


def _add_bullet_item(doc: Document, text: str):
    """添加出版级无序列表项。"""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(24)
    p.paragraph_format.first_line_indent = Pt(-12)
    p.paragraph_format.line_spacing = 1.35
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    bullet_run = p.add_run("•  ")
    _format_run(bullet_run, font_name='Times New Roman', east_asia='仿宋', font_size=Pt(12))

    parts = _LATEX_INLINE.split(text)
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            run = p.add_run(f"${part}$")
            _format_run(run, font_name='Times New Roman', east_asia='仿宋', font_size=Pt(12), italic=True)
        else:
            segments = _parse_inline_formatting(part)
            for seg_text, is_bold, is_italic in segments:
                if not seg_text:
                    continue
                run = p.add_run(seg_text)
                _format_run(
                    run,
                    font_name='Times New Roman',
                    east_asia='仿宋',
                    font_size=Pt(12),
                    bold=is_bold,
                    italic=is_italic,
                )


def _add_numbered_item(doc: Document, prefix: str, text: str):
    """添加出版级有序列表项。"""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(24)
    p.paragraph_format.first_line_indent = Pt(-12)
    p.paragraph_format.line_spacing = 1.35
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    num_run = p.add_run(f"{prefix} ")
    _format_run(num_run, font_name='Times New Roman', east_asia='仿宋', font_size=Pt(12))

    parts = _LATEX_INLINE.split(text)
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            run = p.add_run(f"${part}$")
            _format_run(run, font_name='Times New Roman', east_asia='仿宋', font_size=Pt(12), italic=True)
        else:
            segments = _parse_inline_formatting(part)
            for seg_text, is_bold, is_italic in segments:
                if not seg_text:
                    continue
                run = p.add_run(seg_text)
                _format_run(
                    run,
                    font_name='Times New Roman',
                    east_asia='仿宋',
                    font_size=Pt(12),
                    bold=is_bold,
                    italic=is_italic,
                )


def _add_blockquote(doc: Document, text: str):
    """添加出版级引用块。"""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(24)
    p.paragraph_format.right_indent = Pt(24)
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.line_spacing = 1.35
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(
        r'<w:pBdr %s>'
        r'  <w:left w:val="single" w:sz="24" w:space="8" w:color="94A3B8"/>'
        r'  <w:top w:val="none"/>'
        r'  <w:right w:val="none"/>'
        r'  <w:bottom w:val="none"/>'
        r'</w:pBdr>' % nsdecls('w')
    )
    pPr.append(pBdr)
    shd = parse_xml(r'<w:shd %s w:fill="F8FAFC"/>' % nsdecls('w'))
    pPr.append(shd)

    parts = _LATEX_INLINE.split(text)
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            run = p.add_run(f"${part}$")
            _format_run(
                run,
                font_name='Times New Roman',
                east_asia='楷体',
                font_size=Pt(10.5),
                italic=True,
                color=RGBColor(0x33, 0x41, 0x55),
            )
        else:
            segments = _parse_inline_formatting(part)
            for seg_text, is_bold, is_italic in segments:
                if not seg_text:
                    continue
                run = p.add_run(seg_text)
                _format_run(
                    run,
                    font_name='Times New Roman',
                    east_asia='楷体',
                    font_size=Pt(10.5),
                    bold=is_bold,
                    italic=is_italic,
                    color=RGBColor(0x33, 0x41, 0x55),
                )


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


def format_ref_appendix(global_refs: list, numbering: dict) -> str:
    """生成符合国家出版级规范的三源参考文献与资料出处附录 Markdown。"""
    if not global_refs:
        return "## 参考文献与资料出处\n\n（未检测到引用标记）\n"

    sorted_refs = sorted(
        global_refs,
        key=lambda r: numbering.get(r["label"], 99999),
    )

    project_items = [r for r in sorted_refs if r.get("type") == "项目资料"]
    standard_items = [r for r in sorted_refs if r.get("type") == "规程标准"]
    web_items = [r for r in sorted_refs if r.get("type") == "网页链接"]
    ai_items = [r for r in sorted_refs if r.get("type") == "AI自有知识"]

    lines = ["## 参考文献与资料出处\n", "> 自动生成于报告导出时\n"]

    if project_items:
        lines.append("### 一、项目底稿资料\n")
        for r in project_items:
            n = numbering.get(r["label"], "?")
            name = r.get("name", "")
            source = r.get("source", "")
            if source and source != name:
                lines.append(f"- [{n}] {name} — 来源: {source}")
            else:
                lines.append(f"- [{n}] {name}")
        lines.append("")

    if standard_items:
        lines.append("### 二、国家与行业规程标准\n")
        for r in standard_items:
            n = numbering.get(r["label"], "?")
            name = r.get("name", "")
            source = r.get("source", "")
            if source and source != name:
                lines.append(f"- [{n}] {name} — 来源: {source}")
            else:
                lines.append(f"- [{n}] {name}")
        lines.append("")

    if web_items:
        lines.append("### 三、互联网与第三方参考\n")
        for r in web_items:
            n = numbering.get(r["label"], "?")
            name = r.get("name", "")
            source = r.get("source", "")
            if source and source != name:
                lines.append(f"- [{n}] {name} — {source}")
            else:
                lines.append(f"- [{n}] {name}")
        lines.append("")

    if ai_items:
        lines.append("### 四、AI自有知识\n")
        lines.append("（由 AI 在编写过程中补充的通用领域知识）\n")

    return "\n".join(lines)


def generate_report_ref(chapters: dict, output_path: str, refs: list = None):
    """生成三层参考文献文件 report_ref.md。"""
    global_refs = merge_global_refs(chapters)

    body_parts = []
    for ch_key in sorted(chapters.keys(),
                         key=lambda k: int(k) if str(k).lstrip('-').isdigit() else 0):
        content = chapters.get(ch_key, "")
        if content:
            body_parts.append(_strip_ref_section(content))
    full_body = "\n\n".join(body_parts)
    _, numbering = global_assign_ref_numbers(full_body)

    ref_content = format_ref_appendix(global_refs, numbering)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ref_content)
    except IOError:
        pass


def build_merged_md(chapters: dict, include_refs: bool = True) -> str:
    """按 seq 合并各章正文；include_refs 时做全局编号并附参考文献表。"""
    def _sort_key(k):
        try:
            return int(k)
        except (TypeError, ValueError):
            return 0

    ordered = sorted(chapters.keys(), key=_sort_key)

    body_parts = []
    for ch_key in ordered:
        content = chapters.get(ch_key, "")
        if content:
            body_parts.append(_strip_ref_section(content))
    full_body = "\n\n".join(body_parts)

    if not include_refs:
        return full_body

    global_refs = merge_global_refs(chapters)
    numbered_body, numbering = global_assign_ref_numbers(full_body)
    ref_md = format_ref_appendix(global_refs, numbering)
    if ref_md.strip():
        return numbered_body + "\n\n" + ref_md
    return numbered_body


