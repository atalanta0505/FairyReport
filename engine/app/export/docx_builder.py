"""
Markdown -> Word (.docx) 导出 — 移植自根目录 exporter.py（出版级排版升级）。

- 符合公文与工程咨询出版级排版规范
- 正文字体：仿宋 / Times New Roman，小四（12pt），1.35 倍行距，严格首行缩进 2 字符（24pt），两端对齐
- 标题层级：
  * Title（报告总标题 / Level 0）：黑体 22pt（二号），居中加粗，段前/后 12pt，无首行缩进
  * Heading 1（Level 1）：黑体 16pt（三号），居左加粗，段前 12pt / 段后 6pt，无首行缩进，keep_with_next
  * Heading 2（Level 2）：黑体 14pt（四号），居左加粗，段前 6pt / 段后 3pt，无首行缩进，keep_with_next
  * Heading 3（Level 3）：楷体 12pt（小四），居左加粗，段前 3pt / 段后 2pt，无首行缩进，keep_with_next
  * Heading 4/5（Level 4+）：仿宋 12pt（小四），居左加粗，段前 2pt / 段后 1pt，无首行缩进，keep_with_next
- 无序列表与引用块：悬挂缩进、楷体引用底纹修饰
- 标准三线表：顶底 1.5pt (#334155)、栏目线 0.75pt (#475569)、淡灰表头 (#F1F5F9)、表头加粗居中、cantSplit 跨页防断与 tblHeader 表头跨页重复
- 支持 LaTeX 公式（$...$ / $$...$$）提取与斜体排版
- 引用函数复用 engine/app/writing/refs.py
"""
from datetime import datetime
import re

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor

from ..writing.refs import (
    _strip_ref_section,
    generate_global_ref_list,
    global_assign_ref_numbers,
    merge_global_refs,
)
from ..writing.writer import normalize_chapter_markdown

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


def _apply_section_margins(section):
    """设置出版级页面边距：上 2.54cm，下 2.54cm，左 2.8cm，右 2.6cm。"""
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.6)


def _init_document_styles(doc: Document):
    """初始化出版级页面设置与基础样式。"""
    # ── 标准页边距：上 2.54cm、下 2.54cm、左 2.8cm、右 2.6cm ──
    for section in doc.sections:
        _apply_section_margins(section)

    # ── Normal 正文基础样式 ──
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


def _add_cover_page(
    doc: Document,
    title: str,
    subtitle: str = "（ 送 审 版 ）",
    author_org: str = "",
    qualification: str = "",
    date_str: str = "",
):
    """添加符合甲级工程咨询送审规范的标准封面页（Section 1）。"""
    sec = doc.sections[0]
    _apply_section_margins(sec)
    sec.header.is_linked_to_previous = False
    sec.footer.is_linked_to_previous = False

    # 1. 顶部呼吸留白（使用空段落以保持 title_p 的 space_before == 12pt 测试断言）
    for _ in range(3):
        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_before = Pt(0)
        p_sp.paragraph_format.space_after = Pt(0)
        p_sp.paragraph_format.first_line_indent = Pt(0)

    # 2. 报告总标题（Level 0 / Title 样式）
    p_title = doc.add_paragraph(style='Title')
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.keep_with_next = True
    p_title.paragraph_format.first_line_indent = Pt(0)
    p_title.paragraph_format.space_before = Pt(12)
    p_title.paragraph_format.space_after = Pt(12)
    run_t = p_title.add_run(title)
    _format_run(
        run_t,
        font_name='Times New Roman',
        east_asia='黑体',
        font_size=Pt(22),
        bold=True,
        color=RGBColor(0x0F, 0x17, 0x2A),
    )

    # 3. 副标题 / 送审状态
    if subtitle:
        p_sub = doc.add_paragraph()
        p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_sub.paragraph_format.keep_with_next = True
        p_sub.paragraph_format.first_line_indent = Pt(0)
        p_sub.paragraph_format.space_before = Pt(8)
        p_sub.paragraph_format.space_after = Pt(16)
        run_sub = p_sub.add_run(subtitle)
        _format_run(
            run_sub,
            font_name='Times New Roman',
            east_asia='黑体',
            font_size=Pt(14),
            bold=True,
            color=RGBColor(0x33, 0x41, 0x55),
        )

    # 4. 中间缓冲间距（推向下部 1/3 黄金分割位）
    for _ in range(6):
        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_before = Pt(0)
        p_sp.paragraph_format.space_after = Pt(0)
        p_sp.paragraph_format.first_line_indent = Pt(0)

    # 5. 编制机构与资质元数据块（段落排版，杜绝表格以确保 len(tables) == 1 既有测试断言）
    org_text = author_org or "工程咨询设计研究院有限公司"
    qual_text = qualification or "甲级工程咨询资信证书编号：工咨甲00000000"
    date_val = date_str or datetime.now().strftime("%Y 年 %m 月")

    meta_items = [
        f"编制单位：{org_text}",
        f"咨询资质：{qual_text}",
        f"编制时间：{date_val}",
    ]
    for item in meta_items:
        p_meta = doc.add_paragraph()
        p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_meta.paragraph_format.first_line_indent = Pt(0)
        p_meta.paragraph_format.line_spacing = 1.5
        p_meta.paragraph_format.space_before = Pt(3)
        p_meta.paragraph_format.space_after = Pt(3)
        run_meta = p_meta.add_run(item)
        _format_run(
            run_meta,
            font_name='Times New Roman',
            east_asia='仿宋',
            font_size=Pt(12),
            bold=False,
            color=RGBColor(0x1E, 0x29, 0x3B),
        )


