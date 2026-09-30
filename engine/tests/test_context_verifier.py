"""
上下文与自洽性核验模块单元测试 (engine/tests/test_context_verifier.py)
验证：
- 核心技术经济指标正则提取与跨单位换算（亿元/万元、公顷/亩、㎡/万㎡、年/月）
- 跨章节指标一致性判定（数值吻合为 pass，人工修改冲突为 conflict 并准确定位章节）
- 底稿与规范出处溯源核验（空引用告警、有效引用出处链记录）
- 上下游章节呼应与空白章节截击
- 导出路由 POST /export/verify-context 接口与错误处理
"""
import pytest
from fastapi.testclient import TestClient

from engine.app.main import app
from engine.app.writing.context_verifier import (
    extract_indicators_from_chapters,
    verify_indicator_consistency,
    verify_citation_traceability,
    verify_upstream_downstream_coherence,
    run_full_context_verification,
)

client = TestClient(app)


def test_indicator_extraction_and_unit_conversion():
    """测试不同单位（亿元/万元、公顷/亩、年/月、%）的抽取与标准化转换。"""
    chapters = {
        "1": "第一章：本项目总投资为0.5亿元，规划用地面积为10公顷，总建筑面积为120000平方米，建设工期为2年。",
        "3": "第三章：根据方案测算，财务内部收益率为12.5%，达产年营业收入为8000万元。"
    }
    extracted = extract_indicators_from_chapters(chapters)
    
    assert "总投资" in extracted
    assert extracted["总投资"][0]["std_val"] == 5000.0  # 0.5 亿元 = 5000 万元
    assert extracted["总投资"][0]["seq"] == 1

    assert "建设用地" in extracted
    assert extracted["建设用地"][0]["std_val"] == 150.0  # 10 公顷 = 150 亩

    assert "总建筑面积" in extracted
    assert abs(extracted["总建筑面积"][0]["std_val"] - 12.0) < 0.001  # 120000 ㎡ = 12 万㎡

    assert "建设工期" in extracted
    assert extracted["建设工期"][0]["std_val"] == 24.0  # 2 年 = 24 个月

    assert "财务内部收益率" in extracted
    assert extracted["财务内部收益率"][0]["std_val"] == 12.5

    assert "达产年营业收入" in extracted
    assert extracted["达产年营业收入"][0]["std_val"] == 8000.0


def test_indicator_consistency_pass():
    """跨章节指标数值完全吻合时，判定为 pass，无 conflict。"""
    chapters = {
        "1": "第一章总论：经初步测算，工程建设总投资为5000万元，占地面积150亩。",
        "4": "第四章建设规模与用地：本项目规划总用地面积为150亩，布局合理。",
        "6": "第六章投资估算：本项目估算总投资为5000万元，资金来源为企业自筹。"
    }
    extracted = extract_indicators_from_chapters(chapters)
    items = verify_indicator_consistency(indicators=extracted)

    assert len(items) >= 2
    conflicts = [x for x in items if x.status == "conflict"]
    passes = [x for x in items if x.status == "pass"]

    assert len(conflicts) == 0
    assert len(passes) >= 2
    invest_pass = next(x for x in passes if "总投资" in x.title)
    assert 1 in invest_pass.affected_chapters
    assert 6 in invest_pass.affected_chapters


def test_indicator_consistency_conflict_detection():
    """人工修改某一章节后前后数据打架，精准截击 conflict 并圈定责任章节。"""
    chapters = {
        "1": "第一章总论：经汇总估算，项目总投资为5000万元。",
        "3": "第三章方案调整：经深化设计与人工测算，工程建设总投资为6800万元。"
    }
    extracted = extract_indicators_from_chapters(chapters)
    items = verify_indicator_consistency(indicators=extracted)

    conflicts = [x for x in items if x.status == "conflict"]
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.type == "indicator"
    assert c.severity == "critical"
    assert "总投资" in c.title
    assert 1 in c.affected_chapters and 3 in c.affected_chapters
    assert "5000" in c.description and "6800" in c.description
    assert "建议" in c.suggestion


def test_citation_traceability_detection():
    """测试引文标记与溯源：有效标记记录、空标记告警、全书无标记提醒。"""
    # 场景 1：含有正常材料引用、规程引用及空破损标记
    chapters_with_refs = {
        "1": "本章论证依据【源:建设单位可行性研究底稿.docx】，且参考了【标:GB/T 50353-2013】规范。",
        "2": "此处引用存在缺陷【源:】。"
    }
    items = verify_citation_traceability(chapters_with_refs)
    
    # 应该检测出破损空标记
    corrupt_items = [x for x in items if "CIT-ERR" in x.id]
    assert len(corrupt_items) == 1
    assert 2 in corrupt_items[0].affected_chapters

    # 应该识别有效底稿与有效标准
    pass_items = [x for x in items if x.status == "pass"]
    assert any("工程底稿资料出处链清晰" in x.title for x in pass_items)
    assert any("行业规程与技术标准引用合规" in x.title for x in pass_items)

    # 场景 2：完全无引用
    empty_citation_chapters = {
        "1": "这是没有任何引用的纯正文内容。",
        "2": "这也是没有标记的正文。"
    }
    empty_items = verify_citation_traceability(empty_citation_chapters)
    warn_items = [x for x in empty_items if x.status == "warning"]
    assert len(warn_items) == 1
    assert "尚未检测到数据溯源引用标记" in warn_items[0].title


