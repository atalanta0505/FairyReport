"""针对智库专报大纲生成与写作、Word全报告自动目录、报告标题保真的目标验证测试。"""
import os
import pytest
from docx import Document

from engine.app.writing.outline import OutlineGenerator, _extract_chapter_titles, parse_chapter_seq
from engine.app.writing.writer import ChapterWriter, _extract_chapter_skeleton, normalize_chapter_markdown
from engine.app.export.docx_builder import build_merged_md, md_to_docx


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


def test_zhiku_single_number_heading_separation():
    """验证智库专报中单级数字序号或无标点标题与正文粘连能够被精准拆分。"""
    raw = (
        "## （二）建议维度二（要素保障与技术攻坚）\n\n"
        "2. 建立智算中心全生命周期投资风险防控体系针对智算中心投资强度大、技术迭代快、市场波动剧烈的特点，建议构建覆盖“论证—建设—运营—退出”全生命周期的风险防控体系。\n\n"
        "3. 创新绿色金融工具与投融资期限匹配机制破解智算中心融资期限与项目回报周期错配问题，需要系统性创新绿色金融工具。"
    )
    cleaned = normalize_chapter_markdown(raw)

    assert "2. 建立智算中心全生命周期投资风险防控体系\n\n针对智算中心投资强度大" in cleaned
    assert "3. 创新绿色金融工具与投融资期限匹配机制\n\n破解智算中心融资期限" in cleaned


def test_zhiku_template_word_limits_and_chapters():
    """验证智库专报全篇目标字数预算为 5000 字，各章节配置合理预算，且写作顺序为 5 章。"""
    import json
    import shutil
    from pathlib import Path
    from engine.app.config import settings
    from engine.app.writing import templates_loader as tmpl
    from engine.app.writing.prompts import REPORT_WORD_LIMITS, MAX_WORDS_PER_CHAPTER

    assert REPORT_WORD_LIMITS.get("智库专报") == 5000
    assert REPORT_WORD_LIMITS.get("智库决策专报与建言报告") == 5000
    assert MAX_WORDS_PER_CHAPTER.get("智库专报") == 1500

    # 准备测试环境通用包
    vdir = Path(settings.engine_data_dir) / "generic" / "versions" / "v-test" / "templates"
    vdir.mkdir(parents=True, exist_ok=True)
    src_json = Path(__file__).resolve().parents[2] / "generic_knowledge" / "templates" / "zhiku_juece_zhuanbao.json"
    shutil.copy2(src_json, vdir / "zhiku_juece_zhuanbao.json")

    state_path = Path(settings.engine_data_dir) / "generic" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"version": "v-test"}), encoding="utf-8")

    # 验证模板预算配置
    word_limit = tmpl.get_word_limit("智库专报")
    assert word_limit == 5000, f"智库专报全篇预算应为 5000 字，实际为 {word_limit}"

    assert tmpl.get_chapter_word_budget("智库专报", 1) == 500
    assert tmpl.get_chapter_word_budget("智库专报", 2) == 1000
    assert tmpl.get_chapter_word_budget("智库专报", 3) == 1500
    assert tmpl.get_chapter_word_budget("智库专报", 4) == 1500
    assert tmpl.get_chapter_word_budget("智库专报", 5) == 500

    # 验证写作顺序严格为 5 章（[2, 3, 4, 5, 1]）
    order = tmpl.get_writing_order("智库专报")
    assert order == [2, 3, 4, 5, 1]
    assert len(order) == 5


def test_zhiku_appendix_tables_not_parsed_as_chapters():
    """验证大纲中的二级附表（## 附表1、## 附表2）绝不被提取为第6、第7独立章。"""
    outline_md = (
        "# 导语 / 内容摘要\n\n"
        "# 一、总体态势与基本认识\n\n"
        "## （一）发展现状与阶段性特征（数据量化）\n\n"
        "# 二、面临的突出矛盾与风险研判\n\n"
        "## （一）矛盾一\n\n"
        "# 三、对策建议与政策举措\n\n"
        "## （一）建议一\n\n"
        "# 附件/附表\n\n"
        "## 附表1 核心指标与政策对比表\n\n"
        "## 附表2 调研数据与测算支撑表\n"
    )
    titles = _extract_chapter_titles(outline_md)
    assert len(titles) == 5, f"期望提取 5 章，实际提取 {len(titles)}: {titles}"
    assert 6 not in titles
    assert 7 not in titles


