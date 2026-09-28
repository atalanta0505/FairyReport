import { describe, expect, it } from "vitest";
import {
  buildGeneralizedRegex,
  countContentChars,
  countContentCharsExcludingTables,
  assignGlobalRefNumbers,
  convertRefsToNumberedCitations,
  generateBibliographySection,
  escapeHtml,
  extractIssueCandidateKeys,
  extractOutlineHeadings,
  extractReferences,
  extractSubHeadings,
  formatInline,
  getReferencesSummary,
  highlightIssuesInHtml,
  htmlToMarkdown,
  markdownToHtml,
  normalizeMarkdown,
  renderMarkdown,
  stripMarkdownTables,
  unescapeHtml,
} from "../lib/markdown";

describe("Markdown 解析与排版工具", () => {
  describe("基础与边界情况", () => {
    it("空字符串或纯空白返回空", () => {
      expect(markdownToHtml("")).toBe("");
      expect(markdownToHtml("   \n\t  ")).toBe("");
      expect(htmlToMarkdown("")).toBe("");
      expect(extractSubHeadings("")).toEqual([]);
    });

    it("HTML 实体转义与反转义保护及别名兼容", () => {
      expect(renderMarkdown).toBe(markdownToHtml);
      const escaped = escapeHtml("<script>alert('xss')</script>");
      expect(escaped).toBe("&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;");
      expect(unescapeHtml(escaped)).toBe("<script>alert('xss')</script>");

      const rendered = markdownToHtml("<script>alert(1)</script>");
      expect(rendered).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
      expect(rendered).not.toContain("<script>");
    });
  });

  describe("各级标题渲染与锚点生成 (markdownToHtml)", () => {
    it("支持 H1 至 H4 各级标题与内联样式并带唯一锚点 ID", () => {
      const md = [
        "# 第一章 工程概况",
        "## 1.1 地理位置",
        "### 1.1.1 经纬度坐标",
        "#### 详细测绘数据",
      ].join("\n");

      const html = markdownToHtml(md, 1);
      expect(html).toContain('<h1 id="h-ch1-idx0">第一章 工程概况</h1>');
      expect(html).toContain('<h2 id="h-ch1-idx1">1.1 地理位置</h2>');
      expect(html).toContain('<h3 id="h-ch1-idx2">1.1.1 经纬度坐标</h3>');
      expect(html).toContain('<h4 id="h-ch1-idx3">详细测绘数据</h4>');
    });

    it("标题与加粗/来源标签粘连时自动拆分为独立标题与正文段落", () => {
      const md = "# 第一章 建设背景 **重点** 【源:规划纲要.docx】";
      const html = markdownToHtml(md, 2);
      expect(html).toContain('<h1 id="h-ch2-idx0">第一章 建设背景</h1>');
      expect(html).toContain('<p><strong>重点</strong> <span class="inline-ref-tag type-material" data-ref-type="material" data-ref-title="规划纲要.docx" title="点击查看参考资料出处">【源:规划纲要.docx】</span></p>');
    });
  });

  describe("内联格式与来源徽章", () => {
    it("粗体、斜体、删除线与行内代码", () => {
      const text = "这是 **粗体** 和 *斜体* 以及 `const a = 1;` 和 ~~删除内容~~";
      const html = formatInline(text);
      expect(html).toContain("<strong>粗体</strong>");
      expect(html).toContain("<em>斜体</em>");
      expect(html).toContain("<code>const a = 1;</code>");
      expect(html).toContain("<del>删除内容</del>");
    });

    it("来源标签自动识别并语义化内联标签化 (inline-ref-tag)", () => {
      const text = "本段引自水利规程【源:水利规程.docx#L1-10】以及地质监测【源：监测报告.pdf】。";
      const html = formatInline(text);
      expect(html).toContain('<span class="inline-ref-tag type-standard" data-ref-type="standard" data-ref-title="水利规程.docx#L1-10" title="点击查看参考资料出处">【源:水利规程.docx#L1-10】</span>');
      expect(html).toContain('<span class="inline-ref-tag type-material" data-ref-type="material" data-ref-title="监测报告.pdf" title="点击查看参考资料出处">【源：监测报告.pdf】</span>');
    });

    it("行内代码中的特殊字符不被二次解析", () => {
      const text = "配置为 `**not-bold**` 格式";
      const html = formatInline(text);
      expect(html).toContain("<code>**not-bold**</code>");
      expect(html).not.toContain("<strong>not-bold</strong>");
    });
  });

  describe("列表解析 (无序与有序)", () => {
    it("无序列表渲染", () => {
      const md = [
        "- 水库大坝建设",
        "- 溢洪道加固",
        "* 输水隧洞改造",
      ].join("\n");

      const html = markdownToHtml(md);
      expect(html).toContain("<ul>");
      expect(html).toContain("<li>水库大坝建设</li>");
      expect(html).toContain("<li>溢洪道加固</li>");
      expect(html).toContain("<li>输水隧洞改造</li>");
      expect(html).toContain("</ul>");
    });

    it("有序列表渲染", () => {
      const md = [
        "1. 第一阶段规划",
        "2. 第二阶段实施",
        "3) 第三阶段验收",
      ].join("\n");

      const html = markdownToHtml(md);
      expect(html).toContain("<ol>");
      expect(html).toContain("<li>第一阶段规划</li>");
      expect(html).toContain("<li>第二阶段实施</li>");
      expect(html).toContain("<li>第三阶段验收</li>");
      expect(html).toContain("</ol>");
    });
  });

  describe("表格解析 (Markdown Table)", () => {
    it("正确生成 table, thead, tbody, th, td", () => {
      const md = [
        "| 指标名称 | 单位 | 规划目标值 | 来源 |",
        "| :--- | :---: | ---: | --- |",
        "| 总库容 | 万m³ | 1500 | 【源:立项批复.docx】 |",
        "| 防洪标准 | 年一遇 | 100 | 【源:防洪规程.pdf】 |",
      ].join("\n");

      const html = markdownToHtml(md);
      expect(html).toContain("<table>");
      expect(html).toContain("<thead><tr><th>指标名称</th><th>单位</th><th>规划目标值</th><th>来源</th></tr></thead>");
      expect(html).toContain("<tbody>");
      expect(html).toContain("<td>总库容</td>");
      expect(html).toContain("<td>万m³</td>");
      expect(html).toContain("<td>1500</td>");
      expect(html).toContain('<span class="inline-ref-tag type-material" data-ref-type="material" data-ref-title="立项批复.docx" title="点击查看参考资料出处">【源:立项批复.docx】</span>');
      expect(html).toContain("</table>");
    });
  });

  describe("引用块与代码块", () => {
    it("引用块渲染 blockquote", () => {
      const md = [
        "> 引用第一行规范说明",
        "> 引用第二行重点提示 【源:设计手册.pdf】",
      ].join("\n");

      const html = markdownToHtml(md);
      expect(html).toContain("<blockquote><p>");
      expect(html).toContain("引用第一行规范说明<br />引用第二行重点提示 <span class=\"inline-ref-tag type-material\" data-ref-type=\"material\" data-ref-title=\"设计手册.pdf\" title=\"点击查看参考资料出处\">【源:设计手册.pdf】</span>");
      expect(html).toContain("</p></blockquote>");
    });

    it("多行代码块渲染 pre code", () => {
      const md = [
        "```python",
        "def compute_flood(flow, rate):",
        "    return flow * rate",
        "```",
      ].join("\n");

      const html = markdownToHtml(md);
      expect(html).toContain('<pre><code class="language-python">');
      expect(html).toContain("def compute_flood(flow, rate):");
      expect(html).toContain("</code></pre>");
    });
  });

  describe("提取多级子标题 (extractSubHeadings)", () => {
    it("准确提取 H1 至 H4 各级标题与对应锚点 ID", () => {
      const md = [
        "# 第二章 工程建设方案",
        "正文说明段落...",
        "## 2.1 大坝工程",
        "### 2.1.1 坝体填筑方案",
        "#### 材料配比与压实要求",
        "```markdown",
        "# 代码块内的假标题不应被提取",
        "```",
        "## 2.2 泄洪设施 【源:规划.docx】",
      ].join("\n");

      const headings = extractSubHeadings(md, 2);
      expect(headings).toHaveLength(5);
      expect(headings[0]).toEqual({
        id: "h-ch2-idx0",
        level: 1,
        title: "第二章 工程建设方案",
        raw: "# 第二章 工程建设方案",
        index: 0,
      });
      expect(headings[1]).toEqual({
        id: "h-ch2-idx1",
        level: 2,
        title: "2.1 大坝工程",
        raw: "## 2.1 大坝工程",
        index: 1,
      });
      expect(headings[2]).toEqual({
        id: "h-ch2-idx2",
        level: 3,
        title: "2.1.1 坝体填筑方案",
        raw: "### 2.1.1 坝体填筑方案",
        index: 2,
      });
      expect(headings[3]).toEqual({
        id: "h-ch2-idx3",
        level: 4,
        title: "材料配比与压实要求",
        raw: "#### 材料配比与压实要求",
        index: 3,
      });
      expect(headings[4]).toEqual({
        id: "h-ch2-idx4",
        level: 2,
        title: "2.2 泄洪设施",
        raw: "## 2.2 泄洪设施",
        index: 4,
      });
    });
  });

  describe("HTML 反向解析为 Markdown (htmlToMarkdown)", () => {
    it("标题、粗体、斜体、列表反序列化", () => {
      const html = [
        '<h1 id="h-ch1-idx0">第一章 绪论</h1>',
        '<p>本章叙述 <strong>重要背景</strong> 和 <em>设计目的</em>。</p>',
        '<ul><li>项目一</li><li>项目二</li></ul>',
        '<ol><li>阶段一</li><li>阶段二</li></ol>',
      ].join("\n");

      const md = htmlToMarkdown(html);
      expect(md).toContain("# 第一章 绪论");
      expect(md).toContain("本章叙述 **重要背景** 和 *设计目的*。");
      expect(md).toContain("- 项目一\n- 项目二");
      expect(md).toContain("1. 阶段一\n2. 阶段二");
    });

    it("来源徽章与表格反序列化", () => {
      const html = [
        '<p>依据要求 <span class="ref-badge">🏷️ 【源:水利方案.docx】</span> 落实。</p>',
        '<table><thead><tr><th>项目</th><th>指标</th></tr></thead><tbody><tr><td>容积</td><td>500</td></tr></tbody></table>',
      ].join("\n");

      const md = htmlToMarkdown(html);
      expect(md).toContain("依据要求 【源:水利方案.docx】 落实。");
      expect(md).toContain("| 项目 | 指标 |");
      expect(md).toContain("| --- | --- |");
      expect(md).toContain("| 容积 | 500 |");
    });

    it("引用块与代码块反序列化", () => {
      const html = [
        '<blockquote><p>重点指示第一条<br />重点指示第二条</p></blockquote>',
        '<pre><code class="language-rust">fn main() {\n    println!("hello");\n}</code></pre>',
      ].join("\n");

      const md = htmlToMarkdown(html);
      expect(md).toContain("> 重点指示第一条\n> 重点指示第二条");
      expect(md).toContain("```rust\nfn main() {\n    println!(\"hello\");\n}\n```");
    });

    it("Mermaid 流程图容器反序列化为 mermaid 代码块", () => {
      const mdCode = "graph TD\n  A[入料] --> B[粉碎] --> C[(成品仓)]";
      const html = markdownToHtml(`\`\`\`mermaid\n${mdCode}\n\`\`\``);
      const restoredMd = htmlToMarkdown(html);
      expect(restoredMd).toContain("```mermaid");
      expect(restoredMd).toContain("A[入料] --> B[粉碎] --> C[(成品仓)]");
    });
  });

  describe("Markdown 预处理与标题断行规范化 (normalizeMarkdown)", () => {
    it("自动解开粘连的各级标题", () => {
      const glued = "# 第一章 概述## 1.1 项目概况### 1.1.1 项目名称\n\n本工程位于长江中下游流域。";
      const normalized = normalizeMarkdown(glued);
      expect(normalized).toContain("# 第一章 概述\n\n## 1.1 项目概况\n\n### 1.1.1 项目名称\n\n本工程位于长江中下游流域。");
    });

    it("正文紧邻标题自动补双换行", () => {
      const text = "这是前置段落描述。## 2.1 建设规划### 2.1.1 总体布局";
      const normalized = normalizeMarkdown(text);
      expect(normalized).toBe("这是前置段落描述。\n\n## 2.1 建设规划\n\n### 2.1.1 总体布局");
    });

    it("表格与前文粘连时自动规范化换行", () => {
      const text = "说明文字| 表头1 | 表头2 |\n| --- | --- |\n| 单元格1 | 单元格2 |";
      const normalized = normalizeMarkdown(text);
      expect(normalized).toContain("说明文字\n\n| 表头1 | 表头2 |\n| --- | --- |\n| 单元格1 | 单元格2 |");
    });

    it("单行用 || 连接的表格自动还原为标准多行 GFM 表格", () => {
      const singleLineTable = "| 序号 | 指标名称 | 单位 | 目标值 || :--- | :--- | :--- | :--- || 1 | 规划面积 | 平方公里 | 25.4 || 2 | 总投资 | 亿元 | 120 |";
      const normalized = normalizeMarkdown(singleLineTable);
      expect(normalized).toBe(
        "| 序号 | 指标名称 | 单位 | 目标值 |\n| :--- | :--- | :--- | :--- |\n| 1 | 规划面积 | 平方公里 | 25.4 |\n| 2 | 总投资 | 亿元 | 120 |"
      );

      const html = markdownToHtml(singleLineTable);
      expect(html).toContain("<table>");
      expect(html).toContain("<thead><tr><th>序号</th><th>指标名称</th><th>单位</th><th>目标值</th></tr></thead>");
      expect(html).toContain("<tbody>");
      expect(html).toContain("<td>规划面积</td>");
      expect(html).toContain("<td>120</td>");
    });

    it("标题与加粗、来源引用、表格粘连自动拆分", () => {
      const gluedBold = "### 1.1.1 建设地点**项目名称**：本项目位于武汉市。";
      expect(normalizeMarkdown(gluedBold)).toBe("### 1.1.1 建设地点\n\n**项目名称**：本项目位于武汉市。");

      const gluedRef = "### 1.1.2 编制依据【源:批复文件.docx】根据发改委文件...";
      expect(normalizeMarkdown(gluedRef)).toBe("### 1.1.2 编制依据\n\n【源:批复文件.docx】根据发改委文件...");

      const gluedTable = "### 1.1.6 主要技术经济指标| 序号 | 指标 || --- | --- || 1 | 产能 |";
      const normTable = normalizeMarkdown(gluedTable);
      expect(normTable).toContain("### 1.1.6 主要技术经济指标\n\n| 序号 | 指标 |");
      expect(normTable).toContain("| 1 | 产能 |");
    });

    it("复合章节小节标题完整保留为单行（杜绝掉字与断行 Bug）", () => {
      // 8.1 经济影响分析
      expect(normalizeMarkdown("### 8.1 经济影响分析")).toBe("### 8.1 经济影响分析");
      // 1.3.3 主要标准规范
      expect(normalizeMarkdown("### 1.3.3 主要标准规范")).toBe("### 1.3.3 主要标准规范");
      // 1.1.2 项目建设目标与任务
      expect(normalizeMarkdown("### 1.1.2 项目建设目标与任务")).toBe("### 1.1.2 项目建设目标与任务");
      // 1.4.1 主要研究结论
      expect(normalizeMarkdown("### 1.4.1 主要研究结论")).toBe("### 1.4.1 主要研究结论");
      // 2.2.1 规划政策符合性分析
      expect(normalizeMarkdown("### 2.2.1 规划政策符合性分析")).toBe("### 2.2.1 规划政策符合性分析");
      // 1.1.4 投资估算与资金筹措方案
      expect(normalizeMarkdown("### 1.1.4 投资估算与资金筹措方案")).toBe("### 1.1.4 投资估算与资金筹措方案");
    });

    it("单行标题紧跟正文标点时精确拆分为独立标题与正文段落", () => {
      // 冒号拆分
      const s1 = "### 1.4.1 主要研究结论：经研究论证，本项目符合国家重大基础设施建设规划。";
      expect(normalizeMarkdown(s1)).toBe("### 1.4.1 主要研究结论\n\n经研究论证，本项目符合国家重大基础设施建设规划。");

      // 句号拆分
      const s2 = "### 1.4.2 问题与建议。重点关注问题：第一，资金落实进度；第二，征地拆迁。";
      expect(normalizeMarkdown(s2)).toBe("### 1.4.2 问题与建议\n\n重点关注问题：第一，资金落实进度；第二，征地拆迁。");

      // 破折号拆分
      const s3 = "### 2.2.1 与经济社会发展规划衔接性——国家“十四五”发展规划明确指出要加快现代水网建设。";
      expect(normalizeMarkdown(s3)).toBe("### 2.2.1 与经济社会发展规划衔接性\n\n国家“十四五”发展规划明确指出要加快现代水网建设。");

      // 英文冒号拆分
      const s4 = "### 1.1.1 建设地点: 本项目位于武汉市江夏区。";
      expect(normalizeMarkdown(s4)).toBe("### 1.1.1 建设地点\n\n本项目位于武汉市江夏区。");
    });

    it("支持已知大纲标题库配合正文标点精确断行", () => {
      const customGlued = "### 1.1.6 特殊定制标题：这里是自定义的正文开始...";
      const knownHeadings = ["1.1.6 特殊定制标题", "特殊定制标题"];
      const normalized = normalizeMarkdown(customGlued, knownHeadings);
      expect(normalized).toBe("### 1.1.6 特殊定制标题\n\n这里是自定义的正文开始...");

      const gluedWithoutNumInHeading = "### 1.4.1 主要研究结论：经深入评估...";
      const normWithOnlyTitle = normalizeMarkdown(gluedWithoutNumInHeading, ["主要研究结论"]);
      expect(normWithOnlyTitle).toBe("### 1.4.1 主要研究结论\n\n经深入评估...");
    });

    it("支持已知大纲标题库与中文正文无标点直接紧连时精确断行（彻底根除粘连）", () => {
      // 场景 1：已知标题后无任何标点，直接紧连中文正文
      const directGlued = "### 1.4.1 主要研究结论经系统论证，本项目符合国家基础设施规划。";
      const known = ["1.4.1 主要研究结论", "主要研究结论"];
      const res1 = normalizeMarkdown(directGlued, known);
      expect(res1).toBe("### 1.4.1 主要研究结论\n\n经系统论证，本项目符合国家基础设施规划。");

      // 场景 2：带空格但无标点紧连
      const spaceGlued = "### 1.1.2 建设目标与任务 本工程主要目标为防洪与灌溉。";
      const res2 = normalizeMarkdown(spaceGlued, ["建设目标与任务"]);
      expect(res2).toBe("### 1.1.2 建设目标与任务\n\n本工程主要目标为防洪与灌溉。");

      // 场景 3：extractSubHeadings 提取出的子标题在无标点粘连下依然纯净
      const subHeadings = extractSubHeadings(directGlued, 1, known);
      expect(subHeadings).toHaveLength(1);
      expect(subHeadings[0].title).toBe("1.4.1 主要研究结论");
      expect(subHeadings[0].title).not.toContain("经系统论证");
    });

    it("空值或非字符串防御", () => {
      expect(normalizeMarkdown("")).toBe("");
      expect(normalizeMarkdown(null as unknown as string)).toBe("");
      expect(normalizeMarkdown(undefined as unknown as string)).toBe("");
    });

    it("粘连标题在 extractSubHeadings 中被精准拆分为独立纯净标题（不含正文）", () => {
      const glued = [
        "# 第一章 概述## 1.1 项目概况### 1.1.1 项目名称",
        "### 1.1.6 主要技术经济指标：项目主要技术经济指标如下表所示：",
        "| 序号 | 指标 || --- | --- || 1 | 库容 |",
      ].join("\n");

      const headings = extractSubHeadings(glued, 1);
      expect(headings).toHaveLength(4);
      expect(headings[0].title).toBe("第一章 概述");
      expect(headings[1].title).toBe("1.1 项目概况");
      expect(headings[2].title).toBe("1.1.1 项目名称");
      expect(headings[3].title).toBe("1.1.6 主要技术经济指标");
      expect(headings[3].title).not.toContain("项目主要技术经济指标如下表所示");
    });

    it("粘连标题与单行表格在 markdownToHtml 中被正确渲染为独立 HTML 标签与表格", () => {
      const glued = "### 1.1.6 主要技术经济指标：项目主要技术经济指标如下：| 序号 | 指标 || --- | --- || 1 | 投资 |";
      const html = markdownToHtml(glued, 1);
      expect(html).toContain('<h3 id="h-ch1-idx0">1.1.6 主要技术经济指标</h3>');
      expect(html).toContain('<p>项目主要技术经济指标如下：</p>');
      expect(html).toContain('<table>');
      expect(html).toContain('<td>投资</td>');
      expect(html).not.toContain('<h3 id="h-ch1-idx0">1.1.6 主要技术经济指标项目主要技术经济指标');
    });
  });

  describe("大纲标题库提取 (extractOutlineHeadings)", () => {
    it("从完整大纲 Markdown 中提取所有各级纯净标题并降序排序", () => {
      const outlineMd = [
        "# 第一章 概述",
        "## 1.1 项目概况",
        "### 1.4.1 主要研究结论",
        "### 1.4.2 问题与建议",
        "# 第二章 项目建设背景与必要性",
        "## 2.2 规划符合性分析",
        "### 2.2.1 与经济社会发展规划衔接性",
        "### 2.2.2 与区域规划衔接性",
        "### 2.2.4 与国土空间规划衔接性",
        "## 2.3 项目建设必要性",
        "### 2.3.1 宏观层面必要性",
        "### 2.3.4 建设时机适当时",
      ].join("\n");

      const headings = extractOutlineHeadings(outlineMd);
      expect(headings).toContain("第一章 概述");
      expect(headings).toContain("概述");
      expect(headings).toContain("1.4.1 主要研究结论");
      expect(headings).toContain("主要研究结论");
      expect(headings).toContain("2.2.1 与经济社会发展规划衔接性");
      expect(headings).toContain("与经济社会发展规划衔接性");
      expect(headings).toContain("2.3.4 建设时机适当时");
      expect(headings).toContain("建设时机适当时");

      // 验证按长度降序排列
      for (let i = 0; i < headings.length - 1; i++) {
        expect(headings[i].length).toBeGreaterThanOrEqual(headings[i + 1].length);
      }
    });

    it("空值或非字符串防御", () => {
      expect(extractOutlineHeadings("")).toEqual([]);
      expect(extractOutlineHeadings(null as unknown as string)).toEqual([]);
      expect(extractOutlineHeadings(undefined as unknown as string)).toEqual([]);
    });

    it("大纲标题与正文粘连全场景配合解耦验证", () => {
      const outlineMd = [
        "# 第一章 概述",
        "### 1.4.1 主要研究结论",
        "### 1.4.2 问题与建议",
        "### 2.2.1 与经济社会发展规划衔接性",
      ].join("\n");

      const knownHeadings = extractOutlineHeadings(outlineMd);

      const chapterText = [
        "### 1.4.1 主要研究结论：经系统论证，各项指标均满足要求。",
        "### 1.4.2 问题与建议：重点建议：抓紧前期审批。",
        "### 2.2.1 与经济社会发展规划衔接性：符合省市一体化战略。",
      ].join("\n");

      const normalized = normalizeMarkdown(chapterText, knownHeadings);
      expect(normalized).toContain("### 1.4.1 主要研究结论\n\n经系统论证，各项指标均满足要求。");
      expect(normalized).toContain("### 1.4.2 问题与建议\n\n重点建议：抓紧前期审批。");
      expect(normalized).toContain("### 2.2.1 与经济社会发展规划衔接性\n\n符合省市一体化战略。");

      const subHeadings = extractSubHeadings(chapterText, 1, knownHeadings);
      expect(subHeadings).toHaveLength(3);
      expect(subHeadings[0].title).toBe("1.4.1 主要研究结论");
      expect(subHeadings[1].title).toBe("1.4.2 问题与建议");
      expect(subHeadings[2].title).toBe("2.2.1 与经济社会发展规划衔接性");

      const html = markdownToHtml(chapterText, 1, knownHeadings);
      expect(html).toContain('<h3 id="h-ch1-idx0">1.4.1 主要研究结论</h3>');
      expect(html).toContain('<p>经系统论证，各项指标均满足要求。</p>');
      expect(html).toContain('<h3 id="h-ch1-idx1">1.4.2 问题与建议</h3>');
      expect(html).toContain('<p>重点建议：抓紧前期审批。</p>');
      expect(html).toContain('<h3 id="h-ch1-idx2">2.2.1 与经济社会发展规划衔接性</h3>');
      expect(html).toContain('<p>符合省市一体化战略。</p>');
    });
  });

  describe("参考资料来源提取 (extractReferences)", () => {
    it("空文本或无标签返回空数组", () => {
      expect(extractReferences("")).toEqual([]);
      expect(extractReferences("普通正文无任何来源标签")).toEqual([]);
    });

    it("精准提取工程底稿文件来源与频次", () => {
      const text = `
        根据立项批复【源:立项批复文件.docx#L1-10】，本工程总投资 3.5 亿元。
        地质勘察表明【源:地质勘察报告.pdf】，地基承载力良好。
        再次核实【源:立项批复文件.docx#L1-10】，资金筹措方案符合规定。
      `;
      const refs = extractReferences(text);
      expect(refs).toHaveLength(2);
      expect(refs[0].title).toBe("立项批复文件.docx#L1-10");
      expect(refs[0].count).toBe(2);
      expect(refs[0].type).toBe("material");
      expect(refs[0].typeLabel).toBe("项目底稿");

      expect(refs[1].title).toBe("地质勘察报告.pdf");
      expect(refs[1].count).toBe(1);
      expect(refs[1].typeLabel).toBe("项目底稿");
    });

    it("精准分类规程标准、网络来源与参考文献 [Z]", () => {
      const text = `
        依据规程【标:水利水电工程可行性研究报告编制规程】要求；
        结合防洪标准【源:防洪标准GB50201-2014.pdf】测算；
        参考网络数据【网:水利部水雨情信息网】；
        标准规范依据 [Z] 与专题规范 [Z-02]。
      `;
      const refs = extractReferences(text);
      expect(refs.some((r) => r.type === "standard" && r.title.includes("编制规程"))).toBe(true);
      expect(refs.some((r) => r.type === "standard" && r.title.includes("GB50201"))).toBe(true);
      expect(refs.some((r) => r.type === "web" && r.title.includes("水雨情信息网"))).toBe(true);
      expect(refs.some((r) => r.type === "standard" && r.title.includes("[Z]"))).toBe(true);
      expect(refs.some((r) => r.type === "standard" && r.title.includes("[Z-02]"))).toBe(true);
    });

    it("提取网络检索引用并正确关联 URL", () => {
      const text = `
        根据国家政策【网:国家发改委可研编制大纲】，本项目属于鼓励类产业。
      `;
      const ragContext = `
        【网:国家发改委可研编制大纲】
          https://www.ndrc.gov.cn/policy/123
          > 建设标准规程正文。
      `;
      const refs = extractReferences(text, ragContext);
      expect(refs).toHaveLength(1);
      expect(refs[0].type).toBe("web");
      expect(refs[0].title).toBe("国家发改委可研编制大纲");
      expect(refs[0].url).toBe("https://www.ndrc.gov.cn/policy/123");
    });
  });

  describe("审阅高亮与 HTML 反向序列化还原", () => {
    it("htmlToMarkdown 能够正确剥离 review-issue-highlight 标签并保留纯文本", () => {
      const html = '<p>本项目总投资为 <mark class="review-issue-highlight severity-warning" data-issue-id="ISS-1" title="数值自洽: 投资不一致">3500 万元</mark>，工期为 18 个月。</p>';
      const md = htmlToMarkdown(html);
      expect(md).toBe("本项目总投资为 3500 万元，工期为 18 个月。");
      expect(md).not.toContain("<mark");
    });

    it("extractIssueCandidateKeys: 多级特征提取（quote -> 引号内容 -> 工程数值 -> location）", () => {
      // 1. 优先 quote
      const k1 = extractIssueCandidateKeys({
        category: "测试",
        message: "测试消息包含“其他内容”和 5000 万元",
        quote: "  这是直接摘录的文本  ",
        severity: "warning",
      });
      expect(k1).toEqual(["这是直接摘录的文本"]);

      // 2. 无 quote，提取 message 中的引号
      const k2 = extractIssueCandidateKeys({
        category: "测试",
        message: "核实该段落「重要防洪指标」的合理性",
        severity: "error",
      });
      expect(k2).toEqual(["重要防洪指标"]);

      // 3. 无 quote 与引号，提取核心数值与单位
      const k3 = extractIssueCandidateKeys({
        category: "测试",
        message: "设计年径流量 1500万m³ 与水库规模不符",
        severity: "suggestion",
      });
      expect(k3).toContain("1500万m³");

      // 4. 仅有 location
      const k4 = extractIssueCandidateKeys({
        category: "测试",
        location: "第 2 章 2.3 水土保持与环境影响分析",
        message: "缺少必要的水保方案论证",
        severity: "warning",
      });
      expect(k4).toContain("水土保持与环境影响分析");
    });

    it("buildGeneralizedRegex: 全半角标点与空白泛化匹配", () => {
      const regex = buildGeneralizedRegex("投资3500万元，工期（18个月）：符合规划。");
      // 半角逗号、半角括号、半角冒号、半角句号均应匹配
      expect(regex.test("投资3500万元,工期(18个月):符合规划.")).toBe(true);
      // 中文全角标点应匹配
      expect(regex.test("投资3500万元，工期（18个月）：符合规划。")).toBe(true);
    });

    it("highlightIssuesInHtml: 级别 1 精确匹配并注入规范 mark 标签", () => {
      const html = "<p>本项目总投资为 3500 万元，工期为 18 个月。</p>";
      const issues = [
        {
          id: "ISS-101",
          category: "数值自洽",
          severity: "warning",
          message: "投资数据不一致",
          quote: "3500 万元",
        },
      ];
      const res = highlightIssuesInHtml(html, issues, 1);
      expect(res).toContain('<mark class="review-issue-highlight severity-warning" data-issue-id="ISS-101" data-chapter-seq="1" title="数值自洽: 投资数据不一致">3500 万元</mark>');
    });

    it("highlightIssuesInHtml: 级别 2 全半角标点泛化容错高亮", () => {
      const html = "<p>本项目总投资为3500万元,工期为18个月。</p>";
      const issues = [
        {
          id: "ISS-102",
          category: "数据核实",
          severity: "error",
          message: "工期核实",
          quote: "本项目总投资为3500万元，工期为18个月", // 全角逗号
        },
      ];
      const res = highlightIssuesInHtml(html, issues, 2);
      expect(res).toContain('<mark class="review-issue-highlight severity-error" data-issue-id="ISS-102" data-chapter-seq="2"');
      expect(res).toContain("本项目总投资为3500万元,工期为18个月");
    });

    it("highlightIssuesInHtml: 级别 3 长句前缀滑动窗口匹配", () => {
      const html = "<p>根据防洪评价计算报告要求，本工程需设置溢洪道以满足千年一遇校核洪水标准。</p>";
      const issues = [
        {
          id: "ISS-103",
          category: "合规审查",
          severity: "suggestion",
          message: "溢洪道设计需补充校核标准",
          quote: "根据防洪评价计算报告要求，需要进一步验算溢流坝面水力学特性与水工模型。", // 前半句匹配，后半句微调
        },
      ];
      const res = highlightIssuesInHtml(html, issues, 3);
      expect(res).toContain('<mark class="review-issue-highlight severity-suggestion" data-issue-id="ISS-103" data-chapter-seq="3"');
      expect(res).toContain("根据防洪评价计算报告要求");
    });

    it("highlightIssuesInHtml: 避免重复包裹或破坏已有 mark 结构", () => {
      const html = '<p>正常段落。<mark class="review-issue-highlight severity-warning" data-issue-id="ISS-1" data-chapter-seq="1" title="原有问题">已有高亮 3500 万元</mark> 剩余文字 3500 万元。</p>';
      const issues = [
        {
          id: "ISS-2",
          category: "重复核查",
          severity: "error",
          message: "外部投资",
          quote: "3500 万元",
        },
      ];
      const res = highlightIssuesInHtml(html, issues, 1);
      // 原有 mark 结构未被破坏
      expect(res).toContain('data-issue-id="ISS-1"');
      // 剩余外部的 3500 万元被新标记包裹
      expect(res).toContain('data-issue-id="ISS-2"');
    });

    it("highlightIssuesInHtml: 边界处理（空 html 或空 issues）", () => {
      expect(highlightIssuesInHtml("", [])).toBe("");
      expect(highlightIssuesInHtml("<p>测试</p>", [])).toBe("<p>测试</p>");
    });
  });

  describe("标准三线表剥离与纯正文字数统计 (stripMarkdownTables & countContentChars)", () => {
    it("stripMarkdownTables 正确剥离表格结构行与数据", () => {
      const md = [
        "## 1.1 项目主要指标",
        "本项目规划总投资为 5000 万元，建设期 2 年。",
        "",
        "| 指标名称 | 单位 | 数值 | 备注 |",
        "| :--- | :---: | ---: | :--- |",
        "| 建设用地 | 亩 | 120 | 国有划拨 |",
        "| 建筑面积 | 万㎡ | 8.5 | 生产厂房 |",
        "",
        "各项指标均符合国家发改委产业投资指导目录要求。",
      ].join("\n");

      const stripped = stripMarkdownTables(md);
      expect(stripped).not.toContain("| 指标名称");
      expect(stripped).not.toContain("| :---");
      expect(stripped).not.toContain("| 建设用地");
      expect(stripped).not.toContain("| 建筑面积");
      expect(stripped).toContain("## 1.1 项目主要指标");
      expect(stripped).toContain("本项目规划总投资为 5000 万元，建设期 2 年。");
      expect(stripped).toContain("各项指标均符合国家发改委产业投资指导目录要求。");
    });

    it("countContentChars 精准剥离标题行、Markdown 表格与来源标签统计纯正文字数", () => {
      const md = [
        "# 第一章 概述",
        "## 1.1 项目概况",
        "### 1.1.1 建设地点",
        "本项目位于武汉市江夏区【源:立项批复.docx】。",
        "",
        "### 1.1.6 主要技术经济指标",
        "| 序号 | 指标名称 | 单位 | 目标值 |",
        "| :--- | :---: | ---: | --- |",
        "| 1 | 总库容 | 万m³ | 1500 |",
        "| 2 | 防洪标准 | 年一遇 | 100 |",
        "",
        "经科学论证，本项目符合国家重大基础设施建设规划。",
      ].join("\n");

      // 正文内容仅包含：
      // "本项目位于武汉市江夏区。" (12 字符) + "经科学论证，本项目符合国家重大基础设施建设规划。" (24 字符) = 36 字符
      const count = countContentChars(md);
      expect(count).toBe(36);
      expect(countContentCharsExcludingTables(md)).toBe(36);
    });

    it("countContentChars 边界处理（空字符串、纯表格、纯标题）", () => {
      expect(countContentChars("")).toBe(0);
      expect(countContentChars("   \n\t  ")).toBe(0);
      expect(countContentChars("# 纯标题\n## 二级标题\n### 三级标题")).toBe(0);
      expect(countContentChars("| 表头1 | 表头2 |\n|---|---|\n| 数据1 | 数据2 |")).toBe(0);
    });
  });

  describe("V2-T30: 三源参考文献分类统计与内联标签双向联动", () => {
    it("getReferencesSummary: 准确统计三源分类（项目底稿/标准规程/百度联网）数量与引用频次", () => {
      const refs = [
        { type: "material" as const, typeLabel: "项目底稿", title: "可研报告.docx", raw: "【源:可研报告.docx】", count: 3 },
        { type: "material" as const, typeLabel: "项目底稿", title: "地质勘探.pdf", raw: "【源:地质勘探.pdf】", count: 1 },
        { type: "standard" as const, typeLabel: "标准规程", title: "防洪标准GB50201", raw: "【标:防洪标准GB50201】", count: 2 },
        { type: "web" as const, typeLabel: "百度联网", title: "国家发改委产业目录", raw: "【网:国家发改委产业目录】", count: 4, url: "https://www.ndrc.gov.cn" },
      ];

      const summary = getReferencesSummary(refs);
      expect(summary.material.count).toBe(2);
      expect(summary.material.citations).toBe(4); // 3 + 1
      expect(summary.standard.count).toBe(1);
      expect(summary.standard.citations).toBe(2);
      expect(summary.web.count).toBe(1);
      expect(summary.web.citations).toBe(4);
      expect(summary.totalCount).toBe(4);
      expect(summary.totalCitations).toBe(10);
    });

    it("getReferencesSummary: 空数组或异常输入防御", () => {
      const s1 = getReferencesSummary([]);
      expect(s1.totalCount).toBe(0);
      expect(s1.totalCitations).toBe(0);
      expect(s1.material.count).toBe(0);
      expect(s1.standard.citations).toBe(0);

      const s2 = getReferencesSummary(null as unknown as any[]);
      expect(s2.totalCount).toBe(0);
      expect(s2.totalCitations).toBe(0);
    });

    it("markdownToHtml: 三源来源标签生成 semantic inline-ref-tag 包含 type 与 data-ref-title", () => {
      const md = `
        根据立项依据【源:项目立项批复.docx#L10-20】，
        对照规程【标:水工混凝土结构设计规范SL191-2008】，
        结合最新检索【网:国家发展改革委投资项目大纲】，
        以及标准库 [Z] 与专题规范 [Z-03]。
      `;

      const html = markdownToHtml(md);

      // 项目底稿
      expect(html).toContain('class="inline-ref-tag type-material"');
      expect(html).toContain('data-ref-type="material"');
      expect(html).toContain('data-ref-title="项目立项批复.docx#L10-20"');
      expect(html).toContain('【源:项目立项批复.docx#L10-20】');

      // 国标规程
      expect(html).toContain('class="inline-ref-tag type-standard"');
      expect(html).toContain('data-ref-type="standard"');
      expect(html).toContain('data-ref-title="水工混凝土结构设计规范SL191-2008"');
      expect(html).toContain('【标:水工混凝土结构设计规范SL191-2008】');

      // 百度联网
      expect(html).toContain('class="inline-ref-tag type-web"');
      expect(html).toContain('data-ref-type="web"');
      expect(html).toContain('data-ref-title="国家发展改革委投资项目大纲"');
      expect(html).toContain('【网:国家发展改革委投资项目大纲】');

      // 标准依据 [Z]
      expect(html).toContain('data-ref-title="标准规范规程库 [Z]"');
      expect(html).toContain('data-ref-title="标准规范依据 [Z-03]"');
    });

    it("htmlToMarkdown: 双向转换纯净还原为原始 Markdown 标签（杜绝 HTML 与 span 污染）", () => {
      const originalMd = "# 第一章 建设方案\n\n根据立项批复【源:批复文件.docx】，本项目建设规模符合标准【标:水利规范.pdf】及政策【网:发改委文件】。";
      const html = markdownToHtml(originalMd);

      expect(html).toContain("inline-ref-tag");
      expect(html).toContain("data-ref-title");

      const roundTripMd = htmlToMarkdown(html);
      expect(roundTripMd).toBe(originalMd);
      expect(roundTripMd).not.toContain("<span");
      expect(roundTripMd).not.toContain("inline-ref-tag");
      expect(roundTripMd).not.toContain("data-ref");
    });
  });

  describe("V2-T35: 段落级精准定位特征提取与泛化匹配", () => {
    it("extractIssueCandidateKeys: 优先提取 quote，无 quote 时从 message 与 location 提取引号与数值", () => {
      // 1. 带 quote
      const issue1 = {
        id: "ISSUE-1",
        severity: "warning" as const,
        quote: "总投资 3500 万元，年运行成本 120 万元",
        message: "投资估算缺少明细",
      };
      expect(extractIssueCandidateKeys(issue1)).toEqual(["总投资 3500 万元，年运行成本 120 万元"]);

      // 2. 无 quote，message 带引号
      const issue2 = {
        id: "ISSUE-2",
        severity: "warning" as const,
        message: "段落中提到的「拟建水库总库容1200万m³」与底稿不一致",
      };
      expect(extractIssueCandidateKeys(issue2)).toContain("拟建水库总库容1200万m³");

      // 3. 无 quote，从 message 提取工程数值
      const issue3 = {
        id: "ISSUE-3",
        severity: "warning" as const,
        message: "建设投资估算为 58000万元，与资金筹措表不符",
      };
      const keys3 = extractIssueCandidateKeys(issue3);
      expect(keys3).toContain("58000万元");

      // 4. 无 quote 和数值，从 location 提取标题名
      const issue4 = {
        id: "ISSUE-4",
        severity: "warning" as const,
        message: "论证不充分",
        location: "5.2.1 关键设备比选方案",
      };
      const keys4 = extractIssueCandidateKeys(issue4);
      expect(keys4).toContain("关键设备比选方案");
    });

    it("buildGeneralizedRegex: 兼容全半角标点符号与空白", () => {
      const reg = buildGeneralizedRegex("投资估算：总额为3500万元，含基本预备费。");
      expect(reg.test("投资估算:总额为3500万元,含基本预备费.")).toBe(true);
      expect(reg.test("投资估算：总额为3500万元，含基本预备费。")).toBe(true);
      expect(reg.test("投资估算 : 总额为3500万元 , 含基本预备费 .")).toBe(true);
    });

    it("highlightIssuesInHtml: 多级穿透匹配并注入 data-issue-id 与 review-issue-highlight 标记", () => {
      const html = "<p>本项目建设投资估算为 5800万元，资金来源全部为政府专项债。</p>";
      const issues = [
        {
          id: "ISSUE-VAL-1",
          severity: "high" as const,
          message: "数值自洽问题",
          quote: "5800万元",
        },
      ];
      const highlighted = highlightIssuesInHtml(html, issues, 7);
      expect(highlighted).toContain('data-issue-id="ISSUE-VAL-1"');
      expect(highlighted).toContain("review-issue-highlight");
      expect(highlighted).toContain("5800万元");
    });
  });

  describe("全书全局引用编号与参考文献总清单体系", () => {
    it("assignGlobalRefNumbers: 按章节顺序赋全局唯一编号并跨章复用", () => {
      const chapters: Record<number, string> = {
        1: "本项目依据【源:立项批复文件.docx】进行立项，符合【标:GB 30486—2013】标准。",
        2: "工艺要求符合【标:GB 30486—2013】与【网:生态环境部通知】。\n【网:生态环境部通知】\nhttps://mee.gov.cn/notice/1",
        3: "再次依据【源:立项批复文件.docx】核定。",
      };

      const { labelToNumber, refEntries } = assignGlobalRefNumbers(chapters, [1, 2, 3]);

      // 全书共 3 个独立参考资料，分别赋 1, 2, 3 号
      expect(labelToNumber["【源:立项批复文件.docx】"]).toBe(1);
      expect(labelToNumber["【标:GB 30486—2013】"]).toBe(2);
      expect(labelToNumber["【网:生态环境部通知】"]).toBe(3);

      expect(refEntries.length).toBe(3);
      expect(refEntries[0].number).toBe(1);
      expect(refEntries[0].count).toBe(2); // 第 1 章与第 3 章各 1 次
      expect(refEntries[1].number).toBe(2);
      expect(refEntries[1].count).toBe(2); // 第 1 章与第 2 章各 1 次
      expect(refEntries[2].number).toBe(3);
      expect(refEntries[2].url).toBe("https://mee.gov.cn/notice/1");
    });

    it("convertRefsToNumberedCitations: 将正文中的语义标签转换为 [1][2] 编号", () => {
      const text = "本项目依据【源:立项批复文件.docx】进行立项，符合【标:GB 30486—2013】标准。";
      const labelToNumber = {
        "【源:立项批复文件.docx】": 1,
        "【标:GB 30486—2013】": 2,
      };
      const converted = convertRefsToNumberedCitations(text, labelToNumber);
      expect(converted).toBe("本项目依据[1]进行立项，符合[2]标准。");
    });

    it("generateBibliographySection: 生成 GB/T 7714 规范的参考文献总表", () => {
      const refEntries = [
        {
          number: 1,
          label: "【源:立项批复文件.docx】",
          title: "立项批复文件.docx",
          name: "立项批复文件.docx",
          type: "material" as const,
          typeLabel: "项目资料",
          count: 2,
          raw: "【源:立项批复文件.docx】",
        },
        {
          number: 2,
          label: "【标:GB 30486—2013】",
          title: "GB 30486—2013 制革及毛皮加工工业水污染物排放标准",
          name: "GB 30486—2013",
          type: "standard" as const,
          typeLabel: "标准规范",
          count: 2,
          raw: "【标:GB 30486—2013】",
        },
        {
          number: 3,
          label: "【网:生态环境部通知】",
          title: "生态环境部关于发布2023年重点区域执行通知",
          name: "生态环境部通知",
          type: "web" as const,
          typeLabel: "联网检索",
          count: 1,
          raw: "【网:生态环境部通知】",
          url: "https://mee.gov.cn/notice/1",
        },
      ];

      const bib = generateBibliographySection(refEntries);
      expect(bib).toContain("# 参考文献");
      expect(bib).toContain("[1] [项目资料] 立项批复文件.docx.");
      expect(bib).toContain("[2] [标准规范] GB 30486—2013 制革及毛皮加工工业水污染物排放标准.");
      expect(bib).toContain("[3] [联网检索] 生态环境部关于发布2023年重点区域执行通知. 访问网址: https://mee.gov.cn/notice/1");
    });
  });

  describe("V2-T47: 节首句标点补齐、段落融合与引用标记行内消除换行", () => {
    it("引用标记消除孤立换行并紧随前置句子", () => {
      const raw = "本项目符合国家绿色发展产业目录要求。\n\n【源:产业目录.docx】\n规划建设规模为年产1000万件。";
      const normalized = normalizeMarkdown(raw);
      expect(normalized).toContain("【源:产业目录.docx】。");
      expect(normalized).not.toContain("\n\n【源:产业目录.docx】");

      const rawNumbered = "本项目工程地质条件稳定。\n\n[1]\n各项参数均满足抗震设防要求。";
      const normNumbered = normalizeMarkdown(rawNumbered);
      expect(normNumbered).toContain("[1]。");
      expect(normNumbered).not.toContain("\n\n[1]");
    });

    it("末级小节下孤立无标点引导短句自动补齐句号并与后文段落合并", () => {
      const raw = [
        "### 1.1.1 建设地点",
        "",
        "本项目主要能源消耗品种为电力和天然气",
        "",
        "项目总规划用地面积 120 亩，总建筑面积约 85000 平方米。",
      ].join("\n");

      const normalized = normalizeMarkdown(raw);
      expect(normalized).toBe(
        "### 1.1.1 建设地点\n\n本项目主要能源消耗品种为电力和天然气。项目总规划用地面积 120 亩，总建筑面积约 85000 平方米。"
      );
    });

    it("末级小节下单行无标点短句自动补充句号", () => {
      const raw = [
        "### 1.1.2 建设规模",
        "",
        "本项目年产各类高档皮革制品 500 万件",
        "",
        "### 1.1.3 建设周期",
      ].join("\n");

      const normalized = normalizeMarkdown(raw);
      expect(normalized).toContain("### 1.1.2 建设规模\n\n本项目年产各类高档皮革制品 500 万件。\n\n### 1.1.3 建设周期");
    });
  });

  describe("V2-T48: 双句号消除、长粘连节标题彻底拆分与段落行内引用不换行", () => {
    it("彻底消除引用后双句号及各种重复标点（[1]。。 / 【源:...】。。）", () => {
      const raw1 = "产值达60亿元。\n\n【源:政府工作报告.docx】。随着正源牧业二期建成投产。";
      const norm1 = normalizeMarkdown(raw1);
      expect(norm1).toContain("【源:政府工作报告.docx】。随着");
      expect(norm1).not.toContain("。。");

      const raw2 = "核心竞争力【源:利辛县2026年政府工作报告.docx】。。在市场环境方面。";
      const norm2 = normalizeMarkdown(raw2);
      expect(norm2).toContain("【源:利辛县2026年政府工作报告.docx】。在市场环境方面");
      expect(norm2).not.toContain("。。");

      const raw3 = "投资规模符合规划。[1]。。资金来源已落实。";
      const norm3 = normalizeMarkdown(raw3);
      expect(norm3).toBe("投资规模符合规划[1]。资金来源已落实。");
      expect(norm3).not.toContain("。。");

      const raw4 = "重复标点清理测试，，包含、、多个；；标点。。";
      const norm4 = normalizeMarkdown(raw4);
      expect(norm4).toBe("重复标点清理测试，包含、多个；标点。");
    });

    it("长粘连数字小节标题与正文彻底拆分（无空格无标点直接粘连）", () => {
      const longGlued = "### 3.1.2 市场需求潜力国内皮革制品市场需求总体保持稳定，生态化、高品质皮化材料及成品革的市场潜力较为突出。我国是世界最大的皮革生产与消费国，皮革制品涵盖鞋面革、服装革、箱包革、沙发革等多个应用领域，年需求量长期保持在较高水平。";
      const norm = normalizeMarkdown(longGlued);
      expect(norm).toContain("### 3.1.2 市场需求潜力\n\n国内皮革制品市场需求总体保持稳定");

      const parenGlued = "### 3.2.5 分期建设安排（如适用）项目采用一次性规划、分两期实施的安排。";
      const normParen = normalizeMarkdown(parenGlued);
      expect(normParen).toContain("### 3.2.5 分期建设安排（如适用）\n\n项目采用一次性规划");

      const layoutGlued = "### 3.2.2 总体布局项目总体布局按照“生产流程顺畅、功能分区明确”的原则进行设计。";
      const normLayout = normalizeMarkdown(layoutGlued);
      expect(normLayout).toContain("### 3.2.2 总体布局\n\n项目总体布局按照");

      // 智库专报长小节标题、引导词与超长段落粘连
      const zhiku1 = "### 1. 构建多元组合的投融资工具体系在中央超长期特别国债2026年安排\n\n1600亿元专项支持的基础上";
      expect(normalizeMarkdown(zhiku1)).toContain("### 1. 构建多元组合的投融资工具体系\n\n在中央超长期特别国债2026年安排");

      const zhiku2 = "### 2. 推进非开挖与智能感知关键技术攻关超大特大城市核心城区普遍面临“无路可挖”的空间约束，应大力推广非开挖修复技术、微型隧道掘进技术、原位固化修复工艺，最大限度减少路面开挖与交通干扰。同时加快智能感知装备攻关，重点突破高精度管网泄漏监测传感器、管道内检测机器人、分布式光纤测温与声波定位系统等关键设备，提升管网运行状态的实时感知与预警能力。";
      const normZhiku2 = normalizeMarkdown(zhiku2);
      expect(normZhiku2).toContain("### 2. 推进非开挖与智能感知关键技术攻关\n\n超大特大城市核心城区普遍面临“无路可挖”的空间约束");

      const zhiku3 = "### 3. 建立统一管网数据标准与数字孪生底座数据分散、标准不一、共享不畅是制约智慧管网建设的基础性障碍\n\n建议由城市政府牵头制定统一标准。";
      expect(normalizeMarkdown(zhiku3)).toContain("### 3. 建立统一管网数据标准与数字孪生底座\n\n数据分散、标准不一、共享不畅是制约智慧管网建设的基础性障碍");
    });

    it("markdownToHtml 普通段落内换行不插入 <br />，引用标签自然行内流式", () => {
      const mdWithSoftBreak = "利辛县具有显著区位优势\n【源:规划报告.docx】。项目建设条件良好。";
      const html = markdownToHtml(mdWithSoftBreak);
      expect(html).not.toContain("<br />");
      expect(html).toContain("利辛县具有显著区位优势<span class=\"inline-ref-tag type-material\"");
      expect(html).toContain("【源:规划报告.docx】</span>。项目建设条件良好。");

      // 显式双空格换行仍保留 <br />
      const mdWithHardBreak = "第一行重点要求  \n第二行细则说明";
      const htmlHard = markdownToHtml(mdWithHardBreak);
      expect(htmlHard).toContain("第一行重点要求<br />第二行细则说明");
    });

    it("V2-T49: markdownToHtml 将参考文献条目逐行独立渲染为 ref-entry-line，不被段落吞并", () => {
      const bibMd = `# 参考文献\n\n> 依据 GB/T 7714 自动汇总\n\n[1] [项目资料] 立项文件.docx.\n\n[2] [规程标准] GB 50016.\n`;
      const html = markdownToHtml(bibMd);
      expect(html).toContain('<p class="ref-entry-line">[1] [项目资料] 立项文件.docx.</p>');
      expect(html).toContain('<p class="ref-entry-line">[2] [规程标准] GB 50016.</p>');
      expect(html).toContain("<blockquote><p>依据 GB/T 7714 自动汇总</p></blockquote>");
    });

    it("V2-T49: normalizeMarkdown 严格隔离保护参考文献章，不消除条目间换行符", () => {
      const fullDoc = `## 1.1 章节概述\n正文阐述[1]。\n\n# 参考文献\n\n> 依据 GB/T 7714 自动汇总\n\n[1] [项目资料] 报告.docx.\n\n[2] [规程标准] 标准.md.\n`;
      const norm = normalizeMarkdown(fullDoc);
      expect(norm).toContain("# 参考文献\n\n> 依据 GB/T 7714 自动汇总\n\n[1] [项目资料] 报告.docx.\n\n[2] [规程标准] 标准.md.");
    });
  });
});

