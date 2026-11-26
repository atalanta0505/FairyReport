"""
FairyReport MCP Server 单元与集成测试。

覆盖核心零 API Key 工具链：
1. list_report_templates — 15 类内置模板与推荐写作顺序
2. get_report_blueprint — 指定报告类型的大纲骨架、字数配额与写作规范
3. ingest_project_materials & retrieve_report_evidence — 本地底稿入库与【源:...】引用检索
4. verify_report_consistency — 跨章节工程经济指标冲突检出（亿元 vs 万元等）与自洽通过验证
5. export_consulting_docx — 出版级 Word (.docx) 导出、三线表与参考文献自动编号落盘
6. consulting_report_workflow — 标准五步 SOP Prompt 模板
"""
from __future__ import annotations

import os
from pathlib import Path

from docx import Document

from engine.mcp_server import (
    consulting_report_workflow,
    draft_chapter_with_engine,
    export_consulting_docx,
    get_report_blueprint,
    ingest_project_materials,
    list_report_templates,
    mcp,
    retrieve_report_evidence,
    verify_report_consistency,
)


def test_list_report_templates_returns_all_15_types():
    res = list_report_templates()
    assert res["total_templates"] == 15
    names = [t["report_type"] for t in res["templates"]]
    assert "可行性研究报告" in names
    assert "资金申请报告" in names
    assert "智库专报" in names
    for item in res["templates"]:
        assert item["chapter_count"] > 0
        assert item["total_words_max"] > 0
        assert isinstance(item["recommended_writing_order"], list)


def test_get_report_blueprint_success_and_unknown_type():
    bp = get_report_blueprint("可行性研究报告")
    assert bp["status"] == "ok"
    assert bp["report_type"] == "可行性研究报告"
    assert bp["total_words_max"] == 50000
    assert "# 第一章" in bp["outline_md"]
    assert len(bp["chapters"]) >= 7
    assert "三线表" in bp["writing_specification_prompt"]

    bad = get_report_blueprint("不存在的报告类型")
    assert bad["status"] == "error"
    assert "可行性研究报告" in bad["supported_report_types"]


def test_ingest_and_retrieve_local_material_evidence(tmp_path: Path):
    sample_doc = tmp_path / "算力中心立项批复底稿.md"
    sample_doc.write_text(
        "# 长三角生态绿色算力中心项目批复底稿\n\n"
        "本项目规划建设智能算力规模 42.0 EFLOPS，项目估算总投资为 125000 万元，"
        "规划建设用地面积为 120 亩，平均设计 PUE 指标控制在 1.18 以内，建设工期为 24 个月。\n",
        encoding="utf-8",
    )

    project_name = "test_mcp_project_rag"
    ingest_res = ingest_project_materials(
        project=project_name,
        file_paths=[str(sample_doc)],
    )
    assert ingest_res["status"] == "ok"
    assert ingest_res["ingested_files"] == 1
    assert ingest_res["total_vector_chunks"] >= 1

    rag_res = retrieve_report_evidence(
        query="智能算力规模 总投资 PUE 指标",
        project=project_name,
        chapter_title="第一章 概述",
        report_type="可行性研究报告",
        include_generic=False,
        include_web=False,
    )
    assert "【源:算力中心立项批复底稿.md】" in rag_res["evidence_context"]
    assert "125000" in rag_res["evidence_context"] or "42.0" in rag_res["evidence_context"]


def test_verify_report_consistency_detects_cross_chapter_conflict():
    # 第 1 章写总投资 1.2 亿元（=12000 万元），第 7 章写总投资 10500 万元 → 应检出跨章节指标冲突
    conflicting_chapters = {
        "1": (
            "# 第一章 项目概述\n\n"
            "## 1.1 建设规模与投资\n\n"
            "本项目估算总投资为 1.2 亿元，规划用地面积 100 亩，建设工期 24 个月【源:算力中心立项批复底稿.md】。\n"
        ),
        "7": (
            "# 第七章 投资估算与资金筹措\n\n"
            "## 7.1 投资估算结果\n\n"
            "经详细测算，本项目总投资为 10500 万元，建设工期 2 年【源:算力中心立项批复底稿.md】。\n"
        ),
    }
    res_conflict = verify_report_consistency(
        chapters=conflicting_chapters,
        project="test_mcp_project_rag",
        report_type="可行性研究报告",
    )
    assert res_conflict["conflicts_count"] >= 1
    assert res_conflict["is_consistent"] is False
    assert res_conflict["score"] < 100

    # 修正第 7 章总投资为 12000 万元（与第 1 章 1.2 亿元完全相等，且 24 个月 == 2 年）→ 指标零冲突
    consistent_chapters = {
        "1": conflicting_chapters["1"],
        "7": (
            "# 第七章 投资估算与资金筹措\n\n"
            "## 7.1 投资估算结果\n\n"
            "经详细测算，本项目总投资为 12000 万元，规划用地面积 100 亩，建设工期 2 年【源:算力中心立项批复底稿.md】。\n"
        ),
    }
    res_ok = verify_report_consistency(
        chapters=consistent_chapters,
        project="test_mcp_project_rag",
        report_type="可行性研究报告",
    )
    assert res_ok["conflicts_count"] == 0
    assert res_ok["is_consistent"] is True


