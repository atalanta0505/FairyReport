"""
生成项目根目录下 pattern/ 文件夹中的 15 种标准报告 Word 模板 (.docx)。

每个模板均具备出版级排版规范：
- 封面页：报告类型标题、副标题（初稿）、留空的编制单位/资质/时间
- 目录页：标准“目    录”标题与点导线制表位，无 updateFields 弹窗警告
- 正文节：独立页眉（带下划线）、居中页脚页码
"""
from datetime import datetime
from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

REPORT_TYPES = [
    "产业发展规划报告",
    "企业发展规划报告",
    "园区发展规划报告",
    "投资机会研究报告",
    "初步可行性研究报告",
    "项目建议书",
    "可行性研究报告",
    "项目申请书(报告)",
    "资金申请报告",
    "社会评价报告",
    "后评价报告",
    "政府和社会资本合作项目特许经营方案",
    "项目评估报告",
    "专题研究报告",
    "智库专报",
]


def _format_run(
    run,
    font_name="Times New Roman",
    east_asia="仿宋",
    font_size=Pt(12),
    bold=False,
    italic=False,
    color=None,
):
    run.font.name = font_name
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:eastAsia"), east_asia)
    run.font.size = font_size
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = color


def _apply_margins(sec):
    sec.top_margin = Inches(1.0)
    sec.bottom_margin = Inches(1.0)
    sec.left_margin = Inches(1.18)
    sec.right_margin = Inches(1.02)


