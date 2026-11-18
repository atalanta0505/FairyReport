import type * as engineApi from "../lib/engineApi";
import type { ChapterInfo } from "../lib/engineApi";

export function normalizeReportTypeName(type: string): string {
  return type === "智库决策专报与建言报告" ? "智库专报" : type;
}

export function parseChaptersFromOutline(outlineMd: string): ChapterInfo[] {
  if (!outlineMd) return [];
  const lines = outlineMd.split("\n");
  const chapters: ChapterInfo[] = [];
  let seq = 1;
  for (const line of lines) {
    const trimmed = line.trim();
    if (
      trimmed.startsWith("# 标题（") ||
      trimmed === "# 标题" ||
      trimmed.includes("（体现核心研判")
    ) {
      continue;
    }
    const match =
      trimmed.match(/^#{1,2}\s+(第[一二三四五六七八九十百零\d]+章[\s：:].+)/) ||
      trimmed.match(/^#{1,2}\s+(第[一二三四五六七八九十百零\d]+章.+)/) ||
      trimmed.match(/^(第[一二三四五六七八九十百零\d]+章[\s：:].+)/) ||
      trimmed.match(/^#\s+([一二三四五六七八九十]+[、\.\s].+)/) ||
      trimmed.match(/^#\s+(\d+[、\.\s].+)/) ||
      trimmed.match(/^#\s+(【?(?:导语|内容摘要|前言|概述|附件|附表|附录)】?.*)/) ||
      trimmed.match(/^#\s+([^#\n]+)/);
    if (match) {
      const title = match[1].trim();
      if (title && !title.startsWith("标题（") && title !== "标题") {
        chapters.push({ seq: seq++, title });
      }
    }
  }
  return chapters;
}

export function deriveDefaultWritingOrder(
  chapters: ChapterInfo[],
  _reportTypeStr = "",
): number[] {
  if (!chapters || chapters.length === 0) return [];
  const seqs = chapters.map((c) => c.seq);
  if (seqs.length <= 1) return seqs;

  const maxSeq = Math.max(...seqs);
  const body = seqs.filter((s) => s !== 1 && s !== maxSeq);
  const res = [...body, 1];
  if (maxSeq > 1) {
    res.push(maxSeq);
  }
  return res;
}

export function defaultWritingOrderReason(order: number[]): string {
  return order[0] !== 1
    ? "先完成背景、需求、选址、工程方案及投资等主体论证章节，再汇总提炼第一章概述与综合结论，确保全书数据逻辑自洽与高效推演。"
    : "按照报告标准章节结构依次推进编写，确保各章节逻辑严密衔接。";
}

function readRawStorage(key: string, fallbackSession = false): string | null {
  try {
    if (typeof localStorage !== "undefined") {
      const val = localStorage.getItem(key);
      if (val !== null) return val;
    }
    if (fallbackSession && typeof sessionStorage !== "undefined") {
      return sessionStorage.getItem(key);
    }
  } catch {
    /* ignore storage access errors */
  }
  return null;
}

function writeRawStorage(key: string, value: string | null, syncSession = false): void {
  try {
    if (typeof localStorage !== "undefined") {
      if (value !== null) localStorage.setItem(key, value);
      else localStorage.removeItem(key);
    }
    if (syncSession && typeof sessionStorage !== "undefined") {
      if (value !== null) sessionStorage.setItem(key, value);
      else sessionStorage.removeItem(key);
    }
  } catch {
    /* ignore storage access errors */
  }
}

function readJsonLocal<T>(key: string): T | null {
  const raw = readRawStorage(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function writeJsonLocal(key: string, value: unknown): void {
  try {
    writeRawStorage(key, JSON.stringify(value));
  } catch {
    /* ignore */
  }
}

export function getStoredStep(): number {
  const raw = readRawStorage("frl_current_step", true);
  if (raw) {
    const val = Number(raw);
    if (Number.isInteger(val) && val >= 1 && val <= 5) return val;
  }
  return 1;
}

export function setStoredStep(step: number): void {
  writeRawStorage("frl_current_step", String(step), true);
}

export function getStoredProjectName(): string | null {
  return readRawStorage("frl_current_project", true) || null;
}

export function setStoredProjectName(name: string | null): void {
  writeRawStorage("frl_current_project", name && name.length > 0 ? name : null, true);
}

export const getOutlineStorageKey = (projectName: string) => `frl_outline_${projectName}`;
export const getWritingOrderStorageKey = (projectName: string) => `frl_writing_order_${projectName}`;
export const getChaptersStorageKey = (projectName: string) => `frl_chapters_${projectName}`;
export const getReviewsStorageKey = (projectName: string) => `frl_reviews_${projectName}`;
export const getFullReviewStorageKey = (projectName: string) => `frl_full_review_${projectName}`;

export function clearProjectLocalStorage(projectName: string): void {
  for (const key of [
    getOutlineStorageKey(projectName),
    getWritingOrderStorageKey(projectName),
    getChaptersStorageKey(projectName),
    getReviewsStorageKey(projectName),
    getFullReviewStorageKey(projectName),
  ]) {
    writeRawStorage(key, null);
  }
}

export function loadWritingOrderFromLocal(
  projectName: string,
): { order: number[]; reason: string } | null {
  return readJsonLocal<{ order: number[]; reason: string }>(getWritingOrderStorageKey(projectName));
}

export function saveWritingOrderToLocal(
  projectName: string,
  order: number[],
  reason = "",
): void {
  writeJsonLocal(getWritingOrderStorageKey(projectName), { order, reason });
}

export interface LocalOutlineCache {
  report_type?: string;
  outline_md?: string;
  chapters?: ChapterInfo[];
  writing_order?: number[];
  writing_order_reason?: string;
  updated_at?: string;
}

export function loadOutlineFromLocal(projectName: string): LocalOutlineCache | null {
  return readJsonLocal<LocalOutlineCache>(getOutlineStorageKey(projectName));
}

export function saveOutlineToLocal(
  projectName: string,
  data: {
    report_type: string;
    outline_md: string;
    chapters: ChapterInfo[];
    writing_order?: number[];
    writing_order_reason?: string;
    updated_at?: string;
  },
): void {
  writeJsonLocal(getOutlineStorageKey(projectName), data);
}

export function loadChaptersFromLocal(projectName: string): Record<number, string> | null {
  const parsed = readJsonLocal<Record<string, unknown>>(getChaptersStorageKey(projectName));
  if (!parsed) return null;
  const result: Record<number, string> = {};
  for (const [k, v] of Object.entries(parsed)) {
    const num = Number(k);
    if (!isNaN(num) && typeof v === "string") {
      result[num] = v;
    }
  }
  return result;
}

export function saveChaptersToLocal(
  projectName: string,
  chapters: Record<number, string>,
): void {
  writeJsonLocal(getChaptersStorageKey(projectName), chapters);
}

export function loadReviewsFromLocal(
  projectName: string,
): Record<number, engineApi.ExpertReviewResult> | null {
  const parsed = readJsonLocal<Record<string, unknown>>(getReviewsStorageKey(projectName));
  if (!parsed) return null;
  const result: Record<number, engineApi.ExpertReviewResult> = {};
  for (const [k, v] of Object.entries(parsed)) {
    const num = Number(k);
    if (!isNaN(num) && v && typeof v === "object") {
      result[num] = v as engineApi.ExpertReviewResult;
    }
  }
  return result;
}

export function saveReviewsToLocal(
  projectName: string,
  reviews: Record<number, engineApi.ExpertReviewResult>,
): void {
  writeJsonLocal(getReviewsStorageKey(projectName), reviews);
}

export function loadFullReviewFromLocal(projectName: string): engineApi.FullReviewData | null {
  return readJsonLocal<engineApi.FullReviewData>(getFullReviewStorageKey(projectName));
}

export function saveFullReviewToLocal(
  projectName: string,
  data: engineApi.FullReviewData,
): void {
  writeJsonLocal(getFullReviewStorageKey(projectName), data);
}
