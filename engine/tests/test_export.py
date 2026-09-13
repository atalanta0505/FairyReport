"""导出 docx 测试：出版级排版/页面边距/标题层级/字体与缩进/三线表/参考文献/422/落盘（不联网）。"""
import os
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

from engine.app.config import settings


def _read_back(path):
    """用 python-docx 读回 docx，返回 (paragraphs, tables, headings, title_paras, runs)。"""
    doc = Document(path)
    paras = [p.text for p in doc.paragraphs]
    tables = doc.tables
    headings = [p.text for p in doc.paragraphs if p.style and p.style.name.startswith("Heading")]
    title_paras = [p.text for p in doc.paragraphs if p.style and p.style.name == "Title"]
    runs = []
    for p in doc.paragraphs:
        for r in p.runs:
            runs.append((r.text, r.bold, r.italic))
    return paras, tables, headings, title_paras, runs


SAMPLE_CH1 = (
    "# 第一章 概述\n"
    "## 1.1 项目概况\n"
    "### 1.1.1 建设背景\n"
    "#### 1.1.1.1 政策支持\n"
    "这是**加粗内容**和*斜体内容*的正文段落，具备出版级排版。\n"
    "> 引用提示说明：严格遵守出版级规范。\n"
    "- 第一条清单要点说明\n"
    "1. 第一项有序步骤说明\n"
)
SAMPLE_TABLE = (
    "\n| 指标 | 规划值 | 备注 |\n| :--- | ---: | :---: |\n| 产能 | 1000 | 达产 |\n| 投资 | 5000 | 自筹 |\n"
)
SAMPLE_CH2 = "# 第二章 背景\n## 2.1 建设背景\n项目背景描述正文。\n"


def test_export_basic_structure(client):
    """样例 md（标题层级/加粗/斜体/表格）导出后读回断言结构一致。"""
    ch = SAMPLE_CH1 + SAMPLE_TABLE
    resp = client.post("/export/docx", json={
        "project": "demo", "title": "可行性研究报告",
        "chapters": {"1": ch}, "include_refs": False,
    })
    assert resp.status_code == 200, resp.text
    path = resp.json()["path"]
    assert os.path.exists(path)

    paras, tables, headings, titles, runs = _read_back(path)
    # 标题页/报告标题存在
    assert "可行性研究报告" in titles
    # 标题层级
    assert any("第一章" in h for h in headings)
    assert any("1.1" in h for h in headings)
    assert any("1.1.1" in h for h in headings)
    assert any("1.1.1.1" in h for h in headings)
    # 表格
    assert len(tables) == 1
    t = tables[0]
    assert t.cell(0, 0).text == "指标"
    assert t.cell(1, 0).text == "产能"
    # 加粗/斜体 run
    assert any(r[1] is True and "加粗" in r[0] for r in runs)
    assert any(r[2] is True and "斜体" in r[0] for r in runs)


