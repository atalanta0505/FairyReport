import { describe, expect, it } from "vitest";
import {
  escapeHtml,
  extractSubHeadings,
  formatInline,
  htmlToMarkdown,
  markdownToHtml,
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

    it("标题中包含来源引用标签与粗体", () => {
      const md = "# 第一章 建设背景 **重点** 【源:规划纲要.docx】";
      const html = markdownToHtml(md, 2);
      expect(html).toContain('<h1 id="h-ch2-idx0">第一章 建设背景 <strong>重点</strong> <span class="ref-badge">🏷️ 【源:规划纲要.docx】</span></h1>');
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
        raw: "## 2.2 泄洪设施 【源:规划.docx】",
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
});