def test_zhiku_resolve_chapter_seq_and_skeleton_injection():
    """验证 ChapterWriter._resolve_chapter_seq 能正确将公文序号章标题解析为对应大纲 seq，
    并成功将本章骨架和最高格式红线注入 prompt。"""
    zhiku_md = (
        "# 导语 / 内容摘要\n\n"
        "（一段话提纲挈领）\n\n"
        "# 一、总体态势与基本认识\n\n"
        "## （一）发展现状与阶段性特征\n\n"
        "## （二）重大战略意义与前瞻定位\n\n"
        "# 二、面临的突出矛盾与风险研判\n\n"
        "## （一）关键要素供给与核心瓶颈制约\n\n"
        "## （二）结构性矛盾凸显与协同机制短板\n\n"
        "## （三）潜在安全风险隐患与合规红线挑战\n\n"
        "# 三、对策建议与政策举措\n\n"
        "## （一）完善顶层制度设计\n\n"
        "# 附件/附表\n\n"
        "## 附表1 核心指标与政策对比表\n"
    )

    # 1. 验证各章节标题反向解析序号
    assert ChapterWriter._resolve_chapter_seq("导语 / 内容摘要", zhiku_md) == 1
    assert ChapterWriter._resolve_chapter_seq("一、总体态势与基本认识", zhiku_md) == 2
    assert ChapterWriter._resolve_chapter_seq("二、面临的突出矛盾与风险研判", zhiku_md) == 3
    assert ChapterWriter._resolve_chapter_seq("三、对策建议与政策举措", zhiku_md) == 4
    assert ChapterWriter._resolve_chapter_seq("附件/附表", zhiku_md) == 5

    # 2. 验证生成 prompt 时骨架被正确注入
    writer = ChapterWriter(llm=None, report_type="智库专报")
    prompt, system = writer._build_chapter_write_args(
        chapter_title="二、面临的突出矛盾与风险研判",
        outline_md=zhiku_md,
        predecessor_chapters={},
        rag_context="",
        topic="专项债券项目",
    )

    assert "## 待填充的本章结构骨架（已锁定）" in prompt
    assert "# 二、面临的突出矛盾与风险研判" in prompt
    assert "## （一）关键要素供给与核心瓶颈制约" in prompt
    assert "【最高格式红线】" in prompt
    assert "本章一级标题「# 二、面临的突出矛盾与风险研判」开头" in prompt


def test_zhiku_merged_export_recovers_missing_h1_and_renders_in_docx(tmp_path):
    """验证当大模型生成的第二章（二、...）与附表章缺失 # 一级标题时，
    build_merged_md 与 md_to_docx 仍能从 outline.json 自动补齐并在 Word 目录及导航大纲中恢复。"""
    import json
    from engine.app.config import settings

    proj_name = "test_zhiku_heal_export"
    pdir = settings.project_dir(proj_name)
    pdir.mkdir(parents=True, exist_ok=True)

    outline_content = (
        "# 导语 / 内容摘要\n\n"
        "# 一、总体态势与基本认识\n\n"
        "## （一）发展现状\n\n"
        "# 二、面临的突出矛盾与风险研判\n\n"
        "## （一）关键要素供给制约\n\n"
        "## （二）结构性矛盾凸显\n\n"
        "# 三、对策建议与政策举措\n\n"
        "## （一）完善顶层设计\n\n"
        "# 附件/附表\n\n"
        "## 附表1 核心指标表\n"
    )
    (pdir / "outline.json").write_text(
        json.dumps({"outline_md": outline_content, "report_type": "智库专报"}, ensure_ascii=False),
        encoding="utf-8",
    )

    # 模拟大模型输出：第3章（二、...）和第5章（附件/附表）均丢失了 # 一级标题，直接以二级标题开头
    chapters = {
        "1": "# 导语 / 内容摘要\n\n导语内容正文分析。",
        "2": "# 一、总体态势与基本认识\n\n## （一）发展现状\n\n发展现状正文。",
        "3": "## （一）关键要素供给制约\n\n要素供给正文。\n\n## （二）结构性矛盾凸显\n\n矛盾正文。",
        "4": "# 三、对策建议与政策举措\n\n## （一）完善顶层设计\n\n建议正文。",
        "5": "## 附表1 核心指标表\n\n表格数据内容。",
    }

    final_md = build_merged_md(chapters, include_refs=False, project=proj_name)

    # 验证合并后的 markdown 必须完整包含所有 5 个一级标题
    assert "# 导语 / 内容摘要" in final_md
    assert "# 一、总体态势与基本认识" in final_md
    assert "# 二、面临的突出矛盾与风险研判" in final_md, "第3章（二、...）一级标题应被自动补齐！"
    assert "# 三、对策建议与政策举措" in final_md
    assert "# 附件/附表" in final_md, "第5章（附件/附表）一级标题应被自动补齐！"

    # 生成 docx 并验证 Word 标题大纲与目录条目
    docx_path = str(tmp_path / "zhiku_healed.docx")
    md_to_docx(
        final_md,
        docx_path,
        title="专项债券专报",
        project=proj_name,
        include_cover=True,
        include_toc=True,
    )

    doc = Document(docx_path)
    h1_paras = [p.text for p in doc.paragraphs if p.style.name == "Heading 1"]

    assert any("导语" in t for t in h1_paras)
    assert any("一、总体态势与基本认识" in t for t in h1_paras)
    assert any("二、面临的突出矛盾与风险研判" in t for t in h1_paras), "Word Heading 1 必须包含二、面临的突出矛盾与风险研判！"
    assert any("三、对策建议与政策举措" in t for t in h1_paras)
    assert any("附件/附表" in t for t in h1_paras), "Word Heading 1 必须包含附件/附表！"


