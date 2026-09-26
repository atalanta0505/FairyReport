"""
FairyReport 新人极简图文上手指南 — 出版级 Word (.docx) 排版与导出工具
"""

import os
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

REPO_ROOT = Path(r"D:\Repo\FairyReport_lite")
DOCS_DIR = REPO_ROOT / "docs"
IMAGES_DIR = DOCS_DIR / "images"
OUTPUT_DOCX_DOCS = DOCS_DIR / "FairyReport_新人极简图文上手指南.docx"
OUTPUT_DOCX_DIST = REPO_ROOT / "dist" / "FairyReport_新人极简图文上手指南.docx"

# ── 颜色常量 ──
COLOR_PRIMARY = RGBColor(0x1E, 0x3A, 0x8A)      # 科技深蓝 #1E3A8A
COLOR_TITLE = RGBColor(0x0F, 0x17, 0x2A)        # 极深板岩灰 #0F172A
COLOR_HEADING2 = RGBColor(0x1E, 0x29, 0x3B)     # 标题二级 #1E293B
COLOR_TEXT = RGBColor(0x33, 0x41, 0x55)         # 正文板岩灰 #334155
COLOR_ACCENT = RGBColor(0x25, 0x63, 0xEB)       # 强调亮蓝 #2563EB
COLOR_MUTED = RGBColor(0x64, 0x74, 0x8B)        # 注释与说明灰色 #64748B
COLOR_BORDER = "CBD5E1"                         # 浅边框灰
COLOR_CALLOUT_BG = "F0F7FF"                     # 提示框浅蓝底纹
COLOR_CALLOUT_BORDER = "2563EB"                 # 提示框左侧边框蓝


def format_run(
    run,
    font_name="Times New Roman",
    east_asia="仿宋",
    font_size=Pt(12),
    bold=False,
    italic=False,
    color=None,
):
    """设置西文与中文字体属性。"""
    run.font.name = font_name
    run.font.size = font_size
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color

    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:eastAsia"), east_asia)
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)


def apply_margins(section):
    """出版级边距设置：上 2.54cm, 下 2.54cm, 左 2.8cm, 右 2.6cm。"""
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.6)


