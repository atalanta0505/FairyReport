/**
 * 轻量高性能 Markdown 排版解析与渲染器
 *
 * 0 外部依赖，原生 TypeScript 实现
 * 支持各级标题（带锚点 ID）、粗体/斜体、代码、列表、表格、引用块、来源标签高亮徽章与反向 Markdown 序列化
 */

import type { ReviewIssue } from "./engineApi";
import { renderMermaidToHtml } from "./mermaid";

export { renderMermaidToHtml };

export interface SubHeading {
  id: string;
  level: number;
  title: string;
  raw: string;
  index: number;
}

export interface ReferenceItem {
  type: "material" | "standard" | "web" | "other";
  typeLabel: string;
  title: string;
  raw: string;
  count: number;
  url?: string;
}

export interface ReferencesSummary {
  material: { count: number; citations: number };
  standard: { count: number; citations: number };
  web: { count: number; citations: number };
  totalCount: number;
  totalCitations: number;
}

/**
 * 汇总三源参考文献的条目数量与引用次数
 */
export function getReferencesSummary(refs: ReferenceItem[]): ReferencesSummary {
  const summary: ReferencesSummary = {
    material: { count: 0, citations: 0 },
    standard: { count: 0, citations: 0 },
    web: { count: 0, citations: 0 },
    totalCount: 0,
    totalCitations: 0,
  };
  if (!refs || !Array.isArray(refs)) return summary;

  for (const ref of refs) {
    const count = typeof ref.count === "number" && ref.count > 0 ? ref.count : 1;
    if (ref.type === "standard") {
      summary.standard.count += 1;
      summary.standard.citations += count;
    } else if (ref.type === "web") {
      summary.web.count += 1;
      summary.web.citations += count;
    } else {
      summary.material.count += 1;
      summary.material.citations += count;
    }
    summary.totalCount += 1;
    summary.totalCitations += count;
  }

  return summary;
}

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function unescapeHtml(text: string): string {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ");
}

/**
 * 格式化行内元素：代码、来源标签、粗体、斜体、删除线
 */