def test_export_publication_typography_and_margins(client):
    """验证出版级页面边距、正文字体/缩进/行距、各级标题字体及引用与列表格式。"""
    resp = client.post("/export/docx", json={
        "project": "typesetting", "title": "出版级排版测试报告",
        "chapters": {"1": SAMPLE_CH1}, "include_refs": False,
    })
    assert resp.status_code == 200, resp.text
    path = resp.json()["path"]

    doc = Document(path)

    # 1. 验证页面边距 (上 2.54cm = 72pt, 下 2.54cm = 72pt, 左 2.8cm ≈ 79.37pt, 右 2.6cm ≈ 73.7pt)
    section = doc.sections[0]
    assert abs(section.top_margin.pt - 72.0) < 1.0
    assert abs(section.bottom_margin.pt - 72.0) < 1.0
    assert abs(section.left_margin.pt - 79.37) < 1.0
    assert abs(section.right_margin.pt - 73.7) < 1.0

    # 2. 验证正文段落首行缩进与行距
    body_paras = [
        p for p in doc.paragraphs
        if "这是" in p.text and "正文段落" in p.text
    ]
    assert len(body_paras) == 1
    bp = body_paras[0]
    assert bp.paragraph_format.first_line_indent.pt == 24.0  # 严格缩进 2 字符 (24pt)
    assert bp.paragraph_format.line_spacing == 1.35
    assert bp.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY

    # 验证正文字体 (Times New Roman + 仿宋)
    assert bp.runs[0].font.name == "Times New Roman"
    assert bp.runs[0].font.size.pt == 12.0
    rFonts = bp.runs[0]._r.get_or_add_rPr().rFonts
    assert rFonts.get(qn("w:eastAsia")) == "仿宋"

    # 3. 验证标题层级样式
    title_p = [p for p in doc.paragraphs if p.text == "出版级排版测试报告"][0]
    assert title_p.paragraph_format.first_line_indent.pt == 0
    assert title_p.paragraph_format.space_before.pt == 12.0
    assert title_p.paragraph_format.space_after.pt == 12.0
    assert title_p.runs[0].font.size.pt == 22.0  # 二号 22pt
    assert title_p.runs[0]._r.get_or_add_rPr().rFonts.get(qn("w:eastAsia")) == "黑体"

    h1_p = [p for p in doc.paragraphs if "第一章" in p.text][0]
    assert h1_p.paragraph_format.first_line_indent.pt == 0
    assert h1_p.paragraph_format.space_before.pt == 12.0
    assert h1_p.paragraph_format.space_after.pt == 6.0
    assert h1_p.paragraph_format.keep_with_next is True
    assert h1_p.runs[0].font.size.pt == 16.0  # 三号 16pt
    assert h1_p.runs[0]._r.get_or_add_rPr().rFonts.get(qn("w:eastAsia")) == "黑体"

    h2_p = [p for p in doc.paragraphs if "1.1 项目概况" in p.text][0]
    assert h2_p.paragraph_format.first_line_indent.pt == 0
    assert h2_p.paragraph_format.space_before.pt == 6.0
    assert h2_p.paragraph_format.space_after.pt == 3.0
    assert h2_p.paragraph_format.keep_with_next is True
    assert h2_p.runs[0].font.size.pt == 14.0  # 四号 14pt
    assert h2_p.runs[0]._r.get_or_add_rPr().rFonts.get(qn("w:eastAsia")) == "黑体"

    h3_p = [p for p in doc.paragraphs if "1.1.1 建设背景" in p.text][0]
    assert h3_p.paragraph_format.keep_with_next is True
    assert h3_p.runs[0].font.size.pt == 12.0  # 小四 12pt
    assert h3_p.runs[0]._r.get_or_add_rPr().rFonts.get(qn("w:eastAsia")) == "楷体"

    h4_p = [p for p in doc.paragraphs if "1.1.1.1 政策支持" in p.text][0]
    assert h4_p.paragraph_format.keep_with_next is True
    assert h4_p.runs[0].font.size.pt == 12.0  # 小四 12pt
    assert h4_p.runs[0]._r.get_or_add_rPr().rFonts.get(qn("w:eastAsia")) == "仿宋"

    # 4. 验证引用块 (楷体 10.5pt, 左右缩进 2 字符, 淡灰底纹)
    quote_p = [p for p in doc.paragraphs if "引用提示说明" in p.text][0]
    assert quote_p.paragraph_format.left_indent.pt == 24.0
    assert quote_p.paragraph_format.right_indent.pt == 24.0
    assert quote_p.paragraph_format.first_line_indent.pt == 0
    assert quote_p.runs[0].font.size.pt == 10.5
    assert quote_p.runs[0]._r.get_or_add_rPr().rFonts.get(qn("w:eastAsia")) == "楷体"
    quote_xml = quote_p._p.pPr.xml
    assert "w:pBdr" in quote_xml
    assert 'w:fill="F8FAFC"' in quote_xml

    # 5. 验证无序列表与有序列表悬挂缩进
    bullet_p = [p for p in doc.paragraphs if "第一条清单要点" in p.text][0]
    assert bullet_p.paragraph_format.left_indent.pt == 24.0
    assert bullet_p.paragraph_format.first_line_indent.pt == -12.0
    assert "•" in bullet_p.text


def test_export_multi_chapter_order(client):
    """多章按 seq 合并顺序正确。"""
    resp = client.post("/export/docx", json={
        "project": "order", "title": "T",
        "chapters": {"2": SAMPLE_CH2, "1": SAMPLE_CH1, "3": "# 第三章 结论\n结束。"},
        "include_refs": False,
    })
    assert resp.status_code == 200, resp.text
    paras, tables, headings, titles, runs = _read_back(resp.json()["path"])
    full = "\n".join(paras)
    i1 = full.find("第一章")
    i2 = full.find("第二章")
    i3 = full.find("第三章")
    assert 0 <= i1 < i2 < i3