def create_cover_page(doc: Document):
    """构建精美现代的技术手册封面。"""
    sec = doc.sections[0]
    apply_margins(sec)
    sec.header.is_linked_to_previous = False
    sec.footer.is_linked_to_previous = False

    # 1. 顶部机构名称与品类
    p_org = doc.add_paragraph()
    p_org.paragraph_format.first_line_indent = Pt(0)
    p_org.paragraph_format.space_before = Pt(36)
    p_org.paragraph_format.space_after = Pt(4)
    p_org.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_org = p_org.add_run("现代工程设计咨询研究院  ·  智能技术创新中心")
    format_run(r_org, font_name="Arial", east_asia="黑体", font_size=Pt(11), bold=True, color=COLOR_MUTED)

    # 细横线
    p_line = doc.add_paragraph()
    p_line.paragraph_format.first_line_indent = Pt(0)
    p_line.paragraph_format.space_before = Pt(4)
    p_line.paragraph_format.space_after = Pt(48)
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_line = p_line.add_run("―" * 28)
    format_run(r_line, font_size=Pt(10), color=RGBColor(0x94, 0xA3, 0xB8))

    # 2. 软件与系统名称
    p_badge = doc.add_paragraph()
    p_badge.paragraph_format.first_line_indent = Pt(0)
    p_badge.paragraph_format.space_before = Pt(0)
    p_badge.paragraph_format.space_after = Pt(12)
    p_badge.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_badge = p_badge.add_run("FAIRYREPORT  DESKTOP  PLATFORM")
    format_run(r_badge, font_name="Arial", east_asia="Arial", font_size=Pt(10), bold=True, color=COLOR_ACCENT)

    # 3. 主标题
    p_title = doc.add_paragraph()
    p_title.paragraph_format.first_line_indent = Pt(0)
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(16)
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("FairyReport 智能报告写作平台")
    format_run(r_title, font_name="Times New Roman", east_asia="黑体", font_size=Pt(26), bold=True, color=COLOR_TITLE)

    # 4. 副标题
    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.first_line_indent = Pt(0)
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(40)
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("新人极简图文上手指南")
    format_run(r_sub, font_name="Times New Roman", east_asia="黑体", font_size=Pt(18), bold=True, color=COLOR_PRIMARY)

    # 5. 特性亮点卡片 (1行4列表格)
    features_table = doc.add_table(rows=1, cols=4)
    features_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = features_table._tbl.tblPr
    tblBorders = parse_xml(
        rf'<w:tblBorders {nsdecls("w")}>'
        rf'  <w:top w:val="single" w:sz="6" w:space="0" w:color="{COLOR_BORDER}"/>'
        rf'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="{COLOR_BORDER}"/>'
        rf'  <w:left w:val="none"/>'
        rf'  <w:right w:val="none"/>'
        rf'  <w:insideH w:val="none"/>'
        rf'  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        rf'</w:tblBorders>'
    )
    tblPr.append(tblBorders)

    col_widths = [Cm(3.8), Cm(3.8), Cm(3.8), Cm(3.8)]
    cards = [
        ("零代码门槛", "解压双击即跑"),
        ("支持资料留空", "内置规程智识起草"),
        ("标准三线表", "出版级工程格式"),
        ("自洽度复核", "跨章节闭环质检"),
    ]
    for idx, (title, sub) in enumerate(cards):
        cell = features_table.cell(0, idx)
        cell.width = col_widths[idx]
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        shd = parse_xml(rf'<w:shd {nsdecls("w")} w:fill="F8FAFC"/>')
        cell._tc.get_or_add_tcPr().append(shd)

        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        r1 = p.add_run(title)
        format_run(r1, font_name="Times New Roman", east_asia="黑体", font_size=Pt(10.5), bold=True, color=COLOR_TITLE)

        p2 = cell.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_before = Pt(0)
        p2.paragraph_format.space_after = Pt(6)
        r2 = p2.add_run(sub)
        format_run(r2, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(9), color=COLOR_MUTED)

    # 6. 下部间距推移
    for _ in range(5):
        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_before = Pt(0)
        p_sp.paragraph_format.space_after = Pt(0)
        p_sp.paragraph_format.first_line_indent = Pt(0)

    # 7. 底部元数据信息
    meta_info = [
        ("适用版本", "FairyReport v1.5.0 正式版"),
        ("受众定位", "零技术背景业务人员 · 投资与工程咨询规划师"),
        ("配图说明", "系统真实操作界面截屏"),
        ("交付标准", "出版级公文排版 · 行业现行工程咨询规范"),
        ("发布日期", "2026 年 09 月"),
    ]
    for label, val in meta_info:
        p_meta = doc.add_paragraph()
        p_meta.paragraph_format.first_line_indent = Pt(0)
        p_meta.paragraph_format.space_before = Pt(2)
        p_meta.paragraph_format.space_after = Pt(2)
        p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER

        r_lbl = p_meta.add_run(f"{label}：")
        format_run(r_lbl, font_name="Times New Roman", east_asia="黑体", font_size=Pt(10.5), bold=True, color=COLOR_MUTED)
        r_val = p_meta.add_run(val)
        format_run(r_val, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(10.5), color=COLOR_TITLE)