export function formatInline(text: string): string {
  if (!text) return "";

  // 1. 转义 HTML 特殊字符，杜绝 XSS
  let escaped = escapeHtml(text);

  // 2. 行内代码 `code`：提取保护避免被后续加粗/斜体正则干扰（使用不含 _ 或 * 的特殊占位符）
  const codeBlocks: string[] = [];
  escaped = escaped.replace(/`([^`]+)`/g, (_match, codeContent) => {
    const idx = codeBlocks.length;
    codeBlocks.push(`<code>${codeContent}</code>`);
    return `\uFFF0CODE${idx}\uFFF0`;
  });

  // 3. 来源引用语义化内联标签：【源:...】、【网:...】、【标:...】、【规:...】与 [Z]
  escaped = escaped.replace(
    /【(源|材料|网|网络|标|标准|规|规程|法|法规)([:：][^】]+)】/g,
    (_match, prefix: string, rest: string) => {
      const colon = rest[0];
      const content = rest.slice(1).trim();
      let type: "material" | "standard" | "web" = "material";
      if (prefix.startsWith("网")) {
        type = "web";
      } else if (prefix.startsWith("标") || prefix.startsWith("规") || prefix.startsWith("法")) {
        type = "standard";
      } else {
        if (/规程|规范|标准|GB|SL|NB|DL|定额|导则|通则|法/i.test(content)) {
          type = "standard";
        } else {
          type = "material";
        }
      }
      const escapedTitle = escapeHtml(unescapeHtml(content));
      const rawTag = `【${prefix}${colon}${content}】`;
      return `<span class="inline-ref-tag type-${type}" data-ref-type="${type}" data-ref-title="${escapedTitle}" title="点击查看参考资料出处">${rawTag}</span>`;
    }
  );

  escaped = escaped.replace(
    /\[Z(?::|：|-)?([a-zA-Z0-9_\-\u4e00-\u9fa5]*)\]/g,
    (_match, suffix: string) => {
      const s = suffix ? suffix.trim() : "";
      const identifier = s ? `标准规范依据 [Z-${s}]` : "标准规范规程库 [Z]";
      const rawTag = s ? `[Z-${s}]` : "[Z]";
      const escapedTitle = escapeHtml(identifier);
      return `<span class="inline-ref-tag type-standard" data-ref-type="standard" data-ref-title="${escapedTitle}" title="点击查看参考资料出处">${rawTag}</span>`;
    }
  );

  // 4. 粗斜体 ***text***
  escaped = escaped.replace(/\*\*\*([^*]+)\*\*\*/g, "<strong><em>$1</em></strong>");

  // 5. 粗体 **bold** 或 __bold__
  escaped = escaped.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  escaped = escaped.replace(/__([^_]+)__/g, "<strong>$1</strong>");

  // 6. 斜体 *italic* 或 _italic_
  escaped = escaped.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, "<em>$1</em>");
  escaped = escaped.replace(/(?<!_)_([^_]+)_(?!_)/g, "<em>$1</em>");

  // 7. 删除线 ~~deleted~~
  escaped = escaped.replace(/~~([^~]+)~~/g, "<del>$1</del>");

  // 8. 还原行内代码
  escaped = escaped.replace(/\uFFF0CODE(\d+)\uFFF0/g, (_match, idx) => {
    return codeBlocks[Number(idx)] || "";
  });

  return escaped;
}

function isTableLine(line: string): boolean {
  const trimmed = line.trim();
  return trimmed.startsWith("|") || (trimmed.includes("|") && trimmed.endsWith("|"));
}

function parseTableRow(line: string): string[] {
  let content = line.trim();
  if (content.startsWith("|")) content = content.slice(1);
  if (content.endsWith("|")) content = content.slice(0, -1);
  return content.split("|").map((c) => c.trim());
}

function isTableSeparator(line: string): boolean {
  if (!isTableLine(line)) return false;
  const cells = parseTableRow(line);
  if (cells.length === 0) return false;
  return cells.every((cell) => /^:?-{1,}:?$/.test(cell.trim()));
}

/**
 * 从大纲 Markdown 中提取所有纯净标题文本（# ~ ####）
 * 包含带序号和去除序号前缀的标题，按长度降序排序，保证长标题优先匹配
 */
export function extractOutlineHeadings(outlineMd: string): string[] {
  if (!outlineMd || typeof outlineMd !== "string") return [];
  const lines = outlineMd.split("\n");
  const headingSet = new Set<string>();
  for (const line of lines) {
    const trimmed = line.trim();
    const match = trimmed.match(/^#{1,4}\s+(.+)$/);
    if (match) {
      const full = match[1].trim();
      if (full) {
        headingSet.add(full);
        // 去除章节序号前缀（如 "1.4.1 主要研究结论" -> "主要研究结论", "第一章 概述" -> "概述"）
        const noPrefix = full.replace(/^(?:第[一二三四五六七八九十百零\d]+章|\d+(?:\.\d+)*)\s*/, "").trim();
        if (noPrefix) {
          headingSet.add(noPrefix);
        }
      }
    }
  }
  // 长度降序排序，保证长标题优先匹配
  return Array.from(headingSet).sort((a, b) => b.length - a.length);
}

const REPORT_TITLE_KEYWORDS = [
  "必要性", "可行性", "合理性", "衔接性", "符合性", "适当性", "适应性", "可靠性", "安全性", "经济性", "合规性",
  "立项背景", "建设背景", "项目背景", "行业背景", "政策背景", "前期进展", "工作进展", "审批情况",
  "建设条件", "选址方案", "规划选址", "建设规模", "产品方案", "技术方案", "工艺方案", "工程方案",
  "总图布置", "设备方案", "节能评估", "环境保护", "环境影响", "水土保持", "劳动安全", "消防安全",
  "组织机构", "劳动定员", "实施进度", "工程进度", "投资估算", "资金筹措", "财务评价", "经济评价",
  "社会效益", "生态效益", "环境效益", "风险分析", "防范对策", "招标方案", "结论建议", "编制依据",
  "生产或服务能力", "市场需求潜力", "产出合理性评价", "建设规模方案比选", "总体布局", "分期建设安排",
  "建设标准", "质量标准要求", "需求现状调查", "功能定位与目标", "需求总量与结构", "主要建设内容",
  "背景", "进展", "情况", "分析", "评价", "方案", "选址", "条件", "保障", "规模", "指标",
  "概算", "估算", "预测", "规划", "目标", "措施", "对策", "建议", "结论", "论述", "研究",
  "内容", "概况", "要求", "依据", "原则", "构想", "说明", "安排", "计划", "总结", "表",
  "体系", "定位", "布局", "工艺", "设备", "工程", "效益", "风险", "基础", "现状", "需求",
  "标准", "能力", "潜力", "水平", "时机", "特征", "参数", "比选", "模式", "机制",
  "设计", "施工", "运营", "管理", "定员", "招标", "效果", "影响",
  "举措", "抓手", "制度", "政策", "行动", "平台", "生态", "协同", "试点", "示范",
  "支撑", "导向", "闭环", "转型", "赋能", "供给", "攻坚", "防护", "风控", "治理",
  "路径", "指引", "防线", "预警", "清单",
  "规范", "指南", "任务", "策略"
];

export function normalizeMarkdown(md: string, knownHeadings?: string[]): string {
  if (!md || typeof md !== "string") return "";
  let text = md.replace(/\r\n/g, "\n");

  // 若包含独立的参考文献章（# 参考文献 或 ## 参考文献），将其彻底隔离保护
  const refMarker = text.search(/\n(?=#{1,2}\s+参考文献\b)/);
  let refSection = "";
  if (refMarker !== -1) {
    refSection = text.slice(refMarker);
    text = text.slice(0, refMarker);
  } else if (/^#{1,2}\s+参考文献\b/.test(text)) {
    return text;
  }

  // 1. 核心：在所有非换行符/非#紧邻的 #{1,6}\s+ 前面强制补双换行符
  text = text.replace(/([^#\n])\s*(#{1,6}\s+)/g, "$1\n\n$2");

  // 2. 表格单行粘连还原：将单行用 || 连接的全部表格行（表头、分隔线、数据行）还原为标准换行
  // 例如：|序号|指标名称|...||------|...|| 1 | ... || 2 | ... |
  text = text.replace(/\|\s*\|/g, "|\n|");

  // 3. 表格与前置文本粘连时规范化换行
  text = text.replace(/^([^|\n].*?)(\|.+?\|\s*\n\s*\|[-: ]+?\|)/gm, "$1\n\n$2");

  // 4. 标题与加粗/引用/表格粘连拆解（如 ### 1.1.1 建设地点**项目名称**）
  text = text.replace(/(#{1,6}\s+[^\n*|【]*?)\s*(\*\*|【源|\|)/g, "$1\n\n$2");

  // 5. 若传入已知大纲标题库，不论后面跟随的是标点、空格还是直接是中文正文字符，无条件在已知标题边界处截断并插入双换行符 \n\n
  if (knownHeadings && Array.isArray(knownHeadings)) {
    for (const h of knownHeadings) {
      if (!h || typeof h !== "string") continue;
      const cleanH = h.replace(/^#+\s*/, "").trim();
      if (!cleanH) continue;
      const escaped = cleanH.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      // 匹配形如 ### 1.4.1 主要研究结论：经研究论证， 或 ### 1.4.1 主要研究结论经研究论证， -> ### 1.4.1 主要研究结论\n\n经研究论证，
      const reg = new RegExp(`^(#{1,6}\\s+(?:\\d+(?:\\.\\d+)*\\s+)?${escaped})\\s*([:：，。—\\-\\u2014\\u2013\\s]*)([^\\n]+)$`, "gm");
      text = text.replace(reg, (_match, hPart, _punct, restPart) => {
        const cleanRest = restPart.replace(/^[:：—\\-\\u2014\\u2013,，。\\s]+/, "").trim();
        return cleanRest ? `${hPart}\n\n${cleanRest}` : hPart;
      });
    }
  }

  // 6. 仅在单行标题后紧跟冒号/句号/破折号等明显正文标点时才执行标题正文拆分（如 ### 1.1.1 建设地点：本项目位于...）
  text = text.replace(
    /^(#{1,6}\s+[^\n:：。—\-\u2014\u2013]{2,50}?)\s*([:：。—\-\u2014\u2013]+)\s*([^\n]+)$/gm,
    (_match, titlePart, _punct, rest) => {
      const cleanRest = rest.replace(/^[:：。—\-\u2014\u2013\s]+/, "").trim();
      return cleanRest ? `${titlePart}\n\n${cleanRest}` : titlePart;
    }
  );

  // 6.1 & 6.2 标题（Markdown标题或带数字/公文编号条目）与正文粘连精准拆分（全面覆盖多级工程数字 2.3.1、单级编号 2.、1、以及公文序号 （一）、一、）
  function splitHeadingBody(prefix: string, numPart: string, rest: string): string | null {
    const p = (prefix || "").trim();
    const num = (numPart || "").trim();
    const cleanRest = (rest || "").trim();
    if (!cleanRest) return null;

    const prefixFinal = !p && /^\d+(?:\.\d+)+$/.test(num) ? "###" : p;
    const lead = prefixFinal ? `${prefixFinal} ` : "";
    const numLead = num ? `${num} ` : "";

    // 若以 "第X章" 开头（如 "第二章 工程建设方案"），公文序号（如 "三、对策建议"），或附表/附件（如 "附表1 核心指标..."），绝不可拆分为标题与正文
    if (/^(?:第[一二三四五六七八九十百零\d]+[章节]|附[表录图件]\d+|[一二三四五六七八九十]+[、\.\s])/.test(cleanRest)) {
      return null;
    }

    // 显式分隔标点（如 标题：正文、标题。正文）；纯空格分隔仅在有序号引导 num 时生效
    const sepPattern = num
      ? /^([^\n.:：。—\-\u2014\u2013\s]{2,35}?)(?:\s+|[:：。—\-\u2014\u2013]+)([\u4e00-\u9fa5].{4,})$/
      : /^([^\n.:：。—\-\u2014\u2013\s]{2,35}?)(?:[:：。—\-\u2014\u2013]+)([\u4e00-\u9fa5].{4,})$/;
    const mSep = cleanRest.match(sepPattern);
    if (mSep) {
      const hText = mSep[1].trim();
      const bodyText = mSep[2].trim();
      return `${lead}${numLead}${hText}\n\n${bodyText}`;
    }

    // 无标点无空格粘连（扫描标题关键词，严格限制在首个中文标点前，防止跨越正文）
    const punctMatch = cleanRest.match(/[，。；！？]/);
    // 若整行没有任何标点且长度在常规标题范围内（<= 30字），说明是纯净标题，绝不拆分
    if (!punctMatch && cleanRest.length <= 30) {
      return null;
    }
    let searchLimit = punctMatch && punctMatch.index !== undefined ? punctMatch.index : cleanRest.length;
    searchLimit = Math.min(searchLimit, 35);

    let maxEnd = -1;
    let startIdxMatch = -1;
    for (const kw of REPORT_TITLE_KEYWORDS) {
      const kwIdx = cleanRest.indexOf(kw);
      if (kwIdx >= 0) {
        let endPos = kwIdx + kw.length;
        const parenMatch = cleanRest.slice(endPos).match(/^(?:（[^）]+）|\([^)]+\))/);
        if (parenMatch) {
          endPos += parenMatch[0].length;
        }
        if (endPos <= searchLimit) {
          if (kwIdx === 0) {
            if (endPos > maxEnd) {
              maxEnd = endPos;
              startIdxMatch = 0;
            }
          } else if (startIdxMatch !== 0 && endPos > maxEnd) {
            maxEnd = endPos;
          }
        }
      }
    }

    if (maxEnd > 0 && maxEnd < cleanRest.length) {
      const hText = cleanRest.slice(0, maxEnd).trim();
      const bodyText = cleanRest.slice(maxEnd).replace(/^[:：。—\-\u2014\u2013，,\s\t]+/, "").trim();
      if (/^[与及和]/.test(bodyText)) {
        return null;
      }
      if (bodyText.length >= 4) {
        return `${lead}${numLead}${hText}\n\n${bodyText}`;
      }
    }
    return null;
  }

  // A) 以 Markdown # 开头（后跟可选数字/公文编号）
  text = text.replace(
    /^(#{1,6})\s+((?:\d+(?:\.\d+)+|\d+[\.、]|\d+\s+|（[一二三四五六七八九十\d]+）|[一二三四五六七八九十]+[、\.\s])\s*)?([^\n]+)$/gm,
    (m, prefix, num, rest) => {
      const res = splitHeadingBody(prefix, num, rest);
      return res ? res : m;
    }
  );

  // B) 无 Markdown #，以数字序号或公文序号开头
  text = text.replace(
    /^((?:\d+(?:\.\d+)+|\d+[\.、]|\d+\s+|（[一二三四五六七八九十\d]+）|[一二三四五六七八九十]+[、\.\s]))\s*([^\n]+)$/gm,
    (m, num, rest) => {
      const res = splitHeadingBody("", num, rest);
      return res ? res : m;
    }
  );

  // 7. 引用标记行内紧随融合与标点去重（消除孤立换行，贴合在陈述句末尾，根除双标点）
  // 7.1 句末标点与换行的引用标签（前置标点移动至引用后，若后置已带标点则合并为单标点）
  text = text.replace(
    /([，。；！？])\s*\n+\s*【(源|材料|标|标准|规|规程|网|网络)[:：]([^】]+)】\s*([，。；！？])?/g,
    "【$2:$3】$1"
  );
  // 7.2 [Z] 或 [N] 引用同理：仅匹配陈述句末尾孤立换行的学术引用标记，严禁误吞以 [N] 开头的参考文献条目
  text = text.replace(
    /([，。；！？])\s*\n+\s*(\[Z(?:-[^\]]+)?\]|\[\d+\])(?!\s*\[)\s*([，。；！？])?/g,
    "$2$1"
  );
  // 7.3 普通文本换行后紧跟引用标记：排除标题行
  text = text.replace(
    /^(?!\s*#{1,6}\s)(.+[^\s\n#|>-])\s*\n+\s*【(源|材料|标|标准|规|规程|网|网络)[:：]([^】]+)】\s*$/gm,
    "$1【$2:$3】"
  );
  // 7.4 消除紧随引用标记后或正文中的重复句号与标点（如 [1]。。 / 【源:...】。。 等）
  text = text.replace(
    /(【(?:源|材料|标|标准|规|规程|网|网络)[:：][^】]+】|\[\d+\]|\[Z(?:-[^\]]+)?\])\s*([。！？；!?,，、]){2,}/g,
    "$1$2"
  );
  // 消除引用标记前后同时出现标点的情况（如 。【源:xxx】。 -> 【源:xxx】。）
  text = text.replace(
    /([，。；！？])\s*(【(?:源|材料|标|标准|规|规程|网|网络)[:：][^】]+】|\[\d+\]|\[Z(?:-[^\]]+)?\])\s*([，。；！？])/g,
    "$2$3"
  );
  // 消除连续同类中文标点（双句号、双逗号、双分号等，保留……与——）
  text = text.replace(/([。，、；])\1+/g, "$1");

  // 8. 节首孤立无标点引导短句补齐标点与正文段落融合
  const lines = text.split("\n");
  const newLines: string[] = [];
  let idx = 0;
  while (idx < lines.length) {
    const line = lines[idx];
    newLines.push(line);
    if (/^#{2,6}\s+/.test(line.trim())) {
      let b = idx + 1;
      while (b < lines.length && !lines[b].trim()) {
        b++;
      }
      if (b < lines.length) {
        const firstBody = lines[b].trim();
        const isSpecial = (
          firstBody.startsWith("#") ||
          firstBody.startsWith("|") ||
          firstBody.startsWith("-") ||
          firstBody.startsWith("*") ||
          firstBody.startsWith(">") ||
          firstBody.startsWith("```") ||
          /^\d+[\.、]/.test(firstBody)
        );
        if (!isSpecial) {
          const hasEndPunct = /[。！？；!?;:…”’\.：—~]$/.test(firstBody);
          const normFirst = hasEndPunct ? firstBody : firstBody + "。";

          let merged = false;
          if (firstBody.length <= 80 && !firstBody.endsWith("：") && !firstBody.endsWith(":")) {
            let c = b + 1;
            while (c < lines.length && !lines[c].trim()) {
              c++;
            }
            if (c < lines.length) {
              const secondBody = lines[c].trim();
              const isSecondSpecial = (
                secondBody.startsWith("#") ||
                secondBody.startsWith("|") ||
                secondBody.startsWith("-") ||
                secondBody.startsWith("*") ||
                secondBody.startsWith(">") ||
                secondBody.startsWith("```") ||
                /^\d+[\.、]/.test(secondBody)
              );
              if (!isSecondSpecial) {
                newLines.push("");
                newLines.push(normFirst + (secondBody.startsWith(" ") ? "" : "") + secondBody);
                idx = c;
                merged = true;
              }
            }
          }

          if (!merged) {
            newLines.push("");
            newLines.push(normFirst);
            idx = b;
          }
        }
      }
    }
    idx++;
  }

  const res = newLines.join("\n");
  const cleaned = res.replace(/\n{3,}/g, "\n\n");
  if (refSection) {
    return `${cleaned.trimEnd()}\n\n${refSection.trim()}\n`;
  }
  return cleaned;
}

