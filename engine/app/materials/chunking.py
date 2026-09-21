"""
资料分块 — 移植自根目录 pipeline.py（含 FRL-003 式边界保护）。

按 Markdown 标题边界分段，再按固定大小重叠分块。
"""
import re

from ..config import settings

# ── 支持的扩展名 ──
SUPPORTED_EXTENSIONS = {
    ".docx": "word",
    ".xlsx": "excel",
    ".csv": "csv",
    ".md": "markdown",
    ".txt": "text",
    ".pdf": "pdf",
}

ALLOWED_EXTS = frozenset(SUPPORTED_EXTENSIONS.keys())


def chunk_text(
    text: str,
    source_name: str,
    size: int = None,
    overlap: int = None,
    doc_id: int = None,
    source_id: str = None,
) -> list[dict]:
    """按重叠分块（优先尊重段落/标题边界）。

    每个 chunk：text / source / source_id / doc_id。
    """
    if size is None:
        size = settings.chunk_size
    if overlap is None:
        overlap = settings.chunk_overlap

    chunks: list[dict] = []
    text = text.strip()
    if not text:
        return chunks

    # 按 Markdown 标题边界分段（保留标题为块首）
    headings = list(re.finditer(r"^(#{1,6})\s+", text, re.MULTILINE))

    if len(headings) > 1:
        segments = []
        for i, h in enumerate(headings):
            start = h.start()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            segments.append(text[start:end])

        for seg in segments:
            if len(seg) <= size:
                chunks.append(_mk_chunk(seg, source_name, doc_id, source_id))
            else:
                chunks.extend(_chunk_segment(seg, source_name, size, overlap, doc_id, source_id))
    else:
        chunks.extend(_chunk_segment(text, source_name, size, overlap, doc_id, source_id))

    return chunks


def _mk_chunk(text: str, source_name: str, doc_id: int | None, source_id: str | None) -> dict:
    ch = {"text": text, "source": source_name}
    if doc_id is not None:
        ch["doc_id"] = doc_id
    if source_id is not None:
        ch["source_id"] = source_id
    return ch


def _chunk_segment(
    text: str,
    source_name: str,
    size: int,
    overlap: int,
    doc_id: int = None,
    source_id: str = None,
) -> list[dict]:
    """按固定大小分块，尽量在句/行边界断开。

    安全：overlap 被钳制以保证前进。
    """
    # FRL-003：校验并钳制参数，防止死循环
    if size <= 0:
        raise ValueError(f"chunk size must be > 0, got {size}")
    if overlap < 0:
        overlap = 0
    if overlap >= size:
        overlap = max(0, size // 4)  # 钳制到安全值

    chunks: list[dict] = []
    start = 0
    while start < len(text):
        end = start + size
        if end >= len(text):
            chunks.append(_mk_chunk(text[start:], source_name, doc_id, source_id))
            break

        chunk = text[start:end]
        last_nl = chunk.rfind("\n")
        if last_nl > size * 0.5:
            end = start + last_nl + 1

        chunks.append(_mk_chunk(text[start:end], source_name, doc_id, source_id))
        # FRL-003：确保前进
        next_start = end - overlap
        if next_start <= start:
            next_start = start + 1
        start = next_start

    return chunks