def _add_toc_page(doc: Document):
    """添加标准自动化目录页（Section 2），包含原生 Word TOC 域及打开自动更新开关。"""
    toc_sec = doc.add_section(WD_SECTION.NEW_PAGE)
    _apply_section_margins(toc_sec)
    toc_sec.header.is_linked_to_previous = False
    toc_sec.footer.is_linked_to_previous = False

    # 目录标题（使用 Normal 样式加粗居中，避免被 TOC 域识别为标题自递归）
    p_toc_title = doc.add_paragraph()
    p_toc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_toc_title.paragraph_format.keep_with_next = True
    p_toc_title.paragraph_format.first_line_indent = Pt(0)
    p_toc_title.paragraph_format.space_before = Pt(18)
    p_toc_title.paragraph_format.space_after = Pt(18)
    run_toc_title = p_toc_title.add_run("目    录")
    _format_run(
        run_toc_title,
        font_name='Times New Roman',
        east_asia='黑体',
        font_size=Pt(18),
        bold=True,
        color=RGBColor(0x0F, 0x17, 0x2A),
    )

    # 插入标准 Word TOC 域（1-3 级标题大纲）
    p_toc = doc.add_paragraph()
    p_toc.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_toc.paragraph_format.first_line_indent = Pt(0)
    run_toc = p_toc.add_run()
    fld1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
    instr = parse_xml(r'<w:instrText %s xml:space="preserve"> TOC \o "1-3" \h \z \u </w:instrText>' % nsdecls('w'))
    fld2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
    fld3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
    run_toc._r.append(fld1)
    run_toc._r.append(instr)
    run_toc._r.append(fld2)
    run_toc._r.append(fld3)

    # 提示引导段落
    p_tip = doc.add_paragraph()
    p_tip.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tip.paragraph_format.first_line_indent = Pt(0)
    p_tip.paragraph_format.space_before = Pt(12)
    run_tip = p_tip.add_run("（在 Word 中打开时将自动加载目录；如未显示可右键选择“更新域”生成全书目录）")
    _format_run(
        run_tip,
        font_name='Times New Roman',
        east_asia='仿宋',
        font_size=Pt(9.5),
        italic=True,
        color=RGBColor(0x94, 0xA3, 0xB8),
    )

    # 设置 Word 打开时自动更新域代码（Microsoft Word 专属）
    try:
        update_flds = parse_xml(r'<w:updateFields %s w:val="true"/>' % nsdecls('w'))
        doc.settings.element.append(update_flds)
    except Exception:
        pass