/**
 * 剥离 Markdown 中的表格行（| ... |），保留纯正文文本
 */
export function stripMarkdownTables(md: string): string {
  if (!md || typeof md !== "string") return "";
  return md.replace(/^\s*\|.*?\|\s*$/gm, "");
}

/**
 * 统计 Markdown 纯正文字数（剥离标题行、Markdown 表格行、来源标签及前后空白）
 */
export function countContentChars(md: string): number {
  if (!md || typeof md !== "string") return 0;
  // 1. 去除标题行
  let text = md.replace(/^#{1,6}\s+.*$/gm, "");
  // 2. 剥离表格行
  text = stripMarkdownTables(text);
  // 3. 去除来源标签
  text = text.replace(/【(?:源|材料|网|网络|标|标准|规|规程|法|法规)[:：][^】]+】/g, "");
  text = text.replace(/\[Z(?::|：|-)?([a-zA-Z0-9_\-\u4e00-\u9fa5]*)\]/g, "");
  // 4. 去除空白并统计有效正文字符数
  const cleaned = text.replace(/\s+/g, "");
  return cleaned.length;
}

/**
 * 别名，兼容语义化调用
 */
export const countContentCharsExcludingTables = countContentChars;

/**
 * 提取 Markdown 中的子标题列表（H1~H4），带锚点 ID
 */
export function extractSubHeadings(
  md: string,
  chapterSeq?: number,
  knownHeadings?: string[]
): SubHeading[] {
  if (!md || typeof md !== "string") {
    return [];
  }

  const normalized = normalizeMarkdown(md, knownHeadings);
  const lines = normalized.split("\n");
  const headings: SubHeading[] = [];
  let index = 0;
  let inCodeBlock = false;
  const seq = chapterSeq !== undefined ? chapterSeq : 0;

  for (const line of lines) {
    const trimmed = line.trim();

    if (trimmed.startsWith("```")) {
      inCodeBlock = !inCodeBlock;
      continue;
    }
    if (inCodeBlock) continue;

    const match = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (match) {
      const level = match[1].length;
      const rawTitle = match[2].trim();
      // 清理标题中的 markdown 标记，得到纯文本标题
      const cleanTitle = rawTitle
        .replace(/\*\*([^*]+)\*\*/g, "$1")
        .replace(/\*([^*]+)\*/g, "$1")
        .replace(/`([^`]+)`/g, "$1")
        .replace(/【(?:源|材料|网|网络|标|标准|规|规程)[:：][^】]+】/g, "")
        .replace(/\[Z(?::|：|-)?([a-zA-Z0-9_\-\u4e00-\u9fa5]*)\]/g, "")
        .trim();

      headings.push({
        id: `h-ch${seq}-idx${index}`,
        level,
        title: cleanTitle || rawTitle,
        raw: trimmed,
        index,
      });
      index++;
    }
  }

  return headings;
}

/**
 * 从正文中提取所有参考资料与底稿规程引用来源标签清单
 */
export function extractReferences(text: string, ragContext?: string): ReferenceItem[] {
  if (!text || typeof text !== "string") return [];

  const map = new Map<string, { type: "material" | "standard" | "web" | "other"; typeLabel: string; title: string; raw: string; count: number; url?: string }>();

  // 1. 匹配 【源:...】 / 【材料:...】 / 【标:...】 / 【网:...】 / 【规:...】
  const bracketRegex = /【(源|材料|网|网络|标|标准|规|规程|法|法规)[:：]\s*([^】]+)】/g;
  let m: RegExpExecArray | null;
  while ((m = bracketRegex.exec(text)) !== null) {
    const rawTag = m[0];
    const prefix = m[1];
    const content = m[2].trim();
    if (!content) continue;

    let type: "material" | "standard" | "web" | "other" = "material";
    let typeLabel = "项目底稿";
    let url: string | undefined = undefined;

    if (prefix.startsWith("网")) {
      type = "web";
      typeLabel = "百度联网";
      // 尝试提取真实 URL（从正文、附带格式或 ragContext 中）
      const escapedTitle = content.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const urlPattern = new RegExp(`【(?:网|网络)[:：]\\s*${escapedTitle}】\\s*\\n?\\s*(https?:\\/\\/[^\\s\\n>"\\]]+)`);
      const urlMatch = text.match(urlPattern) || (ragContext ? ragContext.match(urlPattern) : null);
      if (urlMatch) {
        url = urlMatch[1].trim();
      } else {
        const linkPattern = new RegExp(`\\[${escapedTitle}\\]\\((https?:\\/\\/[^\\s\\n>"\\]]+)\\)`);
        const linkMatch = text.match(linkPattern) || (ragContext ? ragContext.match(linkPattern) : null);
        if (linkMatch) {
          url = linkMatch[1].trim();
        } else {
          const generalMatch = (ragContext || text).match(new RegExp(`${escapedTitle}[\\s\\S]{0,80}?(https?:\\/\\/[^\\s\\n>"\\]]+)`));
          if (generalMatch) {
            url = generalMatch[1].trim();
          }
        }
      }
    } else if (prefix.startsWith("标") || prefix.startsWith("规") || prefix.startsWith("法")) {
      type = "standard";
      typeLabel = "标准规程";
    } else {
      if (/规程|规范|标准|GB|SL|NB|DL|定额|导则|通则|法/i.test(content)) {
        type = "standard";
        typeLabel = "标准规程";
      } else {
        type = "material";
        typeLabel = "项目底稿";
      }
    }

    const key = `${type}::${content}`;
    if (map.has(key)) {
      const item = map.get(key)!;
      item.count += 1;
      if (!item.url && url) {
        item.url = url;
      }
    } else {
      map.set(key, {
        type,
        typeLabel,
        title: content,
        raw: rawTag,
        count: 1,
        url,
      });
    }
  }

  // 从章末 ## 📎 本章参考资料 中提取并补齐可能缺失的 web URL
  const footerLines = text.split("\n");
  let inWebSection = false;
  for (const line of footerLines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("### 网页链接")) {
      inWebSection = true;
    } else if (trimmed.startsWith("### ") || trimmed.startsWith("## ")) {
      inWebSection = false;
    } else if (inWebSection && trimmed.startsWith("- ")) {
      const item = trimmed.slice(2).trim();
      const linkM = item.match(/^\[(.*?)\]\((https?:\/\/[^\s\n>"]+)\)$/);
      if (linkM) {
        const nameClean = linkM[1].trim();
        const srcClean = linkM[2].trim();
        for (const val of map.values()) {
          if (val.type === "web" && (val.title === nameClean || val.title.includes(nameClean) || nameClean.includes(val.title))) {
            if (!val.url) val.url = srcClean;
          }
        }
      } else if (item.includes(" — ")) {
        const [n, s] = item.split(" — ", 2);
        const nameClean = n.trim();
        const srcClean = s.trim();
        if (srcClean.startsWith("http")) {
          for (const val of map.values()) {
            if (val.type === "web" && (val.title === nameClean || val.title.includes(nameClean) || nameClean.includes(val.title))) {
              if (!val.url) val.url = srcClean;
            }
          }
        }
      }
    }
  }

  // 2. 匹配标准引用标签 [Z] 或 [Z-1] 或 [文献...]（向下兼容）
  const citationRegex = /\[Z(?::|：|-)?([a-zA-Z0-9_\-\u4e00-\u9fa5]*)\]/g;
  while ((m = citationRegex.exec(text)) !== null) {
    const rawTag = m[0];
    const suffix = m[1] ? m[1].trim() : "";
    const identifier = suffix ? `标准规范依据 [Z-${suffix}]` : "标准规范规程库 [Z]";
    const key = `standard::${identifier}`;
    if (map.has(key)) {
      map.get(key)!.count += 1;
    } else {
      map.set(key, {
        type: "standard",
        typeLabel: "标准规程",
        title: identifier,
        raw: rawTag,
        count: 1,
      });
    }
  }

  // 排序：频次降序，然后标题排序
  return Array.from(map.values()).sort((a, b) => {
    if (b.count !== a.count) {
      return b.count - a.count;
    }
    return a.title.localeCompare(b.title, "zh-CN");
  });
}

/**
 * 将 Markdown 文本解析转换为语义化且安全的 HTML（标题带锚点 ID）
 */
export function markdownToHtml(
  md: string,
  chapterSeq?: number,
  knownHeadings?: string[]
): string {
  if (!md || typeof md !== "string" || !md.trim()) {
    return "";
  }

  const normalized = normalizeMarkdown(md, knownHeadings);
  const lines = normalized.split("\n");
  const htmlParts: string[] = [];
  let i = 0;
  let headingIndex = 0;
  const seq = chapterSeq !== undefined ? chapterSeq : 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // 1. 空行跳过
    if (!trimmed) {
      i++;
      continue;
    }

    // 2. 标题 (# H1 ~ ###### H6)
    const headingMatch = line.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const content = headingMatch[2];
      const headingId = `h-ch${seq}-idx${headingIndex++}`;
      htmlParts.push(`<h${level} id="${headingId}">${formatInline(content)}</h${level}>`);
      i++;
      continue;
    }

    // 3. 分割线 (---, ***, ___)
    if (/^(\*{3,}|-{3,}|_{3,})$/.test(trimmed)) {
      htmlParts.push("<hr />");
      i++;
      continue;
    }

    // 4. 引用块 (> ...)
    if (trimmed.startsWith(">")) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ""));
        i++;
      }
      const quoteContent = quoteLines.map((l) => formatInline(l)).join("<br />");
      htmlParts.push(`<blockquote><p>${quoteContent}</p></blockquote>`);
      continue;
    }

    // 5. 代码块 (```lang ... ```)
    if (trimmed.startsWith("```")) {
      const lang = trimmed.slice(3).trim();
      i++;
      const rawCodeLines: string[] = [];
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        rawCodeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length && lines[i].trim().startsWith("```")) {
        i++; // 跳过结束 ```
      }

      if (lang.toLowerCase() === "mermaid") {
        const mermaidCode = rawCodeLines.join("\n");
        htmlParts.push(renderMermaidToHtml(mermaidCode));
        continue;
      }

      const escapedLines = rawCodeLines.map((l) => escapeHtml(l));
      const langClass = lang ? ` class="language-${escapeHtml(lang)}"` : "";
      htmlParts.push(`<pre><code${langClass}>${escapedLines.join("\n")}</code></pre>`);
      continue;
    }

    // 6. 表格 (| Col 1 | Col 2 |)
    if (isTableLine(trimmed) && i + 1 < lines.length && isTableSeparator(lines[i + 1].trim())) {
      const headerLine = trimmed;
      const headers = parseTableRow(headerLine);
      i += 2; // 跳过表头和分隔线

      const rows: string[][] = [];
      while (i < lines.length && isTableLine(lines[i].trim())) {
        rows.push(parseTableRow(lines[i].trim()));
        i++;
      }

      let tableHtml = "<table><thead><tr>";
      for (const h of headers) {
        tableHtml += `<th>${formatInline(h)}</th>`;
      }
      tableHtml += "</tr></thead><tbody>";
      for (const row of rows) {
        tableHtml += "<tr>";
        for (let c = 0; c < headers.length; c++) {
          const cell = row[c] ?? "";
          tableHtml += `<td>${formatInline(cell)}</td>`;
        }
        tableHtml += "</tr>";
      }
      tableHtml += "</tbody></table>";
      htmlParts.push(tableHtml);
      continue;
    }

    // 7. 无序列表 (- item, * item, + item)
    if (/^[\*\-\+]\s+/.test(trimmed)) {
      const listItems: string[] = [];
      while (i < lines.length && /^[\*\-\+]\s+/.test(lines[i].trim())) {
        const itemContent = lines[i].trim().replace(/^[\*\-\+]\s+/, "");
        listItems.push(itemContent);
        i++;
      }
      let ulHtml = "<ul>";
      for (const item of listItems) {
        ulHtml += `<li>${formatInline(item)}</li>`;
      }
      ulHtml += "</ul>";
      htmlParts.push(ulHtml);
      continue;
    }

    // 8. 有序列表 (1. item, 2) item, (1) item)
    if (/^(\d+[\.\)]|\(\d+\))\s+/.test(trimmed)) {
      const listItems: string[] = [];
      while (i < lines.length && /^(\d+[\.\)]|\(\d+\))\s+/.test(lines[i].trim())) {
        const itemContent = lines[i].trim().replace(/^(\d+[\.\)]|\(\d+\))\s+/, "");
        listItems.push(itemContent);
        i++;
      }
      let olHtml = "<ol>";
      for (const item of listItems) {
        olHtml += `<li>${formatInline(item)}</li>`;
      }
      olHtml += "</ol>";
      htmlParts.push(olHtml);
      continue;
    }

    // 8.1 参考文献条目列表 ([1] item, [2] item) — 逐条独立显示，悬挂缩进
    if (/^\[\d+\]\s+/.test(trimmed)) {
      const refItems: string[] = [];
      while (i < lines.length && /^\[\d+\]\s+/.test(lines[i].trim())) {
        refItems.push(lines[i].trim());
        i++;
      }
      for (const item of refItems) {
        htmlParts.push(`<p class="ref-entry-line">${formatInline(item)}</p>`);
      }
      continue;
    }

    // 9. 段落 (普通连续文本行)
    const paragraphLines: { text: string; hasHardBreak: boolean }[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trim().match(/^#{1,6}\s+/) &&
      !lines[i].trim().startsWith(">") &&
      !lines[i].trim().startsWith("```") &&
      !/^(\*{3,}|-{3,}|_{3,})$/.test(lines[i].trim()) &&
      !/^[\*\-\+]\s+/.test(lines[i].trim()) &&
      !/^(\d+[\.\)]|\(\d+\))\s+/.test(lines[i].trim()) &&
      !/^\[\d+\]\s+/.test(lines[i].trim()) &&
      !(isTableLine(lines[i].trim()) && i + 1 < lines.length && isTableSeparator(lines[i + 1].trim()))
    ) {
      const rawLine = lines[i];
      const hasHardBreak = / {2,}$|\\$|<br\s*\/?>$/i.test(rawLine);
      paragraphLines.push({ text: rawLine.trim(), hasHardBreak });
      i++;
    }

    if (paragraphLines.length > 0) {
      let pContent = "";
      for (let j = 0; j < paragraphLines.length; j++) {
        const curr = paragraphLines[j];
        if (j === 0) {
          pContent = formatInline(curr.text);
        } else {
          const prev = paragraphLines[j - 1];
          // 仅在上一行显式以双空格、反斜杠或 <br> 结尾时插入 <br />
          if (prev.hasHardBreak) {
            pContent += "<br />" + formatInline(curr.text);
          } else {
            const prevChar = prev.text.slice(-1);
            const nextChar = curr.text.charAt(0);
            if (/[a-zA-Z0-9]/.test(prevChar) && /[a-zA-Z0-9]/.test(nextChar)) {
              pContent += " " + formatInline(curr.text);
            } else {
              pContent += formatInline(curr.text);
            }
          }
        }
      }
      htmlParts.push(`<p>${pContent}</p>`);
    }
  }

  return htmlParts.join("\n");
}