def test_export_refs_numbering_global(client):
    """全局参考文献表：编号全局唯一且生成规范三源附录。"""
    ch1 = (
        "# 第一章 概述\n正文【源:policy.md】引用资料与【标:GB50016】标准。\n\n"
        "---\n\n## 📎 本章参考资料\n\n### 项目资料\n- policy.md\n\n### 规程标准\n- GB50016\n"
    )
    ch2 = (
        "# 第二章 背景\n正文【源:policy.md】再次引用与【网:国家发改委】[Z]。\n\n"
        "---\n\n## 📎 本章参考资料\n\n### 项目资料\n- policy.md\n\n### 网页链接\n- 国家发改委 — https://www.ndrc.gov.cn\n"
    )
    resp = client.post("/export/docx", json={
        "project": "refs", "title": "带引用报告",
        "chapters": {"1": ch1, "2": ch2}, "include_refs": True,
    })
    assert resp.status_code == 200, resp.text
    paras, tables, headings, titles, runs = _read_back(resp.json()["path"])
    full = "\n".join(paras)
    # 正文标记已编号为 [1]、[2]、[3]
    assert "[1]" in full
    assert "[2]" in full
    assert "[3]" in full
    # 原始标签被替换
    assert "【源:policy.md】" not in full
    assert "【标:GB50016】" not in full
    # 规范参考文献附录存在且包含各引用
    assert "参考文献" in full
    assert "GB/T 7714" in full
    assert "policy.md" in full
    assert "GB50016" in full
    assert "https://www.ndrc.gov.cn" in full
    # [Z] 保留
    assert "[Z]" in full


def test_export_422_empty_chapters(client):
    resp = client.post("/export/docx", json={
        "project": "x", "title": "T", "chapters": {}, "include_refs": True,
    })
    assert resp.status_code == 422


def test_export_422_non_string_chapter(client):
    resp = client.post("/export/docx", json={
        "project": "x", "title": "T",
        "chapters": {"1": 12345}, "include_refs": True,
    })
    assert resp.status_code == 422


def test_export_returns_path_and_size(client):
    """产物真实落盘且返回 path 可读、size 一致。"""
    resp = client.post("/export/docx", json={
        "project": "size", "title": "T",
        "chapters": {"1": SAMPLE_CH1}, "include_refs": False,
    })
    assert resp.status_code == 200
    body = resp.json()
    path = body["path"]
    size = body["size_bytes"]
    assert os.path.exists(path)
    assert os.path.getsize(path) == size
    assert size > 0
    exports_dir = os.path.join(settings.engine_data_dir, "exports")
    assert os.path.normpath(os.path.dirname(path)) == os.path.normpath(exports_dir)


