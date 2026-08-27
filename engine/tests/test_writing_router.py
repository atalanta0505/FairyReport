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
    """chapter stream=true：SSE 格式正确、含阶段指示与 RAG 引用标记。"""
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
    # 包含阶段指示事件
    assert '"stage": "rag"' in text
    assert '"stage": "skeleton"' in text
    assert '"stage": "reasoning"' in text
    # 透传 LLM 输出含引用标记
    assert "【源:sample.md】" in text
    # RAG 注入 prompt（LLM 收到的请求体含引用标记）
    sent = json.loads(stub.requests[0].content)
    assert "【源:sample.md】" in sent["messages"][-1]["content"]


def test_chapter_stream_thought_chunks(client, installed_pack):
    """chapter stream=true：透传思考片段。"""
    name = _make_project_with_material(client)
    stub = _set_llm(LLMStub(chunks=[
        '{"type": "thought", "chunk": "正在推演水文参数"}',
        '正文段落第一节。',
    ]))
    resp = client.post("/writing/chapter", json={
        "project": name, "report_type": "可行性研究报告",
        "outline_md": _outline_md(), "chapter_seq": 1, "stream": True,
        "llm_config": LLM_CONFIG,
    })
    assert resp.status_code == 200
    text = resp.text
    assert '"type": "thought"' in text
    assert "正在推演水文参数" in text
    assert "正文段落第一节。" in text



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


# ── outline 持久化 ──
def test_outline_persistence_get_default_when_missing(client):
    """项目大纲不存在时返回默认结构。"""
    resp = client.get("/projects/nonexistent_proj/outline")
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_type"] == "可行性研究报告"
    assert data["outline_md"] == ""
    assert data["chapters"] == []
    assert data["updated_at"] == ""


def test_outline_persistence_save_and_get(client):
    """保存并读取项目大纲持久化数据。"""
    client.post("/projects", json={"name": "persist_proj"})
    payload = {
        "report_type": "产业发展规划报告",
        "outline_md": "# 第一章 总述\n# 第二章 规划布局",
        "chapters": [
            {"seq": 1, "title": "第一章 总述"},
            {"seq": 2, "title": "第二章 规划布局"},
        ],
        "updated_at": "2026-08-25T12:00:00Z",
    }
    save_resp = client.post("/projects/persist_proj/outline", json=payload)
    assert save_resp.status_code == 200
    saved = save_resp.json()
    assert saved["report_type"] == "产业发展规划报告"
    assert saved["outline_md"] == payload["outline_md"]
    assert len(saved["chapters"]) == 2

    get_resp = client.get("/projects/persist_proj/outline")
    assert get_resp.status_code == 200
    loaded = get_resp.json()
    assert loaded["report_type"] == "产业发展规划报告"
    assert loaded["outline_md"] == payload["outline_md"]
    assert len(loaded["chapters"]) == 2
    assert loaded["chapters"][0]["title"] == "第一章 总述"


def test_outline_auto_save_on_generate(client, installed_pack):
    """调用 /writing/outline 生成大纲时，若包含 project 则自动持久化至项目 outline.json。"""
    client.post("/projects", json={"name": "auto_save_proj"})
    _set_llm(LLMStub())
    gen_resp = client.post("/writing/outline", json={
        "project": "auto_save_proj",
        "report_type": "可行性研究报告",
        "llm_config": LLM_CONFIG,
    })
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()

    # 验证已自动落盘
    get_resp = client.get("/projects/auto_save_proj/outline")
    assert get_resp.status_code == 200
    outline_data = get_resp.json()
    assert outline_data["report_type"] == "可行性研究报告"
    assert outline_data["outline_md"] == gen_data["outline_md"]
    assert len(outline_data["chapters"]) == len(gen_data["chapters"])
    assert outline_data["updated_at"] != ""


# ── chapters 持久化 ──
def test_chapters_persistence_get_default_when_missing(client):
    """项目章节不存在时返回空字典映射。"""
    resp = client.get("/projects/nonexistent_ch_proj/chapters")
    assert resp.status_code == 200
    data = resp.json()
    assert data["chapters"] == {}
    assert data["updated_at"] == ""


def test_chapters_persistence_save_and_get(client):
    """保存章节内容并在 chapters.json 与单个 markdown 文件中落盘。"""
    from engine.app.config import settings
    client.post("/projects", json={"name": "persist_ch_proj"})

    r1 = client.post("/projects/persist_ch_proj/chapters/1", json={"text": "# 第一章 概述\n\n项目总体概述正文。"})
    assert r1.status_code == 200
    assert r1.json()["chapters"]["1"] == "# 第一章 概述\n\n项目总体概述正文。"

    r2 = client.post("/projects/persist_ch_proj/chapters/2", json={"text": "# 第二章 建设背景\n\n建设必要性分析。"})
    assert r2.status_code == 200
    assert r2.json()["chapters"]["2"] == "# 第二章 建设背景\n\n建设必要性分析。"

    # 验证 GET 获取全部章节
    get_resp = client.get("/projects/persist_ch_proj/chapters")
    assert get_resp.status_code == 200
    all_chapters = get_resp.json()
    assert len(all_chapters["chapters"]) == 2
    assert all_chapters["chapters"]["1"] == "# 第一章 概述\n\n项目总体概述正文。"
    assert all_chapters["chapters"]["2"] == "# 第二章 建设背景\n\n建设必要性分析。"

    # 验证 markdown 单文件存在
    ch1_file = settings.project_dir("persist_ch_proj") / "chapters" / "chapter_1.md"
    assert ch1_file.exists()
    assert ch1_file.read_text(encoding="utf-8") == "# 第一章 概述\n\n项目总体概述正文。"