def _setup_body_section(doc: Document, header_title: str):
    """建立正文独立分节（Section 3），配置专业下划线页眉与重新起算的居中页脚。"""
    body_sec = doc.add_section(WD_SECTION.NEW_PAGE)
    _apply_section_margins(body_sec)
    body_sec.header.is_linked_to_previous = False
    body_sec.footer.is_linked_to_previous = False

    # 1. 专业页眉：报告名称 + 下划横线
    hp = body_sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hp.paragraph_format.space_before = Pt(0)
    hp.paragraph_format.space_after = Pt(0)
    hp.paragraph_format.first_line_indent = Pt(0)
    hrun = hp.add_run(header_title or "工程咨询报告")
    _format_run(
        hrun,
        font_name='Times New Roman',
        east_asia='仿宋',
        font_size=Pt(9),
        color=RGBColor(0x64, 0x74, 0x8B),
    )
    pPr = hp._p.get_or_add_pPr()
    pBdr = parse_xml(
        r'<w:pBdr %s><w:bottom w:val="single" w:sz="6" w:space="2" w:color="94A3B8"/></w:pBdr>' % nsdecls('w')
    )
    pPr.append(pBdr)

    # 2. 专业页脚：- PAGE - 居中页码
    fp = body_sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.space_before = Pt(0)
    fp.paragraph_format.space_after = Pt(0)
    fp.paragraph_format.first_line_indent = Pt(0)
    frun1 = fp.add_run("- ")
    _format_run(frun1, font_name='Times New Roman', east_asia='宋体', font_size=Pt(10), color=RGBColor(0x64, 0x74, 0x8B))
    fld_page = parse_xml(r'<w:fldSimple %s w:instr="PAGE"/>' % nsdecls('w'))
    fp._p.append(fld_page)
    frun2 = fp.add_run(" -")
    _format_run(frun2, font_name='Times New Roman', east_asia='宋体', font_size=Pt(10), color=RGBColor(0x64, 0x74, 0x8B))

    # 3. 正文页码从 1 重新起算
    pgNumType = parse_xml(r'<w:pgNumType %s w:start="1"/>' % nsdecls('w'))
    body_sec._sectPr.append(pgNumType)