def test_export_consulting_docx_creates_valid_word_document(tmp_path: Path):
    out_docx = tmp_path / "导出测试可研报告.docx"
    chapters = {
        "1": (
            "# 第一章 项目概述\n\n"
            "## 1.1 项目背景与建设必要性\n\n"
            "近年来，智能算力枢纽建设加快推进，项目总投资为 12000 万元【标:GB 50174 数据中心设计规范】。\n\n"
            "| 指标名称 | 数值 | 单位 |\n"
            "| :--- | :---: | ---: |\n"
            "| 项目总投资 | 12000 | 万元 |\n"
            "| 设计 PUE | 1.18 | - |\n"
        ),
        "2": (
            "# 第二章 需求分析与建设规模\n\n"
            "## 2.1 算力市场需求预测\n\n"
            "区域智能算力需求年均增长率超过 40%，项目总投资 1.2 亿元配置合理【标:GB 50174 数据中心设计规范】。\n"
        ),
    }
    res = export_consulting_docx(
        chapters=chapters,
        title="长三角智能算力中心项目可行性研究报告",
        project="test_mcp_export",
        report_type="可行性研究报告",
        author_org="智算工程咨询研究院",
        output_path=str(out_docx),
    )
    assert res["status"] == "ok"
    assert os.path.isfile(res["path"])
    assert res["size_bytes"] > 5000

    doc = Document(res["path"])
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "第一章 项目概述" in full_text
    assert "参考文献" in full_text
    assert len(doc.tables) >= 1


def test_prompt_and_no_key_fallback(monkeypatch):
    prompt_text = consulting_report_workflow(
        report_type="资金申请报告",
        topic="城市地下管网更新改造项目",
        project="pipe_project",
    )
    assert "资金申请报告" in prompt_text
    assert "get_report_blueprint" in prompt_text
    assert "verify_report_consistency" in prompt_text

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    no_key_res = draft_chapter_with_engine(
        report_type="可行性研究报告",
        outline_md="# 第一章 概述",
        chapter_seq=1,
        chapter_title="第一章 概述",
        topic="测试项目",
    )
    assert no_key_res["status"] == "no_engine_api_key"
    assert "retrieve_report_evidence" in no_key_res["message"]


def test_pyproject_bundles_templates_and_patterns():
    """确保 uvx / pip 从仓库安装时，15 类大纲 JSON 与 15 套封面模板均随包打入。"""
    import tomllib
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    find_cfg = data["tool"]["setuptools"]["packages"]["find"]
    assert find_cfg.get("namespaces") is True
    assert "generic_knowledge*" in find_cfg["include"]
    assert "pattern*" in find_cfg["include"]
    pkg_data = data["tool"]["setuptools"]["package-data"].get("*", [])
    assert "*.json" in pkg_data and "*.docx" in pkg_data


def test_ingest_project_materials_supports_directory_scan(tmp_path: Path):
    """支持直接传入整个文件夹路径：自动递归扫描有效文档，跳过 Office ~$ 锁文件与不支持格式。"""
    folder = tmp_path / "项目底稿目录"
    sub = folder / "财务附件"
    sub.mkdir(parents=True)

    (folder / "01_立项批复.md").write_text("项目估算总投资 26000 万元，工期 18 个月。", encoding="utf-8")
    (sub / "02_技术参数.txt").write_text("规划新建智算机柜 2000 架，设计 PUE 1.15。", encoding="utf-8")
    # 干扰项：Office 临时锁文件、隐藏文件与不支持后缀均应被静默跳过
    (folder / "~$01_立项批复.docx").write_text("lock", encoding="utf-8")
    (folder / ".DS_Store").write_text("meta", encoding="utf-8")
    (folder / "logo.png").write_bytes(b"\x89PNG\r\n")

    res = ingest_project_materials(
        project="test_folder_ingest",
        file_paths=[str(folder)],
    )
    assert res["status"] == "ok"
    assert res["ingested_files"] == 2
    assert res["total_files"] == 2
    assert res["total_vector_chunks"] >= 2

    empty_dir = tmp_path / "空文件夹"
    empty_dir.mkdir()
    empty_res = ingest_project_materials(
        project="test_folder_ingest_empty",
        file_paths=[str(empty_dir)],
    )
    assert empty_res["status"] == "error"
    assert empty_res["ingested_files"] == 0