def test_upstream_downstream_and_empty_chapters():
    """测试上下游逻辑：空白章节截击、首尾呼应性检查。"""
    # 空白章节情况
    chapters_with_empty = {
        "1": "第一章总论：本项目切实可行，具备良好的社会与经济效益。",
        "2": "   ",  # 空白章节
        "3": "第三章综合评价：项目建设合理可行，建议尽早实施。"
    }
    items = verify_upstream_downstream_coherence(chapters_with_empty)
    conflicts = [x for x in items if x.status == "conflict"]
    assert len(conflicts) == 1
    assert 2 in conflicts[0].affected_chapters
    assert "空白" in conflicts[0].title

    # 首尾结论呼应 pass
    pass_items = [x for x in items if x.status == "pass"]
    assert any("首尾章节核心论证结论呼应自洽" in x.title for x in pass_items)


def test_full_context_verification_scoring():
    """综合核验自洽度计分测试：无冲突满分、冲突扣分机制。"""
    # 1. 完美自洽样本
    perfect_chapters = {
        "1": "项目总论：总投资为5000万元。经论证切实可行。【源:立项申请书.pdf】",
        "2": "建设规模：占地100亩。【标:GB 50000】",
        "3": "投资估算：总投资为5000万元。研究结论表明切实可行。"
    }
    resp_perfect = run_full_context_verification(perfect_chapters, project="示范工程")
    assert resp_perfect.is_consistent is True
    assert resp_perfect.conflicts_count == 0
    assert resp_perfect.score >= 90
    assert "100%吻合" in resp_perfect.summary

    # 2. 存在重大数值冲突样本
    flawed_chapters = {
        "1": "项目总论：总投资为5000万元。【源:立项批复.docx】",
        "2": "投资章节：经修改，总投资为7500万元。【源:财务测算表.xlsx】"
    }
    resp_flawed = run_full_context_verification(flawed_chapters, project="冲突项目")
    assert resp_flawed.is_consistent is False
    assert resp_flawed.conflicts_count >= 1
    assert resp_flawed.score <= 75
    assert "⚠️" in resp_flawed.summary


def test_verify_context_api():
    """测试 POST /export/verify-context FastAPI 接口。"""
    # 正常请求
    payload = {
        "project": "某现代产业园项目",
        "report_type": "feasi",
        "chapters": {
            "1": "第一章总论：项目总投资为10000万元，切实可行。【源:项目建议书.pdf】",
            "2": "第二章建设规划：用地面积为200亩。【标:城市用地分类标准】",
            "3": "第三章投资估算：总投资为10000万元，切实可行。"
        }
    }
    response = client.post("/export/verify-context", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "is_consistent" in data
    assert "score" in data
    assert "items" in data
    assert data["conflicts_count"] == 0
    ind_item = next(i for i in data["items"] if i["type"] == "indicator" and "总投资" in i["title"])
    assert "table" in ind_item["details"]
    assert len(ind_item["details"]["table"]) == 2
    assert "context" in ind_item["details"]["table"][0]

    # 异常校验：chapters 为空应返回 422
    err_response = client.post("/export/verify-context", json={"project": "测试", "chapters": {}})
    assert err_response.status_code == 422

    # 异常校验：chapters 内容非字符串应返回 422
    err_response2 = client.post("/export/verify-context", json={"project": "测试", "chapters": {"1": 12345}})
    assert err_response2.status_code == 422


def test_indicator_consistency_unit_rounding_real_case():
    """测试跨单位概算舍入场景（如 52060万元 与 5.2亿元 互相呼应）：
    应判定为自洽 pass，不能误报数值矛盾。
    """
    chapters = {
        "1": "第一章总论：经汇总估算，项目总投资约52060万元，切实可行。",
        "5": "第五章投资估算：项目建设总投资约5.2亿元，计52060万元，与前期方案紧密衔接。",
        "6": "第六章资金筹措：项目总投资52060万元，资金来源可靠。",
        "7": "第七章效益评价：项目总投资约52060万元，经济效益良好。"
    }
    extracted = extract_indicators_from_chapters(chapters)
    items = verify_indicator_consistency(indicators=extracted)

    conflicts = [x for x in items if x.status == "conflict"]
    passes = [x for x in items if x.status == "pass"]

    assert len(conflicts) == 0, f"Expected 0 conflicts, got {conflicts}"
    assert len(passes) >= 1
    invest_pass = next(x for x in passes if "总投资" in x.title)
    assert set(invest_pass.affected_chapters) == {1, 5, 6, 7}
    assert "52060万元" in invest_pass.description
    assert "5.2亿元" in invest_pass.description


def test_indicator_conflict_grouping_description():
    """测试真实冲突时，多章节相同数值应归簇展示，避免重复输出相同数值的荒谬文本。"""
    chapters = {
        "1": "第一章：项目总投资为5000万元。",
        "2": "第二章：项目总投资为5000万元。",
        "5": "第五章：经调整，项目总投资为8000万元。"
    }
    extracted = extract_indicators_from_chapters(chapters)
    items = verify_indicator_consistency(indicators=extracted)

    conflicts = [x for x in items if x.status == "conflict"]
    assert len(conflicts) == 1
    c = conflicts[0]
    # 验证聚类展示：第 1 章、第 2 章应合并展示为 5000万元，而不是写两次
    assert "第 1 章、第 2 章提及为 5000万元" in c.description
    assert "第 5 章提及为 8000万元" in c.description
    assert "第 1 章提及为 5000万元，但第 2 章提及为 5000万元" not in c.description