def test_chapters_persistence_delete(client):
    """删除单章内容，同时更新 chapters.json 并删除 markdown 文件。"""
    from engine.app.config import settings
    client.post("/projects", json={"name": "del_ch_proj"})

    client.post("/projects/del_ch_proj/chapters/1", json={"text": "章1"})
    client.post("/projects/del_ch_proj/chapters/2", json={"text": "章2"})

    del_resp = client.delete("/projects/del_ch_proj/chapters/1")
    assert del_resp.status_code == 200
    assert del_resp.json()["ok"] is True
    assert del_resp.json()["seq"] == 1

    get_resp = client.get("/projects/del_ch_proj/chapters")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "1" not in data["chapters"]
    assert data["chapters"]["2"] == "章2"

    ch1_file = settings.project_dir("del_ch_proj") / "chapters" / "chapter_1.md"
    assert not ch1_file.exists()


def test_markdown_formatting_rules_in_prompts():
    """验证章节写作与修改的系统提示词中包含标题独占行与表格标准换行强约束。"""
    from engine.app.writing.prompts import _MODIFY_SYSTEM_PROMPT
    from engine.app.writing.writer import ChapterWriter, _build_writing_system_prompt

    # 1. 验证 _build_writing_system_prompt 包含 Markdown 格式规则
    system_prompt = _build_writing_system_prompt(
        report_type="可行性研究报告",
        chapter_budget=3000,
        chapter_title="第1章 概述",
        topic="水利枢纽",
    )
    assert "Markdown 格式规范" in system_prompt
    assert "严禁标题与正文连在同一行" in system_prompt
    assert "严禁使用 || 连写在同一行" in system_prompt

    # 2. 验证 _MODIFY_SYSTEM_PROMPT 包含 Markdown 格式规则
    mod_prompt = _MODIFY_SYSTEM_PROMPT.format(word_constraint="保持约1000字")
    assert "严禁标题与正文连在同一行" in mod_prompt
    assert "严禁使用 || 连写在同一行" in mod_prompt

    # 3. 验证 _build_chapter_write_args 的 user prompt 包含格式要求
    class FakeLLM:
        pass

    writer = ChapterWriter(FakeLLM(), report_type="可行性研究报告")
    prompt, sys = writer._build_chapter_write_args(
        chapter_title="第1章 概述",
        outline_md="# 第1章 概述\n## 1.1 项目概况\n### 1.1.1 建设地点",
        predecessor_chapters={},
        rag_context="",
        topic="水利枢纽",
    )
    assert "格式规范（极重要）" in prompt
    assert "严禁使用 || 连写在同一行" in prompt


def test_extract_chapter_skeleton():
    """验证 _extract_chapter_skeleton 多层级提取、描述性内容剔除与跨章截断。"""
    from engine.app.writing.writer import _extract_chapter_skeleton

    outline = """# 第一章 概述
本章概述项目的基本建设背景与范围。
## 1.1 项目概况
- 重点关注选址与规模
### 1.1.1 建设地点与用地
#### 1.1.1.1 地理坐标与四至范围
#### 1.1.1.2 土地利用性质
### 1.1.2 建设规模与内容
## 1.2 编制依据
一些说明文字

# 第二章 项目建设背景和必要性
## 2.1 建设背景
### 2.1.1 宏观政策背景
## 2.2 建设必要性

# 第三章 研究结论及建议
## 3.1 主要结论
"""

    # 1. 提取第1章：包含 H1, H2, H3, H4 标题，剔除说明文字与列表项，在第2章前截断
    sk1 = _extract_chapter_skeleton(outline, 1)
    expected_sk1 = "\n".join([
        "# 第一章 概述",
        "## 1.1 项目概况",
        "### 1.1.1 建设地点与用地",
        "#### 1.1.1.1 地理坐标与四至范围",
        "#### 1.1.1.2 土地利用性质",
        "### 1.1.2 建设规模与内容",
        "## 1.2 编制依据",
    ])
    assert sk1 == expected_sk1
    assert "本章概述项目的基本建设背景与范围" not in sk1
    assert "第二章" not in sk1

    # 2. 提取第2章：只含第2章的骨架
    sk2 = _extract_chapter_skeleton(outline, 2)
    expected_sk2 = "\n".join([
        "# 第二章 项目建设背景和必要性",
        "## 2.1 建设背景",
        "### 2.1.1 宏观政策背景",
        "## 2.2 建设必要性",
    ])
    assert sk2 == expected_sk2
    assert "第一章" not in sk2
    assert "第三章" not in sk2

    # 3. 提取第3章（尾章）：在末尾正常结束
    sk3 = _extract_chapter_skeleton(outline, 3)
    expected_sk3 = "\n".join([
        "# 第三章 研究结论及建议",
        "## 3.1 主要结论",
    ])
    assert sk3 == expected_sk3

    # 4. 提取不存在的章节
    assert _extract_chapter_skeleton(outline, 99) == ""
    assert _extract_chapter_skeleton(outline, 0) == ""
    assert _extract_chapter_skeleton("", 1) == ""