def create_toc_page(doc: Document):
    """构建专业目录页（Section 2），包含原生 Word TOC 域与可视化精美目录列表。"""
    toc_sec = doc.add_section(WD_SECTION.NEW_PAGE)
    apply_margins(toc_sec)
    toc_sec.header.is_linked_to_previous = False
    toc_sec.footer.is_linked_to_previous = False

    # 目录标题
    p_toc_title = doc.add_paragraph()
    p_toc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_toc_title.paragraph_format.keep_with_next = True
    p_toc_title.paragraph_format.first_line_indent = Pt(0)
    p_toc_title.paragraph_format.space_before = Pt(24)
    p_toc_title.paragraph_format.space_after = Pt(20)
    run_toc_title = p_toc_title.add_run("目    录")
    format_run(run_toc_title, font_name="Times New Roman", east_asia="黑体", font_size=Pt(16), bold=True, color=COLOR_PRIMARY)

    # 目录装饰细线
    p_line = doc.add_paragraph()
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_line.paragraph_format.first_line_indent = Pt(0)
    p_line.paragraph_format.space_before = Pt(0)
    p_line.paragraph_format.space_after = Pt(18)
    r_line = p_line.add_run("―" * 32)
    format_run(r_line, font_size=Pt(9), color=RGBColor(0xCB, 0xD5, 0xE1))

    # 可视化目录项列表
    toc_items = [
        ("【前言】献给新手：你的 24 小时专业报告起草助理", True, 0),
        ("【第一篇】零门槛极速上手（3 分钟掌握核心概念）", True, 0),
        ("1. 软件启动只需一步", False, 1),
        ("2. 认识核心操作流水线", False, 1),
        ("【第二篇】五步全流程图文实操指南（附真实界面）", True, 0),
        ("步骤 1：项目与资料 —— 资料留空，即开即写", False, 1),
        ("步骤 2：模板与大纲 —— 锁定智库专报标准骨架", False, 1),
        ("步骤 3：章节写作 —— 边思索、边查证、自动绘表", False, 1),
        ("步骤 4：审阅修改 —— 专家诊断总台账逐项把关", False, 1),
        ("步骤 5：成果导出 —— 综合自洽度 100 分一键交付", False, 1),
        ("【第三篇】新手日常使用常见疑问（FAQ）", True, 0),
        ("Q1：智库专报真的不需要上传任何项目材料吗？", False, 1),
        ("Q2：我完全不懂怎么给 AI 写提示词，也能写出这么专业的报告吗？", False, 1),
        ("Q3：如果导出的 Word 初稿我还想进一步修改怎么办？", False, 1),
    ]

    for title, is_h1, level in toc_items:
        p_item = doc.add_paragraph()
        p_item.paragraph_format.first_line_indent = Pt(0)
        p_item.paragraph_format.space_before = Pt(5 if is_h1 else 2)
        p_item.paragraph_format.space_after = Pt(4 if is_h1 else 2)
        p_item.paragraph_format.left_indent = Pt(16 if level == 1 else 0)

        if is_h1:
            r_bullet = p_item.add_run("■ ")
            format_run(r_bullet, font_size=Pt(8), color=COLOR_PRIMARY)
            r_t = p_item.add_run(title)
            format_run(r_t, font_name="Times New Roman", east_asia="黑体", font_size=Pt(11.5), bold=True, color=COLOR_TITLE)
        else:
            r_bullet = p_item.add_run("□ ")
            format_run(r_bullet, font_size=Pt(7), color=COLOR_MUTED)
            r_t = p_item.add_run(title)
            format_run(r_t, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(10.5), color=COLOR_TEXT)


def init_body_section(doc: Document):
    """初始化正文节（Section 3），配置标准出版级页眉与页脚。"""
    body_sec = doc.add_section(WD_SECTION.NEW_PAGE)
    apply_margins(body_sec)
    body_sec.header.is_linked_to_previous = False
    body_sec.footer.is_linked_to_previous = False

    # ── 页眉设置 ──
    header = body_sec.header
    p_hdr = header.paragraphs[0]
    p_hdr.paragraph_format.first_line_indent = Pt(0)
    p_hdr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_hdr = p_hdr.add_run("FairyReport 智能报告写作平台 · 新人极简图文上手指南 (v1.5.0)")
    format_run(r_hdr, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(9), color=COLOR_MUTED)

    # 页眉下划线
    pPr = p_hdr._p.get_or_add_pPr()
    pBdr = parse_xml(
        rf'<w:pBdr {nsdecls("w")}>'
        rf'  <w:bottom w:val="single" w:sz="6" w:space="4" w:color="{COLOR_BORDER}"/>'
        rf'</w:pBdr>'
    )
    pPr.append(pBdr)

    # ── 页脚设置（页码从 1 开始） ──
    footer = body_sec.footer
    p_ftr = footer.paragraphs[0]
    p_ftr.paragraph_format.first_line_indent = Pt(0)
    p_ftr.alignment = WD_ALIGN_PARAGRAPH.CENTER

    r_f1 = p_ftr.add_run("第 ")
    format_run(r_f1, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(9), color=COLOR_MUTED)
    fld_page = parse_xml(r'<w:fldSimple %s w:instr="PAGE"/>' % nsdecls("w"))
    p_ftr._p.append(fld_page)
    r_f2 = p_ftr.add_run(" 页")
    format_run(r_f2, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(9), color=COLOR_MUTED)

    # 起始页码 = 1
    body_sec._sectPr.append(parse_xml(r'<w:pgNumType %s w:start="1"/>' % nsdecls("w")))


def add_heading_1(doc: Document, text: str):
    """一级篇章标题（黑体 16pt，科技蓝，加粗，段前16pt，段后8pt）。"""
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.keep_with_next = True

    # 左侧装饰小色块
    r_decor = p.add_run("▍ ")
    format_run(r_decor, font_name="Arial", east_asia="黑体", font_size=Pt(16), bold=True, color=COLOR_PRIMARY)
    r_text = p.add_run(text)
    format_run(r_text, font_name="Times New Roman", east_asia="黑体", font_size=Pt(16), bold=True, color=COLOR_PRIMARY)
    return p


