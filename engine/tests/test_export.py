"""导出 docx 测试：结构读回/多章顺序/参考文献编号/422/落盘（不联网）。"""
import os

from docx import Document

from engine.app.config import settings


def _read_back(path):
    """用 python-docx 读回 docx，返回 (paragraphs_text, tables, headings, runs)。"""
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
    "这是**加粗内容**和*斜体内容*的正文段落。\n"
)
SAMPLE_TABLE = (
    "\n| 指标 | 数值 |\n|---|---|\n| 产能 | 1000 |\n| 投资 | 5000 |\n"
)
SAMPLE_CH2 = "# 第二章 背景\n## 2.1 建设背景\n项目背景描述。\n"


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
    # 表格
    assert len(tables) == 1
    t = tables[0]
    assert t.cell(0, 0).text == "指标"
    assert t.cell(1, 0).text == "产能"
    # 加粗/斜体 run
    assert any(r[1] is True and "加粗" in r[0] for r in runs)
    assert any(r[2] is True and "斜体" in r[0] for r in runs)


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
    # 第一章在第二章前，第二章在第三章前
    i1 = full.find("第一章")
    i2 = full.find("第二章")
    i3 = full.find("第三章")
    assert 0 <= i1 < i2 < i3


def test_export_refs_numbering_global(client):
    """全局参考文献表：编号全局唯一且与正文标记对应。"""
    ch1 = (
        "# 第一章 概述\n正文【源:policy.md】引用资料。\n\n"
        "---\n\n## 📎 本章参考资料\n\n### 项目资料\n- policy.md\n"
    )
    ch2 = (
        "# 第二章 背景\n正文【源:policy.md】再次引用[Z]。\n\n"
        "---\n\n## 📎 本章参考资料\n\n### 项目资料\n- policy.md\n"
    )
    resp = client.post("/export/docx", json={
        "project": "refs", "title": "带引用报告",
        "chapters": {"1": ch1, "2": ch2}, "include_refs": True,
    })
    assert resp.status_code == 200, resp.text
    paras, tables, headings, titles, runs = _read_back(resp.json()["path"])
    full = "\n".join(paras)
    # 正文标记已编号为 [1]
    assert "[1]" in full
    # 【源:policy.md】已被替换为 [1]（编号后）
    assert "【源:policy.md】" not in full
    # 参考文献表存在且含 policy.md
    assert "参考资料清单" in full
    assert "policy.md" in full
    # [Z] 保留（不参与编号）
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
    # 落在 ENGINE_DATA_DIR/exports/
    exports_dir = os.path.join(settings.engine_data_dir, "exports")
    assert os.path.normpath(os.path.dirname(path)) == os.path.normpath(exports_dir)


def test_export_standard_three_line_table_format(client):
    """验证导出的 Word 表格符合标准三线表规范（加粗顶底线、细栏目线、无竖线与表头加粗底色）。"""
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

    # 验证表头文字与加粗
    header_cell_0 = table.cell(0, 0)
    assert header_cell_0.text == "指标名称"
    assert len(header_cell_0.paragraphs[0].runs) > 0
    assert header_cell_0.paragraphs[0].runs[0].bold is True

    # 验证数据行
    assert table.cell(1, 0).text == "总投资"
    assert table.cell(1, 1).text == "万元"
    assert table.cell(1, 2).text == "5000"

    # 验证 XML 边框包含标准三线表属性 (top sz=12, bottom sz=12, tcBorders sz=6, shading F8FAFC)
    tbl_xml = table._tbl.tblPr.xml
    assert 'w:top w:val="single" w:sz="12"' in tbl_xml
    assert 'w:bottom w:val="single" w:sz="12"' in tbl_xml
    assert 'w:insideH w:val="none"' in tbl_xml
    assert 'w:insideV w:val="none"' in tbl_xml

    # 验证表头单元格底线与浅灰背景
    header_tc_xml = header_cell_0._tc.tcPr.xml
    assert 'w:bottom w:val="single" w:sz="6"' in header_tc_xml
    assert 'w:fill="F8FAFC"' in header_tc_xml

