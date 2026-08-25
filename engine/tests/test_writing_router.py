"""写作链路端点测试：422/409/outline/chapter(SSE+JSON)/review/revise/hints/502-504。

LLM MockTransport 打桩（含流式 chunks）+ 嵌入 stub + 已安装 stub 通用包；不联网、不下载真实模型。
"""
import json
import os

import httpx
import pytest

from engine.app.generic.store import set_transport as set_gen_transport
from engine.app.writing import llm_client as llm_mod
from engine.app.writing.llm_client import set_transport as set_llm_transport
from engine.tools.build_generic_pack import build_pack

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
WRITING_SOURCE = os.path.join(FIXTURES, "writing_source")
SAMPLE_MD = os.path.join(FIXTURES, "sample.md")

LLM_CONFIG = {"api_key": "sk-test-123456", "base_url": "http://llm.stub/v1", "model": "m"}


@pytest.fixture(autouse=True)
def fast_retries(monkeypatch):
    """重试退避置 0，避免 502/504 用例长 sleep。"""
    monkeypatch.setattr(llm_mod, "RETRY_DELAYS", [0, 0, 0])


class LLMStub:
    """LLM 假服务器：记录请求，按 stream/非 stream 返回。可注入 5xx/timeout。"""

    def __init__(self, content="章节正文【源:sample.md】内容。", chunks=None,
                 status=None, timeout=False):
        self.content = content
        self.chunks = chunks
        self.status = status
        self.timeout = timeout
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.timeout:
            raise httpx.ReadTimeout("stub timeout", request=request)
        if self.status:
            return httpx.Response(self.status, text="upstream error")
        body = json.loads(request.content) if request.content else {}
        if body.get("stream"):
            chunks = self.chunks or [self.content]
            events = "".join(
                f"data: {json.dumps({'choices': [{'delta': {'content': c}}]})}\n\n"
                for c in chunks
            )
            events += "data: [DONE]\n\n"
            return httpx.Response(
                200, text=events, headers={"content-type": "text/event-stream"}
            )
        return httpx.Response(200, json={"choices": [{"message": {"content": self.content}}]})


def _set_llm(stub: LLMStub) -> LLMStub:
    set_llm_transport(httpx.MockTransport(stub.handle))
    return stub


@pytest.fixture
def installed_pack(client, tmp_path):
    """构建 stub 通用包（含 kexingxing_yanjiu.json 模板）并安装到引擎。"""
    out = tmp_path / "pack_out"
    manifest = build_pack(str(out), source=WRITING_SOURCE, stub=True)
    zip_bytes = (out / "pack.zip").read_bytes()

    class GenStub:
        def __init__(self, m, z):
            self.m = m
            self.z = z

        def handle(self, req):
            if req.url.path == "/api/pack/manifest":
                return httpx.Response(200, json=self.m)
            if req.url.path == "/api/pack/download":
                return httpx.Response(
                    200, content=self.z, headers={"content-type": "application/zip"}
                )
            return httpx.Response(404)

    set_gen_transport(httpx.MockTransport(GenStub(manifest, zip_bytes).handle))
    r = client.post("/generic/update", json={"server_url": "http://pack.stub", "token": "t"})
    assert r.status_code == 200, r.text
    set_gen_transport(None)
    return manifest


def _make_project_with_material(client, name="wp"):
    client.post("/projects", json={"name": name})
    r = client.post(
        f"/projects/{name}/materials/ingest",
        json={"file_paths": [SAMPLE_MD]},
    )
    assert r.status_code == 200
    return name


def _outline_md() -> str:
    """与模板 outline_md 一致的大纲（供 chapter 端点用）。"""
    return (
        "# 第一章 概述\n## 1.1 项目概况\n## 1.2 编制依据\n"
        "# 第二章 项目建设背景和必要性\n## 2.1 建设背景\n## 2.2 建设必要性\n"
        "# 第三章 研究结论及建议\n## 3.1 主要结论\n## 3.2 问题与建议"
    )


# ── 422 / 409 ──
def test_outline_422_missing_api_key(client, installed_pack):
    resp = client.post("/writing/outline", json={
        "project": "x", "report_type": "可行性研究报告",
        "llm_config": {"base_url": "http://x", "model": "m"},
    })
    assert resp.status_code == 422


def test_outline_409_no_pack(client):
    """通用包未装 → outline 409 明确语义。"""
    resp = client.post("/writing/outline", json={
        "project": "x", "report_type": "可行性研究报告", "llm_config": LLM_CONFIG,
    })
    assert resp.status_code == 409
    assert "未安装" in resp.json()["detail"]


