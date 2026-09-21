"""PDF 转换模块

使用 pypdf 提取 PDF 纯文本并转为 Markdown 格式。
若遇到未包含文字图层的纯图片扫描件，给出明确的 OCR 转换指引。
"""
import os
from pypdf import PdfReader


def convert_pdf(file_path: str) -> str:
    """提取 PDF 文本并转换为 Markdown 格式字符串。"""
    fname = os.path.basename(file_path)
    try:
        reader = PdfReader(file_path)
        parts: list[str] = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                parts.append(f"<!-- Page {i + 1} -->\n{text.strip()}")

        if not parts:
            raise RuntimeError(
                f"PDF 文件「{fname}」中未检测到可提取的文本内容（可能为纯图片扫描件）。\n"
                f"建议使用 OCR 工具（如 MinerU、福昕 OCR 或微信识别）将 PDF 转换为文字或 Word/Markdown 后再导入。"
            )
        return f"# {fname}\n\n" + "\n\n".join(parts)
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"解析 PDF「{fname}」失败: {e}") from e

