"""
FairyReport MCP Server — 本地优先的工程咨询、投资立项与智库报告 MCP 工具链。

核心设计（零 API Key 宿主驱动模式 / Host-LLM Mode）：
- 宿主客户端（Cherry Studio、Claude Desktop / Cowork、Cursor、Trae、OpenClaw、Antigravity 等）
  自带大模型负责推理与撰文；
- FairyReport MCP Server 提供通用聊天 Agent 缺失的四大确定性专业能力：
  1. 15 类权威工程与咨询报告标准大纲蓝图、写作顺序与三线表规范（list_report_templates / get_report_blueprint）
  2. 本地多格式工程底稿（PDF/Word/Excel/TXT）向量建库与三源深度 RAG 检索（ingest_project_materials / retrieve_report_evidence）
  3. 跨章节核心工程经济指标（总投资、用地、建筑面积、工期、IRR、营业收入）与引用溯源自洽核验（verify_report_consistency）
  4. 出版级工程咨询 Word (.docx) 编译导出（含封面、目录、标准三线表、多级标题防粘连、文末自动编号参考文献）（export_consulting_docx）
- 可选增强：若环境变量配置了 DEEPSEEK_API_KEY（或 OPENAI_API_KEY），还可通过 draft_chapter_with_engine
  将超长单章生成卸载给本地引擎配置的模型。

启动方式：
  - 标准 STDIO（默认，供桌面 Agent 挂载）：
      python -m engine.mcp_server
      或
      fairyreport-mcp
  - Streamable HTTP / SSE 模式：
      python -m engine.mcp_server --transport streamable-http --port 8002
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 严格将日志输出指向 stderr，防止污染 MCP stdio JSON-RPC 通信流
logging.basicConfig(
    level=logging.WARNING,
    format="[FairyReport-MCP] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
_logger = logging.getLogger("fairyreport.mcp")

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:  # 兼容 mcp 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer  # type: ignore[no-redef]

from sqlalchemy import select

from .app import db as db_module
from .app import models
from .app.config import settings
from .app.embedding import get_embedder
from .app.export.docx_builder import build_merged_md, md_to_docx
from .app.materials.chunking import ALLOWED_EXTS
from .app.materials.router import _process_file
from .app.materials.vectorstore import ProjectVectorStore
from .app.writing import templates_loader as tmpl
from .app.writing.context_verifier import run_full_context_verification
from .app.writing.llm_client import LLMClient
from .app.writing.prompts import REPORT_TYPES, REPORT_WORD_LIMITS
from .app.writing.rag import query_rag
from .app.writing.writer import (
    ChapterWriter,
    _build_writing_system_prompt,
    normalize_chapter_markdown,
)

# 确保本地 SQLite 元数据表已就绪
db_module.create_tables()

_INSTRUCTIONS = (
    "FairyReport MCP Server 提供 15 类专业工程咨询与智库报告的标准大纲蓝图、"
    "本地工程底稿向量建库、三源深度 RAG 检索（底稿【源】+ 国标【标】+ 权威联网【网】）、"
    "跨章节工程经济指标自洽性核验以及出版级三线表 Word (.docx) 导出能力。"
    "推荐按以下五步工作流调用工具：1. list_report_templates / get_report_blueprint 获取标准大纲与写作规范 -> "
    "2. ingest_project_materials 导入本地底稿（如有） -> "
    "3. retrieve_report_evidence 检索章节证据并遵循蓝图规范撰写各章 Markdown -> "
    "4. verify_report_consistency 核验跨章节投资/用地/收益率指标自洽性 -> "
    "5. export_consulting_docx 编译导出带封面、目录、三线表与参考文献的出版级 Word 初稿。"
)

mcp = MCPServer(
    "FairyReport",
    instructions=_INSTRUCTIONS,
)

_SAFE_PROJECT_RE = re.compile(r"^[^/\\:*?\"<>|\s]+$")


def _normalize_project_name(project: str) -> str:
    """规范化项目名，确保文件系统安全。"""
    cleaned = (project or "default_project").strip()
    cleaned = re.sub(r"[/\\:*?\"<>|\s]+", "_", cleaned).strip("._")
    return cleaned or "default_project"


def _ensure_project_record(session, project_name: str) -> models.Project:
    """确保项目在 SQLite 与本地目录中已创建。"""
    proj = (
        session.execute(
            select(models.Project).where(models.Project.name == project_name)
        )
        .scalars()
        .first()
    )
    if not proj:
        proj = models.Project(name=project_name)
        session.add(proj)
        session.commit()
        session.refresh(proj)
    settings.files_dir(project_name).mkdir(parents=True, exist_ok=True)
    settings.vector_dir(project_name).mkdir(parents=True, exist_ok=True)
    return proj


@mcp.tool()
def list_report_templates() -> dict[str, Any]:
    """列出 FairyReport 支持的全部 15 类专业工程咨询、投资立项与智库报告模板清单、字数上限及推荐写作顺序。"""
    items: list[dict[str, Any]] = []
    for rtype in REPORT_TYPES:
        data = tmpl.load_template(rtype) or {}
        chapters = data.get("chapters") or []
        total_words = data.get("total_words_max") or REPORT_WORD_LIMITS.get(rtype, 30000)
        order = tmpl.get_writing_order(rtype, total_chapters=len(chapters))
        reason = tmpl.get_writing_order_reason(rtype)
        items.append(
            {
                "report_type": rtype,
                "chapter_count": len(chapters),
                "total_words_max": total_words,
                "recommended_writing_order": order,
                "writing_order_reason": reason,
                "notes": data.get("notes", ""),
            }
        )
    return {
        "total_templates": len(items),
        "templates": items,
    }


@mcp.tool()
def get_report_blueprint(report_type: str = "可行性研究报告") -> dict[str, Any]:
    """获取指定报告类型的权威标准章节大纲（outline_md）、各章节字数预算、推荐写作顺序及出版级写作规范提示词。

    参数:
        report_type: 报告类型名称（如 "可行性研究报告"、"项目建议书"、"资金申请报告"、"智库专报" 等，可通过 list_report_templates 查看）。
    """
    rtype = (report_type or "可行性研究报告").strip()
    data = tmpl.load_template(rtype)
    if not data:
        return {
            "status": "error",
            "error": f"未找到报告类型 '{rtype}'，请先调用 list_report_templates 查看支持的 15 类标准报告名称。",
            "supported_report_types": REPORT_TYPES,
        }

    chapters = data.get("chapters") or []
    total_words = data.get("total_words_max") or REPORT_WORD_LIMITS.get(rtype, 30000)
    writing_order = tmpl.get_writing_order(rtype, total_chapters=len(chapters))
    writing_order_reason = tmpl.get_writing_order_reason(rtype)
    writing_rules = _build_writing_system_prompt(
        report_type=rtype,
        total_words=total_words,
        total_chapters=len(chapters),
    )

    return {
        "status": "ok",
        "report_type": rtype,
        "total_words_max": total_words,
        "per_chapter_max": data.get("per_chapter_max", 0),
        "summary_chapter_max": data.get("summary_chapter_max", 0),
        "notes": data.get("notes", ""),
        "recommended_writing_order": writing_order,
        "writing_order_reason": writing_order_reason,
        "outline_md": data.get("outline_md", ""),
        "chapters": chapters,
        "writing_specification_prompt": writing_rules,
    }


@mcp.tool()
def ingest_project_materials(
    project: str,
    file_paths: list[str],
) -> dict[str, Any]:
    """将本地工程底稿或参考资料（支持 .pdf, .docx, .xlsx, .txt, .md）解析、分块并向量化入库到指定项目知识库。

    参数:
        project: 项目名称（如 "长三角算力中心可研项目"）。
        file_paths: 本地文件绝对路径列表。
    """
    project_name = _normalize_project_name(project)
    if not file_paths:
        return {"status": "error", "error": "file_paths 不能为空"}

    session_gen = db_module.get_db()
    session = next(session_gen)
    try:
        proj = _ensure_project_record(session, project_name)
        store = ProjectVectorStore.get(project_name, settings.vector_dir(project_name))
        embedder = get_embedder()
        dest_dir = str(settings.files_dir(project_name))

        results: list[dict[str, Any]] = []
        success_count = 0
        for raw_path in file_paths:
            fpath = os.path.abspath(raw_path)
            ext = os.path.splitext(fpath)[1].lower()
            if not os.path.isfile(fpath):
                results.append(
                    {
                        "file_path": raw_path,
                        "status": "error",
                        "error": f"文件不存在: {fpath}",
                    }
                )
                continue
            if ext not in ALLOWED_EXTS:
                results.append(
                    {
                        "file_path": raw_path,
                        "status": "error",
                        "error": f"不支持的文件格式 '{ext}'，仅支持: {sorted(ALLOWED_EXTS)}",
                    }
                )
                continue

            res = _process_file(
                session=session,
                proj=proj,
                store=store,
                embedder=embedder,
                fpath=fpath,
                copy_dest_dir=dest_dir,
            )
            item = res.model_dump()
            results.append(item)
            if item.get("status") == "ok":
                success_count += 1

        return {
            "status": "ok" if success_count > 0 else "error",
            "project": project_name,
            "ingested_files": success_count,
            "total_files": len(file_paths),
            "total_vector_chunks": store.count(),
            "results": results,
        }
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass


@mcp.tool()
def retrieve_report_evidence(
    query: str,
    project: str = "",
    chapter_title: str = "",
    report_type: str = "可行性研究报告",
    include_generic: bool = True,
    include_web: bool = True,
    n_results: int = 5,
) -> dict[str, Any]:
    """执行三源深度 RAG 检索（1. 项目底稿向量库【源:文件名】 + 2. 行业标准规程库【标:标准名称】 + 3. 百度免 Key 权威联网检索【网:标题】）。

    宿主大模型在撰写报告章节时，必须仅使用本工具返回的【源:...】、【标:...】、【网:...】标签作为行内引用，严禁虚构出处。

    参数:
        query: 检索关键词或当前小节核心主题。
        project: 项目名称（若已通过 ingest_project_materials 导入底稿，传入对应项目名以检索本地底稿库）。
        chapter_title: 当前撰写的章节标题（用于智能提炼高命中率行业与政策检索词）。
        report_type: 报告类型（默认 "可行性研究报告"）。
        include_generic: 是否检索内置行业规程与通用标准库（默认 True）。
        include_web: 是否执行免 Key 权威联网检索（默认 True；离线环境或纯底稿测试可设为 False）。
        n_results: 每个来源返回的最大片段数（1~15，默认 5）。
    """
    proj_name = _normalize_project_name(project) if project and project.strip() else ""
    safe_n = max(1, min(int(n_results or 5), 15))
    evidence_text = query_rag(
        project_name=proj_name,
        query_text=query,
        n_results=safe_n,
        include_generic=include_generic,
        include_web=include_web,
        topic=query,
        report_name=proj_name,
        report_type=report_type,
    )
    return {
        "project": proj_name,
        "query": query,
        "chapter_title": chapter_title,
        "report_type": report_type,
        "citation_format_rule": (
            "引用时只能使用下方 evidence_context 中实际出现的标签："
            "项目底稿用【源:文件名】，行业标准用【标:标准全称】，联网资料用【网:标题】，"
            "必须紧随事实陈述句末尾（如 `...符合规范【标:相关标准】。`），严禁单独成行或编造标签。"
        ),
        "evidence_context": evidence_text,
    }


@mcp.tool()
def verify_report_consistency(
    chapters: dict[str, str],
    project: str = "",
    report_type: str = "可行性研究报告",
) -> dict[str, Any]:
    """跨章节工程经济指标与上下文自洽性核验引擎。

    自动抽取各章中的核心工程经济量纲指标（总投资、建设用地、总建筑面积、建设工期、财务内部收益率 FIRR、资本金内部收益率、达产年营业收入），
    自动换算统一单位（如亿元<->万元、公顷<->亩、年<->个月），识别基准方案与敏感性情景，并核验引用标签与跨章逻辑呼应。

    参数:
        chapters: 章节序号到章节 Markdown 正文的映射字典，例如 {"1": "# 第一章 概述...", "7": "# 第七章 投资估算..."}。
        project: 项目名称（可选，用于核对项目底稿引用真实性）。
        report_type: 报告类型名称。
    """
    if not chapters or not isinstance(chapters, dict):
        return {"status": "error", "error": "chapters 字典不能为空，键为章节序号字符串（如 '1', '2'），值为 Markdown 正文。"}

    normalized_chapters = {str(k): str(v or "") for k, v in chapters.items()}
    proj_name = _normalize_project_name(project) if project and project.strip() else ""
    res = run_full_context_verification(
        chapters=normalized_chapters,
        project=proj_name,
        report_type=report_type,
    )
    return res.model_dump()


@mcp.tool()
def export_consulting_docx(
    chapters: dict[str, str],
    title: str,
    project: str = "mcp_report",
    report_type: str = "可行性研究报告",
    subtitle: str = "（ 初 稿 ）",
    author_org: str = "",
    qualification: str = "",
    date_str: str = "",
    include_cover: bool = True,
    include_toc: bool = True,
    include_refs: bool = True,
    output_path: str = "",
) -> dict[str, Any]:
    """将多章节 Markdown 编译导出为符合中国工程咨询与政企出版规范的 Word (.docx) 报告文件。

    内置特性：
    - 标准封面、自动目录（TOC）与页眉页脚
    - 多级工程标题与正文粘连智能清洗拆分，100% 映射为 Word 原生 Heading 样式
    - Markdown 表格自动渲染为出版级标准学术/工程三线表
    - 全文【源:...】【标:...】【网:...】引用按首次出现顺序自动重编号为 [1], [2], [3]... 并在文末生成标准《参考文献》章（联网文献保留完整 URL）

    参数:
        chapters: 章节序号到章节 Markdown 正文的字典，例如 {"1": "# 第一章...", "2": "# 第二章..."}。
        title: 报告主标题（封面与正文大标题，如 "长三角绿色智能算力枢纽项目可行性研究报告"）。
        project: 项目标识名（用于生成默认文件名与匹配项目底稿库）。
        report_type: 报告类型（如 "可行性研究报告"、"智库专报"）。
        subtitle: 封面副标题标识（默认 "（ 初 稿 ）"）。
        author_org: 编制单位名称（可选，显示在封面底部）。
        qualification: 工程咨询资信或资质编号（可选）。
        date_str: 编制日期字符串（可选，如 "二〇二六年十一月"）。
        include_cover: 是否生成专业封面（默认 True）。
        include_toc: 是否生成目录页（默认 True）。
        include_refs: 是否自动汇总生成文末《参考文献》章（默认 True）。
        output_path: 自定义输出 .docx 绝对路径（可选；留空则自动输出至 ENGINE_DATA_DIR/exports/ 目录）。
    """
    if not chapters or not isinstance(chapters, dict):
        return {"status": "error", "error": "chapters 不能为空"}

    normalized_chapters = {str(k): str(v or "") for k, v in chapters.items() if str(v or "").strip()}
    if not normalized_chapters:
        return {"status": "error", "error": "chapters 中没有任何非空正文内容"}

    proj_name = _normalize_project_name(project)
    final_md = build_merged_md(
        normalized_chapters,
        include_refs=include_refs,
        project=proj_name,
    )
    if not final_md.strip():
        return {"status": "error", "error": "合并后的章节内容为空"}

    if output_path and output_path.strip():
        out_file = os.path.abspath(output_path.strip())
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
    else:
        exports_dir = os.path.join(settings.engine_data_dir, "exports")
        os.makedirs(exports_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"{proj_name}_{stamp}.docx"
        out_file = os.path.join(exports_dir, fname)

    md_to_docx(
        final_md,
        out_file,
        title=title,
        subtitle=subtitle or "（ 初 稿 ）",
        project=proj_name,
        report_type=report_type,
        author_org=author_org,
        qualification=qualification,
        date_str=date_str,
        include_cover=include_cover,
        include_toc=include_toc,
    )
    size_bytes = os.path.getsize(out_file)
    return {
        "status": "ok",
        "path": out_file,
        "filename": os.path.basename(out_file),
        "size_bytes": size_bytes,
        "chapters_exported": len(normalized_chapters),
    }


@mcp.tool()
def draft_chapter_with_engine(
    report_type: str,
    outline_md: str,
    chapter_seq: int,
    chapter_title: str,
    topic: str,
    project: str = "",
    predecessor_chapters: dict[str, str] | None = None,
    writing_hint: str = "",
    include_web: bool = True,
) -> dict[str, Any]:
    """（可选自带 Key 工具）使用本地引擎配置的 OpenAI 兼容大模型（如环境变量 DEEPSEEK_API_KEY）直接自动检索并撰写指定章节。

    适用场景：当宿主 Agent 希望将超长单章（如 5000~8000 字工程技术章节）卸载给后台高性价比模型（如 DeepSeek）生成时调用。
    若未配置 DEEPSEEK_API_KEY / OPENAI_API_KEY，请优先使用 retrieve_report_evidence + 宿主自身大模型直接撰写。
    """
    api_key = (
        os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or getattr(settings, "llm_api_key", "")
        or ""
    ).strip()
    base_url = (
        os.environ.get("DEEPSEEK_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or getattr(settings, "llm_base_url", "")
        or "https://api.deepseek.com/v1"
    ).strip()
    model_name = (
        os.environ.get("DEEPSEEK_MODEL")
        or os.environ.get("OPENAI_MODEL")
        or getattr(settings, "llm_model", "")
        or "deepseek-chat"
    ).strip()

    if not api_key:
        return {
            "status": "no_engine_api_key",
            "message": (
                "本地引擎未配置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY。"
                "无需配置额外 Key，请直接调用 get_report_blueprint 与 retrieve_report_evidence 工具，"
                "由当前宿主 Agent 自身大模型完成章节撰写，随后调用 verify_report_consistency 与 export_consulting_docx 即可。"
            ),
        }

    proj_name = _normalize_project_name(project) if project and project.strip() else ""
    rag_context = query_rag(
        project_name=proj_name,
        query_text=f"{topic} {chapter_title}".strip(),
        include_generic=True,
        include_web=include_web,
        topic=topic,
        report_name=proj_name,
        report_type=report_type,
    )
    budget = tmpl.get_chapter_word_budget(report_type, chapter_seq) or tmpl.get_chapter_word_limit(report_type)
    is_sum = tmpl.is_summary_chapter(report_type, chapter_seq)

    llm = LLMClient({"api_key": api_key, "base_url": base_url, "model": model_name})
    writer = ChapterWriter(llm=llm, report_type=report_type)
    chapter_md = writer.write_chapter(
        chapter_title=chapter_title,
        outline_md=outline_md,
        predecessor_chapters=predecessor_chapters or {},
        rag_context=rag_context,
        topic=topic,
        writing_hint=writing_hint,
        report_name=proj_name,
        chapter_budget=budget,
        is_summary=is_sum,
        chapter_seq=chapter_seq,
    )
    cleaned_md = normalize_chapter_markdown(chapter_md)
    return {
        "status": "ok",
        "chapter_seq": chapter_seq,
        "chapter_title": chapter_title,
        "model_used": model_name,
        "chapter_markdown": cleaned_md,
    }


@mcp.prompt()
def consulting_report_workflow(
    report_type: str = "可行性研究报告",
    topic: str = "",
    project: str = "consulting_project",
) -> str:
    """FairyReport 五步标准工程咨询与智库报告编制 SOP 提示词模板。"""
    return (
        f"你现在接入了 FairyReport 专业报告编制工具链，请围绕主题「{topic or '用户指定项目'}」"
        f"编制一份符合行业出版规范的《{report_type}》（项目标识：`{project}`）。\n\n"
        "请严格按照以下五步闭环调用 FairyReport MCP 工具：\n"
        f"1. **获取权威蓝图**：首先调用 `get_report_blueprint(report_type='{report_type}')`，"
        "读取标准章节大纲（`outline_md`）、推荐写作顺序（`recommended_writing_order`）以及写作规范（`writing_specification_prompt`）。\n"
        "2. **底稿建库（如用户提供了本地文件）**：若用户提供了 PDF/Word/Excel 等本地底稿路径，调用 `ingest_project_materials` 建立本地项目向量库。\n"
        "3. **三源检索与骨架锁定撰文**：按照推荐写作顺序，在写每一章前调用 `retrieve_report_evidence` 获取项目底稿【源:...】、行业标准【标:...】与权威联网【网:...】证据；"
        "严格遵循蓝图中的各级标题骨架、标准三线表规定动作与行内紧随引用格式撰写章节正文（严禁虚构不存在的引用标签，严禁标题行内粘连正文）。\n"
        "4. **跨章节量纲与指标自洽核验**：各章节初稿完成后，调用 `verify_report_consistency` 传入 `chapters` 字典，"
        "检查总投资、用地面积、建筑面积、工期、财务内部收益率（FIRR）等指标在前后章节是否 100% 自洽；若发现 `conflict`，立即修正对应章节数值直至核验通过。\n"
        "5. **出版级 Word 成果导出**：调用 `export_consulting_docx` 一键导出带专业封面、目录、三线表与自动编号《参考文献》的 `.docx` 报告，并向用户汇报输出文件路径与核验得分。"
    )


def main() -> None:
    """FairyReport MCP Server 命令行入口。"""
    parser = argparse.ArgumentParser(description="FairyReport MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP 传输协议（默认 stdio，供桌面端 Agent 直接挂载）",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP/SSE 模式下的绑定主机（默认 127.0.0.1）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="HTTP/SSE 模式下的绑定端口（默认 8002）",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