def generate_pattern_template(report_type: str, out_path: Path):
    doc = Document()

    # ── Section 1: 封面 ──
    sec1 = doc.sections[0]
    _apply_margins(sec1)
    sec1.header.is_linked_to_previous = False
    sec1.footer.is_linked_to_previous = False

    # 呼吸留白
    for _ in range(3):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)

    # 报告总标题
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(12)
    p_title.paragraph_format.space_after = Pt(12)
    run_t = p_title.add_run(f"【项目名称】{report_type}")
    _format_run(run_t, font_name="Times New Roman", east_asia="黑体", font_size=Pt(22), bold=True, color=RGBColor(0x0F, 0x17, 0x2A))

    # 副标题
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(8)
    p_sub.paragraph_format.space_after = Pt(16)
    run_sub = p_sub.add_run("（ 初 稿 ）")
    _format_run(run_sub, font_name="Times New Roman", east_asia="黑体", font_size=Pt(14), bold=True, color=RGBColor(0x33, 0x41, 0x55))

    # 中部推移间距
    for _ in range(6):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)

    # 编制机构与资质元数据块（全部留空）
    meta_items = [
        "编制单位：",
        "编制资质：",
        "编制时间：",
    ]
    for item in meta_items:
        p_m = doc.add_paragraph()
        p_m.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_m.paragraph_format.line_spacing = 1.5
        p_m.paragraph_format.space_before = Pt(3)
        p_m.paragraph_format.space_after = Pt(3)
        run_m = p_m.add_run(item)
        _format_run(run_m, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(12), color=RGBColor(0x1E, 0x29, 0x3B))

    # ── Section 2: 目录 ──
    sec2 = doc.add_section(WD_SECTION.NEW_PAGE)
    _apply_margins(sec2)
    sec2.header.is_linked_to_previous = False
    sec2.footer.is_linked_to_previous = False

    p_toc_t = doc.add_paragraph()
    p_toc_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_toc_t.paragraph_format.space_before = Pt(12)
    p_toc_t.paragraph_format.space_after = Pt(18)
    run_toc_t = p_toc_t.add_run("目    录")
    _format_run(run_toc_t, font_name="Times New Roman", east_asia="黑体", font_size=Pt(16), bold=True, color=RGBColor(0x0F, 0x17, 0x2A))

    # 示例目录条目（带点导线）
    sample_entries = [
        (1, "第一章 概述 / 总体态势", 1),
        (2, "1.1 背景与现状", 1),
        (2, "1.2 重大意义与定位", 2),
        (1, "第二章 核心论证 / 矛盾研判", 3),
        (2, "2.1 突出瓶颈与约束分析", 3),
        (2, "2.2 风险评估与成因剖析", 4),
        (1, "第三章 对策建议与政策举措", 5),
        (2, "3.1 体制机制与保障举措", 5),
        (2, "3.2 实施路径与关键抓手", 6),
    ]

    for lvl, title, page in sample_entries:
        p_e = doc.add_paragraph()
        p_e.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_e.paragraph_format.line_spacing = 1.25
        p_e.paragraph_format.left_indent = Pt(0) if lvl == 1 else Pt(14)
        pPr = p_e._p.get_or_add_pPr()
        tabs_xml = r'<w:tabs %s><w:tab w:val="right" w:leader="dot" w:pos="9072"/></w:tabs>' % nsdecls("w")
        pPr.append(parse_xml(tabs_xml))

        r_title = p_e.add_run(title)
        _format_run(r_title, font_name="Times New Roman", east_asia="黑体" if lvl == 1 else "仿宋", font_size=Pt(10.5), bold=(lvl == 1))

        p_e.add_run("\t")
        r_page = p_e.add_run(str(page))
        _format_run(r_page, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(10.5))

    p_tip = doc.add_paragraph()
    p_tip.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tip.paragraph_format.space_before = Pt(12)
    run_tip = p_tip.add_run("（在 Word 中可按 F9 或右键“更新域”同步最新物理页码）")
    _format_run(run_tip, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(9.5), italic=True, color=RGBColor(0x94, 0xA3, 0xB8))

    # ── Section 3: 正文 ──
    sec3 = doc.add_section(WD_SECTION.NEW_PAGE)
    _apply_margins(sec3)
    sec3.header.is_linked_to_previous = False
    sec3.footer.is_linked_to_previous = False

    # 页眉
    hp = sec3.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hrun = hp.add_run(report_type)
    _format_run(hrun, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(9), color=RGBColor(0x64, 0x74, 0x8B))

    # 页脚：居中页码
    fp = sec3.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    frun = fp.add_run()
    _format_run(frun, font_name="Times New Roman", font_size=Pt(9), color=RGBColor(0x64, 0x74, 0x8B))
    fld = parse_xml(r'<w:fldSimple %s w:instr="PAGE"/>' % nsdecls("w"))
    frun._r.append(fld)

    # 正文占位
    p_h1 = doc.add_paragraph()
    p_h1.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_h1.paragraph_format.space_before = Pt(12)
    p_h1.paragraph_format.space_after = Pt(6)
    r_h1 = p_h1.add_run("第一章 概述")
    _format_run(r_h1, font_name="Times New Roman", east_asia="黑体", font_size=Pt(16), bold=True)

    p_body = doc.add_paragraph()
    p_body.paragraph_format.first_line_indent = Pt(24)
    p_body.paragraph_format.line_spacing = 1.35
    r_b = p_body.add_run(f"本报告为标准的【{report_type}】专业交付成果文档模板。正文内容遵循国家相关规程与出版级排版规范，段落采用小四号仿宋字体，严格首行缩进两字符，行距适中、两端对齐。")
    _format_run(r_b, font_name="Times New Roman", east_asia="仿宋", font_size=Pt(12))

    doc.save(str(out_path))


def main():
    root = Path(__file__).resolve().parents[1]
    pdir = root / "pattern"
    pdir.mkdir(parents=True, exist_ok=True)

    print(f"正在向 {pdir} 生成 15 个标准报告 Word 模板...")
    for rt in REPORT_TYPES:
        safe_name = rt.replace("/", "_")
        target_path = pdir / f"{safe_name}.docx"
        generate_pattern_template(rt, target_path)
        print(f"  [OK] Generated template: {safe_name}.docx")
    print("全部 15 个标准模板生成完毕！")


if __name__ == "__main__":
    main()