def test_build_chapter_write_args_skeleton_infilling():
    """验证 _build_chapter_write_args 正确提取并注入结构骨架，且包含骨架靶向填空指令。"""
    from engine.app.writing.writer import ChapterWriter

    class FakeLLM:
        pass

    writer = ChapterWriter(FakeLLM(), report_type="可行性研究报告")
    outline = (
        "# 第一章 概述\n"
        "## 1.1 项目概况\n"
        "### 1.1.1 建设地点\n"
        "#### 1.1.1.1 四至范围\n"
        "## 1.2 编制依据\n"
        "# 第二章 建设背景\n"
        "## 2.1 政策背景\n"
    )

    prompt, system = writer._build_chapter_write_args(
        chapter_title="第一章 概述",
        outline_md=outline,
        predecessor_chapters={},
        rag_context="【源:data.docx】项目总投资5000万元",
        topic="水利枢纽",
        report_name="某水库工程",
        chapter_budget=4000,
    )

    # 验证结构骨架块正确注入
    assert "## 待填充的本章结构骨架（已锁定）" in prompt
    assert "# 第一章 概述\n## 1.1 项目概况\n### 1.1.1 建设地点\n#### 1.1.1.1 四至范围\n## 1.2 编制依据" in prompt
    assert "第二章" not in prompt.split("## 待填充的本章结构骨架（已锁定）")[1].split("## 前文已完成章节")[0]

    # 验证骨架靶向填充写作要求
    assert "## 写作要求（骨架靶向填充模式）" in prompt
    assert "骨架锁定（最高优先级）" in prompt
    assert "末级小节精准填充：在每一个最低级别标题（### / ####）下方强制空一行（\\n\\n）" in prompt
    assert "非末级标题禁止堆砌正文：一级章（#）和二级节（##）作为分类与结构导引" in prompt
    assert "格式规范（极重要）" in prompt


def test_build_outline_system_prompt_deep_hierarchy():
    """验证 _build_outline_system_prompt 包含末级小节全层级深度覆盖强规则。"""
    from engine.app.writing.outline import _build_outline_system_prompt

    prompt = _build_outline_system_prompt(report_type="可行性研究报告", total_words=50000)
    assert "深度要求（极重要）" in prompt
    assert "三级（###）或四级（####）末级实施小节" in prompt
    assert "每个二级节（##）下必须细分 2~5 个具体的末级小节" in prompt
    assert "构建全书完整的标题骨架，严禁输出只有一级章或二级节的粗粒度空章" in prompt


def test_llm_chat_stream_iter_with_thought(fast_retries):
    """验证 LLMClient 捕获 reasoning_content 与 thought 并产生标准 JSON 思考事件。"""
    from engine.app.writing.llm_client import LLMClient
    sse = "data: {\"choices\":[{\"delta\":{\"reasoning_content\":\"思考步骤1\"}}]}\n\n" \
          "data: {\"choices\":[{\"delta\":{\"thought\":\"思考步骤2\"}}]}\n\n" \
          "data: {\"choices\":[{\"delta\":{\"content\":\"正文输出\"}}]}\n\n" \
          "data: [DONE]\n\n"
    set_llm_transport(httpx.MockTransport(lambda req: httpx.Response(
        200, text=sse, headers={"content-type": "text/event-stream"}
    )))
    c = LLMClient(LLM_CONFIG)
    chunks = list(c.chat_stream_iter([{"role": "user", "content": "x"}], temperature=0.2))
    assert len(chunks) == 3
    assert json.loads(chunks[0]) == {"type": "thought", "chunk": "思考步骤1"}
    assert json.loads(chunks[1]) == {"type": "thought", "chunk": "思考步骤2"}
    assert chunks[2] == "正文输出"

    # 验证 chat_stream 累积正文时忽略 thought JSON
    set_llm_transport(httpx.MockTransport(lambda req: httpx.Response(
        200, text=sse, headers={"content-type": "text/event-stream"}
    )))
    full = c.chat_stream([{"role": "user", "content": "x"}], temperature=0.2)
    assert full == "正文输出"
    set_llm_transport(None)






