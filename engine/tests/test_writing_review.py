"""
专家审阅与修改系统测试 — 提示词、结构化解析、审查/修订端点及持久化 CRUD。
"""
import json
import os
import httpx
import pytest
from fastapi.testclient import TestClient

from engine.app.main import app
from engine.app.writing import llm_client as llm_mod
from engine.app.writing.llm_client import LLMClient, set_transport as set_llm_transport
from engine.app.writing.writer import (
    ChapterWriter,
    expert_review_chapter,
    parse_expert_review_result,
    parse_tech_review_result,
)

LLM_CONFIG = {
    "api_key": "sk-test-review-123456",
    "base_url": "http://llm.review.stub/v1",
    "model": "deepseek-chat",
}


@pytest.fixture(autouse=True)
def fast_retries(monkeypatch):
    monkeypatch.setattr(llm_mod, "RETRY_DELAYS", [0, 0, 0])


class ReviewLLMStub:
    def __init__(self, content="", chunks=None, reasoning_chunks=None):
        self.content = content
        self.chunks = chunks
        self.reasoning_chunks = reasoning_chunks
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        body = json.loads(request.content) if request.content else {}
        if body.get("stream"):
            events = ""
            if self.reasoning_chunks:
                for r in self.reasoning_chunks:
                    events += f"data: {json.dumps({'choices': [{'delta': {'reasoning_content': r}}]})}\n\n"
            chunks = self.chunks or [self.content]
            for c in chunks:
                events += f"data: {json.dumps({'choices': [{'delta': {'content': c}}]})}\n\n"
            events += "data: [DONE]\n\n"
            return httpx.Response(
                200, text=events, headers={"content-type": "text/event-stream"}
            )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": self.content}}]},
        )


def _set_stub_llm(content: str, chunks=None, reasoning_chunks=None) -> ReviewLLMStub:
    stub = ReviewLLMStub(content=content, chunks=chunks, reasoning_chunks=reasoning_chunks)
    set_llm_transport(httpx.MockTransport(stub.handle))
    return stub


# ═══════════════════════════════════════════════════════════════
# 1. 结构化解析单元测试 (parse_expert_review_result)
# ═══════════════════════════════════════════════════════════════

def test_parse_expert_review_result_json_codeblock():
    raw = """
以下是专家审查诊断结果：
```json
{
  "status": "通过",
  "score": 92,
  "summary": "本章节工程方案论证详实，合规性要件齐备，数值指标自洽。",
  "issues": [
    {
      "id": "ISSUE-1",
      "severity": "warning",
      "category": "数值计算",
      "message": "第 3.2 节变压器容量计算与总装机负荷存在 5% 偏差",
      "location": "3.2 节",
      "suggestion": "建议统一按 2500kVA 进行复核"
    },
    {
      "id": "ISSUE-2",
      "severity": "suggestion",
      "category": "文字表达",
      "message": "部分段落套话较多",
      "location": "3.1 节首段",
      "suggestion": "删减空泛修饰词"
    }
  ],
  "numerical_checks": [
    {
      "parameter": "总投资",
      "extracted_value": "12,500万元",
      "status": "normal",
      "note": "与估算表一致"
    },
    {
      "parameter": "装机容量",
      "extracted_value": "2000kW",
      "status": "pending",
      "note": "待复核峰值系数"
    }
  ],
  "data_gap_checklist": [
    "需补充电网接入批复文件"
  ],
  "suggestions": "1. 重点复核 3.2 节负荷计算；2. 补充电网批复附件说明。"
}
```
如有疑问请进一步核实。
"""
    parsed = parse_expert_review_result(raw)
    assert parsed["status"] == "通过"
    assert parsed["score"] == 92
    assert "工程方案论证详实" in parsed["summary"]
    assert len(parsed["issues"]) == 2
    assert parsed["issues"][0]["severity"] == "warning"
    assert parsed["issues"][0]["category"] == "数值计算"
    assert len(parsed["numerical_checks"]) == 2
    assert parsed["numerical_checks"][0]["status"] == "normal"
    assert parsed["numerical_checks"][1]["status"] == "pending"
    assert len(parsed["data_gap_checklist"]) == 1
    assert "电网接入批复文件" in parsed["data_gap_checklist"][0]
    assert "重点复核" in parsed["suggestions"]
    assert parsed["parse_error"] is None


