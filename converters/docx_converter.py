"""docx -> Markdown converter

Prefers pandoc (preserves full structure: headings/bold/italic/lists/tables/links/images)
Falls back to python-docx (only heading levels and basic tables) if pandoc is unavailable
"""
import os
import subprocess


def convert_docx(file_path: str) -> str:
    """Convert a docx file to Markdown."""

    # ── Option 1: pandoc ──
    try:
        result = subprocess.run(
            ['pandoc', '-f', 'docx', '-t', 'markdown', '--wrap=none', file_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass  # pandoc unavailable, fall back

    # ── Option 2: python-docx ──
    return _convert_with_python_docx(file_path)


def _convert_with_python_docx(file_path: str) -> str:
    """Parse docx with python-docx, preserving structure as much as possible."""
    from docx import Document

    doc = Document(file_path)
    parts = []

    # Paragraphs
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            parts.append('')
            continue

        style = para.style.name.lower()

        # Heading
        if style.startswith('heading'):
            level = style.replace('heading ', '')
            if level.isdigit():
                prefix = '#' * int(level)
            else:
                prefix = '##'
            parts.append(f"{prefix} {text}")
            continue

        # List (try to detect indented paragraphs)
        if para.paragraph_format.left_indent and para.paragraph_format.left_indent > 0:
            # Indented paragraph -> list item
            indent_level = int(para.paragraph_format.left_indent / 180_000)  # EMU ≈ 72pt
            prefix = '  ' * indent_level + '- '
            parts.append(f"{prefix}{text}")
            continue

        # Regular paragraph -> handle inline formatting
        formatted = _format_run(para)
        parts.append(formatted)

    # Tables -> Markdown tables
    for idx, table in enumerate(doc.tables):
        parts.append('')
        parts.append(f"**[Table {idx + 1}]**")
        parts.append('')
        parts.append(_table_to_markdown(table))
        parts.append('')

    return '\n'.join(parts)


def _format_run(para) -> str:
    """Handle inline formatting in a paragraph (bold, italic)."""
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
    return ''.join(parts) if parts else para.text


def _table_to_markdown(table) -> str:
    """Convert a python-docx Table to a Markdown table."""
    rows = []
    for row in table.rows:
        cells = [cell.text.replace('\n', ' ').replace('|', '\\|').strip() for cell in row.cells]
        if any(c for c in cells):  # Skip empty rows
            rows.append(cells)

    if not rows:
        return ''

    # Unify column count
    max_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < max_cols:
            r.append('')

    # First row as header
    header = rows[0]
    separator = ['---'] * max_cols
    lines = []
    lines.append('| ' + ' | '.join(header) + ' |')
    lines.append('| ' + ' | '.join(separator) + ' |')
    for row in rows[1:]:
        lines.append('| ' + ' | '.join(row) + ' |')

    return '\n'.join(lines)