def test_export_md_success(client):
    """验证 /export/md 能够正确生成包含学术编号与参考文献章的 .md 文件。"""
    ch1 = "# 第一章 概况\n正文【源:doc1.docx】与【标:GB50016】测试。"
    ch2 = "# 第二章 建设条件\n正文【源:doc1.docx】再次引用与【网:国家生态部】测试。"
    resp = client.post("/export/md", json={
        "project": "md_test",
        "title": "项目可行性研究报告",
        "chapters": {"1": ch1, "2": ch2},
        "include_refs": True,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert os.path.exists(data["path"])
    assert data["path"].endswith(".md")
    assert data["size_bytes"] > 0
    with open(data["path"], "r", encoding="utf-8") as f:
        content = f.read()
    assert "# 项目可行性研究报告" in content
    assert "[1]" in content
    assert "[2]" in content
    assert "[3]" in content
    assert "# 参考文献" in content
    assert "GB/T 7714" in content
def test_export_open_folder(client):
    """验证 /export/open-folder 能够正常返回 exports 目录路径。"""
    resp = client.post("/export/open-folder", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "path" in data
    assert os.path.exists(data["path"])
    assert "exports" in data["path"].lower()


def test_dense_heading_separation():
    """验证多级数字节标题无空格直接粘连正文时的智能拆分能力。"""
    from engine.app.writing.writer import normalize_chapter_markdown
    raw = (
        "2.3.1 宏观层面必要性从宏观层面看，本项目建设是推动皮革工业绿色转型、落实生态文明建设要求的客观需要。\n"
        "2.3.2 中观层面必要性从中观层面看，本项目建设是利辛县完善主导产业链条的现实需要。\n"
        "2.3.3 微观层面必要性从微观层面看，本项目建设具备明确的资源条件。"
    )
    cleaned = normalize_chapter_markdown(raw)
    assert "### 2.3.1 宏观层面必要性\n\n从宏观层面看" in cleaned
    assert "### 2.3.2 中观层面必要性\n\n从中观层面看" in cleaned
    assert "### 2.3.3 微观层面必要性\n\n从微观层面看" in cleaned


def test_export_standard_three_line_table_format(client):
    """验证导出的 Word 表格符合标准三线表规范（加粗顶底线、细栏目线、无竖线、淡灰表头、cantSplit 与 tblHeader）。"""
    md_with_table = (
        "# 第一章 概述\n\n"
        "## 1.1 主要技术经济指标\n\n"
        "| 指标名称 | 单位 | 规划值 | 备注 |\n"
        "| :--- | :---: | ---: | :--- |\n"
        "| 总投资 | 万元 | 5000 | 自筹与银行贷款 |\n"
        "| 建设用地 | 亩 | 120 | 规划许可已办结 |\n"
    )
    resp = client.post("/export/docx", json={
        "project": "three_line_table", "title": "可行性研究报告",
        "chapters": {"1": md_with_table}, "include_refs": False,
    })
    assert resp.status_code == 200
    path = resp.json()["path"]
    assert os.path.exists(path)

    doc = Document(path)
    assert len(doc.tables) == 1
    table = doc.tables[0]
    assert len(table.rows) == 3
    assert len(table.columns) == 4

    # 验证表头文字与加粗、居中
    header_cell_0 = table.cell(0, 0)
    assert header_cell_0.text == "指标名称"
    assert len(header_cell_0.paragraphs[0].runs) > 0
    assert header_cell_0.paragraphs[0].runs[0].bold is True
    assert header_cell_0.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert header_cell_0.paragraphs[0].runs[0]._r.get_or_add_rPr().rFonts.get(qn("w:eastAsia")) == "黑体"

    # 验证数据行
    assert table.cell(1, 0).text == "总投资"
    assert table.cell(1, 1).text == "万元"
    assert table.cell(1, 2).text == "5000"

    # 验证 XML 边框包含标准三线表属性 (top sz=12, bottom sz=12, tcBorders sz=6, shading F1F5F9)
    tbl_xml = table._tbl.tblPr.xml
    assert 'w:top w:val="single" w:sz="12"' in tbl_xml
    assert 'w:bottom w:val="single" w:sz="12"' in tbl_xml
    assert 'w:insideH w:val="none"' in tbl_xml
    assert 'w:insideV w:val="none"' in tbl_xml
    # 验证单元格内边距优化 (6pt top/bottom = 120 dxa, 8pt left/right = 160 dxa)
    assert 'w:tblCellMar' in tbl_xml
    assert 'w:top w:w="120"' in tbl_xml
    assert 'w:left w:w="160"' in tbl_xml

    # 验证表头单元格底线与浅灰背景
    header_tc_xml = header_cell_0._tc.tcPr.xml
    assert 'w:bottom w:val="single" w:sz="6"' in header_tc_xml
    assert 'w:fill="F1F5F9"' in header_tc_xml or 'w:fill="F8FAFC"' in header_tc_xml

    # 验证跨页防断行与表头重复
    assert 'w:cantSplit' in table.rows[0]._tr.trPr.xml
    assert 'w:cantSplit' in table.rows[1]._tr.trPr.xml
    assert 'w:tblHeader' in table.rows[0]._tr.trPr.xml


def test_export_mermaid_flow_chart_to_table(client):
    """验证 Mermaid 流程图在 Word 导出时规范转换为出版级标准三线对照表。"""
    md_with_mermaid = (
        "# 第三章 生产工艺与工程技术方案\n"
        "## 3.1 工艺技术流程\n"
        "本项目采用全自动化水处理净化工序：\n"
        "```mermaid\n"
        "graph TD\n"
        "  A[原水进入] --> B[混凝反应沉淀池]\n"
        "  B --> C{在线水质监测}\n"
        "  C -->|指标达标| D[超滤膜过滤]\n"
        "  C -->|浑浊超标| E[加药二次深化处理]\n"
        "  E --> D\n"
        "  D --> F[(5000m³ 高位清水储罐)]\n"
        "```\n"
        "上述工序严格遵循《给水排水工程通用规范》执行。\n"
    )
    resp = client.post("/export/docx", json={
        "project": "mermaid_export", "title": "水厂扩建工程可行性研究报告",
        "chapters": {"1": md_with_mermaid}, "include_refs": False,
    })
    assert resp.status_code == 200, resp.text
    path = resp.json()["path"]
    assert os.path.exists(path)

    doc = Document(path)
    assert len(doc.tables) >= 1
    table = doc.tables[0]

    # 验证题注存在
    assert any("【表: 工艺/工程流程步骤与拓扑关系对照表】" in p.text for p in doc.paragraphs)

    # 验证表头字段
    headers = [table.cell(0, c).text.strip() for c in range(len(table.columns))]
    assert "工序/环节名称" in headers
    assert "前置/输入工序" in headers
    assert "承接/输出工序" in headers
    assert "流转说明与控制要点" in headers

    # 验证数据行中包含原水、沉淀池、检测、储罐等关键流程
    all_table_text = " ".join(cell.text for row in table.rows for cell in row.cells)
    assert "原水进入" in all_table_text
    assert "混凝反应沉淀池" in all_table_text
    assert "在线水质监测" in all_table_text
    assert "超滤膜过滤" in all_table_text
    assert "5000m³ 高位清水储罐" in all_table_text


def test_docx_glued_heading_decoupling_and_double_period_cleanup(client, tmp_path):
    """V2-T48 验证：导出 docx 自动解耦长粘连节标题，Heading 样式仅含纯标题，根除双句号。"""
    from engine.app.export.docx_builder import _split_heading_and_body, md_to_docx
    from docx import Document

    # 1. 单元函数验证 _split_heading_and_body
    h1, b1 = _split_heading_and_body(
        "3.1.2 市场需求潜力国内皮革制品市场需求总体保持稳定，生态化、高品质皮化材料及成品革的市场潜力较为突出。",
        ["3.1.2 市场需求潜力", "市场需求潜力"],
    )
    assert h1 == "3.1.2 市场需求潜力"
    assert b1.startswith("国内皮革制品市场需求总体保持稳定")

    h2, b2 = _split_heading_and_body(
        "3.2.2 总体布局项目总体布局按照“生产流程顺畅、功能分区明确”的原则进行规划设计。",
        None,
    )
    assert h2 == "3.2.2 总体布局"
    assert b2.startswith("项目总体布局按照")

    # 2. 端到端导出验证
    md_content = (
        "# 第三章 项目需求分析与产出方案\n\n"
        "## 3.1 需求分析\n\n"
        "### 3.1.2 市场需求潜力国内皮革制品市场需求总体保持稳定，生态化、高品质皮化材料及成品革的市场潜力较为突出。我国是世界最大的皮革生产与消费国【源:市场报告.docx】。。年需求量长期保持在较高水平。\n\n"
        "### 3.2.2 总体布局项目总体布局按照“生产流程顺畅、功能分区明确、物料流向合理、环保设施集中”的原则进行规划设计。厂区分为原料皮库区、湿加工车间区等七个功能区。\n"
    )

    out_file = str(tmp_path / "decoupled_test.docx")
    md_to_docx(md_content, out_file, title="生态皮革加工项目可研报告")
    assert os.path.exists(out_file)

    doc = Document(out_file)
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    assert "3.1.2 市场需求潜力" in headings
    assert "3.2.2 总体布局" in headings
    # 验证 Heading 样式中绝不包含粘连的长句正文
    for h in headings:
        assert len(h) < 40, f"Heading 过长污染目录: {h}"
        assert "国内皮革制品" not in h
        assert "原则进行规划设计" not in h

    # 验证全文无双句号
    full_text = " ".join(p.text for p in doc.paragraphs)
    assert "。。" not in full_text
    assert "【源:市场报告.docx】。年需求量" in full_text




