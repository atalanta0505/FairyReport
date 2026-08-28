/**
 * 纯 TypeScript 原生高性能 Mermaid 矢量 SVG 渲染引擎
 *
 * 0 外部依赖，原生解析与计算
 * 支持方向：graph TD / TB / LR / RL / BT, flowchart TD / LR 等
 * 支持形状：矩形 [text], 圆角 (text), 胶囊 ([text]), 数据库 [(text)], 圆形 ((text)), 菱形决策 {text}, 平行四边形 [/text/] / [\text\], 子程序 [[text]], 标签旗帜 >text]
 * 支持连线：--> (实线箭头), -.-> (虚线箭头), ==> (粗线箭头), --- (无箭头), 带文本连线 -->|文本| 与 -- 文本 -->
 * 支持子图：subgraph 标题 ... end
 * 支持样式：classDef, class, style
 * 拓扑排序与分层坐标计算：DAG 拓扑分层算法与平滑三次贝塞尔曲线
 * 出版级蓝绿工程风貌与容错降级
 */

export type DiagramDirection = "TD" | "TB" | "LR" | "RL" | "BT";

export type NodeShape =
  | "rect"
  | "round"
  | "capsule"
  | "cylinder"
  | "circle"
  | "diamond"
  | "parallelogram"
  | "parallelogram_alt"
  | "subroutine"
  | "asymmetric";

export interface MermaidNode {
  id: string;
  label: string;
  shape: NodeShape;
  subgraphId?: string;
  className?: string;
  style?: Record<string, string>;
  x: number;
  y: number;
  width: number;
  height: number;
  rank: number;
}

export type EdgeType =
  | "solid"
  | "dashed"
  | "thick"
  | "solid_no_arrow"
  | "dashed_no_arrow"
  | "thick_no_arrow";

export interface MermaidEdge {
  from: string;
  to: string;
  label?: string;
  type: EdgeType;
  style?: Record<string, string>;
}

export interface MermaidSubgraph {
  id: string;
  title: string;
  nodeIds: string[];
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ParsedMermaidDiagram {
  direction: DiagramDirection;
  nodes: Map<string, MermaidNode>;
  edges: MermaidEdge[];
  subgraphs: MermaidSubgraph[];
  classDefs: Map<string, Record<string, string>>;
}

/**
 * 转义 HTML/SVG 字符
 */
export function escapeSvgText(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * 估算单行文本宽度（中文字符约 13px，英文字符约 7.5px）
 */
function estimateTextWidth(text: string, fontSize = 12): number {
  let w = 0;
  for (let i = 0; i < text.length; i++) {
    const code = text.charCodeAt(i);
    if (code > 255) {
      w += fontSize * 1.05;
    } else {
      w += fontSize * 0.62;
    }
  }
  return Math.max(w, 20);
}

/**
 * 将长文本按最大字符长度自动分行
 */
function wrapNodeLabel(label: string, maxLineChars = 10): string[] {
  if (!label) return [""];
  // 处理显式换行符 <br> 或 \n
  const explicitLines = label.split(/<br\s*\/?>|\\n|\n/i);
  const result: string[] = [];

  for (const rawLine of explicitLines) {
    const trimmed = rawLine.trim();
    if (!trimmed) continue;
    if (trimmed.length <= maxLineChars) {
      result.push(trimmed);
      continue;
    }

    // 自动按长度截断分行
    let curr = "";
    let currLen = 0;
    for (let i = 0; i < trimmed.length; i++) {
      const ch = trimmed[i];
      const charWeight = ch.charCodeAt(0) > 255 ? 1 : 0.5;
      if (currLen + charWeight > maxLineChars && curr.length > 0) {
        result.push(curr);
        curr = ch;
        currLen = charWeight;
      } else {
        curr += ch;
        currLen += charWeight;
      }
    }
    if (curr) {
      result.push(curr);
    }
  }

  return result.length > 0 ? result : [label];
}

/**
 * 解析节点定义字符串，例如：
 * A[开始节点]、B(圆角环节)、C([胶囊])、D[(数据库)]、E((圆形))、F{决策判定}、G[/平行四边形/]、H[\反平行四边形\]、I[[子程序]]、J>旗帜]
 */
function parseNodeDefinition(raw: string): {
  id: string;
  label: string;
  shape: NodeShape;
  className?: string;
} | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;

  // 检查 inline class: A[text]:::className
  let cleanDef = trimmed;
  let className: string | undefined = undefined;
  const classMatch = cleanDef.match(/^(.*?):::([a-zA-Z0-9_\-]+)$/);
  if (classMatch) {
    cleanDef = classMatch[1].trim();
    className = classMatch[2].trim();
  }

  // 1. 胶囊 ([text])
  let m = cleanDef.match(/^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\(\[\s*(.*?)\s*\]\)$/);
  if (m) {
    return { id: m[1], label: cleanLabel(m[2]), shape: "capsule", className };
  }

  // 2. 数据库/圆柱 [(text)]
  m = cleanDef.match(/^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\[\(\s*(.*?)\s*\)\]$/);
  if (m) {
    return { id: m[1], label: cleanLabel(m[2]), shape: "cylinder", className };
  }

  // 3. 圆形 ((text))
  m = cleanDef.match(/^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\(\(\s*(.*?)\s*\)\)$/);
  if (m) {
    return { id: m[1], label: cleanLabel(m[2]), shape: "circle", className };
  }

  // 4. 子程序 [[text]]
  m = cleanDef.match(/^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\[\[\s*(.*?)\s*\]\]$/);
  if (m) {
    return { id: m[1], label: cleanLabel(m[2]), shape: "subroutine", className };
  }

  // 5. 平行四边形 [/text/]
  m = cleanDef.match(/^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\[\/\s*(.*?)\s*\/\]$/);
  if (m) {
    return { id: m[1], label: cleanLabel(m[2]), shape: "parallelogram", className };
  }

  // 6. 反平行四边形 [\text\]
  m = cleanDef.match(/^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\[\\\s*(.*?)\s*\\\]$/);
  if (m) {
    return { id: m[1], label: cleanLabel(m[2]), shape: "parallelogram_alt", className };
  }

  // 7. 菱形决策 {text}
  m = cleanDef.match(/^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\{\s*(.*?)\s*\}$/);
  if (m) {
    return { id: m[1], label: cleanLabel(m[2]), shape: "diamond", className };
  }

  // 8. 旗帜/不对称 >text]
  m = cleanDef.match(/^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*>\s*(.*?)\s*\]$/);
  if (m) {
    return { id: m[1], label: cleanLabel(m[2]), shape: "asymmetric", className };
  }