def test_parse_expert_review_result_bare_json():
    data = {
        "status": "需补充",
        "score": 75,
        "summary": "缺少投资估算及能耗指标",
        "issues": [
            {
                "id": "ISSUE-1",
                "severity": "error",
                "category": "合规性",
                "message": "未引用 2024 新规程",
                "location": "第一节",
                "suggestion": "更新引用标准为 GB/T 50123-2024",
            }
        ],
        "numerical_checks": [
            {
                "parameter": "年耗水量",
                "extracted_value": "待定",
                "status": "abnormal",
                "note": "缺少基础用水定额",
            }
        ],
        "data_gap_checklist": ["用水定额测算表", "水资源论证报告"],
        "suggestions": "请补充能耗与用水指标分析。",
    }
    raw = json.dumps(data, ensure_ascii=False)
    parsed = parse_expert_review_result(raw)
    assert parsed["status"] == "需补充"
    assert parsed["score"] == 75
    assert len(parsed["issues"]) == 1
    assert parsed["issues"][0]["severity"] == "error"
    assert parsed["numerical_checks"][0]["status"] == "abnormal"
    assert len(parsed["data_gap_checklist"]) == 2


def test_parse_expert_review_result_text_fallback():
    raw_text = """
【校核结果】需补充
【评分】78分
【原因说明】该章节技术方案可行，但缺少工程投资分项计算表及能耗指标依据。
【修改建议】
1. 补充各单项工程造价明细；
2. 依据行业规程核算综合能耗。
【缺失资料清单】
- 投资估算指标底稿
- 当地节能审查意见书
"""
    parsed = parse_expert_review_result(raw_text)
    assert parsed["status"] == "需补充"
    assert parsed["score"] == 78
    assert "缺少工程投资分项计算表" in parsed["summary"]
    assert "补充各单项工程造价明细" in parsed["suggestions"]
    assert len(parsed["data_gap_checklist"]) == 2
    assert "投资估算指标底稿" in parsed["data_gap_checklist"][0]


def test_parse_expert_review_result_empty():
    parsed = parse_expert_review_result("")
    assert parsed["status"] == "需补充"
    assert parsed["score"] == 0
    assert parsed["parse_error"] is not None


def test_parse_expert_review_result_status_clamping():
    raw = json.dumps({
        "status": "存在重大合规风险不通过",
        "score": 150,  # 超出 100
        "summary": "严重违规",
    })
    parsed = parse_expert_review_result(raw)
    assert parsed["status"] == "风险警告"
    assert parsed["score"] == 100


# ═══════════════════════════════════════════════════════════════
# 2. ChapterWriter 与 expert_review 单元测试
# ═══════════════════════════════════════════════════════════════

def test_chapter_writer_expert_review_modes():
    sample_json = json.dumps({
        "status": "通过",
        "score": 90,
        "summary": "审查通过",
        "issues": [],
        "numerical_checks": [],
        "data_gap_checklist": [],
        "suggestions": "可直接使用",
    })
    _set_stub_llm(sample_json)

    llm = LLMClient(LLM_CONFIG)
    writer = ChapterWriter(llm, report_type="可行性研究报告")

    # mode="fast" (默认或显式常规审查)
    raw_fast, res_fast = writer.expert_review("第三章 建设方案", "# 第三章 建设方案\n正文内容...", mode="fast")
    assert res_fast["status"] == "通过"
    assert res_fast["score"] == 90

    # mode="all"
    raw_all, res_all = writer.expert_review("第三章 建设方案", "# 第三章 建设方案\n正文内容...", mode="all")
    assert res_all["status"] == "通过"
    assert res_all["score"] == 90

    # mode="compliance"
    raw_comp, res_comp = writer.expert_review("第二章 政策合规", "# 第二章 政策合规\n正文内容...", mode="compliance")
    assert res_comp["status"] == "通过"

    # mode="numeric"
    raw_num, res_num = writer.expert_review("第七章 投资估算", "# 第七章 投资估算\n投资共 1 亿元...", mode="numeric")
    assert res_num["status"] == "通过"

    # helper function
    raw_h, res_h = expert_review_chapter("第一章 概述", "正文...", report_type="可行性研究报告", review_mode="fast", llm=llm)
    assert res_h["status"] == "通过"


def test_chapter_writer_build_expert_review_args_modes():
    from engine.app.writing.prompts import (
        FAST_REVIEW_SYSTEM_PROMPT,
        FULL_EXPERT_REVIEW_SYSTEM_PROMPT,
        COMPLIANCE_REVIEW_SYSTEM_PROMPT,
        NUMERICAL_REVIEW_SYSTEM_PROMPT,
    )
    llm = LLMClient(LLM_CONFIG)
    writer = ChapterWriter(llm, report_type="可行性研究报告")

    prompt_fast, sys_fast = writer._build_expert_review_args("第一章", "正文", mode="fast")
    assert sys_fast == FAST_REVIEW_SYSTEM_PROMPT
    assert "100% 使用纯中文" in sys_fast
    assert "极速常规审查约束" in sys_fast
    assert "300~500 字符" in sys_fast
    assert "【思考链语言与长度约束】" in prompt_fast

    _, sys_all = writer._build_expert_review_args("第一章", "正文", mode="all")
    assert sys_all == FULL_EXPERT_REVIEW_SYSTEM_PROMPT
    assert "100% 使用纯中文" in sys_all

    _, sys_comp = writer._build_expert_review_args("第一章", "正文", mode="compliance")
    assert sys_comp == COMPLIANCE_REVIEW_SYSTEM_PROMPT

    _, sys_num = writer._build_expert_review_args("第一章", "正文", mode="numeric")
    assert sys_num == NUMERICAL_REVIEW_SYSTEM_PROMPT