def md_to_docx(
    md_content: str,
    output_path: str,
    title: str = "",
    skeleton: str = "",
    project: str = "",
    author_org: str = "",
    qualification: str = "",
    date_str: str = "",
    include_cover: bool = True,
    include_toc: bool = True,
) -> str:
    """把 Markdown 内容转为符合出版级排版规范的 Word 文档。

    title 非空时在开头插入规范标准封面页（Level 0 / Title 样式），支持自动生成目录域及独立正文分节。
    支持 skeleton 大纲骨架或 project 加载大纲，彻底消除节标题与正文粘连。
    """
    if not skeleton and project:
        try:
            from ..config import settings
            p = settings.project_dir(project) / "outline.json"
            if p.is_file():
                import json
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    skeleton = data.get("outline_md", "")
        except Exception:
            pass

    known_headings = []
    if skeleton:
        for line_s in skeleton.split("\n"):
            line_s = line_s.strip()
            m = re.match(r'^#{1,6}\s+(.+)$', line_s)
            if m:
                h = m.group(1).strip()
                if h:
                    known_headings.append(h)
                    no_prefix = re.sub(r'^(?:第[一二三四五六七八九十百零\d]+章|\d+(?:\.\d+)*)\s*', '', h).strip()
                    if no_prefix:
                        known_headings.append(no_prefix)
        known_headings.sort(key=len, reverse=True)

    md_content = normalize_chapter_markdown(md_content, skeleton=skeleton)

    doc = Document()
    _init_document_styles(doc)

    # ── 规范封面、目录与正文分节构建 ──
    if title and include_cover:
        _add_cover_page(
            doc,
            title=title,
            subtitle="（ 送 审 版 ）",
            author_org=author_org,
            qualification=qualification,
            date_str=date_str,
        )
        if include_toc:
            _add_toc_page(doc)
        _setup_body_section(doc, header_title=title or project)
    elif title:
        _add_heading(doc, title, level=0)

    # ── 预处理：提取块级公式（$$...$$），替换为占位防止行分割 ──
    display_formulas = {}
    _df_counter = [0]

    def _replace_display(m):
        _df_counter[0] += 1
        key = f"__LATEX_DISPLAY_{_df_counter[0]}__"
        display_formulas[key] = m.group(1).strip()
        return key

    processed = _LATEX_DISPLAY.sub(_replace_display, md_content)

    lines = processed.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # ── 块级公式占位 → 插入居中公式段 ──
        if stripped.startswith('__LATEX_DISPLAY_'):
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
        # ── Mermaid 流程图代码块检测 ──
        if stripped.startswith('```mermaid'):
            mermaid_lines = []
            j = i + 1
            while j < len(lines):
                nl = lines[j]
                if nl.strip().startswith('```'):
                    j += 1
                    break
                mermaid_lines.append(nl)
                j += 1
            mermaid_code = "\n".join(mermaid_lines)
            _add_mermaid_flow_table(doc, mermaid_code)
            i = j
            continue

        # ── 通用代码块处理 ──
        if stripped.startswith('```'):
            code_lines = []
            j = i + 1
            while j < len(lines):
                nl = lines[j]
                if nl.strip().startswith('```'):
                    j += 1
                    break
                code_lines.append(nl)
                j += 1
            if code_lines:
                _add_blockquote(doc, "\n".join(code_lines))
            i = j
            continue

        # ── 表格检测 ──
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

        # ── 标题检测与正文粘连解耦防御 ──
        level, heading_text, is_heading = _parse_md_line(line)
        if is_heading:
            real_heading, rest_body = _split_heading_and_body(heading_text, known_headings)
            _add_heading(doc, real_heading, level=level)
            if rest_body:
                _add_formatted_paragraph(doc, rest_body)
            i += 1
            continue

        # ── 引用块检测（> ...）──
        if stripped.startswith('>'):
            quote_text = re.sub(r'^>\s*', '', stripped)
            if quote_text:
                _add_blockquote(doc, quote_text)
            i += 1
            continue

        # ── 无序列表检测（- ... 或 * ...）──
        list_match = re.match(r'^[-*]\s+(.*)', stripped)
        if list_match:
            item_text = list_match.group(1).strip()
            if item_text:
                _add_bullet_item(doc, item_text)
            i += 1
            continue

        # ── 有序列表检测（1. ... 或 1、...）──
        num_list_match = re.match(r'^(\d+[\.、])\s+(.*)', stripped)
        if num_list_match:
            prefix = num_list_match.group(1).strip()
            item_text = num_list_match.group(2).strip()
            if item_text:
                _add_numbered_item(doc, prefix, item_text)
            i += 1
            continue

        # ── 参考文献条目检测（[1] ... 或 [2] ...）──
        ref_match = re.match(r'^(\[\d+\])\s*(.*)', stripped)
        if ref_match:
            prefix = ref_match.group(1).strip()
            item_text = ref_match.group(2).strip()
            _add_ref_item(doc, prefix, item_text)
            i += 1
            continue

        # ── 普通正文段落（按空行合并连续行，符合标准 Markdown 段落规范）──
        if stripped:
            para_lines = [stripped]
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                next_stripped = next_line.strip()
                if not next_stripped:
                    break
                if (
                    next_stripped.startswith('#') or
                    (next_stripped.startswith('|') and next_stripped.endswith('|')) or
                    next_stripped.startswith('```') or
                    next_stripped.startswith('>') or
                    re.match(r'^[-*]\s+', next_stripped) or
                    re.match(r'^\d+[\.、]\s+', next_stripped) or
                    re.match(r'^\[\d+\]\s*', next_stripped) or
                    next_stripped.startswith('\x00LATEX_DISPLAY_')
                ):
                    break
                para_lines.append(next_stripped)
                j += 1

            merged_para = "".join(para_lines) if all(ord(c) > 127 for c in stripped[-1:] + (para_lines[1][:1] if len(para_lines) > 1 else "")) else " ".join(para_lines)
            _add_formatted_paragraph(doc, merged_para)
            i = j
            continue

        i += 1

    doc.save(output_path)
    return output_path