def add_heading_2(doc: Document, text: str):
    """二级标题（黑体 14pt，板岩灰，加粗，段前12pt，段后6pt）。"""
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True

    r_text = p.add_run(text)
    format_run(r_text, font_name="Times New Roman", east_asia="黑体", font_size=Pt(14), bold=True, color=COLOR_HEADING2)
    return p


def add_heading_3(doc: Document, text: str):
    """三级标题 / FAQ 提问（黑体 12pt，亮蓝，加粗，段前8pt，段后3pt）。"""
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True

    r_text = p.add_run(text)
    format_run(r_text, font_name="Times New Roman", east_asia="黑体", font_size=Pt(12), bold=True, color=COLOR_ACCENT)
    return p


def add_body_paragraph(doc: Document, text: str):
    """正文段落（仿宋小四 12pt，1.35倍行距，严格首行缩进 2 字符）。"""
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(24)  # 2 字符
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.35
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    r = p.add_run(text)
    format_run(r, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(12), color=COLOR_TITLE)
    return p


def add_bullet_item(doc: Document, bold_prefix: str, content: str):
    """列表项（悬挂缩进 20pt，黑体前缀 + 仿宋正文）。"""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(20)
    p.paragraph_format.first_line_indent = Pt(-14)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.3

    r_dot = p.add_run("●  ")
    format_run(r_dot, font_name="Arial", east_asia="Arial", font_size=Pt(8), color=COLOR_ACCENT)

    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        format_run(r_pre, font_name="Times New Roman", east_asia="黑体", font_size=Pt(11), bold=True, color=COLOR_HEADING2)

    r_cnt = p.add_run(content)
    format_run(r_cnt, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(11), color=COLOR_TITLE)
    return p


def add_image_with_caption(doc: Document, img_path: Path, caption: str):
    """插入 1080P 高清实机截图，配微细边框与专业居中图题。"""
    if not img_path.exists():
        print(f"Warning: image {img_path} not found!")
        return

    # 截图容器表格（单单元格，用于添加精美边框与底纹）
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = table._tbl.tblPr
    tblBorders = parse_xml(
        rf'<w:tblBorders {nsdecls("w")}>'
        rf'  <w:top w:val="single" w:sz="6" w:space="0" w:color="{COLOR_BORDER}"/>'
        rf'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="{COLOR_BORDER}"/>'
        rf'  <w:left w:val="single" w:sz="6" w:space="0" w:color="{COLOR_BORDER}"/>'
        rf'  <w:right w:val="single" w:sz="6" w:space="0" w:color="{COLOR_BORDER}"/>'
        rf'</w:tblBorders>'
    )
    tblPr.append(tblBorders)

    cell = table.cell(0, 0)
    cell.width = Cm(15.4)
    shd = parse_xml(rf'<w:shd {nsdecls("w")} w:fill="FAFAFA"/>')
    cell._tc.get_or_add_tcPr().append(shd)

    p_img = cell.paragraphs[0]
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.first_line_indent = Pt(0)
    p_img.paragraph_format.space_before = Pt(4)
    p_img.paragraph_format.space_after = Pt(4)
    r_img = p_img.add_run()
    # 宽度设为 15.0cm，高度保持 16:9 比例 (8.44cm)
    r_img.add_picture(str(img_path), width=Cm(15.0))

    # 图题
    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.first_line_indent = Pt(0)
    p_cap.paragraph_format.space_before = Pt(4)
    p_cap.paragraph_format.space_after = Pt(10)
    p_cap.paragraph_format.keep_with_next = True
    r_cap = p_cap.add_run(caption)
    format_run(r_cap, font_name="Times New Roman", east_asia="楷体", font_size=Pt(10), bold=True, color=COLOR_MUTED)


