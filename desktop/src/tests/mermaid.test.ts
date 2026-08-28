import { describe, expect, it } from "vitest";
import { htmlToMarkdown, markdownToHtml } from "../lib/markdown";
import {
  escapeSvgText,
  layoutMermaidDiagram,
  parseMermaid,
  renderMermaidSvg,
  renderMermaidToHtml,
} from "../lib/mermaid";

describe("Mermaid 矢量渲染引擎与双向联动 (mermaid.ts)", () => {
  describe("方向与基础语法解析", () => {
    it("支持 graph TD / TB / LR / RL / BT 与 flowchart 声明头", () => {
      const codeTD = "graph TD\n  A --> B";
      const diagTD = parseMermaid(codeTD);
      expect(diagTD.direction).toBe("TD");
      expect(diagTD.nodes.size).toBe(2);
      expect(diagTD.edges.length).toBe(1);

      const codeLR = "flowchart LR\n  A[开始] --> B[结束]";
      const diagLR = parseMermaid(codeLR);
      expect(diagLR.direction).toBe("LR");
      expect(diagLR.nodes.get("A")?.label).toBe("开始");
      expect(diagLR.nodes.get("B")?.label).toBe("结束");

      const codeBT = "graph BT\n  A --> B";
      const diagBT = parseMermaid(codeBT);
      expect(diagBT.direction).toBe("BT");

      const codeRL = "flowchart RL\n  A --> B";
      const diagRL = parseMermaid(codeRL);
      expect(diagRL.direction).toBe("RL");
    });

    it("支持空字符串与注释 %% 及特殊字符转义", () => {
      expect(escapeSvgText("<>&\"'")).toBe("&lt;&gt;&amp;&quot;&#39;");
      const code = `
        %% 这是工艺流程图注释
        graph TD
        %% 准备工序
        A[进料] --> B[加工]
      `;
      const diag = parseMermaid(code);
      expect(diag.nodes.size).toBe(2);
      expect(diag.nodes.has("A")).toBe(true);
      expect(diag.nodes.has("B")).toBe(true);
    });
  });

  describe("节点形状解析", () => {
    it("正确解析多种节点形状（矩形、圆角、胶囊、数据库、圆形、菱形、平行四边形、子程序、旗帜）", () => {
      const code = `
        graph TD
        A[标准矩形]
        B(圆角矩形)
        C([胶囊/体育场])
        D[(圆柱/数据库)]
        E((圆形集散))
        F{菱形决策判断}
        G[/平行四边形/]
        H[\\反平行四边形\\]
        I[[双边框子程序]]
        J>旗帜标签]
      `;
      const diag = parseMermaid(code);
      expect(diag.nodes.get("A")?.shape).toBe("rect");
      expect(diag.nodes.get("A")?.label).toBe("标准矩形");

      expect(diag.nodes.get("B")?.shape).toBe("round");
      expect(diag.nodes.get("B")?.label).toBe("圆角矩形");

      expect(diag.nodes.get("C")?.shape).toBe("capsule");
      expect(diag.nodes.get("C")?.label).toBe("胶囊/体育场");

      expect(diag.nodes.get("D")?.shape).toBe("cylinder");
      expect(diag.nodes.get("D")?.label).toBe("圆柱/数据库");

      expect(diag.nodes.get("E")?.shape).toBe("circle");
      expect(diag.nodes.get("E")?.label).toBe("圆形集散");

      expect(diag.nodes.get("F")?.shape).toBe("diamond");
      expect(diag.nodes.get("F")?.label).toBe("菱形决策判断");

      expect(diag.nodes.get("G")?.shape).toBe("parallelogram");
      expect(diag.nodes.get("G")?.label).toBe("平行四边形");

      expect(diag.nodes.get("H")?.shape).toBe("parallelogram_alt");
      expect(diag.nodes.get("H")?.label).toBe("反平行四边形");

      expect(diag.nodes.get("I")?.shape).toBe("subroutine");
      expect(diag.nodes.get("I")?.label).toBe("双边框子程序");

      expect(diag.nodes.get("J")?.shape).toBe("asymmetric");
      expect(diag.nodes.get("J")?.label).toBe("旗帜标签");
    });

    it("支持双引号/单引号包裹的标签与多行文本", () => {
      const code = `
        graph TD
        A["水库大坝<br>防洪调度"] --> B['二级泵站\\n加压提升']
      `;
      const diag = parseMermaid(code);
      expect(diag.nodes.get("A")?.label).toBe("水库大坝<br>防洪调度");
      expect(diag.nodes.get("B")?.label).toBe("二级泵站\\n加压提升");
    });
  });

  describe("连线类型与带文本连线解析", () => {
    it("支持实线、虚线、粗线、无箭头及各类连线文本标注", () => {
      const code = `
        graph TD
        A -->|实线文本| B
        B -.->|虚线文本| C
        C ==>|粗线文本| D
        D ---|无箭头实线| E
        E -.- F
        F === G
        A -- 另一种文本语法 --> H
      `;
      const diag = parseMermaid(code);
      expect(diag.edges.length).toBe(7);

      expect(diag.edges[0].type).toBe("solid");
      expect(diag.edges[0].label).toBe("实线文本");

      expect(diag.edges[1].type).toBe("dashed");
      expect(diag.edges[1].label).toBe("虚线文本");

      expect(diag.edges[2].type).toBe("thick");
      expect(diag.edges[2].label).toBe("粗线文本");

      expect(diag.edges[3].type).toBe("solid_no_arrow");
      expect(diag.edges[3].label).toBe("无箭头实线");

      expect(diag.edges[4].type).toBe("dashed_no_arrow");
      expect(diag.edges[5].type).toBe("thick_no_arrow");

      expect(diag.edges[6].type).toBe("solid");
      expect(diag.edges[6].label).toBe("另一种文本语法");
    });

    it("支持连续链式连接声明 (A --> B --> C)", () => {
      const code = "graph LR\n  A[原水] --> B(混凝沉淀) --> C{水质检测} -->|合格| D[出水]";
      const diag = parseMermaid(code);
      expect(diag.nodes.size).toBe(4);
      expect(diag.edges.length).toBe(3);
      expect(diag.edges[2].from).toBe("C");
      expect(diag.edges[2].to).toBe("D");
      expect(diag.edges[2].label).toBe("合格");
    });
  });

  describe("子图嵌套 (subgraph) 与样式绑定", () => {
    it("支持 subgraph ... end 子图分组与跨子图连线", () => {
      const code = `
        graph TD
        subgraph 水处理区 [水源地净水工程]
          A[取水口] --> B[絮凝沉淀池]
        end
        subgraph 输配区 [配水管网]
          C[高位清水池] --> D[市政供水管网]
        end
        B --> C
      `;
      const diag = parseMermaid(code);
      expect(diag.subgraphs.length).toBe(2);
      expect(diag.subgraphs[0].title).toBe("水源地净水工程");
      expect(diag.subgraphs[0].nodeIds).toContain("A");
      expect(diag.subgraphs[0].nodeIds).toContain("B");

      expect(diag.subgraphs[1].title).toBe("配水管网");
      expect(diag.subgraphs[1].nodeIds).toContain("C");
      expect(diag.subgraphs[1].nodeIds).toContain("D");

      expect(diag.edges.length).toBe(3);
    });

    it("支持 classDef, class, style 与内联 :::class 自定义样式", () => {
      const code = `
        graph TD
        classDef highlight fill:#dcfce7,stroke:#16a34a,color:#15803d
        A[进水节点]:::highlight --> B[出水节点]
        style B fill:#fee2e2,stroke:#dc2626,color:#991b1b
        class B alertClass
      `;
      const diag = parseMermaid(code);
      expect(diag.classDefs.has("highlight")).toBe(true);
      expect(diag.nodes.get("A")?.className).toBe("highlight");
      expect(diag.nodes.get("B")?.style?.fill).toBe("#fee2e2");
      expect(diag.nodes.get("B")?.className).toBe("alertClass");
    });
  });

  describe("分层 DAG 拓扑排序与坐标计算 (layoutMermaidDiagram)", () => {
    it("正确计算节点层次等级与几何坐标", () => {
      const code = `
        graph TD
        A[步骤1] --> B[步骤2]
        A --> C[步骤2副线]
        B --> D[步骤3]
        C --> D
      `;
      const diag = parseMermaid(code);
      const layout = layoutMermaidDiagram(diag);

      expect(layout.viewWidth).toBeGreaterThan(200);
      expect(layout.viewHeight).toBeGreaterThan(150);

      const nodeA = diag.nodes.get("A")!;
      const nodeB = diag.nodes.get("B")!;
      const nodeC = diag.nodes.get("C")!;
      const nodeD = diag.nodes.get("D")!;

      expect(nodeA.rank).toBe(0);
      expect(nodeB.rank).toBe(1);
      expect(nodeC.rank).toBe(1);
      expect(nodeD.rank).toBe(2);

      // TD 布局下 Y 轴应严格递增
      expect(nodeA.y).toBeLessThan(nodeB.y);
      expect(nodeB.y).toBeLessThan(nodeD.y);
      expect(nodeC.y).toBeLessThan(nodeD.y);
    });

    it("正确计算水平流 LR 布局下的 X 轴递增", () => {
      const code = `
        graph LR
        A[始发] --> B[中转] --> C[终到]
      `;
      const diag = parseMermaid(code);
      layoutMermaidDiagram(diag);

      const nodeA = diag.nodes.get("A")!;
      const nodeB = diag.nodes.get("B")!;
      const nodeC = diag.nodes.get("C")!;

      expect(nodeA.x).toBeLessThan(nodeB.x);
      expect(nodeB.x).toBeLessThan(nodeC.x);
    });
  });

  describe("SVG 矢量图与出版级样式生成 (renderMermaidSvg)", () => {
    it("生成合规且包含 defs、marker、gradient、path、text 的 SVG 字符串", () => {
      const code = `
        graph TD
        A([原水流入]) --> B{水质合格?}
        B -->|是| C[(储水罐)]
        B -->|否| D[/排污沉淀/]
      `;
      const diag = parseMermaid(code);
      const svg = renderMermaidSvg(diag);

      expect(svg).toContain("<svg");
      expect(svg).toContain("viewBox=");
      expect(svg).toContain("<defs>");
      expect(svg).toContain('id="mermaid-arrow-solid"');
      expect(svg).toContain('id="mermaid-grad-blue"');
      expect(svg).toContain('id="mermaid-grad-teal"');
      expect(svg).toContain('id="mermaid-grad-amber"');
      expect(svg).toContain("原水流入");
      expect(svg).toContain("水质合格?");
      expect(svg).toContain("储水罐");
      expect(svg).toContain("排污沉淀");
      expect(svg).toContain("class=\"mermaid-edge\"");
    });
  });

  describe("富交互 HTML 卡片生成与容错保护 (renderMermaidToHtml)", () => {
    it("生成结构化卡片容器，包含顶部工具栏与双视图包装器", () => {
      const code = "graph TD\n  A[工序1] --> B[工序2]";
      const html = renderMermaidToHtml(code);

      expect(html).toContain('class="mermaid-container"');
      expect(html).toContain('data-mermaid-code=');
      expect(html).toContain('class="mermaid-toolbar"');
      expect(html).toContain("工艺/工程流程拓扑图");
      expect(html).toContain("2 个工序节点");
      expect(html).toContain('class="mermaid-btn mermaid-btn-toggle-view"');
      expect(html).toContain('class="mermaid-btn mermaid-btn-copy"');
      expect(html).toContain('class="mermaid-svg-wrapper"');
      expect(html).toContain('class="mermaid-code-wrapper"');
      expect(html).toContain("<svg");
    });

    it("容错保护：空输入返回空，异常/不合法输入平滑降级为优雅代码块而不抛错", () => {
      expect(renderMermaidToHtml("")).toBe("");
      expect(renderMermaidToHtml("   ")).toBe("");

      // 故意触发解析边界或特殊字符
      const html = renderMermaidToHtml("unknown_invalid_syntax_12345");
      expect(html).toContain("mermaid-container");
      expect(html).not.toThrow;
    });
  });

  describe("前端 Markdown 解析与双向编辑无损序列化联动", () => {
    it("markdownToHtml 自动将 ```mermaid 转换为流程图卡片", () => {
      const md = [
        "# 第一章 工艺流程",
        "```mermaid",
        "graph TD",
        "  A[原料进厂] --> B[高温熔炼]",
        "  B --> C[(成品仓库)]",
        "```",
        "工艺流程说明正文段落。",
      ].join("\n");

      const html = markdownToHtml(md, 1);
      expect(html).toContain('<h1 id="h-ch1-idx0">第一章 工艺流程</h1>');
      expect(html).toContain('class="mermaid-container"');
      expect(html).toContain("原料进厂");
      expect(html).toContain("成品仓库");
      expect(html).toContain("<p>工艺流程说明正文段落。</p>");
    });

    it("htmlToMarkdown 100% 无损反向序列化 Mermaid 代码块", () => {
      const originalMermaid = [
        "graph TD",
        "  A[原料进厂] --> B{质量检测}",
        "  B -->|合格| C[(合格品库)]",
        "  B -->|不合格| D[回炉重炼]",
      ].join("\n");

      const originalMd = [
        "# 第二章 工艺方案",
        "",
        "```mermaid",
        originalMermaid,
        "```",
        "",
        "这是流程说明文字。",
      ].join("\n");

      const html = markdownToHtml(originalMd, 2);
      const restoredMd = htmlToMarkdown(html);

      expect(restoredMd).toContain("# 第二章 工艺方案");
      expect(restoredMd).toContain("```mermaid");
      expect(restoredMd).toContain("A[原料进厂] --> B{质量检测}");
      expect(restoredMd).toContain("B -->|合格| C[(合格品库)]");
      expect(restoredMd).toContain("这是流程说明文字。");
    });
  });
});