def test_chapter_writer_modify_chapter():
    _set_stub_llm("# 第三章 建设方案\n修改后的详细正文内容，已补充 2025 年新规范。")
    llm = LLMClient(LLM_CONFIG)
    writer = ChapterWriter(llm, report_type="可行性研究报告")

    revised = writer.modify_chapter(
        original_content="# 第三章 建设方案\n原文内容...",
        instruction="请补充 2025 年新规范的合规论述",
        chapter_budget=3000,
        chapter_title="第三章 建设方案",
    )
    assert "修改后的详细正文内容" in revised
    assert "2025 年新规范" in revised


# ═══════════════════════════════════════════════════════════════
# 3. HTTP 接口端点测试
# ═══════════════════════════════════════════════════════════════

def test_api_review_and_revise_endpoints():
    sample_response = json.dumps({
        "status": "通过",
        "score": 95,
        "summary": "合规与技术均达标",
        "issues": [],
        "numerical_checks": [
            {"parameter": "装机", "extracted_value": "50MW", "status": "normal", "note": "符合规划"}
        ],
        "data_gap_checklist": [],
        "suggestions": "无须修改",
    })
    _set_stub_llm(sample_response)

    client = TestClient(app)

    # 1. POST /writing/review with mode="fast"
    resp = client.post("/writing/review", json={
        "chapter_text": "# 第四章 技术方案\n技术参数详细内容...",
        "chapter_title": "第四章 技术方案",
        "report_type": "可行性研究报告",
        "mode": "fast",
        "llm_config": LLM_CONFIG,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "raw" in data
    assert data["review"]["status"] == "通过"
    assert data["review"]["score"] == 95
    assert len(data["review"]["numerical_checks"]) == 1

    # 2. POST /writing/revise
    _set_stub_llm("# 第四章 技术方案\n经 AI 修订后的正文。")
    resp_rev = client.post("/writing/revise", json={
        "chapter_text": "# 第四章 技术方案\n原文...",
        "instruction": "请精炼表达",
        "chapter_title": "第四章 技术方案",
        "report_type": "可行性研究报告",
        "chapter_budget": 2500,
        "llm_config": LLM_CONFIG,
    })
    assert resp_rev.status_code == 200, resp_rev.text
    assert "经 AI 修订后的正文" in resp_rev.json()["revised_text"]


def test_api_review_stream():
    sample_review = {
        "status": "通过",
        "score": 96,
        "summary": "常规审查合格",
        "issues": [],
        "numerical_checks": [],
        "data_gap_checklist": [],
        "suggestions": "无",
    }
    raw_json = json.dumps(sample_review, ensure_ascii=False)
    _set_stub_llm(
        content=raw_json,
        chunks=[raw_json[:20], raw_json[20:]],
        reasoning_chunks=["思考：正在核对发改委规程与数值自洽...", "核对完成。"],
    )

    client = TestClient(app)
    resp = client.post("/writing/review_stream", json={
        "chapter_text": "# 第一章 概述\n项目建设内容...",
        "chapter_title": "第一章 概述",
        "report_type": "可行性研究报告",
        "mode": "fast",
        "llm_config": LLM_CONFIG,
    })
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = []
    for line in resp.text.split("\n\n"):
        line = line.strip()
        if line.startswith("data: "):
            val = line[6:]
            if val == "[DONE]":
                events.append({"done": True})
            else:
                events.append(json.loads(val))

    assert any(e.get("type") == "stage" and "常规快速体检" in e.get("message", "") for e in events)
    assert any(e.get("type") == "thought" and "思考" in e.get("chunk", "") for e in events)
    assert any(e.get("type") == "chunk" for e in events)
    done_ev = [e for e in events if e.get("type") == "done"]
    assert len(done_ev) == 1
    assert done_ev[0]["review"]["status"] == "通过"
    assert done_ev[0]["review"]["score"] == 96


def test_api_project_reviews_persistence(tmp_path, monkeypatch):
    client = TestClient(app)
    proj_name = "test_review_persist_proj"

    # 创建项目
    client.post("/projects", json={"name": proj_name})

    # 1. 初始 GET -> 空
    r1 = client.get(f"/projects/{proj_name}/reviews")
    assert r1.status_code == 200
    assert r1.json()["reviews"] == {}

    # 2. POST 保存第 1 章审阅结果
    rev1 = {
        "status": "通过",
        "score": 88,
        "summary": "第一章通过",
        "issues": [{"id": "I1", "severity": "suggestion", "category": "格式", "message": "排版优化", "location": "1.1", "suggestion": "空行"}],
        "numerical_checks": [],
        "data_gap_checklist": [],
        "suggestions": "建议微调",
    }
    r2 = client.post(f"/projects/{proj_name}/reviews/1", json={"review": rev1})
    assert r2.status_code == 200
    assert "1" in r2.json()["reviews"]
    assert r2.json()["reviews"]["1"]["score"] == 88

    # 3. POST 保存第 2 章审阅结果
    rev2 = {
        "status": "需补充",
        "score": 70,
        "summary": "第二章需补充",
        "issues": [],
        "numerical_checks": [],
        "data_gap_checklist": ["底稿 A"],
        "suggestions": "补充底稿",
    }
    r3 = client.post(f"/projects/{proj_name}/reviews/2", json={"review": rev2})
    assert r3.status_code == 200
    assert len(r3.json()["reviews"]) == 2

    # 4. GET 检查
    r4 = client.get(f"/projects/{proj_name}/reviews")
    assert r4.status_code == 200
    assert r4.json()["reviews"]["1"]["status"] == "通过"
    assert r4.json()["reviews"]["2"]["status"] == "需补充"

    # 5. DELETE 第 1 章审阅
    r5 = client.delete(f"/projects/{proj_name}/reviews/1")
    assert r5.status_code == 200

    # 6. GET 再次检查
    r6 = client.get(f"/projects/{proj_name}/reviews")
    assert "1" not in r6.json()["reviews"]
    assert "2" in r6.json()["reviews"]

    # 清理项目
    client.delete(f"/projects/{proj_name}")


def test_api_project_full_review_persistence():
    client = TestClient(app)
    proj_name = "test_full_review_persist_proj"

    # 创建项目
    client.post("/projects", json={"name": proj_name})

    # 1. 初始 GET -> 默认空数据
    r1 = client.get(f"/projects/{proj_name}/full_review")
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["health_status"] == "达标"
    assert d1["compliance_rate"] == 100
    assert d1["issues"] == []

    # 2. POST 保存全书审阅档案
    full_data = {
        "summary": "全书整体质量良好，但有 2 处跨章数据需要复核",
        "compliance_rate": 92,
        "health_status": "待完善",
        "issues": [
            {
                "id": "F-ISSUE-1",
                "severity": "warning",
                "category": "跨章数据自洽",
                "message": "第 2 章投资 1.2 亿与第 7 章 1.35 亿不一致",
                "location": "第 2 章 / 第 7 章",
                "suggestion": "统一采用第 7 章最终审定估算值",
            }
        ],
        "numerical_checks": [
            {
                "parameter": "项目总投资",
                "extracted_value": "13,500万元",
                "status": "normal",
                "note": "经复核一致",
            }
        ],
        "data_gap_checklist": ["节能评估报告批复"],
        "chapter_evaluations": {
            "1": {"status": "通过", "summary": "概述合格", "issues_count": 0, "score": 95},
            "2": {"status": "需补充", "summary": "需对齐投资", "issues_count": 1, "score": 80},
        },
        "general_suggestions": ["1. 统一各章投资数据；2. 补充附表。"],
    }
    r2 = client.post(f"/projects/{proj_name}/full_review", json=full_data)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["health_status"] == "待完善"
    assert d2["compliance_rate"] == 92
    assert len(d2["issues"]) == 1
    assert len(d2["chapter_evaluations"]) == 2
    assert d2["updated_at"] != ""

    # 3. GET 读取验证
    r3 = client.get(f"/projects/{proj_name}/full_review")
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["summary"] == "全书整体质量良好，但有 2 处跨章数据需要复核"
    assert d3["issues"][0]["id"] == "F-ISSUE-1"

    # 4. DELETE 删除
    r4 = client.delete(f"/projects/{proj_name}/full_review")
    assert r4.status_code == 200
    assert r4.json()["ok"] is True

    # 5. 删除后再次 GET -> 恢复默认
    r5 = client.get(f"/projects/{proj_name}/full_review")
    assert r5.status_code == 200
    assert r5.json()["summary"] == ""
    assert r5.json()["issues"] == []

    # 清理项目
    client.delete(f"/projects/{proj_name}")

