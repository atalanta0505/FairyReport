"""针对智库专报大纲生成与写作、Word全报告自动目录、报告标题保真的目标验证测试。"""
import os
import pytest
from docx import Document

from engine.app.writing.outline import OutlineGenerator, _extract_chapter_titles, parse_chapter_seq
from engine.app.writing.writer import _extract_chapter_skeleton
from engine.app.export.docx_builder import md_to_docx


def test_zhiku_extract_chapter_titles():
    """验证 _extract_chapter_titles 能正确从智库专报大纲中抽取所有 5 个章节。"""
    zhiku_md = """# 导语 / 内容摘要

一段话提纲挈领。

# 一、总体态势与基本认识

## （一）发展现状与阶段性特征
## （二）重大意义与战略定位

# 二、面临的突出矛盾与风险研判

## （一）矛盾一

# 三、对策建议与政策举措

## （一）建议一

# 附件/附表

## 附表1 核心指标表
"""
    titles = _extract_chapter_titles(zhiku_md)
    assert len(titles) == 5, f"期望提取 5 个章节，实际提取 {len(titles)}: {titles}"
    assert titles[1] == "导语 / 内容摘要"
    assert "一、总体态势与基本认识" in titles[2]
    assert "二、面临的突出矛盾与风险研判" in titles[3]
    assert "三、对策建议与政策举措" in titles[4]
    assert "附件/附表" in titles[5]


def test_zhiku_chapter_skeleton_extraction():
    """验证 _extract_chapter_skeleton 能精确定位智库专报非'第X章'格式的子章节骨架。"""
    zhiku_md = """# 导语 / 内容摘要

一段话提纲挈领。

# 一、总体态势与基本认识

## （一）发展现状与阶段性特征
## （二）重大意义与战略定位

# 二、面临的突出矛盾与风险研判

## （一）矛盾一
"""
    sk1 = _extract_chapter_skeleton(zhiku_md, 1)
    assert "导语" in sk1

    sk2 = _extract_chapter_skeleton(zhiku_md, 2)
    assert "一、总体态势与基本认识" in sk2
    assert "（一）发展现状与阶段性特征" in sk2
    assert "（二）重大意义与战略定位" in sk2
    assert "二、面临的突出矛盾" not in sk2


def test_report_title_fidelity_no_forced_feasibility_suffix(tmp_path):
    """验证导出报告标题严格忠实于用户输入，绝不硬编码强加'可行性研究报告'。"""
    out_path = str(tmp_path / "title_test.docx")
    custom_title = "重点算力枢纽绿色低碳发展建言专报"

    md_to_docx(
        "# 第一章 概述\n\n正文测试内容。",
        out_path,
        title=custom_title,
        project="test_proj",
        include_cover=True,
    )

    doc = Document(out_path)
    # 封面标题段落
    all_text = " ".join(p.text for p in doc.paragraphs)
    header_text = doc.sections[2].header.paragraphs[0].text

    assert custom_title in all_text
    assert "可行性研究报告" not in all_text, f"标题被意外强加了'可行性研究报告': {all_text}"
    assert custom_title in header_text
    assert "可行性研究报告" not in header_text


def test_export_auto_toc_renders_visible_entries_for_all_reports(tmp_path):
    """验证无论哪种类型的报告，导出的 Word 目录页均自动生成可见的条目与点导线。"""
    out_path = str(tmp_path / "toc_test.docx")
    report_md = """# 导语 / 内容摘要

概述内容。

# 一、总体态势与基本认识

## （一）发展现状与阶段性特征

现状分析。

## （二）重大意义与战略定位

战略定位。

# 二、面临的突出矛盾与风险研判

## （一）核心风险分析

风险内容。
"""
    md_to_docx(
        report_md,
        out_path,
        title="智库专报测试",
        include_cover=True,
        include_toc=True,
    )

    doc = Document(out_path)
    assert len(doc.sections) == 3, "期望包含 3 个 Section（封面、目录、正文）"

    # 获取第二节（目录节）中的所有段落
    all_paras = [p.text for p in doc.paragraphs]
    assert any("目    录" in t for t in all_paras)

    # 验证目录中预置了实质性的章节条目
    assert any("导语" in t for t in all_paras), "目录中应自动生成'导语'条目"
    assert any("一、总体态势与基本认识" in t for t in all_paras), "目录中应自动生成一级章条目"
    assert any("（一）发展现状与阶段性特征" in t for t in all_paras), "目录中应自动生成二级节条目"

    # 验证段落中配置了带点导线的制表位
    all_xml = "".join(p._p.xml for p in doc.paragraphs)
    assert 'w:leader="dot"' in all_xml, "目录条目应具备 dot leader 点导线制表位"