  // 9. 圆角矩形 (text)
  m = cleanDef.match(/^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\(\s*(.*?)\s*\)$/);
  if (m) {
    return { id: m[1], label: cleanLabel(m[2]), shape: "round", className };
  }

  // 10. 标准矩形 [text]
  m = cleanDef.match(/^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s*\[\s*(.*?)\s*\]$/);
  if (m) {
    return { id: m[1], label: cleanLabel(m[2]), shape: "rect", className };
  }

  // 11. 仅有纯 ID，未加括号
  m = cleanDef.match(/^([a-zA-Z0-9_\-\u4e00-\u9fa5]+)$/);
  if (m) {
    return { id: m[1], label: m[1], shape: "rect", className };
  }

  return null;
}

function cleanLabel(raw: string): string {
  let s = raw.trim();
  if (
    (s.startsWith('"') && s.endsWith('"')) ||
    (s.startsWith("'") && s.endsWith("'"))
  ) {
    s = s.slice(1, -1);
  }
  return s.trim();
}

/**
 * 解析单行中的箭头和连线
 */
const EDGE_PATTERNS = [
  // 1. 粗实线带文本 ==>|text| 或 == text ==>
  { regex: /==>\|([^|]+)\|/, type: "thick" as EdgeType, hasLabel: true },
  { regex: /==\s*([^=>|]+?)\s*==>/, type: "thick" as EdgeType, hasLabel: true },
  { regex: /==>/, type: "thick" as EdgeType, hasLabel: false },
  // 2. 虚线带文本 -.->|text| 或 -.- text -.-> 或 -. text .->
  { regex: /-\.->\|([^|]+)\|/, type: "dashed" as EdgeType, hasLabel: true },
  { regex: /-\.\s*([^.\->|]+?)\s*\.->/, type: "dashed" as EdgeType, hasLabel: true },
  { regex: /-\.->|\.->/, type: "dashed" as EdgeType, hasLabel: false },
  // 3. 实线带文本 -->|text| 或 -- text -->
  { regex: /-->\|([^|]+)\|/, type: "solid" as EdgeType, hasLabel: true },
  { regex: /--\s*([^->|]+?)\s*-->/, type: "solid" as EdgeType, hasLabel: true },
  { regex: /-->/, type: "solid" as EdgeType, hasLabel: false },
  // 4. 无箭头粗线 ===|text| 或 ===
  { regex: /===\|([^|]+)\|/, type: "thick_no_arrow" as EdgeType, hasLabel: true },
  { regex: /===/, type: "thick_no_arrow" as EdgeType, hasLabel: false },
  // 5. 无箭头虚线 -.-|text| 或 -.-
  { regex: /-\.-\|([^|]+)\|/, type: "dashed_no_arrow" as EdgeType, hasLabel: true },
  { regex: /-\.-/, type: "dashed_no_arrow" as EdgeType, hasLabel: false },
  // 6. 无箭头实线 ---|text| 或 -- text --- 或 ---
  { regex: /---\|([^|]+)\|/, type: "solid_no_arrow" as EdgeType, hasLabel: true },
  { regex: /--\s*([^->|]+?)\s*---/, type: "solid_no_arrow" as EdgeType, hasLabel: true },
  { regex: /---/, type: "solid_no_arrow" as EdgeType, hasLabel: false },
];

/**
 * 将整段 Mermaid 文本解析为结构化 AST 数据
 */
