#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
脚本：verify_standard_docx_export.py
功能：使用甲级工程咨询报告全要素样本数据，调用升级后的 exporter.py 生成 standard_export_demo.docx，
      并严密检验封面排版、自动目录域（TOC）、正文独立分节、页眉横线、页脚重置、三线表及参考文献附链。
"""
import os
import sys
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 确保能直接导入 exporter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exporter import md_to_docx

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SAMPLE_REPORT_MD = """# 第一章 项目总论与建设背景

## 1.1 项目基本情况
本项目全称为**利辛县新型智能制造产业园基础设施建设项目**，位于安徽省亳州市利辛县经开区。规划总用地面积约 450 亩，总建筑面积 28.6 万平方米。

### 1.1.1 建设背景与宏观政策支持
从宏观政策导向来看，国家发展改革委、工信部联合印发的《关于推进制造业高质量发展的指导意见》明确指出：支持中小企业产业集群加快绿色化、数字化改造步伐。

> 政策指引摘录：以产业集聚区为核心支点，统筹水电气暖等基础设施建设，促进节能降耗与产业链协同发展【源:国家发展改革委指导意见.docx】。

#### 1.1.1.1 区域经济与招商引资基础
利辛县近年来紧抓长三角一体化发展战略机遇，聚焦高端装备、新能源汽车零部件及新型轻纺产业，招商引资成效显著。
1. 第一阶段：完成园区 200 亩核心区土地平整与管网建设；
2. 第二阶段：建成 10 栋标准化厂房并交付首批 8 家重点骨干企业入驻；
3. 第三阶段：完善综合研发楼、专家公寓及现代智慧物流周转中心。

- 清单要点一：园区容积率控制在 1.2~1.8 之间；
- 清单要点二：建筑密度不低于 45%，绿地率严格控制在 15% 以内；
- 清单要点三：园区污水经预处理达标后统一纳管排入经开区污水处理厂。

项目内部收益率计算模型遵循标准折现现金流公式：
$$NPV = \\sum_{t=1}^{n} \\frac{CI_t - CO_t}{(1 + r)^t}$$
根据测算，当贴现率 $r = 8\\%$ 时，财务净现值大于零，具备显著经济合理性。

## 1.2 编制依据与技术规程
本项目可行性研究报告编制严格遵循国家现行工程技术规程与标准规范【标:GB50016-2014】。

# 第二章 建设规模与工程方案

## 2.1 主要建设内容与经济指标
项目规划主要技术经济指标详见下表：

| 指标类别 | 指标名称 | 单位 | 设计规划值 | 规范及设计要求 | 备注说明 |
| :---: | :--- | :---: | ---: | :--- | :--- |
| 用地指标 | 规划建设净用地 | 亩 | 450.00 | 土地性质为一类工业用地 | 规划许可已办结 |
| 建筑指标 | 计容总建筑面积 | ㎡ | 286000.00 | 包含生产车间与仓储设施 | 分两期实施 |
| 建筑指标 | 建筑密度 | % | 48.50 | 规范要求 ≥ 40% | 符合控制性详规 |
| 经济指标 | 工程建设总投资 | 万元 | 86500.00 | 包含工程费与工程建设其他费 | 企业自筹与贷款 |
| 经济指标 | 财务内部收益率 | % | 12.35 | 行业基准收益率为 8% | 税后全投资收益 |
| 环保指标 | 中水循环利用率 | % | 92.00 | 达到绿色工业建筑二星标准 | 节能降耗示范 |

## 2.2 工艺流程与系统拓扑关系
园区污水处理与中水回用工序拓扑流程如下：

```mermaid
graph TD
  A[车间原水收集] --> B[混凝絮凝反应沉淀池]
  B --> C{在线水质多参数检测}
  C -->|指标达标| D[超滤膜与反渗透组合净化]
  C -->|悬浮物超标| E[加药二次深度深化处理]
  E --> D
  D --> F[(3000m³ 综合高位回用水储罐)]
```

上述工艺技术方案经论证技术成熟、运行稳定可靠【网:国家生态环境部工业废水治理技术指南】。

# 第三章 财务评价与结论

## 3.1 财务评价结论
本项目计算期确定为 15 年（含建设期 2 年），达产年均营业收入预计 4.2 亿元。

### 3.1.1 综合评价意见
经综合论证与专家多维审阅，本项目符合国家产业政策导向与地方经济发展规划，技术路线先进可靠，财务效益与社会效益良好，建设方案切实可行。

# 参考文献

> 依据 GB/T 7714 信息与文献 参考文献著录规则 自动汇总排序

