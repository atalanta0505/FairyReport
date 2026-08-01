"""csv -> Markdown converter

- Auto-detect encoding (utf-8 / gbk / gb2312 / utf-8-sig / latin-1)
- Auto-detect delimiter (comma / semicolon / Tab / pipe)
- First row as header -> Markdown table
"""
import csv
import os


# Common delimiters, ordered by frequency of use
DELIMITERS = [',', ';', '\t', '|']

# Common encodings, ordered by frequency of use
ENCODINGS = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1']


def convert_csv(file_path: str) -> str:
    """Convert a CSV file to a Markdown table."""
    file_name = os.path.basename(file_path)

    # ── Detect encoding ──
    content = None
    used_encoding = 'utf-8'
    for enc in ENCODINGS:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
            used_encoding = enc
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if content is None:
        # Final fallback
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

    if not content.strip():
        return ''

    # ── Detect delimiter ──
    first_line = content.split('\n')[0]
    delimiter = ','
    max_count = 0
    for d in DELIMITERS:
        count = first_line.count(d)
        if count > max_count:
            max_count = count
            delimiter = d

    # ── Parse CSV ──
    import io
    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    rows = [r for r in reader if any(cell.strip() for cell in r)]

    if not rows:
        return ''

    # ── Build Markdown ──
    parts = [f"# {file_name}\n"]

    max_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < max_cols:
            r.append('')

    # Header
    header = [c.strip() for c in rows[0]]
    parts.append('| ' + ' | '.join(_esc(c) for c in header) + ' |')
    parts.append('| ' + ' | '.join(['---'] * max_cols) + ' |')

    # Data rows
    for row in rows[1:]:
        cells = [c.strip() for c in row]
        if not any(cells):
            continue
        parts.append('| ' + ' | '.join(_esc(c) for c in cells) + ' |')

    return '\n'.join(parts)


def _esc(text: str) -> str:
    """Escape special characters in Markdown table cells."""
    return text.replace('|', '\\|').replace('\n', ' ').strip()
