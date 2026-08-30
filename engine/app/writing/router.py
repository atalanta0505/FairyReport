"""
写作链路路由 — 大纲/章节/审阅/修订/提示。

- llm_config 缺字段 → 422（Pydantic 校验）
- 通用包未装 → 409（outline/chapter 需模板与字数预算）
- chapter stream=true → SSE 透传；stream=false → JSON
- 上游 5xx/超时 → 502/504；key 不落盘（仅请求内持有）
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..config import settings
from ..embedding import get_embedder
from . import templates_loader as tmpl
from .llm_client import LLMClient, LLMError
from .outline import OutlineGenerator, _extract_chapter_titles, parse_chapter_seq
from .prompts import (
    FREQUENCY_PENALTY,
    PRESENCE_PENALTY,
    REPORT_TYPES,
    TECH_REVIEW_SYSTEM_PROMPT,
    TEMPERATURE_WRITING,
    TOP_P,
)
from .rag import query_rag
from .refs import strip_fabricated_labels
from .templates_loader import TemplatesNotInstalled
from .writer import (
    ChapterWriter,
    normalize_chapter_markdown,
    parse_expert_review_result,
    parse_tech_review_result,
    _build_writing_system_prompt,
)

router = APIRouter(tags=["writing"])


# ── 请求与响应模型 ──
class OutlineData(BaseModel):
    report_type: str = "可行性研究报告"
    outline_md: str = ""
    chapters: list[dict] = Field(default_factory=list)
    writing_order: list[int] = Field(default_factory=list)
    writing_order_reason: str = ""
    updated_at: str = ""


class ChaptersData(BaseModel):
    chapters: dict[str, str] = Field(default_factory=dict)
    updated_at: str = ""


class ChapterSaveRequest(BaseModel):
    text: str = ""


class ReviewsData(BaseModel):
    reviews: dict[str, dict] = Field(default_factory=dict)
    updated_at: str = ""


class ReviewSaveRequest(BaseModel):
    review: dict = Field(default_factory=dict)


class FullReviewData(BaseModel):
    summary: str = ""
    compliance_rate: int = 100
    health_status: str = "达标"  # "达标" | "待完善" | "存在重大缺陷"
    issues: list[dict] = Field(default_factory=list)
    numerical_checks: list[dict] = Field(default_factory=list)
    data_gap_checklist: list[dict | str] = Field(default_factory=list)
    chapter_evaluations: dict[str, dict] = Field(default_factory=dict)
    general_suggestions: list[str] = Field(default_factory=list)
    updated_at: str = ""


class TemplateItemOut(BaseModel):
    report_type: str
    total_words_max: int = 0
    notes: str = ""
    writing_order: list[int] = Field(default_factory=list)
    writing_order_reason: str = ""


class LLMConfig(BaseModel):
    api_key: str = Field(..., min_length=1)
    base_url: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)


class OutlineRequest(BaseModel):
    project: str = ""
    report_type: str
    llm_config: LLMConfig


class ChapterRequest(BaseModel):
    project: str = ""
    report_type: str
    outline_md: str
    chapter_seq: int
    stream: bool = False
    llm_config: LLMConfig
    topic: str = ""
    report_name: str = ""
    predecessor_chapters: dict = Field(default_factory=dict)
    writing_hint: str = ""


class ReviewRequest(BaseModel):
    chapter_text: str
    report_type: str = ""
    chapter_title: str = ""
    mode: str = "fast"
    llm_config: LLMConfig


class ReviseRequest(BaseModel):
    chapter_text: str
    instruction: str
    llm_config: LLMConfig
    chapter_title: str = ""
    report_type: str = ""
    chapter_budget: int = 0


class ReviseParagraphRequest(BaseModel):
    paragraph_text: str
    instruction: str
    llm_config: LLMConfig
    chapter_title: str = ""
    report_type: str = "可行性研究报告"


class HintSaveRequest(BaseModel):
    project: str
    ch_seq: int
    hint: str


# ── 辅助 ──
def _require_pack() -> None:
    """通用包未装 → 409。"""
    try:
        tmpl.require_installed()
    except TemplatesNotInstalled as e:
        raise HTTPException(status_code=409, detail=str(e))


def _make_llm(cfg: LLMConfig) -> LLMClient:
    try:
        return LLMClient(cfg.model_dump())
    except LLMError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


def _map_llm_error(e: LLMError) -> HTTPException:
    return HTTPException(status_code=e.status_code, detail=e.detail)


def _sse_event(data: str) -> str:
    return f"data: {data}\n\n"


def _read_outline_file(name: str) -> OutlineData:
    p = settings.project_dir(name) / "outline.json"
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            outline_data = OutlineData(**data)
            if not outline_data.writing_order and outline_data.report_type:
                outline_data.writing_order = tmpl.get_writing_order(
                    outline_data.report_type, total_chapters=len(outline_data.chapters)
                )
                outline_data.writing_order_reason = tmpl.get_writing_order_reason(outline_data.report_type)
            return outline_data
        except Exception:
            pass
    return OutlineData()


def _write_outline_file(name: str, data: OutlineData) -> OutlineData:
    pdir = settings.project_dir(name)
    pdir.mkdir(parents=True, exist_ok=True)
    p = pdir / "outline.json"
    if not data.updated_at:
        data.updated_at = datetime.now(timezone.utc).isoformat()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data.model_dump(), f, ensure_ascii=False, indent=2)
    return data


def _read_chapters_file(name: str) -> ChaptersData:
    p = settings.project_dir(name) / "chapters.json"
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ChaptersData(**data)
        except Exception:
            pass
    return ChaptersData()


def _write_chapters_file(name: str, data: ChaptersData) -> ChaptersData:
    pdir = settings.project_dir(name)
    pdir.mkdir(parents=True, exist_ok=True)
    p = pdir / "chapters.json"
    if not data.updated_at:
        data.updated_at = datetime.now(timezone.utc).isoformat()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data.model_dump(), f, ensure_ascii=False, indent=2)
    return data


# ── 大纲持久化端点 ──
@router.get("/projects/{name}/outline", response_model=OutlineData)
@router.get("/writing/projects/{name}/outline", response_model=OutlineData)
def get_project_outline(name: str):
    """读取项目大纲持久化文件；不存在则返回默认空数据。"""
    return _read_outline_file(name)


@router.post("/projects/{name}/outline", response_model=OutlineData)
@router.post("/writing/projects/{name}/outline", response_model=OutlineData)
def save_project_outline(name: str, data: OutlineData):
    """保存项目大纲与模板类型到 outline.json。"""
    return _write_outline_file(name, data)


# ── 章节持久化端点 ──
@router.get("/projects/{name}/chapters", response_model=ChaptersData)
@router.get("/writing/projects/{name}/chapters", response_model=ChaptersData)
def get_project_chapters(name: str):
    """读取项目章节持久化数据；不存在则返回空映射。"""
    return _read_chapters_file(name)


@router.post("/projects/{name}/chapters/{seq}", response_model=ChaptersData)
@router.post("/writing/projects/{name}/chapters/{seq}", response_model=ChaptersData)
def save_project_chapter(name: str, seq: int, req: ChapterSaveRequest):
    """保存单章 markdown 内容到 chapters.json 并落盘 chapters/chapter_{seq}.md。"""
    cleaned_text = normalize_chapter_markdown(req.text)
    data = _read_chapters_file(name)
    data.chapters[str(seq)] = cleaned_text
    data.updated_at = datetime.now(timezone.utc).isoformat()
    _write_chapters_file(name, data)

    ch_dir = settings.project_dir(name) / "chapters"
    ch_dir.mkdir(parents=True, exist_ok=True)
    md_file = ch_dir / f"chapter_{seq}.md"
    try:
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
    except Exception:
        pass

    return data


@router.delete("/projects/{name}/chapters/{seq}")
@router.delete("/writing/projects/{name}/chapters/{seq}")
def delete_project_chapter(name: str, seq: int):
    """从 chapters.json 中移除单章并删除对应 markdown 文件。"""
    data = _read_chapters_file(name)
    if str(seq) in data.chapters:
        del data.chapters[str(seq)]
        data.updated_at = datetime.now(timezone.utc).isoformat()
        _write_chapters_file(name, data)

    md_file = settings.project_dir(name) / "chapters" / f"chapter_{seq}.md"
    if md_file.exists():
        try:
            md_file.unlink()
        except Exception:
            pass

    return {"ok": True, "seq": seq}


# ── 专家审阅持久化辅助与端点 ──
def _read_reviews_file(name: str) -> ReviewsData:
    p = settings.project_dir(name) / "reviews.json"
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ReviewsData(**data)
        except Exception:
            pass
    return ReviewsData()


def _write_reviews_file(name: str, data: ReviewsData) -> ReviewsData:
    pdir = settings.project_dir(name)
    pdir.mkdir(parents=True, exist_ok=True)
    p = pdir / "reviews.json"
    if not data.updated_at:
        data.updated_at = datetime.now(timezone.utc).isoformat()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data.model_dump(), f, ensure_ascii=False, indent=2)
    return data


@router.get("/projects/{name}/reviews", response_model=ReviewsData)
@router.get("/writing/projects/{name}/reviews", response_model=ReviewsData)
def get_project_reviews(name: str):
    """读取项目专家审阅持久化数据。"""
    return _read_reviews_file(name)


@router.post("/projects/{name}/reviews/{seq}", response_model=ReviewsData)
@router.post("/writing/projects/{name}/reviews/{seq}", response_model=ReviewsData)
def save_project_review(name: str, seq: int, req: ReviewSaveRequest):
    """保存项目单章专家审阅诊断结果到 reviews.json。"""
    data = _read_reviews_file(name)
    data.reviews[str(seq)] = req.review
    data.updated_at = datetime.now(timezone.utc).isoformat()
    _write_reviews_file(name, data)
    return data


@router.delete("/projects/{name}/reviews/{seq}")
@router.delete("/writing/projects/{name}/reviews/{seq}")
def delete_project_review(name: str, seq: int):
    """删除单章审阅记录。"""
    data = _read_reviews_file(name)
    if str(seq) in data.reviews:
        del data.reviews[str(seq)]
        data.updated_at = datetime.now(timezone.utc).isoformat()
        _write_reviews_file(name, data)
    return {"ok": True, "seq": seq}


# ── 全书一体化审阅总档案持久化 ──
def _read_full_review_file(name: str) -> FullReviewData:
    p = settings.project_dir(name) / "full_review.json"
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return FullReviewData(**data)
        except Exception:
            pass
    return FullReviewData()


def _write_full_review_file(name: str, data: FullReviewData) -> FullReviewData:
    pdir = settings.project_dir(name)
    pdir.mkdir(parents=True, exist_ok=True)
    p = pdir / "full_review.json"
    if not data.updated_at:
        data.updated_at = datetime.now(timezone.utc).isoformat()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data.model_dump(), f, ensure_ascii=False, indent=2)
    return data


@router.get("/projects/{name}/full_review", response_model=FullReviewData)
@router.get("/writing/projects/{name}/full_review", response_model=FullReviewData)
def get_project_full_review(name: str):
    """读取项目全书专家审阅诊断持久化数据；不存在则返回默认空数据。"""
    return _read_full_review_file(name)


@router.post("/projects/{name}/full_review", response_model=FullReviewData)
@router.post("/writing/projects/{name}/full_review", response_model=FullReviewData)
def save_project_full_review(name: str, data: FullReviewData):
    """保存项目全书专家审阅诊断总台账到 full_review.json。"""
    return _write_full_review_file(name, data)


@router.delete("/projects/{name}/full_review")
@router.delete("/writing/projects/{name}/full_review")
def delete_project_full_review(name: str):
    """删除全书专家审阅档案 full_review.json。"""
    p = settings.project_dir(name) / "full_review.json"
    if p.exists():
        try:
            p.unlink()
        except Exception:
            pass
    return {"ok": True}



# ── 写作端点 ──
@router.get("/writing/templates", response_model=list[TemplateItemOut])
def list_templates():
    """返回 14 种标准投前咨询报告类型及其建议字数预算列表。"""
    items = []
    for rt in REPORT_TYPES:
        limit = tmpl.get_word_limit(rt)
        notes = tmpl.get_template_notes(rt)
        writing_order = tmpl.get_writing_order(rt)
        writing_order_reason = tmpl.get_writing_order_reason(rt)
        items.append(TemplateItemOut(
            report_type=rt,
            total_words_max=limit,
            notes=notes,
            writing_order=writing_order,
            writing_order_reason=writing_order_reason,
        ))
    return items


@router.post("/writing/outline")
def outline(req: OutlineRequest):
    """生成大纲 → outline_md + 章节列表。通用包未装→409。若 req.project 存在，自动落盘保存。"""
    _require_pack()
    llm = _make_llm(req.llm_config)
    gen = OutlineGenerator(llm, req.report_type, tmpl.get_word_limit(req.report_type))
    try:
        outline_md = gen.generate(report_name=req.project, context="")
    except LLMError as e:
        raise _map_llm_error(e)

    titles = _extract_chapter_titles(outline_md)
    chapters = [{"seq": seq, "title": t} for seq, t in sorted(titles.items())]
    writing_order = tmpl.get_writing_order(req.report_type, total_chapters=len(chapters))
    writing_order_reason = tmpl.get_writing_order_reason(req.report_type)

    if req.project:
        try:
            _write_outline_file(
                req.project,
                OutlineData(
                    report_type=req.report_type,
                    outline_md=outline_md,
                    chapters=chapters,
                    writing_order=writing_order,
                    writing_order_reason=writing_order_reason,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                ),
            )
        except Exception:
            pass

    return {
        "outline_md": outline_md,
        "chapters": chapters,
        "writing_order": writing_order,
        "writing_order_reason": writing_order_reason,
    }


@router.post("/writing/chapter")
def chapter(req: ChapterRequest):
    """流式/非流式写作章节（含 RAG、字数预算、适用时技术分析框架）。"""
    _require_pack()
    llm = _make_llm(req.llm_config)

    # 从大纲提取章标题
    titles = _extract_chapter_titles(req.outline_md)
    chapter_title = titles.get(req.chapter_seq, f"第{req.chapter_seq}章")
    topic = req.topic or req.project

    # 字数预算与是否综述章
    chapter_budget = tmpl.get_chapter_word_budget(req.report_type, req.chapter_seq)
    is_summary = tmpl.is_summary_chapter(req.report_type, req.chapter_seq)

    writer = ChapterWriter(llm, req.report_type)

    if req.stream:
        return StreamingResponse(
            _stream_chapter(writer, llm, req, chapter_title,
                            chapter_budget, is_summary, topic),
            media_type="text/event-stream",
        )

    # 非流式 JSON
    rep_name = req.report_name or req.project
    rag_context = query_rag(
        req.project,
        chapter_title,
        include_generic=True,
        include_web=True,
        topic=topic,
        report_name=rep_name,
        report_type=req.report_type,
    )
    try:
        content = writer.write_chapter(
            chapter_title, req.outline_md, req.predecessor_chapters,
            rag_context, topic, writing_hint=req.writing_hint,
            report_name=rep_name, chapter_budget=chapter_budget,
            is_summary=is_summary,
        )
    except LLMError as e:
        raise _map_llm_error(e)
    return {"chapter_text": content}


def _stream_chapter(writer, llm, req, chapter_title,
                    chapter_budget, is_summary, topic):
    """SSE 生成器：阶段事件 + 思考事件 + 透传 LLM chunks。"""
    try:
        # 1. RAG 检索阶段
        yield _sse_event(json.dumps({
            "type": "stage",
            "stage": "rag",
            "message": "🔍 正在三源检索：工程底稿库 + 行业规程库 + 百度免 Key 外部联网 RAG...",
        }, ensure_ascii=False))

        rep_name = getattr(req, "report_name", "") or req.project
        rag_context = query_rag(
            req.project,
            chapter_title,
            include_generic=True,
            include_web=True,
            topic=topic,
            report_name=rep_name,
            report_type=getattr(req, "report_type", ""),
        )

        # 2. 骨架锁定与构建阶段
        yield _sse_event(json.dumps({
            "type": "stage",
            "stage": "skeleton",
            "message": "📋 正在提取并锁定章节全层级大纲骨架...",
        }, ensure_ascii=False))

        prompt, system = writer._build_chapter_write_args(
            chapter_title, req.outline_md, req.predecessor_chapters,
            rag_context, topic, writing_hint=req.writing_hint,
            report_name=req.project, chapter_budget=chapter_budget,
            is_summary=is_summary,
        )

        # 3. 深度推理构思阶段
        yield _sse_event(json.dumps({
            "type": "stage",
            "stage": "reasoning",
            "message": "🧠 大模型正在深度构思与组织专业工程论证与数据表格...",
        }, ensure_ascii=False))

        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        for chunk in llm.chat_stream_iter(
            messages, temperature=TEMPERATURE_WRITING,
            frequency_penalty=FREQUENCY_PENALTY,
            presence_penalty=PRESENCE_PENALTY,
            top_p=TOP_P,
        ):
            yield _sse_event(chunk)
        yield "data: [DONE]\n\n"
    except LLMError as e:
        yield _sse_event(json.dumps({"error": e.detail, "status": e.status_code}, ensure_ascii=False))
    except Exception as e:
        yield _sse_event(json.dumps({"error": str(e), "status": 500}, ensure_ascii=False))


@router.post("/writing/review")
def review(req: ReviewRequest):
    """常规快速审查或全维专家审阅/专项审查 → 结构化结果。"""
    llm = _make_llm(req.llm_config)
    writer = ChapterWriter(llm, report_type=req.report_type)
    try:
        raw, parsed = writer.expert_review(
            chapter_title=req.chapter_title,
            chapter_text=req.chapter_text,
            mode=req.mode or "fast",
        )
    except LLMError as e:
        raise _map_llm_error(e)
    return {"raw": raw, "review": parsed}


def _stream_review(writer: ChapterWriter, llm: LLMClient, req: ReviewRequest):
    """SSE 生成器：阶段事件 + 思考事件 + 输出 chunks + 最终解析 review 结果。"""
    try:
        mode = req.mode or "fast"
        # 1. 阶段事件
        if mode == "fast":
            stage_msg = "⚡ 正在执行常规快速体检：校核专有名词称谓、关键数值自洽与底线合规..."
        elif mode == "compliance":
            stage_msg = "🔍 正在对照国家政策法规与行业技术规程进行专项合规校核..."
        elif mode in ("numeric", "numerical"):
            stage_msg = "🔢 正在提取并复核关键工程技术参数与投资测算自洽性..."
        elif mode == "technical":
            stage_msg = "🛠️ 正在进行技术方案可行性与工艺路线专项审校..."
        else:
            stage_msg = "🔍 正在对照行业编制规程与工程底稿进行全维度专家逐句诊断..."

        yield _sse_event(json.dumps({
            "type": "stage",
            "stage": "init",
            "message": stage_msg,
        }, ensure_ascii=False))

        prompt, system = writer._build_expert_review_args(
            chapter_title=req.chapter_title,
            chapter_text=req.chapter_text,
            mode=mode,
        )
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]

        raw_buffer = ""
        for chunk in llm.chat_stream_iter(messages, temperature=0.2):
            if chunk.startswith('{"type": "thought"'):
                yield _sse_event(chunk)
            else:
                raw_buffer += chunk
                yield _sse_event(json.dumps({
                    "type": "chunk",
                    "chunk": chunk,
                }, ensure_ascii=False))

        if mode == "technical":
            parsed = parse_tech_review_result(raw_buffer)
        else:
            parsed = parse_expert_review_result(raw_buffer)

        yield _sse_event(json.dumps({
            "type": "done",
            "review": parsed,
            "raw": raw_buffer,
        }, ensure_ascii=False))
        yield "data: [DONE]\n\n"
    except LLMError as e:
        yield _sse_event(json.dumps({"error": e.detail, "status": e.status_code}, ensure_ascii=False))
    except Exception as e:
        yield _sse_event(json.dumps({"error": str(e), "status": 500}, ensure_ascii=False))


@router.post("/writing/review_stream")
def review_stream(req: ReviewRequest):
    """流式全维专家审阅：返回 SSE 事件流 (stage / thought / chunk / done)。"""
    llm = _make_llm(req.llm_config)
    writer = ChapterWriter(llm, report_type=req.report_type)
    return StreamingResponse(
        _stream_review(writer, llm, req),
        media_type="text/event-stream",
    )


def _stream_revise(writer: ChapterWriter, llm: LLMClient, req: ReviseRequest):
    try:
        yield _sse_event(json.dumps({
            "type": "stage",
            "stage": "locate",
            "message": "统筹专家诊断意见与修改清单...",
        }, ensure_ascii=False))

        prompt, system = writer._build_modify_args(
            req.chapter_text,
            req.instruction,
            chapter_budget=req.chapter_budget,
            report_type=req.report_type,
            chapter_title=req.chapter_title,
        )
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]

        yield _sse_event(json.dumps({
            "type": "stage",
            "stage": "reasoning",
            "message": "AI 专家正在推演深度重构方案...",
        }, ensure_ascii=False))

        raw_buffer = ""
        for chunk in llm.chat_stream_iter(messages, temperature=0.35):
            if chunk.startswith('{"type": "thought"'):
                yield _sse_event(chunk)
            else:
                raw_buffer += chunk
                yield _sse_event(json.dumps({
                    "type": "chunk",
                    "chunk": chunk,
                }, ensure_ascii=False))

        normalized = normalize_chapter_markdown(raw_buffer)

        yield _sse_event(json.dumps({
            "type": "done",
            "revised_text": normalized,
            "raw": raw_buffer,
        }, ensure_ascii=False))
        yield "data: [DONE]\n\n"
    except LLMError as e:
        yield _sse_event(json.dumps({"error": e.detail, "status": e.status_code}, ensure_ascii=False))
    except Exception as e:
        yield _sse_event(json.dumps({"error": str(e), "status": 500}, ensure_ascii=False))


@router.post("/writing/revise_stream")
def revise_stream(req: ReviseRequest):
    """流式 AI 智能修订：返回 SSE 事件流 (stage / thought / chunk / done)。"""
    llm = _make_llm(req.llm_config)
    writer = ChapterWriter(llm, report_type=req.report_type)
    return StreamingResponse(
        _stream_revise(writer, llm, req),
        media_type="text/event-stream",
    )


@router.post("/writing/revise")
def revise(req: ReviseRequest):
    """按指令修订章节 → 修订文本。"""
    llm = _make_llm(req.llm_config)
    writer = ChapterWriter(llm, report_type=req.report_type)
    try:
        revised = writer.modify_chapter(
            req.chapter_text,
            req.instruction,
            chapter_budget=req.chapter_budget,
            chapter_title=req.chapter_title,
        )
    except LLMError as e:
        raise _map_llm_error(e)
    return {"revised_text": revised}


@router.post("/writing/revise-paragraph")
def revise_paragraph(req: ReviseParagraphRequest):
    """按指令针对局部段落执行外科手术式精准修订。"""
    llm = _make_llm(req.llm_config)
    writer = ChapterWriter(llm, report_type=req.report_type)
    try:
        revised = writer.modify_paragraph(
            req.paragraph_text,
            req.instruction,
            chapter_title=req.chapter_title,
            report_type=req.report_type,
        )
    except LLMError as e:
        raise _map_llm_error(e)
    return {"revised_paragraph": revised}


@router.post("/writing/hints")
def save_hint_endpoint(req: HintSaveRequest):
    """保存章节提示（本地，不需 llm_config）。"""
    from .hints import save_hint
    path = save_hint(req.project, req.ch_seq, req.hint)
    return {"saved": path}


@router.get("/writing/hints/{project}/{ch_seq}")
def get_hint_endpoint(project: str, ch_seq: int):
    """读取章节提示（本地，不需 llm_config）。"""
    from .hints import load_hint, get_predecessor_hints
    hint = load_hint(project, ch_seq)
    return {"ch_seq": ch_seq, "hint": hint}