/**
 * 别名，兼容原有调用方式
 */
export const renderMarkdown = markdownToHtml;

/**
 * 将 HTML 还原转换回标准 Markdown 格式
 * 用于 contenteditable 编辑后同步回 Markdown 数据源
 */
export function htmlToMarkdown(html: string): string {
  if (!html || typeof html !== "string" || !html.trim()) {
    return "";
  }

  let text = html.replace(/\r\n/g, "\n");

  // 0. Mermaid 流程图卡片还原：<div class="mermaid-container" data-mermaid-code="...">...</div> -> ```mermaid\n...\n```
  text = text.replace(
    /<div[^>]*\bclass="[^"]*\bmermaid-container\b[^"]*"[^>]*\bdata-mermaid-code="([^"]*)"[\s\S]*?<\/div>\s*<\/div>\s*<\/div>/gi,
    (_match, encodedCode) => {
      const code = unescapeHtml(encodedCode).trim();
      return `\n\n\`\`\`mermaid\n${code}\n\`\`\`\n\n`;
    }
  );
  text = text.replace(
    /<div[^>]*\bdata-mermaid-code="([^"]*)"[^>]*>[\s\S]*?<\/div>/gi,
    (_match, encodedCode) => {
      const code = unescapeHtml(encodedCode).trim();
      return `\n\n\`\`\`mermaid\n${code}\n\`\`\`\n\n`;
    }
  );

  // 1. 来源引用语义化标签还原：<span class="inline-ref-tag type-material" data-ref-type="material" data-ref-title="...">【源:...】</span> -> 【源:...】
  text = text.replace(/<span[^>]*class="[^"]*(?:inline-ref-tag|ref-badge)[^"]*"[^>]*>(?:🏷️\s*)?(【[^】]+】)<\/span>/gi, "$1");
  text = text.replace(/<span[^>]*class="[^"]*(?:inline-ref-tag|ref-badge)[^"]*"[^>]*>(?:🏷️\s*)?(\[Z[^\]]*\])<\/span>/gi, "$1");
  text = text.replace(/<span[^>]*class="[^"]*(?:inline-ref-tag|ref-badge)[^"]*"[^>]*>(?:🏷️\s*)?([^<]+)<\/span>/gi, "$1");

  // 2. 剥离审阅高亮标记 <mark class="review-issue-highlight ...">...</mark>
  text = text.replace(/<mark[^>]*class="[^"]*review-issue-highlight[^"]*"[^>]*>([\s\S]*?)<\/mark>/gi, "$1");

  // 3. 表格转换 <table>...</table> -> Markdown 表格
  text = text.replace(/<table[^>]*>([\s\S]*?)<\/table>/gi, (_match, tableContent: string) => {
    // 提取表头
    const thMatches = [...tableContent.matchAll(/<th[^>]*>([\s\S]*?)<\/th>/gi)];
    const headers = thMatches.map((m) => cleanInlineHtml(m[1]).trim());

    // 提取数据行
    const trMatches = [...tableContent.matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/gi)];
    const rows: string[][] = [];

    for (const trMatch of trMatches) {
      const tdMatches = [...trMatch[1].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/gi)];
      if (tdMatches.length > 0) {
        rows.push(tdMatches.map((m) => cleanInlineHtml(m[1]).trim()));
      }
    }

    if (headers.length === 0 && rows.length === 0) return "";

    const colCount = Math.max(headers.length, ...rows.map((r) => r.length));
    const normalizedHeaders = headers.length > 0 ? headers : new Array(colCount).fill("");
    while (normalizedHeaders.length < colCount) normalizedHeaders.push("");

    let mdTable = "| " + normalizedHeaders.join(" | ") + " |\n";
    mdTable += "| " + new Array(colCount).fill("---").join(" | ") + " |\n";

    for (const row of rows) {
      while (row.length < colCount) row.push("");
      mdTable += "| " + row.join(" | ") + " |\n";
    }

    return `\n\n${mdTable}\n\n`;
  });

  // 4. 代码块 <pre><code class="language-xyz">...</code></pre>
  text = text.replace(/<pre[^>]*><code(?: class="language-([^"]*)")?[^>]*>([\s\S]*?)<\/code><\/pre>/gi, (_match, lang, code) => {
    const language = lang || "";
    const cleanCode = unescapeHtml(code.replace(/<br\s*\/?>/gi, "\n"));
    return `\n\n\`\`\`${language}\n${cleanCode.trim()}\n\`\`\`\n\n`;
  });

  // 5. 各级标题 <h1 id="...">...</h1>
  text = text.replace(/<h([1-6])[^>]*>([\s\S]*?)<\/h\1>/gi, (_match, level, content) => {
    const hashes = "#".repeat(Number(level));
    return `\n\n${hashes} ${cleanInlineHtml(content).trim()}\n\n`;
  });

  // 6. 引用块 <blockquote>...</blockquote>
  text = text.replace(/<blockquote[^>]*>([\s\S]*?)<\/blockquote>/gi, (_match, content) => {
    const lines = cleanInlineHtml(content)
      .replace(/<br\s*\/?>/gi, "\n")
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    return `\n\n` + lines.map((l) => `> ${l}`).join("\n") + `\n\n`;
  });

  // 7. 无序列表 <ul><li>...</li></ul>
  text = text.replace(/<ul[^>]*>([\s\S]*?)<\/ul>/gi, (_match, content) => {
    const liMatches = [...content.matchAll(/<li[^>]*>([\s\S]*?)<\/li>/gi)];
    const items = liMatches.map((m) => `- ${cleanInlineHtml(m[1]).trim()}`);
    return `\n\n` + items.join("\n") + `\n\n`;
  });

  // 8. 有序列表 <ol><li>...</li></ol>
  text = text.replace(/<ol[^>]*>([\s\S]*?)<\/ol>/gi, (_match, content) => {
    const liMatches = [...content.matchAll(/<li[^>]*>([\s\S]*?)<\/li>/gi)];
    const items = liMatches.map((m, idx) => `${idx + 1}. ${cleanInlineHtml(m[1]).trim()}`);
    return `\n\n` + items.join("\n") + `\n\n`;
  });

  // 9. 段落与通用容器标签
  text = text.replace(/<p[^>]*>([\s\S]*?)<\/p>/gi, (_match, content) => {
    return `\n\n${cleanInlineHtml(content).trim()}\n\n`;
  });
  text = text.replace(/<div[^>]*>([\s\S]*?)<\/div>/gi, (_match, content) => {
    return `\n\n${cleanInlineHtml(content).trim()}\n\n`;
  });

  // 10. 分割线
  text = text.replace(/<hr\s*\/?>/gi, "\n\n---\n\n");

  // 11. 处理剩余的内联元素并转义还原
  text = cleanInlineHtml(text);

  // 12. 整理空行与首尾空白
  text = text
    .split("\n")
    .map((line) => line.trimEnd())
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  return text;
}

