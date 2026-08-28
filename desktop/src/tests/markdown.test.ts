import { describe, expect, it } from "vitest";
import {
  buildGeneralizedRegex,
  escapeHtml,
  extractIssueCandidateKeys,
  extractOutlineHeadings,
  extractReferences,
  extractSubHeadings,
  formatInline,
  highlightIssuesInHtml,
  htmlToMarkdown,
  markdownToHtml,
  normalizeMarkdown,
  renderMarkdown,
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
      expect(html).toContain('<p><strong>重点</strong> <span class="ref-badge">🏷️ 【源:规划纲要.docx】</span></p>');
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

    it("来源标签自动识别并徽章化 (ref-badge)", () => {
      const text = "本段引自水利规程【源:水利规程.docx#L1-10】以及地质监测【源：监测报告.pdf】。";
      const html = formatInline(text);
      expect(html).toContain('<span class="ref-badge">🏷️ 【源:水利规程.docx#L1-10】</span>');
      expect(html).toContain('<span class="ref-badge">🏷️ 【源：监测报告.pdf】</span>');
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
      expect(html).toContain('<span class="ref-badge">🏷️ 【源:立项批复.docx】</span>');
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
      expect(html).toContain("引用第一行规范说明<br />引用第二行重点提示 <span class=\"ref-badge\">🏷️ 【源:设计手册.pdf】</span>");
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
      expect(refs[0].typeLabel).toBe("底稿文件");

      expect(refs[1].title).toBe("地质勘察报告.pdf");
      expect(refs[1].count).toBe(1);
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
});
