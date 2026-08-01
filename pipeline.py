"""
Pipeline — File parsing & text chunking

Core workflow:
  Raw file -> converters unify to MD -> MD text chunking -> ingest
"""
import os
import re
from config import CHUNK_SIZE, CHUNK_OVERLAP
from converters import to_markdown

# ── Supported extensions ──
SUPPORTED_EXTENSIONS = {
    '.docx': 'word',
    '.xlsx': 'excel',
    '.csv':  'csv',
    '.md':   'markdown',
    '.txt':  'text',
}


def chunk_text(text: str, source_name: str,
               size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP,
               doc_id: int = None, source_id: str = None) -> list:
    """Split text into overlapping chunks (optimized to respect paragraph/heading boundaries).

    Each chunk contains:
      - text: chunk text
      - source: display name (basename for UI)
      - source_id: unique identifier (relative path from import folder, for dedup)
      - doc_id: document number (sequential, starting from 1), used in reference format [N]
    """
    chunks = []
    text = text.strip()
    if not text:
        return chunks

    # Split by Markdown heading boundaries (keep heading as chunk start)
    headings = list(re.finditer(r'^(#{1,6})\s+', text, re.MULTILINE))

    if len(headings) > 1:
        # Has heading structure: segment by headings, then chunk each segment by size
        segments = []
        for i, h in enumerate(headings):
            start = h.start()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            segments.append(text[start:end])

        for seg in segments:
            if len(seg) <= size:
                ch = {"text": seg, "source": source_name}
                if doc_id is not None:
                    ch["doc_id"] = doc_id
                if source_id is not None:
                    ch["source_id"] = source_id
                chunks.append(ch)
            else:
                chunks.extend(_chunk_segment(seg, source_name, size, overlap, doc_id, source_id))
    else:
        # No heading structure: chunk directly by size
        chunks.extend(_chunk_segment(text, source_name, size, overlap, doc_id, source_id))

    return chunks


def _chunk_segment(text: str, source_name: str,
                   size: int, overlap: int, doc_id: int = None,
                   source_id: str = None) -> list:
    """Chunk a piece of text by fixed size, prefer to break at sentence boundaries.

    Safety: overlap is clamped to ensure forward progress in all cases.
    """
    # FRL-003: validate and clamp parameters to prevent infinite loops
    if size <= 0:
        raise ValueError(f"chunk size must be > 0, got {size}")
    if overlap < 0:
        overlap = 0
    if overlap >= size:
        overlap = max(0, size // 4)  # Clamp to safe value to ensure progress

    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        if end >= len(text):
            ch = {"text": text[start:], "source": source_name}
            if doc_id is not None:
                ch["doc_id"] = doc_id
            if source_id is not None:
                ch["source_id"] = source_id
            chunks.append(ch)
            break

        # Try to break at a sentence boundary
        chunk = text[start:end]
        # Prefer to break at newline
        last_nl = chunk.rfind('\n')
        if last_nl > size * 0.5:
            end = start + last_nl + 1

        ch = {"text": text[start:end], "source": source_name}
        if doc_id is not None:
            ch["doc_id"] = doc_id
        if source_id is not None:
            ch["source_id"] = source_id
        chunks.append(ch)
        # FRL-003: ensure forward progress — next start MUST be > current start
        next_start = end - overlap
        if next_start <= start:
            next_start = start + 1  # Minimum forward progress of 1 char
        start = next_start

    return chunks


def scan_folder(folder_path: str) -> list:
    """Scan folder (including subdirectories), return all supported file paths (PDFs excluded)."""
    file_paths = []
    for root, _dirs, files in os.walk(folder_path):
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                file_paths.append(os.path.join(root, f))
    return file_paths


def scan_folder_with_pdf_warning(folder_path: str) -> tuple:
    """Scan folder, return a (supported_files, pdf_files) tuple.

    PDF files are listed separately for UI warning, not included in downstream processing.
    """
    supported = []
    pdfs = []
    for root, _dirs, files in os.walk(folder_path):
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            full = os.path.join(root, f)
            if ext == '.pdf':
                pdfs.append(full)
            elif ext in SUPPORTED_EXTENSIONS:
                supported.append(full)
    return supported, pdfs


def parse_single_file(f_path: str, output_dir: str = None,
                      doc_id: int = None, source_id: str = None) -> dict:
    """
    Parse a single file: convert to MD -> chunk.

    Args:
        f_path: file path
        output_dir: MD output directory (do not save MD file when None)
        doc_id: document number (sequential, starting from 1), used in reference format [N]
        source_id: unique source identifier (relative path from import folder); falls back to basename

    Returns:
        {"status": "ok"|"skip"|"error",
         "chunks": int,
         "doc_id": int|None,
         "error_msg": str|None,
         "md_path": str|None,
         "format_name": str,
         "_chunks": list}
    """
    f_name = os.path.basename(f_path)
    ext = os.path.splitext(f_name)[1].lower()
    format_name = SUPPORTED_EXTENSIONS.get(ext, ext)
    sid = source_id if source_id else f_name

    # Unknown format (including PDF — v1.0.2 no longer supports; user must pre-convert to .md)
    if ext not in SUPPORTED_EXTENSIONS:
        hint = "PDF 不支持直接导入，请先用 MinerU 等工具转为 .md" if ext == '.pdf' else f"不支持的格式：{ext}"
        return {
            "status": "skip",
            "chunks": 0,
            "doc_id": doc_id,
            "error_msg": hint,
            "md_path": None,
            "format_name": ext,
            "_chunks": [],
        }

    # Convert to Markdown
    md_text, md_path = to_markdown(f_path, output_dir=output_dir)

    if md_text is None or not md_text.strip():
        return {
            "status": "error",
            "chunks": 0,
            "doc_id": doc_id,
            "error_msg": "转换后内容为空",
            "md_path": None,
            "format_name": format_name,
            "_chunks": [],
        }

    # Chunk
    chunks = chunk_text(md_text, f_name, doc_id=doc_id, source_id=sid)
    if not chunks:
        return {
            "status": "error",
            "chunks": 0,
            "doc_id": doc_id,
            "error_msg": "切片后无内容",
            "md_path": md_path,
            "format_name": format_name,
            "_chunks": [],
        }

    return {
        "status": "ok",
        "chunks": len(chunks),
        "doc_id": doc_id,
        "error_msg": None,
        "md_path": md_path,
        "format_name": format_name,
        "_chunks": chunks,
    }


def process_files(imported_files: list, output_dir: str = None) -> list:
    """
    Batch parse files, update imported_files object arrays in place, return all chunks.

    imported_files format: [{doc_id, original, converted, status, chunks, error, imported_at}, ...]
    Each object is updated in place after parsing.

    Returns: list of all chunks (with doc_id).
    """
    all_chunks = []
    for fobj in imported_files:
        if fobj.get("status") in ("skipped", "error"):
            continue
        result = parse_single_file(fobj["original"], output_dir=output_dir,
                                   doc_id=fobj["doc_id"])
        # Update object fields
        fobj["status"] = result["status"]
        fobj["converted"] = result.get("md_path")
        fobj["chunks"] = result["chunks"]
        fobj["error"] = result.get("error_msg")
        if result["status"] == "ok":
            all_chunks.extend(result["_chunks"])
    return all_chunks