/**
 * 转换内联 HTML 标签为 Markdown 内联语法并还原实体
 */
function cleanInlineHtml(html: string): string {
  let str = html;

  // 来源引用语义化标签还原
  str = str.replace(/<span[^>]*class="[^"]*(?:inline-ref-tag|ref-badge)[^"]*"[^>]*>(?:🏷️\s*)?(【[^】]+】)<\/span>/gi, "$1");
  str = str.replace(/<span[^>]*class="[^"]*(?:inline-ref-tag|ref-badge)[^"]*"[^>]*>(?:🏷️\s*)?(\[Z[^\]]*\])<\/span>/gi, "$1");
  str = str.replace(/<span[^>]*class="[^"]*(?:inline-ref-tag|ref-badge)[^"]*"[^>]*>(?:🏷️\s*)?([^<]+)<\/span>/gi, "$1");

  // 剥离审阅高亮
  str = str.replace(/<mark[^>]*class="[^"]*review-issue-highlight[^"]*"[^>]*>([\s\S]*?)<\/mark>/gi, "$1");

  // 换行标签替换为换行符
  str = str.replace(/<br\s*\/?>/gi, "\n");

  // 行内代码 <code>...</code>
  str = str.replace(/<code[^>]*>([\s\S]*?)<\/code>/gi, (_match, code) => {
    return `\`${unescapeHtml(code)}\``;
  });

  // 粗体 <strong> / <b>
  str = str.replace(/<(?:strong|b)[^>]*>([\s\S]*?)<\/(?:strong|b)>/gi, "**$1**");

  // 斜体 <em> / <i>
  str = str.replace(/<(?:em|i)[^>]*>([\s\S]*?)<\/(?:em|i)>/gi, "*$1*");

  // 删除线 <del> / <s>
  str = str.replace(/<(?:del|s)[^>]*>([\s\S]*?)<\/(?:del|s)>/gi, "~~$1~~");

  // 移除其它残留 HTML 标签
  str = str.replace(/<[^>]+>/g, "");

  // 还原 HTML 转义实体
  str = unescapeHtml(str);

  return str;
}

