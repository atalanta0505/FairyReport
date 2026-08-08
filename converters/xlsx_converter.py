"""xlsx -> Markdown converter

Each worksheet -> one Markdown table
- The first row is auto-detected as the header
- Empty rows are auto-skipped
- Multiple worksheets are separated by level-2 headings
"""
import os


def convert_xlsx(file_path: str) -> str:
    """Convert an xlsx file to Markdown (one table per sheet)."""
    import openpyxl

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    parts = []

    # File metadata
    parts.append(f"# {os.path.basename(file_path)}\n")

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows_data = list(ws.iter_rows(values_only=True))

        # Filter empty rows
        rows_data = [r for r in rows_data if any(c is not None for c in r)]

        if not rows_data:
            parts.append(f"## Worksheet: {sheet_name}")
            parts.append("（空工作表）\n")
            continue

        parts.append(f"## Worksheet: {sheet_name}\n")

        # Unify column count
        max_cols = max(len(r) for r in rows_data)
        for r in rows_data:
            while len(r) < max_cols:
                r = list(r) + [None]

        # Header
        header = [str(c) if c is not None else '' for c in rows_data[0]]
        parts.append('| ' + ' | '.join(_esc_md_table(c) for c in header) + ' |')
        parts.append('| ' + ' | '.join(['---'] * max_cols) + ' |')

        # Data rows (skip empty rows)
        for row in rows_data[1:]:
            cells = [str(c) if c is not None else '' for c in row]
            # Skip fully empty rows
            if not any(cells):
                continue
            parts.append('| ' + ' | '.join(_esc_md_table(c) for c in cells) + ' |')

        parts.append('')

    wb.close()
    return '\n'.join(parts)


def _esc_md_table(text: str) -> str:
    """Escape special characters in Markdown table cells."""
    return text.replace('|', '\\|').replace('\n', ' ').strip()