export function parseMermaid(code: string): ParsedMermaidDiagram {
  const lines = code.split("\n");
  let direction: DiagramDirection = "TD";
  const nodes = new Map<string, MermaidNode>();
  const edges: MermaidEdge[] = [];
  const subgraphs: MermaidSubgraph[] = [];
  const classDefs = new Map<string, Record<string, string>>();

  let currentSubgraph: MermaidSubgraph | null = null;
  let subgraphCounter = 1;

  for (let line of lines) {
    line = line.trim();
    if (!line || line.startsWith("%%")) continue;

    // 1. 流程图图表声明头
    const headerMatch = line.match(/^(?:graph|flowchart)\s+(TD|TB|LR|RL|BT)/i);
    if (headerMatch) {
      direction = headerMatch[1].toUpperCase() as DiagramDirection;
      continue;
    }

    // 2. 子图开始: subgraph subId [Title] 或 subgraph "Title" 或 subgraph Title
    const subStartMatch = line.match(/^subgraph\s+(.*?)$/i);
    if (subStartMatch) {
      const rest = subStartMatch[1].trim();
      let subId = `sub_${subgraphCounter++}`;
      let title = rest;

      const titleWithId = rest.match(/^([^\s\[\]]+)\s*\[\s*(.*?)\s*\]$/);
      if (titleWithId) {
        subId = titleWithId[1];
        title = cleanLabel(titleWithId[2]);
      } else {
        title = cleanLabel(rest) || subId;
      }

      currentSubgraph = {
        id: subId,
        title,
        nodeIds: [],
        x: 0,
        y: 0,
        width: 0,
        height: 0,
      };
      subgraphs.push(currentSubgraph);
      continue;
    }

    // 3. 子图结束: end
    if (/^end$/i.test(line)) {
      currentSubgraph = null;
      continue;
    }

    // 4. classDef 声明: classDef className fill:#...,stroke:#...
    const classDefMatch = line.match(/^classDef\s+([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s+(.+)$/i);
    if (classDefMatch) {
      const clsName = classDefMatch[1];
      const styleStr = classDefMatch[2];
      const styles: Record<string, string> = {};
      const pairs = styleStr.split(/[,;\s]+/);
      for (const p of pairs) {
        const [k, v] = p.split(":");
        if (k && v) styles[k.trim()] = v.trim();
      }
      classDefs.set(clsName, styles);
      continue;
    }

    // 5. class 绑定: class A,B className
    const classAssignMatch = line.match(/^class\s+([a-zA-Z0-9_\-\u4e00-\u9fa5,\s]+)\s+([a-zA-Z0-9_\-\u4e00-\u9fa5]+)$/i);
    if (classAssignMatch) {
      const targetIds = classAssignMatch[1].split(",").map((s) => s.trim());
      const clsName = classAssignMatch[2].trim();
      for (const id of targetIds) {
        if (nodes.has(id)) {
          nodes.get(id)!.className = clsName;
        }
      }
      continue;
    }

    // 6. style 声明: style A fill:#...,stroke:#...
    const styleMatch = line.match(/^style\s+([a-zA-Z0-9_\-\u4e00-\u9fa5]+)\s+(.+)$/i);
    if (styleMatch) {
      const targetId = styleMatch[1];
      const styleStr = styleMatch[2];
      const styles: Record<string, string> = {};
      const pairs = styleStr.split(/[,;\s]+/);
      for (const p of pairs) {
        const [k, v] = p.split(":");
        if (k && v) styles[k.trim()] = v.trim();
      }
      if (nodes.has(targetId)) {
        nodes.get(targetId)!.style = {
          ...(nodes.get(targetId)!.style || {}),
          ...styles,
        };
      }
      continue;
    }

    // 7. 解析包含节点与连线的语句
    parseLineConnections(line, nodes, edges, currentSubgraph);
  }

  // 计算每个节点尺寸与多行文本
  for (const node of nodes.values()) {
    const lines = wrapNodeLabel(node.label);
    const maxLineW = Math.max(...lines.map((l) => estimateTextWidth(l, 12)));
    const textH = lines.length * 18 + 16;
    let nodeW = Math.max(maxLineW + 28, 100);
    let nodeH = Math.max(textH, 42);

    if (node.shape === "diamond") {
      nodeW = Math.max(nodeW * 1.35, 115);
      nodeH = Math.max(nodeH * 1.35, 56);
    } else if (node.shape === "circle") {
      const d = Math.max(nodeW, nodeH, 56);
      nodeW = d;
      nodeH = d;
    } else if (node.shape === "cylinder") {
      nodeH += 14;
    } else if (node.shape === "capsule") {
      nodeW = Math.max(nodeW + 10, 110);
    }

    node.width = Math.round(nodeW);
    node.height = Math.round(nodeH);
  }

  return { direction, nodes, edges, subgraphs, classDefs };
}

/**
 * 解析单行中的可能多个节点与连线（例如 A --> B --> C）
 */
function parseLineConnections(
  line: string,
  nodes: Map<string, MermaidNode>,
  edges: MermaidEdge[],
  currentSubgraph: MermaidSubgraph | null
) {
  const edgeRegex =
    /(?:==>\|[^|]+\||==\s*[^=>|]+?\s*==>|==>|-\.->\|[^|]+\||-\.\s*[^.\->|]+?\s*\.->|-\.->|\.->|-->\|[^|]+\||--\s*[^->|]+?\s*-->|-->|===\|[^|]+\||===|-\.-\|[^|]+\||-\.-|---\|[^|]+\||--\s*[^->|]+?\s*---|---)/g;

  const edgeMatches: { match: string; index: number }[] = [];
  let m: RegExpExecArray | null;
  while ((m = edgeRegex.exec(line)) !== null) {
    edgeMatches.push({ match: m[0], index: m.index });
  }

  if (edgeMatches.length === 0) {
    const parsed = parseNodeDefinition(line);
    if (parsed) {
      registerNode(parsed, nodes, currentSubgraph);
    }
    return;
  }

  const nodeSegments: string[] = [];
  const edgeOps: string[] = [];

  let lastIndex = 0;
  for (const em of edgeMatches) {
    nodeSegments.push(line.substring(lastIndex, em.index).trim());
    edgeOps.push(em.match);
    lastIndex = em.index + em.match.length;
  }
  nodeSegments.push(line.substring(lastIndex).trim());

  const parsedNodeIds: string[] = [];
  for (const seg of nodeSegments) {
    const parsed = parseNodeDefinition(seg);
    if (parsed) {
      registerNode(parsed, nodes, currentSubgraph);
      parsedNodeIds.push(parsed.id);
    } else {
      const fallbackId = seg.replace(/[^a-zA-Z0-9_\-\u4e00-\u9fa5]/g, "").trim() || `node_${nodes.size + 1}`;
      registerNode({ id: fallbackId, label: seg, shape: "rect" }, nodes, currentSubgraph);
      parsedNodeIds.push(fallbackId);
    }
  }

  for (let i = 0; i < edgeOps.length; i++) {
    const fromId = parsedNodeIds[i];
    const toId = parsedNodeIds[i + 1];
    if (!fromId || !toId) continue;

    const op = edgeOps[i];
    let edgeType: EdgeType = "solid";
    let edgeLabel: string | undefined = undefined;

    for (const pat of EDGE_PATTERNS) {
      const match = op.match(pat.regex);
      if (match) {
        edgeType = pat.type;
        if (pat.hasLabel && match[1]) {
          edgeLabel = cleanLabel(match[1]);
        }
        break;
      }
    }

    edges.push({
      from: fromId,
      to: toId,
      label: edgeLabel,
      type: edgeType,
    });
  }
}

function registerNode(
  parsed: { id: string; label: string; shape: NodeShape; className?: string },
  nodes: Map<string, MermaidNode>,
  currentSubgraph: MermaidSubgraph | null
) {
  if (nodes.has(parsed.id)) {
    const existing = nodes.get(parsed.id)!;
    if (parsed.label && parsed.label !== parsed.id) {
      existing.label = parsed.label;
    }
    if (parsed.shape !== "rect") {
      existing.shape = parsed.shape;
    }
    if (parsed.className) {
      existing.className = parsed.className;
    }
    if (currentSubgraph && !existing.subgraphId) {
      existing.subgraphId = currentSubgraph.id;
      if (!currentSubgraph.nodeIds.includes(existing.id)) {
        currentSubgraph.nodeIds.push(existing.id);
      }
    }
  } else {
    const newNode: MermaidNode = {
      id: parsed.id,
      label: parsed.label || parsed.id,
      shape: parsed.shape,
      className: parsed.className,
      subgraphId: currentSubgraph?.id,
      x: 0,
      y: 0,
      width: 100,
      height: 42,
      rank: 0,
    };
    nodes.set(parsed.id, newNode);
    if (currentSubgraph) {
      currentSubgraph.nodeIds.push(newNode.id);
    }
  }
}

/**
 * DAG 拓扑分层与几何坐标布局计算
 */
export function layoutMermaidDiagram(diagram: ParsedMermaidDiagram): {
  viewWidth: number;
  viewHeight: number;
} {
  const { direction, nodes, edges, subgraphs } = diagram;
  if (nodes.size === 0) {
    return { viewWidth: 300, viewHeight: 150 };
  }

  // 1. 构建邻接表与入度表
  const adj = new Map<string, string[]>();
  const inDegree = new Map<string, number>();

  for (const id of nodes.keys()) {
    adj.set(id, []);
    inDegree.set(id, 0);
  }

  for (const e of edges) {
    if (adj.has(e.from) && inDegree.has(e.to)) {
      adj.get(e.from)!.push(e.to);
      inDegree.set(e.to, (inDegree.get(e.to) || 0) + 1);
    }
  }

  // 2. DAG 分层排序（拓扑最长路径分配）
  const ranks = new Map<string, number>();
  for (const id of nodes.keys()) {
    ranks.set(id, 0);
  }

  const maxIterations = Math.min(nodes.size + 2, 50);
  for (let iter = 0; iter < maxIterations; iter++) {
    let changed = false;
    for (const e of edges) {
      const uRank = ranks.get(e.from) ?? 0;
      const vRank = ranks.get(e.to) ?? 0;
      if (vRank < uRank + 1) {
        ranks.set(e.to, uRank + 1);
        changed = true;
      }
    }
    if (!changed) break;
  }

  // 3. 将节点划分至各层
  let maxRank = 0;
  for (const [id, r] of ranks.entries()) {
    maxRank = Math.max(maxRank, r);
    const node = nodes.get(id);
    if (node) node.rank = r;
  }

  const layers: MermaidNode[][] = Array.from({ length: maxRank + 1 }, () => []);
  for (const node of nodes.values()) {
    layers[node.rank].push(node);
  }

  // 4. 同层内节点排序（聚类子图与减少交叉）
  for (const layer of layers) {
    layer.sort((a, b) => {
      if (a.subgraphId !== b.subgraphId) {
        return (a.subgraphId || "").localeCompare(b.subgraphId || "");
      }
      return a.id.localeCompare(b.id);
    });
  }

  const isVertical = direction === "TD" || direction === "TB" || direction === "BT";
  const paddingX = 40;
  const paddingY = 40;
  const nodeGap = isVertical ? 36 : 48;
  const layerGap = isVertical ? 56 : 64;

  let totalWidth = 0;
  let totalHeight = 0;

  if (isVertical) {
    const layerWidths: number[] = [];
    const layerHeights: number[] = [];

    for (const layer of layers) {
      let w = 0;
      let h = 0;
      for (let i = 0; i < layer.length; i++) {
        w += layer[i].width;
        if (i < layer.length - 1) w += nodeGap;
        h = Math.max(h, layer[i].height);
      }
      layerWidths.push(w);
      layerHeights.push(Math.max(h, 42));
    }

    const maxLayerWidth = Math.max(...layerWidths, 200);
    let currY = paddingY;

    for (let r = 0; r < layers.length; r++) {
      const layer = layers[r];
      const lWidth = layerWidths[r];
      const lHeight = layerHeights[r];
      let currX = paddingX + (maxLayerWidth - lWidth) / 2;

      for (const node of layer) {
        node.x = Math.round(currX + node.width / 2);
        node.y = Math.round(currY + lHeight / 2);
        currX += node.width + nodeGap;
      }

      currY += lHeight + layerGap;
    }

    totalWidth = maxLayerWidth + paddingX * 2;
    totalHeight = currY - layerGap + paddingY;

    if (direction === "BT") {
      for (const node of nodes.values()) {
        node.y = totalHeight - node.y;
      }
    }
  } else {
    const layerWidths: number[] = [];
    const layerHeights: number[] = [];

    for (const layer of layers) {
      let w = 0;
      let h = 0;
      for (let i = 0; i < layer.length; i++) {
        h += layer[i].height;
        if (i < layer.length - 1) h += nodeGap;
        w = Math.max(w, layer[i].width);
      }
      layerWidths.push(Math.max(w, 100));
      layerHeights.push(h);
    }

    const maxLayerHeight = Math.max(...layerHeights, 150);
    let currX = paddingX;

    for (let r = 0; r < layers.length; r++) {
      const layer = layers[r];
      const lWidth = layerWidths[r];
      const lHeight = layerHeights[r];
      let currY = paddingY + (maxLayerHeight - lHeight) / 2;

      for (const node of layer) {
        node.x = Math.round(currX + lWidth / 2);
        node.y = Math.round(currY + node.height / 2);
        currY += node.height + nodeGap;
      }

      currX += lWidth + layerGap;
    }

    totalWidth = currX - layerGap + paddingX;
    totalHeight = maxLayerHeight + paddingY * 2;

    if (direction === "RL") {
      for (const node of nodes.values()) {
        node.x = totalWidth - node.x;
      }
    }
  }

  // 5. 计算子图包围盒
  for (const sub of subgraphs) {
    const subNodes = sub.nodeIds.map((id) => nodes.get(id)).filter(Boolean) as MermaidNode[];
    if (subNodes.length > 0) {
      let minX = Infinity;
      let maxX = -Infinity;
      let minY = Infinity;
      let maxY = -Infinity;

      for (const n of subNodes) {
        minX = Math.min(minX, n.x - n.width / 2);
        maxX = Math.max(maxX, n.x + n.width / 2);
        minY = Math.min(minY, n.y - n.height / 2);
        maxY = Math.max(maxY, n.y + n.height / 2);
      }

      sub.x = Math.round(minX - 16);
      sub.y = Math.round(minY - 28);
      sub.width = Math.round(maxX - minX + 32);
      sub.height = Math.round(maxY - minY + 44);
    }
  }

  return { viewWidth: Math.max(totalWidth, 240), viewHeight: Math.max(totalHeight, 120) };
}

/**
 * 绘制单个节点形状 SVG
 */
function renderNodeShapeSvg(node: MermaidNode, classDefs: Map<string, Record<string, string>>): string {
  const { shape, x, y, width: w, height: h, label, className, style } = node;
  const halfW = w / 2;
  const halfH = h / 2;

  let fill = "url(#mermaid-grad-blue)";
  let stroke = "#0284c7";
  let strokeWidth = "1.5";
  let textColor = "#0f172a";
  let strokeDash = "";

  if (className && classDefs.has(className)) {
    const def = classDefs.get(className)!;
    if (def.fill) fill = def.fill;
    if (def.stroke) stroke = def.stroke;
    if (def["stroke-width"]) strokeWidth = def["stroke-width"];
    if (def.color) textColor = def.color;
  }

  if (style) {
    if (style.fill) fill = style.fill;
    if (style.stroke) stroke = style.stroke;
    if (style["stroke-width"]) strokeWidth = style["stroke-width"];
    if (style.color) textColor = style.color;
    if (style["stroke-dasharray"]) strokeDash = ` stroke-dasharray="${style["stroke-dasharray"]}"`;
  }

  if (fill === "url(#mermaid-grad-blue)") {
    if (shape === "diamond") {
      fill = "url(#mermaid-grad-amber)";
      stroke = "#d97706";
    } else if (shape === "capsule" || shape === "round") {
      fill = "url(#mermaid-grad-teal)";
      stroke = "#0d9488";
    } else if (shape === "cylinder") {
      fill = "url(#mermaid-grad-indigo)";
      stroke = "#4f46e5";
    }
  }

  let shapeSvg = "";
  const filterAttr = ' filter="url(#mermaid-drop-shadow)"';

  switch (shape) {
    case "rect":
      shapeSvg = `<rect x="${x - halfW}" y="${y - halfH}" width="${w}" height="${h}" rx="6" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"${strokeDash}${filterAttr}/>`;
      break;
    case "round":
      shapeSvg = `<rect x="${x - halfW}" y="${y - halfH}" width="${w}" height="${h}" rx="14" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"${strokeDash}${filterAttr}/>`;
      break;
    case "capsule":
      shapeSvg = `<rect x="${x - halfW}" y="${y - halfH}" width="${w}" height="${h}" rx="${halfH}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"${strokeDash}${filterAttr}/>`;
      break;
    case "circle": {
      const r = Math.min(halfW, halfH);
      shapeSvg = `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"${strokeDash}${filterAttr}/>`;
      break;
    }
    case "diamond":
      shapeSvg = `<polygon points="${x},${y - halfH} ${x + halfW},${y} ${x},${y + halfH} ${x - halfW},${y}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"${strokeDash}${filterAttr}/>`;
      break;
    case "cylinder": {
      const topH = 8;
      const bodyPath = `M ${x - halfW} ${y - halfH + topH} L ${x - halfW} ${y + halfH - topH} A ${halfW} ${topH} 0 0 0 ${x + halfW} ${y + halfH - topH} L ${x + halfW} ${y - halfH + topH} Z`;
      shapeSvg = `
        <g${filterAttr}>
          <path d="${bodyPath}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"${strokeDash}/>
          <ellipse cx="${x}" cy="${y - halfH + topH}" rx="${halfW}" ry="${topH}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>
        </g>`;
      break;
    }
    case "parallelogram": {
      const offset = 12;
      shapeSvg = `<polygon points="${x - halfW + offset},${y - halfH} ${x + halfW},${y - halfH} ${x + halfW - offset},${y + halfH} ${x - halfW},${y + halfH}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"${strokeDash}${filterAttr}/>`;
      break;
    }
    case "parallelogram_alt": {
      const offset = 12;
      shapeSvg = `<polygon points="${x - halfW},${y - halfH} ${x + halfW - offset},${y - halfH} ${x + halfW},${y + halfH} ${x - halfW + offset},${y + halfH}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"${strokeDash}${filterAttr}/>`;
      break;
    }
    case "subroutine": {
      const subOffset = 8;
      shapeSvg = `
        <g${filterAttr}>
          <rect x="${x - halfW}" y="${y - halfH}" width="${w}" height="${h}" rx="4" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"${strokeDash}/>
          <line x1="${x - halfW + subOffset}" y1="${y - halfH}" x2="${x - halfW + subOffset}" y2="${y + halfH}" stroke="${stroke}" stroke-width="${strokeWidth}"/>
          <line x1="${x + halfW - subOffset}" y1="${y - halfH}" x2="${x + halfW - subOffset}" y2="${y + halfH}" stroke="${stroke}" stroke-width="${strokeWidth}"/>
        </g>`;
      break;
    }
    case "asymmetric":
    default:
      shapeSvg = `<rect x="${x - halfW}" y="${y - halfH}" width="${w}" height="${h}" rx="6" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"${strokeDash}${filterAttr}/>`;
      break;
  }

  const lines = wrapNodeLabel(label);
  const totalTextH = (lines.length - 1) * 16;
  const startY = y - totalTextH / 2;

  let textSvg = `<g class="mermaid-node-text" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif" font-size="12" font-weight="600" fill="${textColor}" text-anchor="middle" dominant-baseline="central">`;
  for (let i = 0; i < lines.length; i++) {
    const lineY = startY + i * 16;
    textSvg += `<text x="${x}" y="${lineY}">${escapeSvgText(lines[i])}</text>`;
  }
  textSvg += `</g>`;

  return `<g class="mermaid-node" id="node-${escapeSvgText(node.id)}">${shapeSvg}${textSvg}</g>`;
}

/**
 * 绘制连线与贝塞尔平滑路径
 */
function renderEdgeSvg(
  edge: MermaidEdge,
  fromNode: MermaidNode,
  toNode: MermaidNode,
  direction: DiagramDirection
): string {
  const isVertical = direction === "TD" || direction === "TB" || direction === "BT";
  let x1 = fromNode.x;
  let y1 = fromNode.y;
  let x2 = toNode.x;
  let y2 = toNode.y;

  if (isVertical) {
    if (direction === "BT") {
      y1 = fromNode.y - fromNode.height / 2;
      y2 = toNode.y + toNode.height / 2;
    } else {
      y1 = fromNode.y + fromNode.height / 2;
      y2 = toNode.y - toNode.height / 2;
    }
  } else {
    if (direction === "RL") {
      x1 = fromNode.x - fromNode.width / 2;
      x2 = toNode.x + toNode.width / 2;
    } else {
      x1 = fromNode.x + fromNode.width / 2;
      x2 = toNode.x - toNode.width / 2;
    }
  }

  let d = "";
  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;

  if (isVertical) {
    const dy = y2 - y1;
    const ctrlDist = Math.max(Math.abs(dy) * 0.45, 18);
    const sign = dy >= 0 ? 1 : -1;
    d = `M ${x1} ${y1} C ${x1} ${y1 + ctrlDist * sign}, ${x2} ${y2 - ctrlDist * sign}, ${x2} ${y2}`;
  } else {
    const dx = x2 - x1;
    const ctrlDist = Math.max(Math.abs(dx) * 0.45, 18);
    const sign = dx >= 0 ? 1 : -1;
    d = `M ${x1} ${y1} C ${x1 + ctrlDist * sign} ${y1}, ${x2 - ctrlDist * sign} ${y2}, ${x2} ${y2}`;
  }

  let stroke = "#0284c7";
  let strokeWidth = "1.75";
  let strokeDash = "";
  let markerEnd = ' marker-end="url(#mermaid-arrow-solid)"';

  if (edge.type === "dashed") {
    stroke = "#0d9488";
    strokeDash = ' stroke-dasharray="5,4"';
    markerEnd = ' marker-end="url(#mermaid-arrow-dashed)"';
  } else if (edge.type === "thick") {
    stroke = "#0369a1";
    strokeWidth = "3.2";
    markerEnd = ' marker-end="url(#mermaid-arrow-thick)"';
  } else if (edge.type === "solid_no_arrow") {
    markerEnd = "";
  } else if (edge.type === "dashed_no_arrow") {
    stroke = "#0d9488";
    strokeDash = ' stroke-dasharray="5,4"';
    markerEnd = "";
  } else if (edge.type === "thick_no_arrow") {
    stroke = "#0369a1";
    strokeWidth = "3.2";
    markerEnd = "";
  }

  let edgeLabelSvg = "";
  if (edge.label) {
    const labelW = estimateTextWidth(edge.label, 11) + 14;
    const labelH = 20;
    edgeLabelSvg = `
      <g class="mermaid-edge-label" transform="translate(${midX}, ${midY})">
        <rect x="${-labelW / 2}" y="${-labelH / 2}" width="${labelW}" height="${labelH}" rx="4" fill="#ffffff" stroke="#cbd5e1" stroke-width="1" filter="url(#mermaid-label-shadow)"/>
        <text x="0" y="0" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="11" font-weight="500" fill="#334155" text-anchor="middle" dominant-baseline="central">${escapeSvgText(edge.label)}</text>
      </g>`;
  }

  return `
    <g class="mermaid-edge">
      <path d="${d}" fill="none" stroke="${stroke}" stroke-width="${strokeWidth}"${strokeDash}${markerEnd}/>
      ${edgeLabelSvg}
    </g>`;
}

/**
 * 将 Mermaid AST 渲染为完整出版级 SVG 字符串
 */
export function renderMermaidSvg(diagram: ParsedMermaidDiagram): string {
  const { viewWidth, viewHeight } = layoutMermaidDiagram(diagram);

  let subgraphsSvg = "";
  for (const sub of diagram.subgraphs) {
    if (sub.width > 0 && sub.height > 0) {
      const titleW = estimateTextWidth(sub.title, 11) + 18;
      subgraphsSvg += `
        <g class="mermaid-subgraph">
          <rect x="${sub.x}" y="${sub.y}" width="${sub.width}" height="${sub.height}" rx="10" fill="url(#mermaid-subgraph-grad)" stroke="#94a3b8" stroke-dasharray="6,4" stroke-width="1.5"/>
          <rect x="${sub.x + 12}" y="${sub.y - 10}" width="${titleW}" height="20" rx="4" fill="#0f766e"/>
          <text x="${sub.x + 12 + titleW / 2}" y="${sub.y}" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="11" font-weight="600" fill="#ffffff" text-anchor="middle" dominant-baseline="central">${escapeSvgText(sub.title)}</text>
        </g>`;
    }
  }

  let edgesSvg = "";
  for (const edge of diagram.edges) {
    const fromNode = diagram.nodes.get(edge.from);
    const toNode = diagram.nodes.get(edge.to);
    if (fromNode && toNode) {
      edgesSvg += renderEdgeSvg(edge, fromNode, toNode, diagram.direction);
    }
  }

  let nodesSvg = "";
  for (const node of diagram.nodes.values()) {
    nodesSvg += renderNodeShapeSvg(node, diagram.classDefs);
  }

  return `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${viewWidth} ${viewHeight}" width="100%" height="100%" style="max-width: ${Math.max(viewWidth, 400)}px; margin: 0 auto; display: block;">
  <defs>
    <!-- 箭头 Markers -->
    <marker id="mermaid-arrow-solid" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#0284c7" />
    </marker>
    <marker id="mermaid-arrow-dashed" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#0d9488" />
    </marker>
    <marker id="mermaid-arrow-thick" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#0369a1" />
    </marker>
    <!-- 渐变主题 -->
    <linearGradient id="mermaid-grad-blue" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f0f9ff" />
      <stop offset="100%" stop-color="#e0f2fe" />
    </linearGradient>
    <linearGradient id="mermaid-grad-teal" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f0fdf4" />
      <stop offset="100%" stop-color="#ccfbf1" />
    </linearGradient>
    <linearGradient id="mermaid-grad-amber" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fffbeb" />
      <stop offset="100%" stop-color="#fef3c7" />
    </linearGradient>
    <linearGradient id="mermaid-grad-indigo" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#eef2ff" />
      <stop offset="100%" stop-color="#e0e7ff" />
    </linearGradient>
    <linearGradient id="mermaid-subgraph-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f8fafc" />
      <stop offset="100%" stop-color="#f1f5f9" />
    </linearGradient>
    <!-- 阴影滤镜 -->
    <filter id="mermaid-drop-shadow" x="-10%" y="-10%" width="125%" height="125%">
      <feDropShadow dx="0" dy="2" stdDeviation="2.5" flood-color="#0f172a" flood-opacity="0.07" />
    </filter>
    <filter id="mermaid-label-shadow" x="-15%" y="-15%" width="130%" height="130%">
      <feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#0f172a" flood-opacity="0.05" />
    </filter>
  </defs>
  <g class="mermaid-diagram-body">
    ${subgraphsSvg}
    ${edgesSvg}
    ${nodesSvg}
  </g>
</svg>`.trim();
}

/**
 * 完整渲染 Mermaid 代码块为富交互 HTML 卡片
 * 具备双视图切换、复制代码与异常容错降级
 */
export function renderMermaidToHtml(mermaidCode: string): string {
  if (!mermaidCode || !mermaidCode.trim()) {
    return "";
  }

  const cleanCode = mermaidCode.trim();
  const escapedCode = escapeSvgText(cleanCode);

  try {
    const diagram = parseMermaid(cleanCode);
    const nodeCount = diagram.nodes.size;
    const svgContent = renderMermaidSvg(diagram);

    return `
<div class="mermaid-container" data-mermaid-code="${escapedCode}">
  <div class="mermaid-toolbar" contenteditable="false">
    <div class="mermaid-tag">
      <span class="mermaid-icon">📊</span>
      <span class="mermaid-title">工艺/工程流程拓扑图</span>
      <span class="mermaid-meta">${nodeCount} 个工序节点</span>
    </div>
    <div class="mermaid-actions">
      <button type="button" class="mermaid-btn mermaid-btn-toggle-view" data-action="toggle-view" title="切换矢量视图/源码">
        <span class="btn-icon">👁️</span><span class="btn-text">矢量拓扑</span>
      </button>
      <button type="button" class="mermaid-btn mermaid-btn-copy" data-action="copy" title="复制 Mermaid 源码">
        <span class="btn-icon">📋</span><span class="btn-text">复制代码</span>
      </button>
    </div>
  </div>
  <div class="mermaid-svg-wrapper" contenteditable="false">
    ${svgContent}
  </div>
  <div class="mermaid-code-wrapper" contenteditable="false" style="display: none;">
    <pre><code class="language-mermaid">${escapedCode}</code></pre>
  </div>
</div>`.trim();
  } catch (_e) {
    // 语法错误或极端格式异常降级展示，绝对杜绝白屏与抛错
    return `
<div class="mermaid-container mermaid-fallback" data-mermaid-code="${escapedCode}">
  <div class="mermaid-toolbar" contenteditable="false">
    <div class="mermaid-tag">
      <span class="mermaid-icon">📊</span>
      <span class="mermaid-title">工艺/工程流程图源码</span>
      <span class="mermaid-fallback-badge">⚠️ 源码视图</span>
    </div>
    <div class="mermaid-actions">
      <button type="button" class="mermaid-btn mermaid-btn-copy" data-action="copy" title="复制 Mermaid 源码">
        <span class="btn-icon">📋</span><span class="btn-text">复制代码</span>
      </button>
    </div>
  </div>
  <div class="mermaid-code-wrapper" contenteditable="false">
    <pre><code class="language-mermaid">${escapedCode}</code></pre>
  </div>
</div>`.trim();
  }
}
