"""PDF guidance module

Does not actually parse PDFs. When a PDF file is encountered, guide the user to pre-convert it to
Markdown using tools such as MinerU.
"""
import os


def convert_pdf(file_path: str) -> str:
    """PDF files are not supported for direct conversion; return guidance.

    Users must pre-convert PDFs to .md files using tools such as MinerU
    (https://github.com/opendatalab/MinerU) before placing them in the materials folder.
    """
    fname = os.path.basename(file_path)
    raise RuntimeError(
        f"PDF 不支持直接导入：{fname}\n"
        f"请先用 MinerU 等工具将 PDF 转为 .md 文件后再放入资料文件夹。\n"
        f"参考：https://github.com/opendatalab/MinerU"
    )