def add_callout_box(doc: Document, title: str, points: list):
    """
    插入专业现代高亮看点框（带有亮蓝左边线、浅蓝底纹）。
    """
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = table._tbl.tblPr
    tblBorders = parse_xml(
        rf'<w:tblBorders {nsdecls("w")}>'
        rf'  <w:left w:val="single" w:sz="24" w:space="0" w:color="{COLOR_CALLOUT_BORDER}"/>'
        rf'  <w:top w:val="none"/>'
        rf'  <w:bottom w:val="none"/>'
        rf'  <w:right w:val="none"/>'
        rf'</w:tblBorders>'
    )
    tblPr.append(tblBorders)

    # 内部边距
    tblCellMar = parse_xml(
        rf'<w:tblCellMar {nsdecls("w")}>'
        rf'  <w:top w:w="120" w:type="dxa"/>'
        rf'  <w:left w:w="180" w:type="dxa"/>'
        rf'  <w:bottom w:w="120" w:type="dxa"/>'
        rf'  <w:right w:w="180" w:type="dxa"/>'
        rf'</w:tblCellMar>'
    )
    tblPr.append(tblCellMar)

    cell = table.cell(0, 0)
    cell.width = Cm(15.4)
    shd = parse_xml(rf'<w:shd {nsdecls("w")} w:fill="{COLOR_CALLOUT_BG}"/>')
    cell._tc.get_or_add_tcPr().append(shd)

    # 标题行
    p_head = cell.paragraphs[0]
    p_head.paragraph_format.first_line_indent = Pt(0)
    p_head.paragraph_format.space_before = Pt(2)
    p_head.paragraph_format.space_after = Pt(4)
    r_icon = p_head.add_run("💡 ")
    format_run(r_icon, font_size=Pt(10.5))
    r_tit = p_head.add_run(title)
    format_run(r_tit, font_name="Times New Roman", east_asia="黑体", font_size=Pt(11), bold=True, color=COLOR_PRIMARY)

    # 列表看点
    for pt in points:
        p_pt = cell.add_paragraph()
        p_pt.paragraph_format.left_indent = Pt(14)
        p_pt.paragraph_format.first_line_indent = Pt(-10)
        p_pt.paragraph_format.space_before = Pt(1)
        p_pt.paragraph_format.space_after = Pt(2)
        p_pt.paragraph_format.line_spacing = 1.25

        r_sub_dot = p_pt.add_run("▪ ")
        format_run(r_sub_dot, font_name="Arial", east_asia="Arial", font_size=Pt(8), color=COLOR_ACCENT)

        # 解析可能存在的冒号加粗
        if "：" in pt:
            k, v = pt.split("：", 1)
            r_k = p_pt.add_run(k + "：")
            format_run(r_k, font_name="Times New Roman", east_asia="黑体", font_size=Pt(10), bold=True, color=COLOR_HEADING2)
            r_v = p_pt.add_run(v)
            format_run(r_v, font_name="Times New Roman", east_asia="楷体", font_size=Pt(10), color=COLOR_TITLE)
        else:
            r_all = p_pt.add_run(pt)
            format_run(r_all, font_name="Times New Roman", east_asia="楷体", font_size=Pt(10), color=COLOR_TITLE)

    # 框后空行缓冲
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(6)
    p_after.paragraph_format.first_line_indent = Pt(0)


def add_pipeline_flowchart_table(doc: Document):
    """
    将 Mermaid 流程图转换为现代出版级五阶段流水线表。
    """
    table = doc.add_table(rows=3, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = table._tbl.tblPr

    # 边框
    tblBorders = parse_xml(
        rf'<w:tblBorders {nsdecls("w")}>'
        rf'  <w:top w:val="single" w:sz="12" w:space="0" w:color="1E3A8A"/>'
        rf'  <w:bottom w:val="single" w:sz="12" w:space="0" w:color="1E3A8A"/>'
        rf'  <w:left w:val="none"/>'
        rf'  <w:right w:val="none"/>'
        rf'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        rf'  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        rf'</w:tblBorders>'
    )
    tblPr.append(tblBorders)

    col_widths = [Cm(3.08), Cm(3.08), Cm(3.08), Cm(3.08), Cm(3.08)]
    stages = [
        ("步骤 1", "项目与资料", "新建项目建档\n支持资料留空直接起草"),
        ("步骤 2", "模板与大纲", "15类专业报告预置\n现行标准骨架刚性锁定"),
        ("步骤 3", "章节写作", "全网权威检索溯源\n自动绘制规范工程三线表"),
        ("步骤 4", "审阅修改", "专家诊断总台账把关\n局部精准修补不损上下文"),
        ("步骤 5", "成果导出", "综合自洽度100分复核\n一键输出出版级Word文档"),
    ]

    for c_idx, (st_num, st_name, st_desc) in enumerate(stages):
        # 1. 阶段序号头
        c1 = table.cell(0, c_idx)
        c1.width = col_widths[c_idx]
        shd1 = parse_xml(rf'<w:shd {nsdecls("w")} w:fill="1E3A8A"/>')
        c1._tc.get_or_add_tcPr().append(shd1)
        p1 = c1.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1.paragraph_format.space_before = Pt(4)
        p1.paragraph_format.space_after = Pt(4)
        r1 = p1.add_run(st_num)
        format_run(r1, font_name="Arial", east_asia="黑体", font_size=Pt(10), bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))

        # 2. 阶段名称
        c2 = table.cell(1, c_idx)
        c2.width = col_widths[c_idx]
        shd2 = parse_xml(rf'<w:shd {nsdecls("w")} w:fill="F1F5F9"/>')
        c2._tc.get_or_add_tcPr().append(shd2)
        p2 = c2.paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_before = Pt(4)
        p2.paragraph_format.space_after = Pt(4)
        r2 = p2.add_run(st_name)
        format_run(r2, font_name="Times New Roman", east_asia="黑体", font_size=Pt(10.5), bold=True, color=COLOR_PRIMARY)

        # 3. 核心机制
        c3 = table.cell(2, c_idx)
        c3.width = col_widths[c_idx]
        shd3 = parse_xml(rf'<w:shd {nsdecls("w")} w:fill="FFFFFF"/>')
        c3._tc.get_or_add_tcPr().append(shd3)
        p3 = c3.paragraphs[0]
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p3.paragraph_format.space_before = Pt(4)
        p3.paragraph_format.space_after = Pt(4)
        p3.paragraph_format.line_spacing = 1.2
        r3 = p3.add_run(st_desc)
        format_run(r3, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(9), color=COLOR_TITLE)

    p_post = doc.add_paragraph()
    p_post.paragraph_format.space_before = Pt(4)
    p_post.paragraph_format.space_after = Pt(8)
    p_post.paragraph_format.first_line_indent = Pt(0)


