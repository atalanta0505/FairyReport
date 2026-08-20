"""生成最小 docx 测试 fixture（< 10KB，pandoc 与 python-docx 均可读）。"""
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))

DOC_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:body>'
    '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
    '<w:r><w:t>可行性研究样本</w:t></w:r></w:p>'
    '<w:p><w:r><w:t>本文件为测试样本，用于验证 docx 摄取流程。</w:t></w:r></w:p>'
    '<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr>'
    '<w:r><w:t>技术方案</w:t></w:r></w:p>'
    '<w:p><w:r><w:t>采用成熟工艺结合项目条件适配。</w:t></w:r></w:p>'
    '<w:p><w:r><w:t>投资估算控制在合理区间。</w:t></w:r></w:p>'
    '</w:body></w:document>'
)

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    '</Types>'
)

RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    '</Relationships>'
)

DOC_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    '</Relationships>'
)

STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:docDefaults><w:rPrDefault><w:rPr>'
    '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>'
    '<w:sz w:val="22"/>'
    '</w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="160" w:line="259" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
    '<w:name w:val="Normal"/>'
    '</w:style>'
    '<w:style w:type="paragraph" w:styleId="Heading1">'
    '<w:name w:val="heading 1"/>'
    '<w:pPr><w:outlineLvl w:val="0"/></w:pPr>'
    '</w:style>'
    '<w:style w:type="paragraph" w:styleId="Heading2">'
    '<w:name w:val="heading 2"/>'
    '<w:pPr><w:outlineLvl w:val="1"/></w:pPr>'
    '</w:style>'
    '</w:styles>'
)


def build(path: str | None = None) -> str:
    if path is None:
        path = os.path.join(HERE, "sample.docx")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", DOC_XML)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("word/styles.xml", STYLES)
    return path


if __name__ == "__main__":
    p = build()
    print(f"docx fixture: {p} ({os.path.getsize(p)} bytes)")