function escapeRegExp(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * 提取审阅问题的多级定位特征候选词列表
 */
export function extractIssueCandidateKeys(issue: ReviewIssue): string[] {
  const candidates: string[] = [];

  // 1. 优先提取 issue.quote（去除首尾空白）
  const quote = (issue.quote || "").trim();
  if (quote && quote.length >= 2) {
    return [quote];
  }

  // 2. 若无 quote 或长度 < 2，提取 issue.message 或 issue.location 中的引号包裹内容
  const quoteRegex = /[“"「『]([^”"』」]+)[”"』」]/g;
  if (issue.message) {
    let match: RegExpExecArray | null;
    while ((match = quoteRegex.exec(issue.message)) !== null) {
      const q = match[1].trim();
      if (q.length >= 2 && !candidates.includes(q)) {
        candidates.push(q);
      }
    }
  }
  if (issue.location) {
    quoteRegex.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = quoteRegex.exec(issue.location)) !== null) {
      const q = match[1].trim();
      if (q.length >= 2 && !candidates.includes(q)) {
        candidates.push(q);
      }
    }
  }
  if (candidates.length > 0) {
    return candidates;
  }

  // 3. 若仍无，提取 issue.message 中的核心数值/工程指标片段
  if (issue.message) {
    const metricRegex =
      /(?:\d+(?:\.\d+)?\s*(?:万元|亿元|万m³|万立方米|km²|km|m²|m|人|亩|%|个|台|套|座|年|月|日|天|元|吨|kw|MW|GW|h|km\/h|m\/s))/gi;
    let mMatch: RegExpExecArray | null;
    while ((mMatch = metricRegex.exec(issue.message)) !== null) {
      const val = mMatch[0].trim();
      if (val.length >= 2 && !candidates.includes(val)) {
        candidates.push(val);
      }
    }
  }
  if (candidates.length > 0) {
    return candidates;
  }

  // 4. 若仍无，提取 issue.location 中的关键小节名或定位关键词
  if (issue.location) {
    const cleanLoc = issue.location
      .replace(/^(?:第\s*[一二三四五六七八九十百零\d]+\s*章|\d+(?:\.\d+)*|[\s、：:])+/g, "")
      .trim();
    if (cleanLoc.length >= 2 && !candidates.includes(cleanLoc)) {
      candidates.push(cleanLoc);
    } else if (
      issue.location.trim().length >= 2 &&
      !candidates.includes(issue.location.trim())
    ) {
      candidates.push(issue.location.trim());
    }
  }

  return candidates;
}

