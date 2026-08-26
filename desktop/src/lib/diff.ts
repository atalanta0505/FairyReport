/**
 * 轻量纯 TypeScript Diff 差异比对算法。
 *
 * 支持：
 * 1. 行级差异计算（LCS 最长公共子序列算法）
 * 2. 词/字级中英文分词微观差异对比
 * 3. 左右双栏块级对齐结构（DiffBlock）
 * 4. 差异统计指标（新增/删除/未变行数）
 */

export type DiffType = "unchanged" | "added" | "removed";

export interface DiffLine {
  type: DiffType;
  text: string;
  oldLineNumber?: number;
  newLineNumber?: number;
}

export interface DiffWord {
  type: DiffType;
  text: string;
}

export interface DiffBlockLine {
  lineNumber?: number;
  text: string;
  type: DiffType;
}

export interface DiffBlock {
  type: "unchanged" | "added" | "removed" | "modified";
  oldLines: DiffBlockLine[];
  newLines: DiffBlockLine[];
}

export interface DiffStats {
  addedLines: number;
  removedLines: number;
  unchangedLines: number;
  totalOriginalLines: number;
  totalModifiedLines: number;
}

/**
 * 字符串按行拆分（规范化处理 \r\n 与 \n）。
 */
function splitLines(text: string): string[] {
  if (!text) return [];
  return text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
}

/**
 * 中英文混合分词：汉字按单字拆分，连续英文/数字/下划线按词拆分，标点与空白独立拆分。
 */
export function tokenizeWords(text: string): string[] {
  if (!text) return [];
  const tokens: string[] = [];
  const regex = /([\u4e00-\u9fa5]|[\u3000-\u303f\uff00-\uffef]|[a-zA-Z0-9_]+|[^\s\w\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]+|\s+)/g;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(text)) !== null) {
    if (match[0]) {
      tokens.push(match[0]);
    }
  }
  return tokens.length > 0 ? tokens : [text];
}

/**
 * 通用 LCS 算法：计算两个字符串数组的最长公共子序列。
 */
function computeLCS<T>(a: T[], b: T[], equals: (x: T, y: T) => boolean = (x, y) => x === y): number[][] {
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));

  for (let i = 0; i < m; i++) {
    for (let j = 0; j < n; j++) {
      if (equals(a[i], b[j])) {
        dp[i + 1][j + 1] = dp[i][j] + 1;
      } else {
        dp[i + 1][j + 1] = Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
  }

  return dp;
}

/**
 * 计算行级差异。
 */
export function computeLineDiff(original: string, modified: string): DiffLine[] {
  const a = splitLines(original);
  const b = splitLines(modified);

  if (a.length === 0 && b.length === 0) {
    return [];
  }
  if (a.length === 0) {
    return b.map((text, idx) => ({
      type: "added",
      text,
      newLineNumber: idx + 1,
    }));
  }
  if (b.length === 0) {
    return a.map((text, idx) => ({
      type: "removed",
      text,
      oldLineNumber: idx + 1,
    }));
  }

  const dp = computeLCS(a, b);

  let i = a.length;
  let j = b.length;

  const backtrack: DiffLine[] = [];

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      backtrack.push({
        type: "unchanged",
        text: a[i - 1],
        oldLineNumber: i,
        newLineNumber: j,
      });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      backtrack.push({
        type: "added",
        text: b[j - 1],
        newLineNumber: j,
      });
      j--;
    } else if (i > 0 && (j === 0 || dp[i][j - 1] < dp[i - 1][j])) {
      backtrack.push({
        type: "removed",
        text: a[i - 1],
        oldLineNumber: i,
      });
      i--;
    }
  }

  backtrack.reverse();
  return backtrack;
}

/**
 * 计算微观字/词级差异。
 */