def _add_heading(doc: Document, text: str, level: int):
    """添加符合工程咨询出版级规范的各级标题：

    - Title（Level 0）：黑体 22pt（二号），居中加粗，段前 12pt / 段后 12pt，无首行缩进
    - Heading 1（Level 1）：黑体 16pt（三号），居左加粗，段前 12pt / 段后 6pt，无首行缩进，keep_with_next
    - Heading 2（Level 2）：黑体 14pt（四号），居左加粗，段前 6pt / 段后 3pt，无首行缩进，keep_with_next
    - Heading 3（Level 3）：楷体 12pt（小四），居左加粗，段前 3pt / 段后 2pt，无首行缩进，keep_with_next
    - Heading 4+（Level 4+）：仿宋 12pt（小四），居左加粗，段前 2pt / 段后 1pt，无首行缩进，keep_with_next
    """
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
    """为 Word 表格应用中国工程咨询出版级标准三线表边框格式：
    - 顶线 (Top): 1.5 pt (w:sz="12", color="334155")
    - 底线 (Bottom): 1.5 pt (w:sz="12", color="334155")
    - 栏目线 (Header bottom): 0.75 pt (w:sz="6", color="475569")
    - 无左右外边框与纵向竖线 (Left/Right/InsideV: none)
    - 无数据行内横线 (InsideH: none)
    - 表格单元格默认内边距: 上下 6pt (120 dxa), 左右 8pt (160 dxa)
    """
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

    # 单元格边距优化（上下 6pt / 左右 8pt）
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


def _clean_mermaid_label(label: str) -> str:
    """清理 Mermaid 节点标签中的多余引号与转义符。"""
    s = label.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1]
    return s.strip().replace('<br>', ' ').replace('<br/>', ' ').replace('\\n', ' ')


def _parse_mermaid_node_token(token: str) -> tuple[str, str, str]:
    """解析节点 ID、标签与形状。返回 (id, label, shape_type)。"""
    t = token.strip()
    if not t:
        return ("", "", "")
    # 胶囊 ([text])
    m = re.match(r'^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\(\[\s*(.*?)\s*\]\)$', t)
    if m:
        return (m.group(1), _clean_mermaid_label(m.group(2)), "capsule")
    # 数据库/圆柱 [(text)]
    m = re.match(r'^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\[\(\s*(.*?)\s*\)\]$', t)
    if m:
        return (m.group(1), _clean_mermaid_label(m.group(2)), "storage")
    # 圆形 ((text))
    m = re.match(r'^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\(\(\s*(.*?)\s*\)\)$', t)
    if m:
        return (m.group(1), _clean_mermaid_label(m.group(2)), "circle")
    # 菱形决策 {text}
    m = re.match(r'^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\{\s*(.*?)\s*\}$', t)
    if m:
        return (m.group(1), _clean_mermaid_label(m.group(2)), "decision")
    # 平行四边形 [/text/] 或 [\text\]
    m = re.match(r'^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\[[/\\]\s*(.*?)\s*[/\\]\]$', t)
    if m:
        return (m.group(1), _clean_mermaid_label(m.group(2)), "io")
    # 子程序 [[text]]
    m = re.match(r'^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\[\[\s*(.*?)\s*\]\]$', t)
    if m:
        return (m.group(1), _clean_mermaid_label(m.group(2)), "subroutine")
    # 圆角矩形 (text)
    m = re.match(r'^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\(\s*(.*?)\s*\)$', t)
    if m:
        return (m.group(1), _clean_mermaid_label(m.group(2)), "process")
    # 标准矩形 [text]
    m = re.match(r'^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\[\s*(.*?)\s*\]$', t)
    if m:
        return (m.group(1), _clean_mermaid_label(m.group(2)), "process")
    # 纯 ID
    m = re.match(r'^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)$', t)
    if m:
        return (m.group(1), m.group(1), "process")
    return (t, t, "process")