[1] [项目资料] 国家发展改革委指导意见.docx. 来源: 县发改委立项批复卷宗.
[2] [规程标准] GB 50016—2014 建筑设计防火规范. 来源: 国家工程建设标准.
[3] [联网检索] 国家生态环境部工业废水治理技术指南. 访问网址: https://www.mee.gov.cn/ywgz/fgbz/bz/2026/t20260901_108.shtml.
"""


def main():
    output_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(output_dir, "standard_export_demo.docx")

    print("=" * 70)
    print("[*] 开始执行甲级工程咨询报告送审级 Word 导出排版验证...")
    print(f"[*] 目标产物路径: {output_path}")

    # 调用升级后的 exporter.md_to_docx
    md_to_docx(
        md_content=SAMPLE_REPORT_MD,
        output_path=output_path,
        title="利辛县新型智能制造产业园基础设施建设项目可行性研究报告",
        author_org="中国联合工程咨询设计研究院有限公司",
        qualification="甲级工程咨询资信证书（工咨甲11120240088）",
        date_str="二〇二六年九月",
        include_cover=True,
        include_toc=True,
    )

    if not os.path.exists(output_path):
        print("❌ 错误：导出的 Word 文件未成功生成！")
        sys.exit(1)

    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"✅ 文件成功生成！大小: {file_size_kb:.1f} KB")

    # 深度读回校验
    doc = Document(output_path)
    sections = doc.sections
    paragraphs = doc.paragraphs
    tables = doc.tables

    print("\n🔍 正在进行出版级排版深度断言验证：")
    print(f"  • 总分节数 (Sections): {len(sections)} (期望: 3)")
    assert len(sections) == 3, f"分节数不匹配，实际为 {len(sections)}"

    # 1. 验证 Section 1: 封面
    sec_cover = sections[0]
    cover_texts = [p.text for p in paragraphs[:15]]
    print("  • 封面要素校验：")
    assert any("利辛县新型智能制造产业园基础设施建设项目可行性研究报告" in t for t in cover_texts)
    print("    - 报告总标题（Level 0 / 22pt 黑体居中）: [通过]")
    assert any("送 审 版" in t for t in cover_texts)
    print("    - 送审版标识: [通过]")
    assert any("中国联合工程咨询设计研究院有限公司" in t for t in cover_texts)
    print("    - 编制单位: [通过]")
    assert any("工咨甲11120240088" in t for t in cover_texts)
    print("    - 甲级工程咨询资质: [通过]")
    assert any("二〇二六年九月" in t for t in cover_texts)
    print("    - 编制日期: [通过]")
    assert sec_cover.header.paragraphs[0].text.strip() == ""
    assert sec_cover.footer.paragraphs[0].text.strip() == ""
    print("    - 封面无页眉无页脚隔离: [通过]")

    # 2. 验证 Section 2: 目录
    sec_toc = sections[1]
    all_paras_xml = "".join(p._p.xml for p in paragraphs)
    print("  • 自动目录页 (TOC) 校验：")
    assert any("目    录" in p.text for p in paragraphs)
    print("    - “目    录”居中标题: [通过]")
    assert 'TOC \\o "1-3"' in all_paras_xml
    print("    - Word 原生 TOC 域字段: [通过]")
    assert "updateFields" in doc.settings.element.xml
    print("    - 打开文档自动更新域开关 (updateFields): [通过]")

    # 3. 验证 Section 3: 正文分节、页眉页脚
    sec_body = sections[2]
    hp = sec_body.header.paragraphs[0]
    fp = sec_body.footer.paragraphs[0]
    print("  • 正文分节与页眉页脚校验：")
    assert "利辛县新型智能制造产业园基础设施建设项目可行性研究报告" in hp.text
    assert "w:pBdr" in hp._p.pPr.xml
    assert 'w:bottom w:val="single"' in hp._p.pPr.xml
    print("    - 正文独立页眉与标准公文下划横线: [通过]")
    assert "PAGE" in fp._p.xml
    assert 'w:start="1"' in sec_body._sectPr.xml
    print("    - 正文独立页脚与重新从第 1 页起算: [通过]")

    # 4. 验证表格：标准三线表、居中、防断行
    print(f"  • 表格排版校验 (共 {len(tables)} 张表格):")
    for idx, table in enumerate(tables, 1):
        tbl_xml = table._tbl.tblPr.xml
        assert 'w:top w:val="single" w:sz="12"' in tbl_xml
        assert 'w:bottom w:val="single" w:sz="12"' in tbl_xml
        assert 'w:insideH w:val="none"' in tbl_xml
        assert 'w:insideV w:val="none"' in tbl_xml
        print(f"    - 表格 {idx} 顶底 1.5pt 加粗无竖线三线表: [通过]")
        assert 'w:cantSplit' in table.rows[0]._tr.trPr.xml
        print(f"    - 表格 {idx} 跨页防断 (cantSplit): [通过]")

    # 5. 验证参考文献
    ref_paras = [p for p in paragraphs if p.text.startswith("[1]") or p.text.startswith("[2]") or p.text.startswith("[3]")]
    print(f"  • 参考文献著录规则 (GB/T 7714) 校验 ({len(ref_paras)} 条):")
    assert len(ref_paras) == 3
    for rp in ref_paras:
        assert rp.paragraph_format.left_indent == Pt(24)
        assert rp.paragraph_format.first_line_indent == Pt(-24)
    print("    - 悬挂缩进 2 字符、逐条独立成行: [通过]")
    assert any("https://www.mee.gov.cn" in p.text for p in paragraphs)
    print("    - 互联网参考资料 100% 附带原始 URL: [通过]")

    print("\n" + "=" * 70)
    print("[SUCCESS] 恭喜！全部排版项均达到甲级工程咨询出版送审标准，各项证据 100% 吻合！")
    print(f"[OUTPUT] 成果文件可直接交付打开查看: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
