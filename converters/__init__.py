"""
Unified file-to-Markdown entry point

Usage:
    from converters import to_markdown
    md_text, save_path = to_markdown("some_file.docx", output_dir=...)
    md_text, save_path = to_markdown("some_file.pdf", output_dir=...)  # PDF returns (None, None) directly
"""
import logging
import os
from pathlib import Path

from .docx_converter import convert_docx
from .xlsx_converter import convert_xlsx
from .csv_converter import convert_csv
from .pdf_converter import convert_pdf

_logger = logging.getLogger(__name__)

# Supported extension -> (converter, format name)
FORMAT_MAP = {
    '.docx': (convert_docx, 'Word 文档'),
    '.xlsx': (convert_xlsx, 'Excel 表格'),
    '.csv':  (convert_csv,  'CSV 表格'),
    '.txt':  (None,         '纯文本'),       # Read directly
    '.md':   (None,         'Markdown'),     # Already MD
}


def to_markdown(file_path: str, output_dir: str = None) -> tuple[str | None, str | None]:
    """
    Convert a file to Markdown.

    Args:
        file_path: absolute path to the file
        output_dir: MD output directory (when None, do not save the file, just return the text)

    Returns:
        (markdown_text, save_path)
        - Success: markdown_text is the MD string, save_path is the file path (when output_dir is not None)
        - PDF: returns (None, None)
        - txt/md: returns the original text directly
        - Failure: returns (None, None)
    """
    ext = os.path.splitext(file_path)[1].lower()

    # Unknown format
    if ext not in FORMAT_MAP:
        return None, None

    converter, format_name = FORMAT_MAP[ext]

    # txt / md: read directly
    if converter is None:
        text = _read_text(file_path)
        if not text.strip():
            return None, None
        save_path = None
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            save_path = os.path.join(output_dir, os.path.basename(file_path))
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(text)
        return text, save_path

    # Other formats: call the converter
    try:
        md_text = converter(file_path)
    except Exception as e:
        _logger.warning("%s conversion failed: %s", os.path.basename(file_path), e)
        return None, None

    if not md_text or not md_text.strip():
        print(f"  ⚠️ {os.path.basename(file_path)} converted content is empty")
        return None, None

    # Save the MD file
    save_path = None
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(file_path))[0]
        save_path = os.path.join(output_dir, f"{base}.md")
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(md_text)

    return md_text, save_path


def _read_text(file_path: str) -> str:
    """Read a text file, trying multiple encodings.

    Uses strict decoding for each candidate so that GBK/GB2312 fallbacks
    actually trigger (unlike errors='replace' which silently succeeds with
    UTF-8 on any byte sequence). Falls back to UTF-8 with replacement
    only as a last resort.
    """
    # Phase 1: try candidate encodings with strict decoding
    for encoding in ('utf-8-sig', 'utf-8', 'gbk', 'gb2312'):
        try:
            with open(file_path, 'r', encoding=encoding, errors='strict') as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            _logger.debug("Reading %s with encoding %s failed, trying next", file_path, encoding)
            continue
        except Exception as e:
            _logger.debug("Reading %s with encoding %s failed: %s", file_path, encoding, e)
            continue

    # Phase 2: last resort — read raw bytes and decode with replacement
    try:
        with open(file_path, 'rb') as f:
            raw = f.read()
        return raw.decode('utf-8', errors='replace')
    except Exception as e:
        _logger.warning("Failed to read %s: %s", file_path, e)
        return ""


def get_format_name(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in FORMAT_MAP:
        return FORMAT_MAP[ext][1]
    return os.path.splitext(file_path)[1]