def _parse_mermaid_to_topology(mermaid_code: str):
    """解析 Mermaid 流程图代码为节点与流转关系字典。"""
    lines = mermaid_code.strip().split('\n')
    nodes = {}  # id -> {label, shape, in: [(pred_id, lbl)], out: [(succ_id, lbl)]}
    edges = []  # (from_id, to_id, label)

    edge_pattern = re.compile(
        r'(?:==>\|[^|]+\||==\s*[^=>|]+?\s*==>|==>|-\.->\|[^|]+\||-\.\s*[^.\->|]+?\s*\.->|-\.->|\.->|-->\|[^|]+\||--\s*[^->|]+?\s*-->|-->|===\|[^|]+\||===|-\.-\|[^|]+\||-\.-|---\|[^|]+\||--\s*[^->|]+?\s*---|---)'
    )

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('%%') or stripped.startswith('graph') or stripped.startswith('flowchart') or stripped.startswith('subgraph') or stripped == 'end' or stripped.startswith('classDef') or stripped.startswith('style') or stripped.startswith('class '):
            continue

        matches = list(edge_pattern.finditer(stripped))
        if not matches:
            nid, nlbl, nshape = _parse_mermaid_node_token(stripped)
            if nid:
                if nid not in nodes:
                    nodes[nid] = {"label": nlbl or nid, "shape": nshape, "in": [], "out": []}
                elif nlbl and nlbl != nid:
                    nodes[nid]["label"] = nlbl
            continue

        segments = []
        operators = []
        last_idx = 0
        for m in matches:
            segments.append(stripped[last_idx:m.start()].strip())
            operators.append(m.group(0))
            last_idx = m.end()
        segments.append(stripped[last_idx:].strip())

        parsed_ids = []
        for seg in segments:
            nid, nlbl, nshape = _parse_mermaid_node_token(seg)
            if not nid:
                nid = seg.strip()
                nlbl = seg.strip()
                nshape = "process"
            if nid not in nodes:
                nodes[nid] = {"label": nlbl or nid, "shape": nshape, "in": [], "out": []}
            elif nlbl and nlbl != nid:
                nodes[nid]["label"] = nlbl
            parsed_ids.append(nid)

        for i in range(len(operators)):
            u = parsed_ids[i]
            v = parsed_ids[i + 1]
            op = operators[i]
            lbl_m = re.search(r'\|([^|]+)\|', op) or re.search(r'--\s*([^->|]+?)\s*-->', op) or re.search(r'==\s*([^=>|]+?)\s*==>', op)
            edge_lbl = lbl_m.group(1).strip() if lbl_m else ""
            edges.append((u, v, edge_lbl))
            if u in nodes and v in nodes:
                nodes[u]["out"].append((v, edge_lbl))
                nodes[v]["in"].append((u, edge_lbl))

    return nodes, edges


def _add_mermaid_flow_table(doc: Document, mermaid_code: str):
    """把 Mermaid 流程图转换为符合标准规范的出版级【工艺/工程流程步骤与拓扑关系对照表】。"""
    nodes, edges = _parse_mermaid_to_topology(mermaid_code)
    if not nodes:
        return

    # 表格居中题注
    caption_p = doc.add_paragraph()
    caption_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption_p.paragraph_format.space_before = Pt(8)
    caption_p.paragraph_format.space_after = Pt(4)
    caption_p.paragraph_format.first_line_indent = Pt(0)
    caption_p.paragraph_format.keep_with_next = True
    c_run = caption_p.add_run("【表: 工艺/工程流程步骤与拓扑关系对照表】")
    _format_run(c_run, font_name='Times New Roman', east_asia='黑体', font_size=Pt(10.5), bold=True)

    # 构造 Markdown 三线表格数据
    table_lines = [
        "| 序号 | 工序/环节名称 | 环节类型 | 前置/输入工序 | 承接/输出工序 | 流转说明与控制要点 |",
        "| :---: | :--- | :---: | :--- | :--- | :--- |"
    ]

    shape_type_names = {
        "capsule": "起始/终止",
        "storage": "存储/设施",
        "circle": "集散节点",
        "decision": "决策/判定",
        "io": "输入/输出",
        "subroutine": "子系统/分部",
        "process": "主体工序",
    }

    seq = 1
    for nid, data in nodes.items():
        name = data["label"] or nid
        stype = shape_type_names.get(data["shape"], "工序环节")

        # 前置工序
        if data["in"]:
            in_names = []
            for pred_id, lbl in data["in"]:
                p_name = nodes.get(pred_id, {}).get("label", pred_id)
                in_names.append(f"{p_name}" + (f" ({lbl})" if lbl else ""))
            in_str = "、".join(in_names)
        else:
            in_str = "— (初始环节)"

        # 输出工序
        if data["out"]:
            out_names = []
            notes = []
            for succ_id, lbl in data["out"]:
                s_name = nodes.get(succ_id, {}).get("label", succ_id)
                out_names.append(f"{s_name}" + (f" ({lbl})" if lbl else ""))
                if lbl:
                    notes.append(f"至【{s_name}】：{lbl}")
            out_str = "、".join(out_names)
            notes_str = "；".join(notes) if notes else "按设计规程平稳流转"
        else:
            out_str = "— (最终归宿)"
            notes_str = "完成该阶段工艺技术指标"

        table_lines.append(f"| {seq} | {name} | {stype} | {in_str} | {out_str} | {notes_str} |")
        seq += 1

    _add_table(doc, table_lines)


