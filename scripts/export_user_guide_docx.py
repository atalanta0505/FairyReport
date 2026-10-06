"""
《用户操作手册》Word (.docx) 导出：内容唯一来源为 docs/USER_GUIDE.md。

用法：python scripts/export_user_guide_docx.py
"""
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parent))

from export_beginner_guide_docx import (  # noqa: E402
    COLOR_ACCENT,
    COLOR_BORDER,
    COLOR_MUTED,
    COLOR_PRIMARY,
    COLOR_TEXT,
    COLOR_TITLE,
    DOCS_DIR,
    REPO_ROOT,
    add_bullet_item,
    add_heading_1,
    add_heading_2,
    apply_margins,
    format_run,
    render_markdown,
)

MD_PATH = DOCS_DIR / "USER_GUIDE.md"
OUTPUTS = [
    DOCS_DIR / "FairyReport_用户操作手册.docx",
    REPO_ROOT / "dist" / "FairyReport_用户操作手册.docx",
]


def app_version() -> str:
    with open(REPO_ROOT / "desktop" / "package.json", encoding="utf-8") as fh:
        return json.load(fh)["version"]


def cover(doc: Document, subtitle: str):
    """封面：与快速上手指南同一版式，仅替换副标题。"""
    sec = doc.sections[0]
    apply_margins(sec)
    sec.header.is_linked_to_previous = False
    sec.footer.is_linked_to_previous = False

    p_org = doc.add_paragraph()
    p_org.paragraph_format.first_line_indent = Pt(0)
    p_org.paragraph_format.space_before = Pt(36)
    p_org.paragraph_format.space_after = Pt(4)
    p_org.alignment = WD_ALIGN_PARAGRAPH.CENTER
    format_run(p_org.add_run("现代工程设计咨询研究院  ·  智能技术创新中心"),
               font_name="Arial", east_asia="黑体", font_size=Pt(11), bold=True, color=COLOR_MUTED)

    p_line = doc.add_paragraph()
    p_line.paragraph_format.first_line_indent = Pt(0)
    p_line.paragraph_format.space_before = Pt(4)
    p_line.paragraph_format.space_after = Pt(48)
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    format_run(p_line.add_run("―" * 28), font_size=Pt(10), color=RGBColor(0x94, 0xA3, 0xB8))

    p_badge = doc.add_paragraph()
    p_badge.paragraph_format.first_line_indent = Pt(0)
    p_badge.paragraph_format.space_after = Pt(12)
    p_badge.alignment = WD_ALIGN_PARAGRAPH.CENTER
    format_run(p_badge.add_run("FAIRYREPORT  DESKTOP  PLATFORM"),
               font_name="Arial", east_asia="Arial", font_size=Pt(10), bold=True, color=COLOR_ACCENT)

    p_title = doc.add_paragraph()
    p_title.paragraph_format.first_line_indent = Pt(0)
    p_title.paragraph_format.space_after = Pt(16)
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    format_run(p_title.add_run("FairyReport 智能报告编制应用"),
               font_name="Times New Roman", east_asia="黑体", font_size=Pt(26), bold=True, color=COLOR_TITLE)

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.first_line_indent = Pt(0)
    p_sub.paragraph_format.space_after = Pt(40)
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    format_run(p_sub.add_run(subtitle),
               font_name="Times New Roman", east_asia="黑体", font_size=Pt(20), bold=True, color=COLOR_PRIMARY)

    p_ver = doc.add_paragraph()
    p_ver.paragraph_format.first_line_indent = Pt(0)
    p_ver.alignment = WD_ALIGN_PARAGRAPH.CENTER
    format_run(p_ver.add_run(f"版本 {app_version()}"), font_size=Pt(11), color=COLOR_MUTED)