/**
 * 构建针对标点与空白泛化的正则表达式
 */
export function buildGeneralizedRegex(cand: string): RegExp {
  let pattern = "";
  for (let i = 0; i < cand.length; i++) {
    const ch = cand[i];
    if (ch === "，" || ch === ",") {
      pattern += "\\s*[，,]\\s*";
    } else if (ch === "：" || ch === ":") {
      pattern += "\\s*[：:]\\s*";
    } else if (ch === "（" || ch === "(") {
      pattern += "\\s*[（\\(]\\s*";
    } else if (ch === "）" || ch === ")") {
      pattern += "\\s*[）\\)]\\s*";
    } else if (ch === "。" || ch === ".") {
      pattern += "\\s*[。\\.]\\s*";
    } else if (ch === "；" || ch === ";") {
      pattern += "\\s*[；;]\\s*";
    } else if (ch === "“" || ch === "”" || ch === '"') {
      pattern += '\\s*(?:[“”"]|&quot;)\\s*';
    } else if (ch === "‘" || ch === "’" || ch === "'") {
      pattern += "\\s*(?:[‘’']|&#39;)\\s*";
    } else if (ch === "「" || ch === "」") {
      pattern += "\\s*[「」]\\s*";
    } else if (ch === "『" || ch === "』") {
      pattern += "\\s*[『』]\\s*";
    } else if (/\s/.test(ch)) {
      pattern += "(?:\\s|&nbsp;)+";
    } else {
      pattern += escapeRegExp(escapeHtml(ch));
    }
  }
  return new RegExp(pattern, "i");
}

/**
 * 审阅问题多级容错高亮匹配与标记注入
 */