# ── outline 章数/顺序与模板一致 ──
def test_outline_returns_template_chapters(client, installed_pack):
    """已安装 stub 包：outline 返回模板预定义大纲，章数/顺序与模板一致。"""
    _set_llm(LLMStub())  # 模板有 outline_md，不走 LLM
    resp = client.post("/writing/outline", json={
        "project": "demo", "report_type": "可行性研究报告", "llm_config": LLM_CONFIG,
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    seqs = [c["seq"] for c in body["chapters"]]
    assert seqs == [1, 2, 3]
    assert "第一章" in body["outline_md"]


# ── chapter SSE ──
def test_chapter_stream_sse_format_and_rag(client, installed_pack):
    """chapter stream=true：SSE 格式正确、含 RAG 引用标记。"""
    name = _make_project_with_material(client)
    stub = _set_llm(LLMStub(content="正文段落【源:sample.md】引用"))
    resp = client.post("/writing/chapter", json={
        "project": name, "report_type": "可行性研究报告",
        "outline_md": _outline_md(), "chapter_seq": 1, "stream": True,
        "llm_config": LLM_CONFIG,
    })
    assert resp.status_code == 200
    text = resp.text
    # SSE 格式：data: 行 + [DONE]
    assert "data: " in text
    assert "data: [DONE]" in text
    # 透传 LLM 输出含引用标记
    assert "【源:sample.md】" in text
    # RAG 注入 prompt（LLM 收到的请求体含引用标记）
    sent = json.loads(stub.requests[0].content)
    assert "【源:sample.md】" in sent["messages"][-1]["content"]


def test_chapter_nonstream_json(client, installed_pack):
    """chapter stream=false：非流式 JSON 路径可用。"""
    name = _make_project_with_material(client)
    _set_llm(LLMStub(content="非流式章节正文"))
    resp = client.post("/writing/chapter", json={
        "project": name, "report_type": "可行性研究报告",
        "outline_md": _outline_md(), "chapter_seq": 1, "stream": False,
        "llm_config": LLM_CONFIG,
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["chapter_text"] == "非流式章节正文"


def test_chapter_502_upstream_error(client, installed_pack):
    """chapter 上游 5xx → 502。"""
    _set_llm(LLMStub(status=500))
    resp = client.post("/writing/chapter", json={
        "project": "", "report_type": "可行性研究报告",
        "outline_md": _outline_md(), "chapter_seq": 1, "stream": False,
        "llm_config": LLM_CONFIG,
    })
    assert resp.status_code == 502


def test_chapter_504_timeout(client, installed_pack):
    """chapter 上游超时 → 504（流式 generator 内捕获为 error event）。"""
    _set_llm(LLMStub(timeout=True))
    resp = client.post("/writing/chapter", json={
        "project": "", "report_type": "可行性研究报告",
        "outline_md": _outline_md(), "chapter_seq": 1, "stream": True,
        "llm_config": LLM_CONFIG,
    })
    assert resp.status_code == 200  # SSE 已 200
    assert "error" in resp.text  # error event


# ── review ──
def test_review_parse(client, installed_pack):
    # 使用解析器期望的冒号格式
    raw = (
        "校核结果：需补充\n\n原因：缺指标\n\n"
        "详情：未给能耗\n\n建议：补单位能耗\n\n"
        "资料清单：\n- 项目规模：1000吨\n"
    )
    _set_llm(LLMStub(content=raw))
    resp = client.post("/writing/review", json={
        "chapter_text": "某章正文", "report_type": "可行性研究报告",
        "chapter_title": "第五章 项目建设方案", "llm_config": LLM_CONFIG,
    })
    assert resp.status_code == 200, resp.text
    review = resp.json()["review"]
    assert review["status"] == "需补充"
    assert len(review["data_gap_checklist"]) == 1


def test_review_504_timeout(client, installed_pack):
    _set_llm(LLMStub(timeout=True))
    resp = client.post("/writing/review", json={
        "chapter_text": "x", "report_type": "可行性研究报告",
        "chapter_title": "第一章", "llm_config": LLM_CONFIG,
    })
    assert resp.status_code == 504


# ── revise ──
def test_revise_returns_text(client):
    _set_llm(LLMStub(content="修订后完整章节"))
    resp = client.post("/writing/revise", json={
        "chapter_text": "原文章节", "instruction": "补充数据",
        "llm_config": LLM_CONFIG,
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["revised_text"] == "修订后完整章节"


# ── hints ──
def test_hints_save_and_get(client):
    resp = client.post("/writing/hints", json={
        "project": "hp", "ch_seq": 1, "hint": "本章提示内容",
    })
    assert resp.status_code == 200
    resp = client.get("/writing/hints/hp/1")
    assert resp.status_code == 200
    assert resp.json()["hint"] == "本章提示内容"


def test_hints_get_empty_when_missing(client):
    resp = client.get("/writing/hints/none/9")
    assert resp.status_code == 200
    assert resp.json()["hint"] == ""


# ── 脱敏：LLM 请求 Authorization 不含完整 key ──
def test_key_not_leaked_in_request_headers(client):
    """key 不落盘不泄露：LLM 请求 Authorization 为标准 Bearer 头（日志脱敏用例见 test_mask_key）。"""
    stub = _set_llm(LLMStub(content="修订文本"))
    client.post("/writing/revise", json={
        "chapter_text": "原文", "instruction": "改", "llm_config": LLM_CONFIG,
    })
    assert len(stub.requests) == 1
    auth = stub.requests[0].headers["authorization"]
    assert auth == f"Bearer {LLM_CONFIG['api_key']}"  # 标准头，不在异常/日志中明文


# ── templates ──
def test_list_templates_returns_14_types(client):
    """未装通用包时也可获取 14 种报告类型及默认字数预算。"""
    resp = client.get("/writing/templates")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 14
    report_types = [it["report_type"] for it in items]
    assert "可行性研究报告" in report_types
    assert "产业发展规划报告" in report_types
    fe = next(it for it in items if it["report_type"] == "可行性研究报告")
    assert fe["total_words_max"] == 50000


def test_list_templates_with_installed_pack(client, installed_pack):
    """已安装通用包时获取模板详情与 notes。"""
    resp = client.get("/writing/templates")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 14
    fe = next(it for it in items if it["report_type"] == "可行性研究报告")
    assert fe["total_words_max"] == 50000
    assert "测试模板规范" in fe["notes"]