def toc_from_markdown(doc: Document, markdown_text: str):
    """目录页：标题直接来自 Markdown 的二级/三级标题。"""
    toc_sec = doc.add_section(WD_SECTION.NEW_PAGE)
    apply_margins(toc_sec)
    toc_sec.header.is_linked_to_previous = False
    toc_sec.footer.is_linked_to_previous = False

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.first_line_indent = Pt(0)
    p_title.paragraph_format.space_before = Pt(24)
    p_title.paragraph_format.space_after = Pt(20)
    format_run(p_title.add_run("目    录"),
               font_name="Times New Roman", east_asia="黑体", font_size=Pt(16), bold=True, color=COLOR_PRIMARY)

    p_line = doc.add_paragraph()
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_line.paragraph_format.first_line_indent = Pt(0)
    p_line.paragraph_format.space_after = Pt(18)
    format_run(p_line.add_run("―" * 32), font_size=Pt(9), color=RGBColor(0xCB, 0xD5, 0xE1))

    for raw in markdown_text.splitlines():
        line = raw.strip()
        if line.startswith("## ") and line[3:].strip() != "目录":
            text, is_h1 = line[3:].strip(), True
        elif line.startswith("### "):
            text, is_h1 = line[4:].strip(), False
        else:
            continue
        if text.startswith("Q") and len(text) > 1 and text[1].isdigit():
            is_h1 = False

        p_item = doc.add_paragraph()
        p_item.paragraph_format.first_line_indent = Pt(0)
        p_item.paragraph_format.space_before = Pt(5 if is_h1 else 2)
        p_item.paragraph_format.space_after = Pt(4 if is_h1 else 2)
        p_item.paragraph_format.left_indent = Pt(0 if is_h1 else 16)
        if is_h1:
            format_run(p_item.add_run("■ "), font_size=Pt(8), color=COLOR_PRIMARY)
            format_run(p_item.add_run(text), font_name="Times New Roman", east_asia="黑体",
                       font_size=Pt(11.5), bold=True, color=COLOR_TITLE)
        else:
            format_run(p_item.add_run("□ "), font_size=Pt(7), color=COLOR_MUTED)
            format_run(p_item.add_run(text), font_name="Times New Roman", east_asia="仿宋",
                       font_size=Pt(10.5), color=COLOR_TEXT)


def body_section(doc: Document, header_text: str):
    """正文节：页眉页脚与页码。"""
    sec = doc.add_section(WD_SECTION.NEW_PAGE)
    apply_margins(sec)
    sec.header.is_linked_to_previous = False
    sec.footer.is_linked_to_previous = False

    p_hdr = sec.header.paragraphs[0]
    p_hdr.paragraph_format.first_line_indent = Pt(0)
    p_hdr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    format_run(p_hdr.add_run(header_text), font_name="Times New Roman", east_asia="仿宋",
               font_size=Pt(9), color=COLOR_MUTED)
    pPr = p_hdr._p.get_or_add_pPr()
    pPr.append(parse_xml(
        rf'<w:pBdr {nsdecls("w")}>'
        rf'  <w:bottom w:val="single" w:sz="6" w:space="4" w:color="{COLOR_BORDER}"/>'
        rf'</w:pBdr>'
    ))

    p_ftr = sec.footer.paragraphs[0]
    p_ftr.paragraph_format.first_line_indent = Pt(0)
    p_ftr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    format_run(p_ftr.add_run("第 "), font_name="Times New Roman", east_asia="仿宋", font_size=Pt(9), color=COLOR_MUTED)
    p_ftr._p.append(parse_xml(r'<w:fldSimple %s w:instr="PAGE"/>' % nsdecls("w")))
    format_run(p_ftr.add_run(" 页"), font_name="Times New Roman", east_asia="仿宋", font_size=Pt(9), color=COLOR_MUTED)
    sec._sectPr.append(parse_xml(r'<w:pgNumType %s w:start="1"/>' % nsdecls("w")))


def build():
    markdown_text = MD_PATH.read_text(encoding="utf-8")
    doc = Document()
    cover(doc, "用户操作手册")
    toc_from_markdown(doc, markdown_text)
    body_section(doc, f"FairyReport 智能报告编制应用 · 用户操作手册 (v{app_version()})")
    render_markdown(doc, markdown_text)

    for out in OUTPUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out))
        print(f"已导出: {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    build()