export function highlightIssuesInHtml(
  html: string,
  issues: ReviewIssue[],
  seq?: number,
): string {
  if (!html || !issues || !issues.length) return html;

  let currentHtml = html;

  for (const issue of issues) {
    const candidates = extractIssueCandidateKeys(issue);
    if (!candidates.length) continue;

    const severity = issue.severity || "warning";
    const cat = escapeHtml(issue.category || "审查问题");
    const msg = escapeHtml(issue.message || "");
    const issueId = escapeHtml(issue.id || "");
    const chapterSeq = issue.chapterSeq || seq || 1;

    let matched = false;

    for (const cand of candidates) {
      if (!cand || cand.length < 2) continue;

      const parts = currentHtml.split(/(<[^>]+>)/g);
      let inExistingMark = false;

      for (let i = 0; i < parts.length; i++) {
        if (i % 2 === 1) {
          const tag = parts[i];
          if (/^<mark\b[^>]*class=["'][^"']*(?:review-issue-highlight|issue-highlight-mark)/i.test(tag)) {
            inExistingMark = true;
          } else if (/^<\/mark>/i.test(tag)) {
            inExistingMark = false;
          }
          continue;
        }

        if (inExistingMark || !parts[i]) continue;
        const textChunk = parts[i];

        // 级别 1: 直接精准子串匹配
        const escapedCand = escapeHtml(cand);
        if (textChunk.includes(escapedCand)) {
          const markTag = `<mark class="review-issue-highlight severity-${severity}" data-issue-id="${issueId}" data-chapter-seq="${chapterSeq}" title="${cat}: ${msg}">${escapedCand}</mark>`;
          parts[i] = textChunk.replace(escapedCand, markTag);
          matched = true;
          break;
        }
        if (textChunk.includes(cand)) {
          const markTag = `<mark class="review-issue-highlight severity-${severity}" data-issue-id="${issueId}" data-chapter-seq="${chapterSeq}" title="${cat}: ${msg}">${escapeHtml(cand)}</mark>`;
          parts[i] = textChunk.replace(cand, markTag);
          matched = true;
          break;
        }

        // 级别 2: 全半角标点与空白泛化匹配
        const genRegex = buildGeneralizedRegex(cand);
        const match = textChunk.match(genRegex);
        if (match && match[0]) {
          const matchedText = match[0];
          const markTag = `<mark class="review-issue-highlight severity-${severity}" data-issue-id="${issueId}" data-chapter-seq="${chapterSeq}" title="${cat}: ${msg}">${matchedText}</mark>`;
          parts[i] = textChunk.replace(genRegex, markTag);
          matched = true;
          break;
        }

        // 级别 3: 长句（>8字符）前缀特征滑动窗口匹配
        if (cand.length > 8) {
          let prefixMatched = false;
          const maxLen = Math.min(12, cand.length);
          for (let pLen = maxLen; pLen >= 8; pLen--) {
            const prefix = cand.slice(0, pLen);
            const prefixEscaped = escapeHtml(prefix);

            if (textChunk.includes(prefixEscaped)) {
              const markTag = `<mark class="review-issue-highlight severity-${severity}" data-issue-id="${issueId}" data-chapter-seq="${chapterSeq}" title="${cat}: ${msg}">${prefixEscaped}</mark>`;
              parts[i] = textChunk.replace(prefixEscaped, markTag);
              matched = true;
              prefixMatched = true;
              break;
            }

            const prefixGenRegex = buildGeneralizedRegex(prefix);
            const pMatch = textChunk.match(prefixGenRegex);
            if (pMatch && pMatch[0]) {
              const matchedText = pMatch[0];
              const markTag = `<mark class="review-issue-highlight severity-${severity}" data-issue-id="${issueId}" data-chapter-seq="${chapterSeq}" title="${cat}: ${msg}">${matchedText}</mark>`;
              parts[i] = textChunk.replace(prefixGenRegex, markTag);
              matched = true;
              prefixMatched = true;
              break;
            }
          }
          if (prefixMatched) break;
        }
      }

      if (matched) {
        currentHtml = parts.join("");
        break;
      }
    }
  }

  return currentHtml;
}

export interface GlobalRefEntry {
  number: number;
  label: string;
  title: string;
  name: string;
  type: "material" | "standard" | "web" | "other";
  typeLabel: string;
  count: number;
  raw: string;
  url?: string;
  firstChapterSeq?: number;
}

/**
 * 遍历全书所有章节正文，按照首次出现先后顺序为所有引用标签赋予唯一的全局数字编号 [1], [2], [3]...
 * 跨章重复出现的同一参考资料共享相同编号。
 */
export function assignGlobalRefNumbers(
  chapters: Record<number, string>,
  outlineSeqs?: number[]
): {
  labelToNumber: Record<string, number>;
  refEntries: GlobalRefEntry[];
} {
  const labelToNumber: Record<string, number> = {};
  const refEntries: GlobalRefEntry[] = [];
  const seenLabels = new Set<string>();

  const seqs = outlineSeqs || Object.keys(chapters).map(Number).sort((a, b) => a - b);

  let currentNumber = 1;

  for (const seq of seqs) {
    const text = chapters[seq];
    if (!text || typeof text !== "string") continue;

    // 匹配 【源:...】 / 【材料:...】 / 【标:...】 / 【网:...】 / 【规:...】
    const bracketRegex = /【(源|材料|网|网络|标|标准|规|规程|法|法规)[:：]\s*([^】]+)】/g;
    let m: RegExpExecArray | null;
    while ((m = bracketRegex.exec(text)) !== null) {
      const rawTag = m[0];
      const prefix = m[1];
      const content = m[2].trim();
      if (!content) continue;

      let type: "material" | "standard" | "web" | "other" = "material";
      let typeLabel = "项目底稿";
      let url: string | undefined = undefined;

      if (prefix.startsWith("网")) {
        type = "web";
        typeLabel = "百度联网";
        const escapedTitle = content.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const urlPattern = new RegExp(`【(?:网|网络)[:：]\\s*${escapedTitle}】\\s*\\n?\\s*(https?:\\/\\/[^\\s\\n>"\\]]+)`);
        const urlMatch = text.match(urlPattern);
        if (urlMatch) {
          url = urlMatch[1].trim();
        } else {
          const linkPattern = new RegExp(`\\[${escapedTitle}\\]\\((https?:\\/\\/[^\\s\\n>"\\]]+)\\)`);
          const linkMatch = text.match(linkPattern);
          if (linkMatch) {
            url = linkMatch[1].trim();
          } else {
            const generalMatch = text.match(new RegExp(`${escapedTitle}[\\s\\S]{0,80}?(https?:\\/\\/[^\\s\\n>"\\]]+)`));
            if (generalMatch) {
              url = generalMatch[1].trim();
            }
          }
        }
      } else if (prefix.startsWith("标") || prefix.startsWith("规") || prefix.startsWith("法")) {
        type = "standard";
        typeLabel = "标准规程";
      } else {
        if (/规程|规范|标准|GB|SL|NB|DL|定额|导则|通则|法/i.test(content)) {
          type = "standard";
          typeLabel = "标准规程";
        } else {
          type = "material";
          typeLabel = "项目底稿";
        }
      }

      if (seenLabels.has(rawTag)) {
        const existing = refEntries.find((e) => e.raw === rawTag);
        if (existing) {
          existing.count += 1;
          if (!existing.url && url) existing.url = url;
        }
      } else {
        seenLabels.add(rawTag);
        labelToNumber[rawTag] = currentNumber;
        refEntries.push({
          number: currentNumber,
          label: rawTag,
          title: content,
          name: content,
          type,
          typeLabel,
          count: 1,
          raw: rawTag,
          url,
          firstChapterSeq: seq,
        });
        currentNumber++;
      }
    }

    // 从该章章末 ## 📎 本章参考资料 中提取并补齐可能缺失的 web URL
    const footerLines = text.split("\n");
    let inWeb = false;
    for (const line of footerLines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("### 网页链接")) {
        inWeb = true;
      } else if (trimmed.startsWith("### ") || trimmed.startsWith("## ")) {
        inWeb = false;
      } else if (inWeb && trimmed.startsWith("- ")) {
        const item = trimmed.slice(2).trim();
        const linkM = item.match(/^\[(.*?)\]\((https?:\/\/[^\s\n>"]+)\)$/);
        if (linkM) {
          const nameClean = linkM[1].trim();
          const srcClean = linkM[2].trim();
          for (const entry of refEntries) {
            if (entry.type === "web" && (entry.title === nameClean || entry.title.includes(nameClean) || nameClean.includes(entry.title))) {
              if (!entry.url) entry.url = srcClean;
            }
          }
        } else if (item.includes(" — ")) {
          const [n, s] = item.split(" — ", 2);
          const nameClean = n.trim();
          const srcClean = s.trim();
          if (srcClean.startsWith("http")) {
            for (const entry of refEntries) {
              if (entry.type === "web" && (entry.title === nameClean || entry.title.includes(nameClean) || nameClean.includes(entry.title))) {
                if (!entry.url) entry.url = srcClean;
              }
            }
          }
        }
      }
    }

    // 匹配 [Z] 或 [Z-1]
    const citationRegex = /\[Z(?::|：|-)?([a-zA-Z0-9_\-\u4e00-\u9fa5]*)\]/g;
    while ((m = citationRegex.exec(text)) !== null) {
      const rawTag = m[0];
      const suffix = m[1] ? m[1].trim() : "";
      const title = suffix ? `标准规范依据 [Z-${suffix}]` : "通用领域行业规程库 [Z]";
      if (seenLabels.has(rawTag)) {
        const existing = refEntries.find((e) => e.raw === rawTag);
        if (existing) existing.count += 1;
      } else {
        seenLabels.add(rawTag);
        labelToNumber[rawTag] = currentNumber;
        refEntries.push({
          number: currentNumber,
          label: rawTag,
          title,
          name: title,
          type: "standard",
          typeLabel: "标准规程",
          count: 1,
          raw: rawTag,
          firstChapterSeq: seq,
        });
        currentNumber++;
      }
    }
  }

  return { labelToNumber, refEntries };
}

/**
 * 将正文中的语义标签替换为标准学术/规程数字上标编号 [1], [2]...
 */
export function convertRefsToNumberedCitations(
  md: string,
  labelToNumber: Record<string, number>
): string {
  if (!md || typeof md !== "string") return "";
  let result = md;
  for (const [label, num] of Object.entries(labelToNumber)) {
    result = result.replaceAll(label, `[${num}]`);
  }
  return result;
}

/**
 * 根据全书全局引用清单，生成符合 GB/T 7714-2015 格式的《全书参考文献总清单》Markdown 段落
 */
export function generateBibliographySection(refEntries: GlobalRefEntry[]): string {
  if (!refEntries || refEntries.length === 0) {
    return "# 参考文献\n\n（全书未引用外部参考资料）\n";
  }

  const lines: string[] = ["# 参考文献", "", "> 依据 GB/T 7714—2015 信息与文献 参考文献著录规则 自动汇总生成", ""];

  for (const item of refEntries) {
    if (item.type === "standard") {
      lines.push(`[${item.number}] [标准规范] ${item.title}.`);
    } else if (item.type === "web") {
      const urlPart = item.url ? ` 访问网址: ${item.url}` : "";
      lines.push(`[${item.number}] [联网检索] ${item.title}.${urlPart}`);
    } else {
      lines.push(`[${item.number}] [项目资料] ${item.title}.`);
    }
    lines.push("");
  }

  return lines.join("\n").trimEnd() + "\n";
}
