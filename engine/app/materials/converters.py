"""
资料格式转换 — 移植自根目录 converters/（五格式统一转 Markdown 文本）。

支持：docx / xlsx / csv / md / txt。
入口：to_markdown(file_path) -> str | None
"""
import csv
import io
import logging
import os
import subprocess

_logger = logging.getLogger(__name__)


def to_markdown(file_path: str) -> str | None:
    """将文件转为 Markdown 文本。

    返回：成功为 MD 字符串；不支持的格式/转换失败/内容为空返回 None。
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".docx":
        return _convert_docx(file_path)
    if ext == ".xlsx":
        return _convert_xlsx(file_path)
    if ext == ".csv":
        return _convert_csv(file_path)
    if ext in (".txt", ".md"):
        text = _read_text(file_path)
        return text if (text and text.strip()) else None
    return None


def _read_text(file_path: str) -> str:
    """多编码直读（strict 探测，末尾 utf-8 replace 兜底）。"""
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb2312"):
        try:
            with open(file_path, "r", encoding=encoding, errors="strict") as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as e:
            _logger.debug("Reading %s with %s failed: %s", file_path, encoding, e)
            continue
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        return raw.decode("utf-8", errors="replace")
    except Exception as e:
        _logger.warning("Failed to read %s: %s", file_path, e)
        return ""


# ── docx ──
def _convert_docx(file_path: str) -> str | None:
    """docx -> Markdown：优先 pandoc，回退 python-docx。"""
    try:
        result = subprocess.run(
            ["pandoc", "-f", "docx", "-t", "markdown", "--wrap=none", file_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass  # pandoc 不可用，回退

    return _convert_docx_with_python_docx(file_path)


def _convert_docx_with_python_docx(file_path: str) -> str | None:
    from docx import Document

    doc = Document(file_path)
    parts: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            parts.append("")
            continue

        style_obj = para.style
        style = (style_obj.name if style_obj and style_obj.name else "").lower()
        if style.startswith("heading"):
            level = style.replace("heading ", "")
            prefix = "#" * int(level) if level.isdigit() else "##"
            parts.append(f"{prefix} {text}")
            continue

        if para.paragraph_format.left_indent and para.paragraph_format.left_indent > 0:
            indent_level = int(para.paragraph_format.left_indent / 180_000)
            parts.append(f"{'  ' * indent_level}- {text}")
            continue

        parts.append(_format_run(para))

    for idx, table in enumerate(doc.tables):
        parts.append("")
        parts.append(f"**[Table {idx + 1}]**")
        parts.append("")
        parts.append(_table_to_markdown(table))
        parts.append("")

    md = "\n".join(parts)
    return md if md.strip() else None


def _format_run(para) -> str:
    parts = []
    for run in para.runs:
        text = run.text
        if not text:
            continue
        if run.bold and run.italic:
            parts.append(f"***{text}***")
        elif run.bold:
            parts.append(f"**{text}**")
        elif run.italic:
            parts.append(f"*{text}*")
        else:
            parts.append(text)
    return "".join(parts) if parts else para.text


def _table_to_markdown(table) -> str:
    rows = []
    for row in table.rows:
        cells = [cell.text.replace("\n", " ").replace("|", "\\|").strip() for cell in row.cells]
        if any(c for c in cells):
            rows.append(cells)
    if not rows:
        return ""
    max_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < max_cols:
            r.append("")
    header = rows[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * max_cols) + " |",
    ]
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


# ── xlsx ──
def _convert_xlsx(file_path: str) -> str | None:
    import openpyxl

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    parts: list[str] = [f"# {os.path.basename(file_path)}\n"]

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows_data = list(ws.iter_rows(values_only=True))
        rows_data = [r for r in rows_data if any(c is not None for c in r)]

        if not rows_data:
            parts.append(f"## Worksheet: {sheet_name}")
            parts.append("（空工作表）\n")
            continue

        parts.append(f"## Worksheet: {sheet_name}\n")
        max_cols = max(len(r) for r in rows_data)
        rows_data = [list(r) + [None] * (max_cols - len(r)) for r in rows_data]
        header = [str(c) if c is not None else "" for c in rows_data[0]]
        parts.append("| " + " | ".join(_esc_md_table(c) for c in header) + " |")
        parts.append("| " + " | ".join(["---"] * max_cols) + " |")
        for row in rows_data[1:]:
            cells = [str(c) if c is not None else "" for c in row]
            if not any(cells):
                continue
            parts.append("| " + " | ".join(_esc_md_table(c) for c in cells) + " |")
        parts.append("")

    wb.close()
    md = "\n".join(parts)
    return md if md.strip() else None


def _esc_md_table(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


# ── csv ──
def _convert_csv(file_path: str) -> str | None:
    file_name = os.path.basename(file_path)
    content = None
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"):
        try:
            with open(file_path, "r", encoding=enc) as f:
                content = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if content is None:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    if not content.strip():
        return None

    first_line = content.split("\n")[0]
    delimiters = [",", ";", "\t", "|"]
    delimiter = ","
    max_count = 0
    for d in delimiters:
        count = first_line.count(d)
        if count > max_count:
            max_count = count
            delimiter = d

    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return None

    parts = [f"# {file_name}\n"]
    max_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < max_cols:
            r.append("")
    header = [c.strip() for c in rows[0]]
    parts.append("| " + " | ".join(_esc_csv(c) for c in header) + " |")
    parts.append("| " + " | ".join(["---"] * max_cols) + " |")
    for row in rows[1:]:
        cells = [c.strip() for c in row]
        if not any(cells):
            continue
        parts.append("| " + " | ".join(_esc_csv(c) for c in cells) + " |")

    return "\n".join(parts)


def _esc_csv(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()