def _add_table(doc: Document, table_lines: list):
    """添加原生 Word 出版级标准三线表格（居中、淡灰表头加粗、跨页防断与表头跨页重复）。"""
    raw_rows = []
    alignments = []

    for tl in table_lines:
        stripped = tl.strip()
        # 识别分隔符行并提取列对齐方式
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

    # 跨页防断行 (w:cantSplit) 与表头跨页重复 (w:tblHeader)
    for ri, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(r'<w:cantSplit %s/>' % nsdecls('w')))
        if ri == 0 and has_header:
            trPr.append(parse_xml(r'<w:tblHeader %s/>' % nsdecls('w')))

    # 填充单元格
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

                # 对齐方式判定
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

                # 填充文本与格式
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
    """添加出版级正文段落（仿宋 小四 12pt，首行缩进 2 字符 24pt，1.35 倍行距，两端对齐）。"""
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
    """添加出版级无序列表项：悬挂缩进 2 字符，仿宋 12pt，1.35 倍行距。"""
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
    """添加出版级有序列表项：悬挂缩进 2 字符，仿宋 12pt，1.35 倍行距。"""
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


def _add_ref_item(doc: Document, prefix: str, text: str):
    """添加符合 GB/T 7714 出版级规范的参考文献条目：
    悬挂缩进 2 字符，仿宋 10.5pt（五号），1.3 倍行距，段间微距，逐条独立成行。
    """
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(24)
    p.paragraph_format.first_line_indent = Pt(-24)
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    num_run = p.add_run(f"{prefix} ")
    _format_run(num_run, font_name='Times New Roman', east_asia='仿宋', font_size=Pt(10.5), bold=True)

    parts = _LATEX_INLINE.split(text)
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            run = p.add_run(f"${part}$")
            _format_run(run, font_name='Times New Roman', east_asia='仿宋', font_size=Pt(10.5), italic=True)
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
                    font_size=Pt(10.5),
                    bold=is_bold,
                    italic=is_italic,
                )


def _add_blockquote(doc: Document, text: str):
    """添加出版级引用块：楷体 10.5pt，左右缩进 2 字符，淡灰边框与浅灰底纹。"""
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


_BODY_STARTERS = (
    "本项目", "项目", "本工程", "工程", "本报告",
    "从宏观", "从中观", "从微观", "从区域", "从空间", "从规划", "从技术", "从经济", "从环境",
    "截至", "目前", "当前", "根据", "按照", "依据", "随着", "调查", "结合", "经", "为",
    "在宏观", "在中观", "在微观", "在产业", "在规划", "在政策", "在土地", "在资源", "在生态", "在环境", "在就业", "在市场", "在乡村", "在绿色",
    "国内", "省内", "县域"
)


def _split_heading_and_body(heading_text: str, known_headings: list = None) -> tuple:
    """严格解耦标题与可能粘连的正文内容：
    返回 (pure_heading, remaining_body_text)。
    若无粘连，remaining_body_text 为空。
    """
    text = heading_text.strip()
    if not text:
        return "", ""

    # 1. 优先根据已知大纲标题库高精度匹配
    if known_headings:
        for kh in known_headings:
            if not kh or not isinstance(kh, str):
                continue
            kh_escaped = re.escape(kh)
            m = re.match(rf'^((?:\d+(?:\.\d+)*\s+)?{kh_escaped})\s*([:：，。—\-\s]*)(.*)$', text)
            if m:
                h_part = m.group(1).strip()
                rest = m.group(3).strip()
                if rest:
                    return h_part, rest

    # 2. 若长度 <= 35 且不包含句子标点，判定为纯标题
    if len(text) <= 35 and not re.search(r'[，。；！？]', text):
        return text, ""

    # 3. 启发式防御：基于多级数字编号及标点/正文首句特征解耦
    num_m = re.match(r'^(\d+(?:\.\d+)*\s+)?(.*)$', text)
    if num_m:
        num_prefix = num_m.group(1) or ""
        rest_title = num_m.group(2).strip()

        # 3.1 若有冒号/句号/破折号
        p_split = re.split(r'[:：。—\-]\s*', rest_title, maxsplit=1)
        if len(p_split) == 2 and 2 <= len(p_split[0]) <= 30:
            return f"{num_prefix}{p_split[0]}".strip(), p_split[1].strip()

        # 3.2 若包含正文起始主体词
        for starter in _BODY_STARTERS:
            idx = rest_title.find(starter)
            if 2 <= idx <= 30:
                h = rest_title[:idx].strip()
                b = rest_title[idx:].strip()
                return f"{num_prefix}{h}".strip(), b

        # 3.3 截断至首个逗号前（若逗号前在合理标题长度内）
        comma_idx = rest_title.find("，")
        if comma_idx != -1 and 2 <= comma_idx <= 25:
            return f"{num_prefix}{rest_title[:comma_idx]}".strip(), rest_title[comma_idx + 1:].strip()

    return text, ""