export function computeWordDiff(original: string, modified: string): DiffWord[] {
  const a = tokenizeWords(original);
  const b = tokenizeWords(modified);

  if (a.length === 0 && b.length === 0) return [];
  if (a.length === 0) return b.map((text) => ({ type: "added", text }));
  if (b.length === 0) return a.map((text) => ({ type: "removed", text }));

  const dp = computeLCS(a, b);
  const backtrack: DiffWord[] = [];

  let i = a.length;
  let j = b.length;

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      backtrack.push({ type: "unchanged", text: a[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      backtrack.push({ type: "added", text: b[j - 1] });
      j--;
    } else if (i > 0 && (j === 0 || dp[i][j - 1] < dp[i - 1][j])) {
      backtrack.push({ type: "removed", text: a[i - 1] });
      i--;
    }
  }

  backtrack.reverse();

  // 合并相同类型的相邻 token
  const merged: DiffWord[] = [];
  for (const item of backtrack) {
    if (merged.length > 0 && merged[merged.length - 1].type === item.type) {
      merged[merged.length - 1].text += item.text;
    } else {
      merged.push({ ...item });
    }
  }

  return merged;
}

/**
 * 计算左右双栏对齐对比块结构（DiffBlock）。
 */
export function computeDiffBlocks(original: string, modified: string): DiffBlock[] {
  const lines = computeLineDiff(original, modified);
  const blocks: DiffBlock[] = [];

  let currentBlock: DiffBlock | null = null;

  for (const line of lines) {
    if (line.type === "unchanged") {
      if (currentBlock && currentBlock.type !== "unchanged") {
        blocks.push(currentBlock);
        currentBlock = null;
      }
      if (!currentBlock) {
        currentBlock = {
          type: "unchanged",
          oldLines: [],
          newLines: [],
        };
      }
      currentBlock.oldLines.push({
        lineNumber: line.oldLineNumber,
        text: line.text,
        type: "unchanged",
      });
      currentBlock.newLines.push({
        lineNumber: line.newLineNumber,
        text: line.text,
        type: "unchanged",
      });
    } else {
      // added or removed
      if (currentBlock && currentBlock.type === "unchanged") {
        blocks.push(currentBlock);
        currentBlock = null;
      }
      if (!currentBlock) {
        currentBlock = {
          type: "modified",
          oldLines: [],
          newLines: [],
        };
      }
      if (line.type === "removed") {
        currentBlock.oldLines.push({
          lineNumber: line.oldLineNumber,
          text: line.text,
          type: "removed",
        });
      } else if (line.type === "added") {
        currentBlock.newLines.push({
          lineNumber: line.newLineNumber,
          text: line.text,
          type: "added",
        });
      }
    }
  }

  if (currentBlock) {
    // 标记纯新增或纯删除
    if (currentBlock.type === "modified") {
      if (currentBlock.oldLines.length === 0 && currentBlock.newLines.length > 0) {
        currentBlock.type = "added";
      } else if (currentBlock.oldLines.length > 0 && currentBlock.newLines.length === 0) {
        currentBlock.type = "removed";
      }
    }
    blocks.push(currentBlock);
  }

  // 二次修正 blocks 内类型
  for (const b of blocks) {
    if (b.type === "modified") {
      if (b.oldLines.length === 0 && b.newLines.length > 0) {
        b.type = "added";
      } else if (b.oldLines.length > 0 && b.newLines.length === 0) {
        b.type = "removed";
      }
    }
  }

  return blocks;
}

/**
 * 统计 Diff 差异指标。
 */
export function computeDiffStats(original: string, modified: string): DiffStats {
  const lines = computeLineDiff(original, modified);
  let added = 0;
  let removed = 0;
  let unchanged = 0;

  for (const l of lines) {
    if (l.type === "added") added++;
    else if (l.type === "removed") removed++;
    else if (l.type === "unchanged") unchanged++;
  }

  return {
    addedLines: added,
    removedLines: removed,
    unchangedLines: unchanged,
    totalOriginalLines: splitLines(original).length,
    totalModifiedLines: splitLines(modified).length,
  };
}