def build_beginner_guide_docx():
    """主构建函数：严格根据 docs/BEGINNER_GUIDE.md 内容生成出版级 Word。"""
    print("开始构建 FairyReport 新人极简图文上手指南 Word 文档...")
    doc = Document()

    # 1. 封面 (Section 1)
    create_cover_page(doc)

    # 2. 目录页 (Section 2)
    create_toc_page(doc)

    # 3. 正文节 (Section 3)
    init_body_section(doc)

    # ──【前言】──
    add_heading_1(doc, "【前言】献给新手：你的 24 小时专业报告起草助理")
    add_body_paragraph(
        doc,
        "在投资项目立项、可行性研究、技术方案编制与智库专报撰写过程中，初涉此业务的新人往往面临三大深层痛点：",
    )
    add_bullet_item(doc, "资料杂乱无头绪：", "面对几十份行业动态、政策汇编与宏观统计数据，不知如何结构化提炼与切入下笔；")
    add_bullet_item(doc, "格式规范严苛：", "主管部门指导意见与现行行业规程对目录大纲层级、前后指标自洽性、工程三线表格式有着极严约束，一旦错漏一项往往需要通篇推倒重来；")
    add_bullet_item(doc, "起草周期漫长：", "纯人工手工编写数万字初稿往往耗费数周时间，且需在后期花费大量精力核对指标冲突与引用出处。")

    add_body_paragraph(
        doc,
        "FairyReport 就是专为你量身打造的“桌面级智能报告起草助手”，其核心理念与优势体现在四个方面：",
    )
    add_bullet_item(doc, "零门槛免配置：", "不用敲任何命令行代码，不用在本地安装复杂的第三方数据库或容器，像打开日常办公软件一样轻盈运行；")
    add_bullet_item(doc, "独创支持资料留空：", "对于智库专报等宏观战略类报告，无需上传复杂项目底稿，平台依托权威联网检索与内置行业标准规程库即可高质量快速起草；")
    add_bullet_item(doc, "全透明可追溯：", "正文每一句关键判断、核心技术指标均清晰标注引用角标，字字有出处、杜绝 AI 幻觉编造；")
    add_bullet_item(doc, "出版级成果输出：", "一键导出的即为排版精良、字体行距符合现行工程咨询公文规范的 Word 初稿（.docx），可直接向上级或协作团队汇报研讨。")

    # ──【第一篇】──
    add_heading_1(doc, "【第一篇】零门槛极速上手（3 分钟掌握核心概念）")
    add_heading_2(doc, "1. 软件启动只需一步")
    add_bullet_item(doc, "单包绿色运行：", "下载解压 FairyReport-Local-v1.5.0-Windows-x64.zip 至任意磁盘文件夹；")
    add_bullet_item(doc, "一键双击启动：", "双击运行「启动 FairyReport.bat」，内置智能引擎全自动就绪并弹出优雅的桌面操作界面；")
    add_bullet_item(doc, "免登录快速体验：", "在登录界面点击下方「🎯 快捷演示体验」按钮，即可免登录直接进入工作台体验全部核心功能。")

    add_heading_2(doc, "2. 认识核心操作流水线")
    add_body_paragraph(
        doc,
        "整个软件界面遵循最符合人类工程咨询直觉的“流水线设计”。用户只需沿着顶部的 5 个步骤一步步往下推进即可完成全生命周期编制："
    )
    add_pipeline_flowchart_table(doc)

    # ──【第二篇】──
    add_heading_1(doc, "【第二篇】五步全流程图文实操指南（附真实界面）")
    add_body_paragraph(
        doc,
        "以下全流程以撰写一份典型的决策参考交付物——《重点算力基础设施绿色低碳发展与智能算力中心布局智库专报》为例，完整演示 5 步全闭环操作："
    )

    # 步骤 1
    add_heading_2(doc, "步骤 1：项目与资料 —— 资料留空，即开即写")
    add_bullet_item(doc, "用户操作：", "点击「+ 新建项目」，输入报告名称；如果手头有参考文档可以直接拖入上传，若尚无资料也可以完全保持留空；")
    add_bullet_item(doc, "系统响应：", "后台自动完成项目建档。系统提示通用知识包已就绪（内含 15 类报告交付物现行标准大纲与规程库）。")
    add_image_with_caption(
        doc,
        IMAGES_DIR / "step1_materials.png",
        "图 2-1 步骤 1：项目与资料管理（支持资料留空状态直接起草）"
    )
    add_callout_box(
        doc,
        "步骤 1 · 新手实战看点",
        [
            "资料留空特性：界面醒目提示“智库专报等宏观战略类报告支持资料留空，可直接点击下方「下一步：模板与大纲」，依托权威联网检索与知识规程库高质量起草”。",
            "零准备成本：不用为了凑材料而到处翻找底稿文件，点击右下角蓝色按钮直接推进到大纲规划！",
        ]
    )

    # 步骤 2
    add_heading_2(doc, "步骤 2：模板与大纲 —— 锁定智库专报标准骨架")
    add_bullet_item(doc, "用户操作：", "在模板网格中点击选中「智库专报」卡片；")
    add_bullet_item(doc, "系统响应：", "弹出智库专报权威业务定位说明，并在右侧严格加载符合现行编制标准指南的 5 大核心章节大纲。")
    add_image_with_caption(
        doc,
        IMAGES_DIR / "step2_outline.png",
        "图 2-2 步骤 2：模板与大纲选择（智库专报现行标准大纲骨架）"
    )
    add_callout_box(
        doc,
        "步骤 2 · 新手实战看点",
        [
            "15 类规整模板：涵盖可行性研究、资金申请、项目建议书、节能评估等 15 类主流咨询交付物，网格规范大方；",
            "权威业务定位：选中即显示智库专报强调“战略前瞻性研判、行业堵点剖析与对策建言，强调问题导向、底线思维与实操可行性”；",
            "刚性骨架锁定：右侧清晰列出导语/摘要、总体态势、突出矛盾、对策建议、附表 5 个核心章节，从根源杜绝写偏漏项。",
        ]
    )

    # 步骤 3
    add_heading_2(doc, "步骤 3：章节写作 —— 边思索、边查证、自动绘表")
    add_bullet_item(doc, "用户操作：", "点击「一键开始全书写作」或点击特定章节卡片进行流式起草；")
    add_bullet_item(doc, "系统响应：", "自动触发权威外部联网检索，边思考边流式打字，遇到技术或经济指标对比自动排版出标准工程三线表，并在正文实时嵌入权威来源引证角标。")
    add_image_with_caption(
        doc,
        IMAGES_DIR / "step3_writing.png",
        "图 2-3 步骤 3：流式章节写作（标准三线表与精准角标引证）"
    )
    add_callout_box(
        doc,
        "步骤 3 · 新手实战看点",
        [
            "推荐写作顺序指引：左上方清晰标注“第 1 章 → 第 2 章 → 第 3 章 → 第 4 章 → 第 5 章”推荐流水线，章节目录全部显示绿色完成徽标；",
            "规范工程三线表：系统自动将重点算力枢纽集群的 PUE 能效与算力规模排版为“顶线 1.5 磅、底线 1.5 磅、栏目线 0.75 磅”的标准工程三线表；",
            "精准官方引用角标：正文清晰标注权威信息通信智库与行业主管部门指导意见的出处角标，言必有据、拒绝空泛。",
        ]
    )

    # 步骤 4
    add_heading_2(doc, "步骤 4：审阅修改 —— 专家诊断总台账逐项把关")
    add_bullet_item(doc, "用户操作：", "初稿撰写完毕后进入审阅界面，点击右上角「专家诊断报告」；")
    add_bullet_item(doc, "系统响应：", "执行完整性、一致性、合规性与充分性四维体检，左侧章节标注红绿黄状态徽章，右侧滑出全高抽屉展示问题台账与修改建议。")
    add_image_with_caption(
        doc,
        IMAGES_DIR / "step4_review.png",
        "图 2-4 步骤 4：专家审阅与诊断总台账（多维体检与定向修补）"
    )
    add_callout_box(
        doc,
        "步骤 4 · 新手实战看点",
        [
            "问题台账一目了然：专家诊断明确指出“建议增加算力集群直供绿电的度电成本测算对照，可补充附表专项比对”；",
            "定向修复不损上下文：支持“定位正文”瞬间跳转，点击“局部修复”只修改瑕疵段落，绝不破坏报告全篇的逻辑结构与数据上下文。",
        ]
    )

    # 步骤 5
    add_heading_2(doc, "步骤 5：成果导出 —— 综合自洽度 100 分一键交付")
    add_bullet_item(doc, "用户操作：", "进入导出页面，查看自洽度评分，点击「🚀 一键导出 Word 报告 (.docx)」；")
    add_bullet_item(doc, "系统响应：", "复核全篇核心数据指标、引用出处链条与上下游逻辑脉络，自动生成规范参考文献排序清单，瞬时输出排版精良的出版级 Word 初稿。")
    add_image_with_caption(
        doc,
        IMAGES_DIR / "step5_export.png",
        "图 2-5 步骤 5：成果格式化导出与自洽性核验（100分放行交付）"
    )
    add_callout_box(
        doc,
        "步骤 5 · 新手实战看点",
        [
            "绿灯安全放行：自洽性核验明确给出“综合自洽度 100 分，100% 吻合！跨章节核心指标完全吻合、引用链溯源清晰、逻辑闭环”；",
            "规范参考文献：右上角自动列出全书参考文献清单（权威智库白皮书、现行标准规程、专业研究中心）；",
            "开箱即用：导出的 Word 文档涵盖规范封面、自动目录、标准仿宋公文字体、1.5 倍行距与标准三线表，拿来即可向领导与团队汇报研讨。",
        ]
    )

    # ──【第三篇】──
    add_heading_1(doc, "【第三篇】新手日常使用常见疑问（FAQ）")

    add_heading_3(doc, "Q1：智库专报真的不需要上传任何项目材料吗？")
    add_body_paragraph(
        doc,
        "答：是的！投资项目可行性研究通常需要特定的现场勘察或工程图纸，而智库专报聚焦宏观战略前瞻、行业堵点剖析与对策建言。FairyReport 内置了行业通用编制指南，并具备官方权威联网检索能力。在资料留空状态下，系统会自动检索官方发布的最新白皮书与政策文件进行高质量起草。",
    )

    add_heading_3(doc, "Q2：我完全不懂怎么给 AI 写提示词，也能写出这么专业的报告吗？")
    add_body_paragraph(
        doc,
        "答：完全不需要写提示词！所有行业标准大纲、公文写作逻辑、三线表规范与格式约束已经全部固化在平台内部。业务人员只需“选类型、看大纲、点开始”，软件全自动完成专业级的提示工程构建与多源 RAG 智识注水。",
    )

    add_heading_3(doc, "Q3：如果导出的 Word 初稿我还想进一步修改怎么办？")
    add_body_paragraph(
        doc,
        "答：系统导出的就是标准的 .docx 文件，完美兼容微软 Office Word 与 WPS Office。你可以像编辑日常文档一样，随意修改文字、增删段落、微调数据或更换企业专属字体。",
    )

    # 保存文档
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUTPUT_DOCX_DOCS))
    print(f"成功导出文档至: {OUTPUT_DOCX_DOCS}")

    # 同时备份到 dist 目录方便分发
    REPO_ROOT.joinpath("dist").mkdir(parents=True, exist_ok=True)
    doc.save(str(OUTPUT_DOCX_DIST))
    print(f"成功同步文档至: {OUTPUT_DOCX_DIST}")

    size_kb = OUTPUT_DOCX_DOCS.stat().st_size / 1024
    print(f"文档大小: {size_kb:.1f} KB")


if __name__ == "__main__":
    build_beginner_guide_docx()