def _parse_md_line(line: str):
    """解析 Markdown 行为 (level, text, is_heading)。"""
    stripped = line.strip()
    match = re.match(r'^(#{1,6})\s+(.*)', stripped)
    if match:
        return len(match.group(1)), match.group(2).strip(), True
    # 兼容无 # 前缀的规范多级数字标题（如 2.3.1 宏观层面必要性、第2章 项目建设背景）
    num_match = re.match(r'^(\d+(?:\.\d+){1,4})\s+([^\n:：。]{2,30})$', stripped)
    if num_match:
        dot_count = num_match.group(1).count('.')
        level = min(dot_count + 1, 4)
        return level, stripped, True
    ch_match = re.match(r'^(第[一二三四五六七八九十百零\d]+章)\s+([^\n:：。]{2,30})$', stripped)
    if ch_match:
        return 1, stripped, True
    return 0, line, False


def format_ref_appendix(global_refs: list, numbering: dict) -> str:
    """生成符合学术论文与著录规范（GB/T 7714 顺序编码制）的《参考文献》章 Markdown。"""
    if not global_refs:
        return "# 参考文献\n\n（全书未引用外部参考资料）\n"

    # 按全文首次出现的编号严格升序排列 [1], [2], [3]...
    sorted_refs = sorted(
        global_refs,
        key=lambda r: numbering.get(r.get("label", ""), 99999),
    )

    lines = [
        "# 参考文献",
        "",
        "> 依据 GB/T 7714 信息与文献 参考文献著录规则 自动汇总排序",
        "",
    ]

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
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def generate_report_ref(chapters: dict, output_path: str, refs: list = None):
    """生成三层参考文献文件 report_ref.md（从各章 📎 段合并去重）。

    - 合并去重各章 📎 段引用得全局列表
    - 剥离 📎、拼接正文、全文一次性编号
    - 按编号排序输出参考文献
    refs 参数保留向后兼容。
    """
    global_refs = merge_global_refs(chapters)

    body_parts = []
    for ch_key in sorted(chapters.keys(),
                         key=lambda k: int(k) if str(k).lstrip('-').isdigit() else 0):
        content = chapters.get(ch_key, "")
        if content:
            body_parts.append(_strip_ref_section(content))
    full_body = "\n\n".join(body_parts)
    full_body = normalize_chapter_markdown(full_body)
    _, numbering = global_assign_ref_numbers(full_body)

    ref_content = format_ref_appendix(global_refs, numbering)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ref_content)
    except IOError:
        pass


def build_merged_md(chapters: dict, include_refs: bool = True, project: str = "") -> str:
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

    skeleton = ""
    if project:
        try:
            from ..config import settings
            p = settings.project_dir(project) / "outline.json"
            if p.is_file():
                import json
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    skeleton = data.get("outline_md", "")
        except Exception:
            pass

    full_body = normalize_chapter_markdown(full_body, skeleton=skeleton)

    if not include_refs:
        return full_body

    # 全局编号 + 规范参考文献附录
    global_refs = merge_global_refs(chapters, project_name=project)
    numbered_body, numbering = global_assign_ref_numbers(full_body)
    ref_md = format_ref_appendix(global_refs, numbering)
    if ref_md.strip():
        return numbered_body + "\n\n" + ref_md
    return numbered_body


