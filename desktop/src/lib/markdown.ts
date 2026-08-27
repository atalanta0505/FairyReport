/**
 * 轻量高性能 Markdown 排版解析与渲染器
 *
 * 0 外部依赖，原生 TypeScript 实现
 * 支持各级标题（带锚点 ID）、粗体/斜体、代码、列表、表格、引用块、来源标签高亮徽章与反向 Markdown 序列化
 */

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

  // 3. 来源引用徽章：【源:...】、【网:...】、【标:...】、【规:...】与 [Z]
  escaped = escaped.replace(
    /【(源|材料|网|网络|标|标准|规|规程)([:：][^】]+)】/g,
    '<span class="ref-badge">🏷️ 【$1$2】</span>'
  );
  escaped = escaped.replace(
    /\[Z(?::|：|-)?([a-zA-Z0-9_\-\u4e00-\u9fa5]*)\]/g,
    '<span class="ref-badge">🏷️ [Z$1]</span>'
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

export function normalizeMarkdown(md: string, knownHeadings?: string[]): string {
  if (!md || typeof md !== "string") return "";
  let text = md.replace(/\r\n/g, "\n");

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

  return text;
}

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
export function extractReferences(text: string): ReferenceItem[] {
  if (!text || typeof text !== "string") return [];

  const map = new Map<string, { type: "material" | "standard" | "web" | "other"; typeLabel: string; title: string; raw: string; count: number }>();

  // 1. 匹配 【源:...】 / 【材料:...】 / 【标:...】 / 【网:...】 / 【规:...】
  const bracketRegex = /【(源|材料|网|网络|标|标准|规|规程|法|法规)[:：]\s*([^】]+)】/g;
  let m: RegExpExecArray | null;
  while ((m = bracketRegex.exec(text)) !== null) {
    const rawTag = m[0];
    const prefix = m[1];
    const content = m[2].trim();
    if (!content) continue;

    let type: "material" | "standard" | "web" | "other" = "material";
    let typeLabel = "底稿文件";

    if (prefix.startsWith("网")) {
      type = "web";
      typeLabel = "网络检索";
    } else if (prefix.startsWith("标") || prefix.startsWith("规") || prefix.startsWith("法")) {
      type = "standard";
      typeLabel = "规程标准";
    } else {
      if (/规程|规范|标准|GB|SL|NB|DL|定额|导则|通则|法/i.test(content)) {
        type = "standard";
        typeLabel = "规程标准";
      } else {
        type = "material";
        typeLabel = "底稿文件";
      }
    }

    const key = `${type}::${content}`;
    if (map.has(key)) {
      map.get(key)!.count += 1;
    } else {
      map.set(key, {
        type,
        typeLabel,
        title: content,
        raw: rawTag,
        count: 1,
      });
    }
  }

  // 2. 匹配标准引用标签 [Z] 或 [Z-1] 或 [文献...]
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
        typeLabel: "规程标准",
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
      const codeLines: string[] = [];
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(escapeHtml(lines[i]));
        i++;
      }
      if (i < lines.length && lines[i].trim().startsWith("```")) {
        i++; // 跳过结束 ```
      }
      const langClass = lang ? ` class="language-${escapeHtml(lang)}"` : "";
      htmlParts.push(`<pre><code${langClass}>${codeLines.join("\n")}</code></pre>`);
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

    // 9. 段落 (普通连续文本行)
    const paragraphLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trim().match(/^#{1,6}\s+/) &&
      !lines[i].trim().startsWith(">") &&
      !lines[i].trim().startsWith("```") &&
      !/^(\*{3,}|-{3,}|_{3,})$/.test(lines[i].trim()) &&
      !/^[\*\-\+]\s+/.test(lines[i].trim()) &&
      !/^(\d+[\.\)]|\(\d+\))\s+/.test(lines[i].trim()) &&
      !(isTableLine(lines[i].trim()) && i + 1 < lines.length && isTableSeparator(lines[i + 1].trim()))
    ) {
      paragraphLines.push(lines[i].trim());
      i++;
    }

    if (paragraphLines.length > 0) {
      const pContent = paragraphLines.map((l) => formatInline(l)).join("<br />");
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

  // 1. 来源引用徽章还原：<span class="ref-badge">🏷️ 【源:...】</span> -> 【源:...】
  text = text.replace(/<span[^>]*class="[^"]*ref-badge[^"]*"[^>]*>🏷️\s*(【[^】]+】)<\/span>/gi, "$1");
  text = text.replace(/<span[^>]*class="[^"]*ref-badge[^"]*"[^>]*>🏷️\s*(\[Z[^\]]*\])<\/span>/gi, "$1");
  text = text.replace(/<span[^>]*class="[^"]*ref-badge[^"]*"[^>]*>(?:🏷️\s*)?([^<]+)<\/span>/gi, "$1");

  // 2. 表格转换 <table>...</table> -> Markdown 表格
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

  // 3. 代码块 <pre><code class="language-xyz">...</code></pre>
  text = text.replace(/<pre[^>]*><code(?: class="language-([^"]*)")?[^>]*>([\s\S]*?)<\/code><\/pre>/gi, (_match, lang, code) => {
    const language = lang || "";
    const cleanCode = unescapeHtml(code.replace(/<br\s*\/?>/gi, "\n"));
    return `\n\n\`\`\`${language}\n${cleanCode.trim()}\n\`\`\`\n\n`;
  });

  // 4. 各级标题 <h1 id="...">...</h1>
  text = text.replace(/<h([1-6])[^>]*>([\s\S]*?)<\/h\1>/gi, (_match, level, content) => {
    const hashes = "#".repeat(Number(level));
    return `\n\n${hashes} ${cleanInlineHtml(content).trim()}\n\n`;
  });

  // 5. 引用块 <blockquote>...</blockquote>
  text = text.replace(/<blockquote[^>]*>([\s\S]*?)<\/blockquote>/gi, (_match, content) => {
    const lines = cleanInlineHtml(content)
      .replace(/<br\s*\/?>/gi, "\n")
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    return `\n\n` + lines.map((l) => `> ${l}`).join("\n") + `\n\n`;
  });

  // 6. 无序列表 <ul><li>...</li></ul>
  text = text.replace(/<ul[^>]*>([\s\S]*?)<\/ul>/gi, (_match, content) => {
    const liMatches = [...content.matchAll(/<li[^>]*>([\s\S]*?)<\/li>/gi)];
    const items = liMatches.map((m) => `- ${cleanInlineHtml(m[1]).trim()}`);
    return `\n\n` + items.join("\n") + `\n\n`;
  });

  // 7. 有序列表 <ol><li>...</li></ol>
  text = text.replace(/<ol[^>]*>([\s\S]*?)<\/ol>/gi, (_match, content) => {
    const liMatches = [...content.matchAll(/<li[^>]*>([\s\S]*?)<\/li>/gi)];
    const items = liMatches.map((m, idx) => `${idx + 1}. ${cleanInlineHtml(m[1]).trim()}`);
    return `\n\n` + items.join("\n") + `\n\n`;
  });

  // 8. 段落与通用容器标签
  text = text.replace(/<p[^>]*>([\s\S]*?)<\/p>/gi, (_match, content) => {
    return `\n\n${cleanInlineHtml(content).trim()}\n\n`;
  });
  text = text.replace(/<div[^>]*>([\s\S]*?)<\/div>/gi, (_match, content) => {
    return `\n\n${cleanInlineHtml(content).trim()}\n\n`;
  });

  // 9. 分割线
  text = text.replace(/<hr\s*\/?>/gi, "\n\n---\n\n");

  // 10. 处理剩余的内联元素并转义还原
  text = cleanInlineHtml(text);

  // 11. 整理空行与首尾空白
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
