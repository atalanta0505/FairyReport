<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import {
  computeDiffStats,
  computeLineDiff,
  type DiffLine,
  type DiffStats,
} from "../lib/diff";
import type * as engineApi from "../lib/engineApi";
import {
  countContentChars,
  escapeHtml,
  extractOutlineHeadings,
  extractReferences,
  extractSubHeadings,
  highlightIssuesInHtml,
  htmlToMarkdown,
  markdownToHtml,
  type ReferenceItem,
  type SubHeading,
} from "../lib/markdown";
import { useEngineStore } from "../stores/engine";
import { useProjectStore } from "../stores/project";
import { useSettingsStore } from "../stores/settings";

const engine = useEngineStore();
const settings = useSettingsStore();
const projectStore = useProjectStore();

// ── 视图模式切换 ──
// rich: 最终排版正文 (就地可编辑) | diff: 修订差异对比 (全宽单栏内联) | source: Markdown 源码
const viewMode = ref<"rich" | "diff" | "source">("rich");

// ── 右侧全高抽屉 (Slide-over Drawer, 540px) ──
const showDiagnosticDrawer = ref<boolean>(false);
const showRefDrawer = ref<boolean>(false);
const diagnosticTab = ref<"issues" | "numerical" | "gaps" | "evals" | "suggestions">("issues");
const refFilterType = ref<"all" | "material" | "standard" | "web">("all");

// ── 审查双模式 ──
// fast: ⚡ 常规审查 (推荐) | all: 🔍 全维精审
const reviewMode = ref<"fast" | "all">("fast");

// ── 章节与小节目录展开 / 定位状态 ──
const activeChapterSeq = ref<number>(1);
const activeHeadingId = ref<string | null>(null);
const chapterCollapsedMap = ref<Record<number, boolean>>({});

// ── 全局操作通知 ──
const actionMessage = ref<{ type: "success" | "error" | "info"; text: string } | null>(null);

// ── 审阅动态心跳与计时器 ──
const reviewElapsedSeconds = ref<number>(0);
const showReviewThoughtDetails = ref<boolean>(true);
let reviewTimer: ReturnType<typeof setInterval> | null = null;

// ── 修订动态心跳与计时器 ──
const revisionElapsedSeconds = ref<number>(0);
const revisionStageIndex = ref<number>(0);
let revisionTimer: ReturnType<typeof setInterval> | null = null;

const revisionStages = [
  { id: "context", title: "解析全书脉络", desc: "统筹上下文逻辑与专家诊断修改指令" },
  { id: "restructure", title: "重构方案论述", desc: "依据发改委与行业规程深化工艺与估算" },
  { id: "polish", title: "技术规范润色", desc: "压制套话，规范 10.5pt 工程出版级术语" },
  { id: "diff", title: "构建内联 Diff", desc: "生成精准全宽单栏段落级差异比对" },
];

const saveDebounceTimers: Record<number, ReturnType<typeof setTimeout>> = {};

const outlineHeadings = computed(() => extractOutlineHeadings(projectStore.outlineMd));

function showMsg(text: string, type: "success" | "error" | "info" = "success") {
  actionMessage.value = { type, text };
  setTimeout(() => {
    if (actionMessage.value?.text === text) {
      actionMessage.value = null;
    }
  }, 4000);
}

function getLLMConfig() {
  if (!settings.llmKey) {
    throw new Error("请先在右上角「设置」中配置 LLM API Key");
  }
  return {
    api_key: settings.llmKey,
    base_url: settings.llmBaseUrl || "https://api.deepseek.com/v1",
    model: settings.llmModel || "deepseek-v4-flash",
  };
}

async function ensureStep4State() {
  if (engine.baseUrl && projectStore.templates.length === 0) {
    try {
      await projectStore.loadTemplates(engine.baseUrl);
    } catch {
      // ignore
    }
  }
  if (projectStore.currentProject?.name) {
    if (!projectStore.outlineMd) {
      try {
        await projectStore.loadOutline(engine.baseUrl, projectStore.currentProject.name);
      } catch {
        // ignore
      }
    }
    try {
      await projectStore.loadChapters(engine.baseUrl, projectStore.currentProject.name);
      await projectStore.loadReviews(engine.baseUrl, projectStore.currentProject.name);
      await projectStore.loadFullBookReview(engine.baseUrl, projectStore.currentProject.name);
    } catch {
      // ignore
    }
  }
}

// ── Step 4 正文审阅问题持久化高亮与批注标记 ──
function applyIssueHighlightsToHtml(html: string, seq: number): string {
  const chapterReview = projectStore.chapterReviews[seq];
  const issues = chapterReview?.issues || [];
  return highlightIssuesInHtml(html, issues, seq);
}

function getUnwrittenPlaceholderHtml(seq: number, title: string): string {
  return `<div class="unwritten-chapter-placeholder"><div class="unwritten-icon">📝</div><div class="unwritten-title">第 ${seq} 章《${escapeHtml(title)}》暂未生成正文</div><div class="unwritten-desc">本章节大纲已就绪，当前内容为空。您可直接在此处点击输入排版正文，或返回【步骤 3 报告写作】进行 AI 一键撰写。</div></div>`;
}

// ── 同步排版正文到各章节 contenteditable DOM ──
function syncAllChaptersHtml() {
  for (const ch of projectStore.outlineChapters) {
    const el = document.getElementById(`chapter-canvas-${ch.seq}`);
    if (el) {
      const text = projectStore.chapters[ch.seq] || "";
      if (!text.trim()) {
        el.innerHTML = getUnwrittenPlaceholderHtml(ch.seq, ch.title);
      } else {
        const rawHtml = markdownToHtml(text, ch.seq, outlineHeadings.value);
        el.innerHTML = applyIssueHighlightsToHtml(rawHtml, ch.seq);
      }
    }
  }
}

// ── 审阅高亮标记点击联动定位至诊断报告卡片 ──
function handleCanvasClick(e: MouseEvent) {
  const target = e.target as HTMLElement | null;
  if (!target) return;
  const mark = target.closest(".review-issue-highlight") as HTMLElement | null;
  if (mark) {
    const issueId = mark.getAttribute("data-issue-id");
    const chapterSeq = Number(mark.getAttribute("data-chapter-seq")) || activeChapterSeq.value || 1;
    if (issueId) {
      openDiagnosticDrawerAndFocusIssue(issueId, chapterSeq);
    }
  }
}

function openDiagnosticDrawerAndFocusIssue(issueId: string, chapterSeq?: number) {
  if (chapterSeq) {
    activeChapterSeq.value = chapterSeq;
  }
  showDiagnosticDrawer.value = true;
  diagnosticTab.value = "issues";
  nextTick(() => {
    const card =
      document.getElementById(`issue-card-${issueId}`) ||
      document.querySelector(`[data-issue-card-id="${issueId}"]`);
    if (card) {
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      card.classList.remove("issue-card-focused");
      void (card as HTMLElement).offsetWidth;
      card.classList.add("issue-card-focused");
      setTimeout(() => {
        card.classList.remove("issue-card-focused");
      }, 2500);
    }
  });
}

onMounted(async () => {
  await ensureStep4State();
  nextTick(() => {
    syncAllChaptersHtml();
  });
});

onUnmounted(() => {
  if (reviewTimer) clearInterval(reviewTimer);
  if (revisionTimer) clearInterval(revisionTimer);
  for (const timer of Object.values(saveDebounceTimers)) {
    clearTimeout(timer);
  }
});

watch(
  () => projectStore.currentStep,
  (step) => {
    if (step === 4) {
      ensureStep4State();
      nextTick(() => {
        syncAllChaptersHtml();
      });
    }
  },
);

watch(
  () => projectStore.outlineChapters,
  () => {
    nextTick(() => {
      syncAllChaptersHtml();
    });
  },
  { deep: true },
);

watch(
  () => projectStore.chapterReviews,
  () => {
    nextTick(() => {
      syncAllChaptersHtml();
    });
  },
  { deep: true },
);

watch(viewMode, (mode) => {
  if (mode === "rich") {
    nextTick(() => {
      syncAllChaptersHtml();
    });
  }
});

// ── 全书统计与计算属性 ──
const totalChapters = computed(() => projectStore.outlineChapters.length);

function isChapterWritten(seq: number): boolean {
  const text = projectStore.chapters[seq];
  return !!(text && text.trim().length > 0);
}

function getChapterTitle(seq: number): string {
  const found = projectStore.outlineChapters.find((c) => c.seq === seq);
  return found?.title || `第 ${seq} 章`;
}

const completedChaptersCount = computed(() => {
  return projectStore.outlineChapters.filter((ch) => isChapterWritten(ch.seq)).length;
});

const unwrittenChaptersCount = computed(() => {
  return projectStore.outlineChapters.filter((ch) => !isChapterWritten(ch.seq)).length;
});

const totalWordCount = computed(() => {
  let count = 0;
  for (const text of Object.values(projectStore.chapters)) {
    if (text) count += countContentChars(text);
  }
  return count;
});

const reviewedChaptersCount = computed(() => {
  let count = 0;
  for (const ch of projectStore.outlineChapters) {
    if (projectStore.chapterReviews[ch.seq]) {
      count++;
    }
  }
  return count;
});

// ── 全书多级子标题提取 ──
const chapterSubheadings = computed<Record<number, SubHeading[]>>(() => {
  const result: Record<number, SubHeading[]> = {};
  for (const ch of projectStore.outlineChapters) {
    const text = projectStore.chapters[ch.seq];
    if (text && text.trim().length > 0) {
      result[ch.seq] = extractSubHeadings(text, ch.seq, outlineHeadings.value).filter(
        (h) => h.level > 1,
      );
    } else {
      result[ch.seq] = [];
    }
  }
  return result;
});

// ── 各章问题与缺口统计 ──
const chapterIssuesCount = computed<Record<number, number>>(() => {
  const map: Record<number, number> = {};
  for (const ch of projectStore.outlineChapters) {
    const rev = projectStore.chapterReviews[ch.seq];
    map[ch.seq] = rev?.issues ? rev.issues.length : 0;
  }
  return map;
});

function getSubheadingIssueCount(seq: number, sub: SubHeading): number {
  const rev = projectStore.chapterReviews[seq];
  if (!rev?.issues || rev.issues.length === 0) return 0;

  const subNumMatch = sub.title.match(/^\d+(?:\.\d+)*/);
  const subNum = subNumMatch ? subNumMatch[0] : null;
  const cleanSubTitle = sub.title.replace(/^\d+(?:\.\d+)*\s*/, "").trim();

  let count = 0;
  for (const iss of rev.issues) {
    const loc = iss.location || "";
    if (subNum && loc.includes(subNum)) {
      count++;
    } else if (cleanSubTitle && loc.includes(cleanSubTitle)) {
      count++;
    } else if (iss.quote && cleanSubTitle && iss.quote.includes(cleanSubTitle)) {
      count++;
    }
  }
  return count;
}

const chapterGapsCount = computed<Record<number, number>>(() => {
  const map: Record<number, number> = {};
  for (const ch of projectStore.outlineChapters) {
    const rev = projectStore.chapterReviews[ch.seq];
    map[ch.seq] = rev?.data_gap_checklist ? rev.data_gap_checklist.length : 0;
  }
  return map;
});

// ── 全书总问题清单 ──
const allIssues = computed<engineApi.ReviewIssue[]>(() => {
  if (projectStore.fullBookReview?.issues && projectStore.fullBookReview.issues.length > 0) {
    return projectStore.fullBookReview.issues;
  }
  const list: engineApi.ReviewIssue[] = [];
  for (const ch of projectStore.outlineChapters) {
    const rev = projectStore.chapterReviews[ch.seq];
    if (rev?.issues && rev.issues.length > 0) {
      for (const iss of rev.issues) {
        list.push({
          ...iss,
          chapterSeq: ch.seq,
          location: iss.location || `第 ${ch.seq} 章 ${ch.title}`,
        });
      }
    }
  }
  return list;
});

// ── 全书跨章数值核验表 ──
const allNumericalChecks = computed(() => {
  if (
    projectStore.fullBookReview?.numerical_checks &&
    projectStore.fullBookReview.numerical_checks.length > 0
  ) {
    return projectStore.fullBookReview.numerical_checks;
  }
  const list: {
    chapterSeq?: number;
    parameter: string;
    extracted_value: string;
    status: string;
    note?: string;
  }[] = [];
  for (const ch of projectStore.outlineChapters) {
    const rev = projectStore.chapterReviews[ch.seq];
    if (rev?.numerical_checks && rev.numerical_checks.length > 0) {
      for (const nc of rev.numerical_checks) {
        list.push({
          chapterSeq: ch.seq,
          parameter: nc.parameter,
          extracted_value: nc.extracted_value,
          status: nc.status,
          note: nc.note || `来自第 ${ch.seq} 章`,
        });
      }
    }
  }
  return list;
});

// ── 全书缺失资料总台账 ──
const allDataGaps = computed(() => {
  if (
    projectStore.fullBookReview?.data_gap_checklist &&
    projectStore.fullBookReview.data_gap_checklist.length > 0
  ) {
    return projectStore.fullBookReview.data_gap_checklist.map((item) => {
      if (typeof item === "string") {
        return { gap: item, chapterTitle: "全书综合" };
      }
      return item;
    });
  }
  const list: {
    chapterSeq?: number;
    chapterTitle?: string;
    gap: string;
  }[] = [];
  for (const ch of projectStore.outlineChapters) {
    const rev = projectStore.chapterReviews[ch.seq];
    if (rev?.data_gap_checklist && rev.data_gap_checklist.length > 0) {
      for (const gap of rev.data_gap_checklist) {
        list.push({
          chapterSeq: ch.seq,
          chapterTitle: ch.title,
          gap,
        });
      }
    }
  }
  return list;
});

// ── 全书参考资料总台账 ──
const allReferences = computed<ReferenceItem[]>(() => {
  let combined = "";
  for (const text of Object.values(projectStore.chapters)) {
    if (text) combined += "\n" + text;
  }
  return extractReferences(combined);
});

const filteredReferences = computed(() => {
  if (refFilterType.value === "all") return allReferences.value;
  return allReferences.value.filter((r) => r.type === refFilterType.value);
});

const totalRefCitations = computed(() => {
  return allReferences.value.reduce((sum, item) => sum + item.count, 0);
});

// ── 报告达标状态与健康评价 (废除 100 分制) ──
const healthStatus = computed(() => {
  if (projectStore.fullBookReview?.health_status) {
    return projectStore.fullBookReview.health_status;
  }
  if (reviewedChaptersCount.value === 0) {
    return "待审阅";
  }
  const hasDanger = allIssues.value.some(
    (i) => i.severity === "danger" || i.severity === "high",
  );
  if (hasDanger) return "存在重大缺陷";
  if (allIssues.value.length > 0) return "待完善";
  return "达标";
});

const complianceRate = computed(() => {
  if (projectStore.fullBookReview?.compliance_rate !== undefined) {
    return projectStore.fullBookReview.compliance_rate;
  }
  if (totalChapters.value === 0 || reviewedChaptersCount.value === 0) return 100;
  const passed = projectStore.outlineChapters.filter(
    (ch) => projectStore.chapterReviews[ch.seq]?.status === "通过",
  ).length;
  return Math.max(0, Math.min(100, Math.round((passed / totalChapters.value) * 100)));
});

// ── Diff 计算 (全宽单栏内联模式) ──
const hasActiveRevision = computed(() => {
  return projectStore.activeRevision !== null;
});

const currentDiffLines = computed<DiffLine[]>(() => {
  if (!projectStore.activeRevision) return [];
  return computeLineDiff(
    projectStore.activeRevision.originalText,
    projectStore.activeRevision.revisedText,
    outlineHeadings.value,
  );
});

const currentDiffStats = computed<DiffStats>(() => {
  if (!projectStore.activeRevision) {
    return {
      addedLines: 0,
      removedLines: 0,
      unchangedLines: 0,
      totalOriginalLines: 0,
      totalModifiedLines: 0,
    };
  }
  return computeDiffStats(
    projectStore.activeRevision.originalText,
    projectStore.activeRevision.revisedText,
    outlineHeadings.value,
  );
});

// ── 连续全书 Markdown ──
const fullBookMarkdown = computed(() => {
  const parts: string[] = [];
  for (const ch of projectStore.outlineChapters) {
    const text = projectStore.chapters[ch.seq];
    if (text && text.trim().length > 0) {
      parts.push(text.trim());
    } else {
      parts.push(`# ${ch.title}\n\n*（本章节暂未生成内容）*`);
    }
  }
  return parts.join("\n\n---\n\n");
});

// ── 交互导航与目录操作 ──
function isChapterCollapsed(seq: number): boolean {
  if (chapterCollapsedMap.value[seq] !== undefined) {
    return chapterCollapsedMap.value[seq];
  }
  return activeChapterSeq.value !== seq;
}

function toggleChapterCollapse(seq: number, e?: Event) {
  if (e) e.stopPropagation();
  const currentlyCollapsed = isChapterCollapsed(seq);
  chapterCollapsedMap.value[seq] = !currentlyCollapsed;
}

async function scrollToChapter(seq: number) {
  activeChapterSeq.value = seq;
  activeHeadingId.value = null;
  chapterCollapsedMap.value[seq] = false;
  if (viewMode.value !== "rich" && viewMode.value !== "source") {
    viewMode.value = "rich";
    await nextTick();
    syncAllChaptersHtml();
  }
  await nextTick();
  const anchorId =
    viewMode.value === "source" ? `source-chapter-${seq}` : `full-chapter-anchor-${seq}`;
  let el = document.getElementById(anchorId);
  if (!el && viewMode.value === "rich") {
    el = document.querySelector(`[data-seq="${seq}"]`) as HTMLElement | null;
  }
  if (el) {
    const container = (
      viewMode.value === "source"
        ? document.querySelector(".canvas-source-view .source-editor-wrap")
        : document.querySelector(".full-book-scroll-canvas")
    ) as HTMLElement | null;

    if (container) {
      const containerRect = container.getBoundingClientRect();
      const elRect = el.getBoundingClientRect();
      const targetTop = container.scrollTop + (elRect.top - containerRect.top) - 16;
      container.scrollTo({ top: Math.max(0, targetTop), behavior: "smooth" });
    } else {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    el.classList.remove("heading-anchor-pulse");
    void el.offsetWidth;
    el.classList.add("heading-anchor-pulse");
    setTimeout(() => {
      el?.classList.remove("heading-anchor-pulse");
    }, 1500);
  }
}

async function scrollToSubheading(seq: number, headingId: string, sub?: SubHeading, e?: Event) {
  if (e) e.stopPropagation();
  activeChapterSeq.value = seq;
  activeHeadingId.value = headingId;
  chapterCollapsedMap.value[seq] = false;
  if (viewMode.value !== "rich") {
    viewMode.value = "rich";
    await nextTick();
    syncAllChaptersHtml();
    await new Promise((r) => setTimeout(r, 60));
  }
  await nextTick();

  let el = document.getElementById(headingId);
  // 模糊查找匹配的 DOM 标题元素
  if (!el) {
    const canvas = document.getElementById(`chapter-canvas-${seq}`);
    if (canvas) {
      const headings = Array.from(canvas.querySelectorAll("h1, h2, h3, h4, h5, h6"));
      const cleanSubTitle = sub ? sub.title.replace(/^\d+(?:\.\d+)*\s*/, "").trim() : "";
      for (const h of headings) {
        const hText = (h.textContent || "").trim();
        if (
          sub &&
          (hText === sub.title ||
            (cleanSubTitle && hText.includes(cleanSubTitle)) ||
            (cleanSubTitle && cleanSubTitle.includes(hText)))
        ) {
          el = h as HTMLElement;
          break;
        }
      }
    }
  }

  if (el) {
    const container = document.querySelector(".full-book-scroll-canvas") as HTMLElement | null;
    if (container) {
      const containerRect = container.getBoundingClientRect();
      const elRect = el.getBoundingClientRect();
      const targetTop = container.scrollTop + (elRect.top - containerRect.top) - 16;
      container.scrollTo({ top: Math.max(0, targetTop), behavior: "smooth" });
    } else {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    el.classList.remove("heading-anchor-pulse");
    void el.offsetWidth;
    el.classList.add("heading-anchor-pulse");
    setTimeout(() => {
      el?.classList.remove("heading-anchor-pulse");
    }, 1500);
  } else {
    scrollToChapter(seq);
  }
}

function openChapterIssuesDrawer(seq: number, e?: Event) {
  if (e) e.stopPropagation();
  activeChapterSeq.value = seq;
  showDiagnosticDrawer.value = true;
  diagnosticTab.value = "issues";
  nextTick(() => {
    const targetCard =
      (document.querySelector(`.issue-card[data-chapter-seq="${seq}"]`) as HTMLElement | null) ||
      (document.querySelector(".issue-card") as HTMLElement | null);
    if (targetCard) {
      targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
      targetCard.classList.remove("issue-card-focused");
      void targetCard.offsetWidth;
      targetCard.classList.add("issue-card-focused");
      setTimeout(() => {
        targetCard?.classList.remove("issue-card-focused");
      }, 2500);
    }
  });
}

function openSubheadingIssuesDrawer(seq: number, sub: SubHeading, e?: Event) {
  if (e) e.stopPropagation();
  activeChapterSeq.value = seq;
  showDiagnosticDrawer.value = true;
  diagnosticTab.value = "issues";

  const rev = projectStore.chapterReviews[seq];
  const issues = rev?.issues || [];
  const subNumMatch = sub.title.match(/^\d+(?:\.\d+)*/);
  const subNum = subNumMatch ? subNumMatch[0] : null;
  const cleanSubTitle = sub.title.replace(/^\d+(?:\.\d+)*\s*/, "").trim();

  let matchedIssueId: string | null = null;
  for (const iss of issues) {
    const loc = iss.location || "";
    if (
      (subNum && loc.includes(subNum)) ||
      (cleanSubTitle && loc.includes(cleanSubTitle)) ||
      (iss.quote && cleanSubTitle && iss.quote.includes(cleanSubTitle))
    ) {
      matchedIssueId = iss.id || null;
      break;
    }
  }

  nextTick(() => {
    let targetCard: HTMLElement | null = null;
    if (matchedIssueId) {
      targetCard =
        document.getElementById(`issue-card-${matchedIssueId}`) ||
        (document.querySelector(`[data-issue-card-id="${matchedIssueId}"]`) as HTMLElement | null);
    }
    if (!targetCard) {
      targetCard =
        (document.querySelector(`.issue-card[data-chapter-seq="${seq}"]`) as HTMLElement | null) ||
        (document.querySelector(".issue-card") as HTMLElement | null);
    }

    if (targetCard) {
      targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
      targetCard.classList.remove("issue-card-focused");
      void targetCard.offsetWidth;
      targetCard.classList.add("issue-card-focused");
      setTimeout(() => {
        targetCard?.classList.remove("issue-card-focused");
      }, 2500);
    }
  });
}

// ── 就地排版编辑输入 (contenteditable 防抖 300ms 自动落盘) ──
function onChapterFocus(seq: number, e: FocusEvent) {
  const target = e.currentTarget as HTMLElement;
  if (!isChapterWritten(seq) && target.querySelector(".unwritten-chapter-placeholder")) {
    target.innerHTML = "";
  }
}

function onChapterBlur(seq: number, e: FocusEvent) {
  const target = e.currentTarget as HTMLElement;
  const currentText = (projectStore.chapters[seq] || "").trim();
  if (!currentText && !target.innerText.trim()) {
    const ch = projectStore.outlineChapters.find((c) => c.seq === seq);
    const title = ch ? ch.title : `第 ${seq} 章`;
    target.innerHTML = getUnwrittenPlaceholderHtml(seq, title);
  }
}

function onChapterInput(seq: number, e: Event) {
  const target = e.currentTarget as HTMLElement;
  const placeholderEl = target.querySelector(".unwritten-chapter-placeholder");
  if (placeholderEl && target.innerText.trim()) {
    placeholderEl.remove();
  }
  const html = target.innerHTML;
  const md = htmlToMarkdown(html);

  if (saveDebounceTimers[seq]) {
    clearTimeout(saveDebounceTimers[seq]);
  }
  saveDebounceTimers[seq] = setTimeout(() => {
    if (engine.baseUrl) {
      projectStore.saveChapter(engine.baseUrl, seq, md);
    }
  }, 300);
}

function onSourceInput(seq: number, e: Event) {
  const target = e.target as HTMLTextAreaElement;
  const md = target.value;
  if (saveDebounceTimers[seq]) {
    clearTimeout(saveDebounceTimers[seq]);
  }
  saveDebounceTimers[seq] = setTimeout(() => {
    if (engine.baseUrl) {
      projectStore.saveChapter(engine.baseUrl, seq, md);
    }
  }, 300);
}

// ── 全书全维专家审阅 ──
async function handleRunFullBookReview(forceAll = false, mode?: "fast" | "all") {
  const targetMode = mode || reviewMode.value;
  if (!engine.baseUrl) {
    showMsg("本地引擎未就绪", "error");
    return;
  }
  let llmConfig;
  try {
    llmConfig = getLLMConfig();
  } catch (e) {
    showMsg((e as Error).message, "error");
    return;
  }

  if (completedChaptersCount.value === 0) {
    showMsg("暂无可审阅的章节，请先在步骤 3 写作并生成正文", "error");
    return;
  }

  reviewElapsedSeconds.value = 0;
  if (reviewTimer) clearInterval(reviewTimer);
  reviewTimer = setInterval(() => {
    reviewElapsedSeconds.value += 1;
  }, 1000);

  try {
    const modeName = targetMode === "fast" ? "⚡ 常规审查" : "🔍 全维精审";
    showMsg(`已启动「${modeName}」，正在执行合规与数据自洽体检...`, "info");
    const fullData = await projectStore.runFullBookReview(
      engine.baseUrl,
      llmConfig,
      forceAll,
      targetMode,
    );
    showMsg(
      `全书专家审阅完成！健康达标状态：「${fullData.health_status}」，发现 ${fullData.issues.length} 处待优化项。`,
    );
    showDiagnosticDrawer.value = true;
  } catch (err) {
    showMsg(`审阅失败：${(err as Error).message}`, "error");
  } finally {
    if (reviewTimer) {
      clearInterval(reviewTimer);
      reviewTimer = null;
    }
  }
}

// ── 单章专家审阅 ──
async function handleRunSingleReview(
  seq: number,
  mode?: "fast" | "all" | "compliance" | "numeric" | "technical",
) {
  const targetMode = mode || reviewMode.value;
  if (!engine.baseUrl) {
    showMsg("本地引擎未就绪", "error");
    return;
  }
  let llmConfig;
  try {
    llmConfig = getLLMConfig();
  } catch (e) {
    showMsg((e as Error).message, "error");
    return;
  }

  const text = projectStore.chapters[seq] || "";
  if (!text.trim()) {
    showMsg(`第 ${seq} 章尚无正文，无法执行审阅`, "error");
    return;
  }

  reviewElapsedSeconds.value = 0;
  if (reviewTimer) clearInterval(reviewTimer);
  reviewTimer = setInterval(() => {
    reviewElapsedSeconds.value += 1;
  }, 1000);

  try {
    const modeLabel = targetMode === "fast" ? "⚡ 常规审查" : (targetMode === "all" ? "🔍 全维精审" : targetMode);
    showMsg(`正在对第 ${seq} 章执行【${modeLabel}】...`, "info");
    const res = await projectStore.runChapterReview(engine.baseUrl, seq, targetMode, llmConfig);
    showMsg(`第 ${seq} 章审阅完成！结论：${res.status}，发现 ${res.issues?.length || 0} 处问题。`);
    // 重新整合全书总档案
    await projectStore.runFullBookReview(engine.baseUrl, llmConfig, false, reviewMode.value);
  } catch (err) {
    showMsg(`单章审阅失败：${(err as Error).message}`, "error");
  } finally {
    if (reviewTimer) {
      clearInterval(reviewTimer);
      reviewTimer = null;
    }
  }
}

// ── AI 一键智能修订 (就地直接执行并切至 Diff 模式) ──
async function handleDirectRevision(seq?: number, customInstruction?: string) {
  if (!engine.baseUrl) {
    showMsg("本地引擎未就绪", "error");
    return;
  }
  let llmConfig;
  try {
    llmConfig = getLLMConfig();
  } catch (e) {
    showMsg((e as Error).message, "error");
    return;
  }

  const targetSeq = seq || activeChapterSeq.value || 1;
  let instruction = (customInstruction || "").trim();

  // 若未指定自定义指令，则优先聚合当前章节的专家审阅建议与问题清单
  if (!instruction) {
    const chapterReview = projectStore.chapterReviews[targetSeq];
    const issues = chapterReview?.issues || [];
    const suggestions = chapterReview?.suggestions || "";
    if (issues.length > 0 || suggestions) {
      const issueDetails = issues
        .map(
          (iss, i) =>
            `${i + 1}. [${iss.category || "合规与自洽"}] ${iss.message}${iss.suggestion ? `（改进建议：${iss.suggestion}）` : ""}`,
        )
        .join("\n");
      instruction = `请依据本章专家诊断报告执行定向修订：\n${issueDetails}\n${suggestions ? `综合指引：${suggestions}` : ""}`.trim();
    } else if (projectStore.fullBookReview?.general_suggestions?.length) {
      instruction = `对照国家发改委与行业工程编制规程要求，结合全书诊断建议深化论述：\n${projectStore.fullBookReview.general_suggestions.join("\n")}`.trim();
    } else {
      instruction = "对照国家发改委与行业工程编制规程要求，核对本章数据自洽性、深化合规论证并润色工程专业术语。";
    }
  }

  revisionElapsedSeconds.value = 0;
  revisionStageIndex.value = 0;
  if (revisionTimer) clearInterval(revisionTimer);
  revisionTimer = setInterval(() => {
    revisionElapsedSeconds.value += 1;
    revisionStageIndex.value = Math.min(3, Math.floor(revisionElapsedSeconds.value / 3));
  }, 1000);

  try {
    showMsg(`正在对第 ${targetSeq} 章执行 AI 智能就地修订并生成 Diff...`, "info");
    await projectStore.runChapterRevision(engine.baseUrl, targetSeq, instruction, llmConfig);
    viewMode.value = "diff";
    showMsg(`第 ${targetSeq} 章 AI 修订已就绪！已进入全宽单栏内联 Diff 差异对比视图。`);
  } catch (err) {
    showMsg(`修订失败：${(err as Error).message}`, "error");
  } finally {
    if (revisionTimer) {
      clearInterval(revisionTimer);
      revisionTimer = null;
    }
  }
}

// ── 采纳 / 放弃修订 ──
async function handleApplyRevision() {
  if (!projectStore.activeRevision) return;
  const seq = projectStore.activeRevision.seq;
  try {
    await projectStore.applyRevision(engine.baseUrl, seq);
    nextTick(() => {
      syncAllChaptersHtml();
    });
    viewMode.value = "rich";
    showMsg(`已成功采纳第 ${seq} 章的修订并保存为最新正文！`);
  } catch (err) {
    showMsg(`采纳修订失败：${(err as Error).message}`, "error");
  }
}

function handleDiscardRevision() {
  projectStore.discardRevision();
  viewMode.value = "rich";
  showMsg("已放弃本次修订结果，恢复原正文。", "info");
}

// ── 审阅问题句子级精准定位与呼吸波纹高亮 ──
async function locateIssueInCanvas(
  issueOrLocation?: engineApi.ReviewIssue | string,
  optionalChapterSeq?: number,
) {
  let targetSeq = optionalChapterSeq;
  let issueId = "";
  let quote = "";
  let location = "";
  let message = "";

  if (issueOrLocation && typeof issueOrLocation === "object") {
    targetSeq = issueOrLocation.chapterSeq || targetSeq;
    issueId = (issueOrLocation.id || "").trim();
    quote = (issueOrLocation.quote || "").trim();
    location = (issueOrLocation.location || "").trim();
    message = (issueOrLocation.message || "").trim();
  } else if (typeof issueOrLocation === "string") {
    location = issueOrLocation.trim();
  }

  // 从 location 推断 chapterSeq
  if (!targetSeq && location) {
    const m = location.match(/第\s*([一二三四五六七八九十百零\d]+)\s*章/);
    if (m) {
      targetSeq = Number(m[1]) || 1;
    } else {
      const numM = location.match(/^(\d+)(?:\.\d+)*/);
      if (numM) {
        targetSeq = Number(numM[1]) || 1;
      }
    }
  }
  if (!targetSeq) targetSeq = 1;

  // 1. 确保在 rich 视图模式并激活章节
  if (viewMode.value !== "rich") {
    viewMode.value = "rich";
    await nextTick();
    syncAllChaptersHtml();
    await new Promise((r) => setTimeout(r, 60));
  }
  activeChapterSeq.value = targetSeq;

  // 2. 找到对应章节的 canvas DOM 容器
  const canvasEl = document.getElementById(`chapter-canvas-${targetSeq}`);
  let targetEl: HTMLElement | null = null;

  if (canvasEl) {
    // 优先级 1: 直接查找已高亮的 mark[data-issue-id] 元素
    if (issueId) {
      const markEl =
        canvasEl.querySelector<HTMLElement>(`mark.review-issue-highlight[data-issue-id="${issueId}"]`) ||
        document.querySelector<HTMLElement>(`mark.review-issue-highlight[data-issue-id="${issueId}"]`);
      if (markEl) {
        targetEl = markEl;
      }
    }

    // 候选富文本容器
    const candidates = Array.from(
      canvasEl.querySelectorAll<HTMLElement>(
        "p, h1, h2, h3, h4, h5, h6, tr, li, blockquote, pre, td, th",
      ),
    );

    // 优先级 2: 按 quote 精确或前缀匹配富文本中的容器
    if (!targetEl && quote && quote.length >= 2) {
      for (const el of candidates) {
        if (el.textContent && el.textContent.includes(quote)) {
          targetEl = el;
          break;
        }
      }
      if (!targetEl && quote.length > 8) {
        const shortQuote = quote.slice(0, Math.min(12, quote.length));
        const shorterQuote = quote.slice(0, 8);
        for (const el of candidates) {
          if (
            el.textContent &&
            (el.textContent.includes(shortQuote) || el.textContent.includes(shorterQuote))
          ) {
            targetEl = el;
            break;
          }
        }
      }
    }

    // 优先级 3: 按 location 标题与小节编号匹配对应 DOM 标题或段落
    if (!targetEl && location) {
      const cleanLoc = location.replace(/^(?:第\s*[一二三四五六七八九十百零\d]+\s*章|\d+(?:\.\d+)*|[\s、：:])+/g, "").trim();
      const locNumMatch = location.match(/\d+(?:\.\d+)*/);
      const locNum = locNumMatch ? locNumMatch[0] : null;

      // 优先匹配标题标签
      for (const el of candidates) {
        if (/^H[1-6]$/i.test(el.tagName)) {
          if (cleanLoc && el.textContent?.includes(cleanLoc)) {
            targetEl = el;
            break;
          }
          if (locNum && el.textContent?.includes(locNum)) {
            targetEl = el;
            break;
          }
        }
      }
      // 其次匹配段落
      if (!targetEl && cleanLoc && cleanLoc.length >= 2) {
        for (const el of candidates) {
          if (el.textContent && el.textContent.includes(cleanLoc)) {
            targetEl = el;
            break;
          }
        }
      }
    }

    // 优先级 4: 按 message 核心关键词、引号片段或核心数值匹配相关段落
    if (!targetEl && message) {
      const quoteInMsg = message.match(/[“"「『]([^”"』」]+)[”"』」]/);
      if (quoteInMsg && quoteInMsg[1].trim().length >= 2) {
        const kw = quoteInMsg[1].trim();
        for (const el of candidates) {
          if (el.textContent && el.textContent.includes(kw)) {
            targetEl = el;
            break;
          }
        }
      }
      if (!targetEl) {
        const numMatches = message.match(
          /(?:\d+(?:\.\d+)?\s*(?:万元|亿元|万m³|万立方米|km²|km|m²|m|人|亩|%|个|台|套|座|年|月|日|天|元|吨|kw|MW|GW|h))/gi,
        );
        if (numMatches) {
          for (const numKw of numMatches) {
            const kw = numKw.trim();
            if (kw.length >= 2) {
              for (const el of candidates) {
                if (el.textContent && el.textContent.includes(kw)) {
                  targetEl = el;
                  break;
                }
              }
              if (targetEl) break;
            }
          }
        }
      }
    }

    // 如果是 td/th 且非 mark，提升为 tr
    if (targetEl && (targetEl.tagName === "TD" || targetEl.tagName === "TH")) {
      targetEl = (targetEl.closest("tr") as HTMLElement) || targetEl;
    }
  }

  if (targetEl) {
    targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
    targetEl.classList.remove("issue-highlight-pulse");
    void targetEl.offsetWidth; // 强制触发 reflow 播放呼吸动画
    targetEl.classList.add("issue-highlight-pulse");
    setTimeout(() => {
      targetEl?.classList.remove("issue-highlight-pulse");
    }, 2500);
    showMsg(`已精准定位至第 ${targetSeq} 章对应问题语句/段落`, "info");
  } else {
    // 降级：平滑滚动到章节头部
    await scrollToChapter(targetSeq);
    showMsg(`已定位至第 ${targetSeq} 章`, "info");
  }
}

// ── 复制全书 Markdown ──
function copyFullBookMarkdown() {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(fullBookMarkdown.value);
    showMsg("已复制全书排版 Markdown 源码至剪贴板！");
  }
}
</script>

<template>
  <div class="step4-container">
    <!-- 全局提示 Banner -->
    <transition name="fade">
      <div v-if="actionMessage" :class="['alert-banner', actionMessage.type]">
        {{ actionMessage.text }}
      </div>
    </transition>

    <!-- ═════════════════════════════════════════════════════════ -->
    <!-- 顶部工作台状态与全局操作区 (Header Toolbar) -->
    <!-- ═════════════════════════════════════════════════════════ -->
    <header class="review-workbench-header card">
      <div class="header-left-meta">
        <div class="project-title-box">
          <span class="proj-badge">{{ projectStore.currentProject?.name || "未选项目" }}</span>
          <h2 class="workbench-main-title">全书一体化审阅与全景工作台</h2>
        </div>

        <div class="health-badges-group">
          <!-- 健康达标度徽标 (彻底废除 100 分制) -->
          <div
            class="health-badge"
            :class="{
              'health-passed': healthStatus === '达标',
              'health-warning': healthStatus === '待完善',
              'health-danger': healthStatus === '存在重大缺陷',
              'health-pending': healthStatus === '待审阅',
            }"
            :title="`全书达标度：${complianceRate}%`"
          >
            <span class="health-dot"></span>
            <span class="health-label">
              {{
                healthStatus === "达标"
                  ? "🟢 达标（优良）"
                  : healthStatus === "待完善"
                  ? `🟡 待完善 (${allIssues.length} 处待核)`
                  : healthStatus === "存在重大缺陷"
                  ? `🔴 存在重大缺陷 (${allIssues.length} 处待改)`
                  : "⏳ 待专家审阅"
              }}
            </span>
            <span class="compliance-pct">达标度 {{ complianceRate }}%</span>
          </div>

          <div class="meta-stat-pills">
            <span class="meta-pill" title="全书总字数（已排除表格与标题）">
              <strong>{{ totalWordCount.toLocaleString() }}</strong> 字 (正文)
            </span>
            <span class="meta-pill" title="已完成编写章节数">
              <strong>{{ completedChaptersCount }} / {{ totalChapters }}</strong> 章已撰写
            </span>
            <span v-if="unwrittenChaptersCount > 0" class="meta-pill meta-pill-unwritten" title="待撰写章节数">
              待撰写 <strong>{{ unwrittenChaptersCount }}</strong> 章
            </span>
            <span class="meta-pill" title="已审阅章节数">
              <strong>{{ reviewedChaptersCount }} / {{ totalChapters }}</strong> 章已体检
            </span>
          </div>
        </div>
      </div>

      <!-- 视图切换 Tab 与核心操作 -->
      <div class="header-center-tabs">
        <div class="view-mode-tabs">
          <button
            class="tab-btn"
            :class="{ active: viewMode === 'rich' }"
            @click="viewMode = 'rich'"
            title="连贯渲染全书出版级排版正文，支持点击就地直接编辑润色"
          >
            📝 最终排版正文 (可编辑)
          </button>
          <button
            class="tab-btn"
            :class="{ active: viewMode === 'diff' }"
            @click="viewMode = 'diff'"
            title="全宽单栏段落级内联高亮差异比对 (删除线/新增背景)"
          >
            🔍 修订差异对比
            <span v-if="hasActiveRevision" class="active-diff-indicator">●</span>
          </button>
          <button
            class="tab-btn"
            :class="{ active: viewMode === 'source' }"
            @click="viewMode = 'source'"
            title="查看与编辑纯文本 Markdown 原生源码"
          >
            📝 Markdown 源码
          </button>
        </div>
      </div>

      <div class="header-right-actions">
        <!-- 审查模式切换胶囊 -->
        <div class="review-mode-pills">
          <button
            class="mode-pill-btn"
            :class="{ active: reviewMode === 'fast' }"
            @click="reviewMode = 'fast'"
            title="常规审查：极速聚焦名词称谓、核心数值自洽与底线合规三大维度，单章约 8~12s（推荐）"
          >
            ⚡ 常规审查
          </button>
          <button
            class="mode-pill-btn"
            :class="{ active: reviewMode === 'all' }"
            @click="reviewMode = 'all'"
            title="全维精审：全维度专家逐句诊断与方案比选深度审查，单章约 30~45s"
          >
            🔍 全维精审
          </button>
        </div>

        <!-- 核心行动按钮 -->
        <button
          v-if="!projectStore.batchReviewing"
          class="btn btn-primary btn-review-hero"
          :disabled="completedChaptersCount === 0"
          @click="handleRunFullBookReview(false)"
          title="以当前选定模式立即运行全书审阅"
        >
          🚀 运行全书审阅
        </button>
        <button
          v-else
          class="btn btn-danger btn-review-hero"
          @click="projectStore.stopBatchReview()"
          title="中止当前正在执行的批量全书审阅任务"
        >
          ⏹ 停止审阅
        </button>

        <button
          class="btn btn-outline"
          :disabled="completedChaptersCount === 0 || projectStore.revisingSeq !== null"
          @click="handleDirectRevision()"
          title="代入本章当前诊断建议或全维综合建议，一键由大模型执行智能就地重构并生成 Diff 对比"
        >
          ⚡ AI 一键智能修订
        </button>

        <div class="drawer-trigger-group">
          <button
            class="btn btn-outline drawer-btn"
            :class="{ active: showDiagnosticDrawer }"
            @click="showDiagnosticDrawer = !showDiagnosticDrawer"
            title="打开全高右侧专家诊断总台账抽屉"
          >
            📋 专家诊断报告
            <span class="count-badge" :class="{ 'has-issues': allIssues.length > 0 }">
              {{ allIssues.length }}
            </span>
          </button>

          <button
            class="btn btn-outline drawer-btn"
            :class="{ active: showRefDrawer }"
            @click="showRefDrawer = !showRefDrawer"
            title="打开全高右侧全书参考资料与行业规程来源抽屉"
          >
            📚 参考资料
            <span class="count-badge">
              {{ allReferences.length }}
            </span>
          </button>
        </div>
      </div>
    </header>

    <!-- 审阅心跳与进度条 (正在执行审阅时展示) -->
    <transition name="fade">
      <div v-if="projectStore.batchReviewing" class="review-heartbeat-bar card">
        <div class="heartbeat-inner">
          <div class="hb-left">
            <span class="radar-pulse"></span>
            <div class="hb-title-box">
              <div class="hb-main-title">
                <strong>⚡ 正在深度审阅 第 {{ projectStore.reviewProgress?.currentIndex || 1 }}/{{ projectStore.reviewProgress?.totalTarget || 1 }} 章：《{{ projectStore.reviewProgress?.currentTitle || '当前章节' }}》（进度 {{ projectStore.reviewProgress?.percent || 0 }}%）· 已耗时 {{ projectStore.reviewProgress?.elapsedSeconds ?? reviewElapsedSeconds }}s</strong>
              </div>
              <div class="hb-desc">
                已完成 {{ projectStore.reviewProgress?.currentIndex ? projectStore.reviewProgress.currentIndex - 1 : 0 }} 章，累计发现 {{ projectStore.reviewProgress?.completedIssuesCount || 0 }} 处优化建议 · 依照国家发改委与行业工程编制规程进行系统体检
              </div>
            </div>
          </div>
          <div class="hb-right">
            <button
              class="btn btn-danger btn-sm btn-stop-review"
              @click="projectStore.stopBatchReview()"
              title="中止当前正在执行的批量全书审阅任务"
            >
              ⏹ 停止审阅
            </button>
          </div>
        </div>

        <!-- 实时 AI 专家审阅思考推演窗 -->
        <div class="review-thought-stream-wrapper">
          <div class="review-thought-card">
            <div class="review-thought-header" @click="showReviewThoughtDetails = !showReviewThoughtDetails">
              <div class="review-thought-title">
                <span class="review-thought-icon">🧠</span>
                <span>专家审阅实时思考推演窗 <span v-if="projectStore.reviewProgress?.thoughtText">({{ projectStore.reviewProgress.thoughtText.length }} 字符)</span></span>
                <span class="thinking-wave">
                  <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                </span>
              </div>
              <button class="review-thought-toggle-btn" type="button">
                {{ showReviewThoughtDetails ? '收起 ▲' : '展开 ▼' }}
              </button>
            </div>
            <div v-show="showReviewThoughtDetails" class="review-thought-body">
              <pre v-if="projectStore.reviewProgress?.thoughtText">{{ projectStore.reviewProgress.thoughtText }}</pre>
              <div v-else class="review-thought-placeholder">
                <span class="placeholder-spinner">🔍</span>
                <span>AI 专家正在对照国家发改委与行业编制规程深度核查章节参数指标与数据自洽性...</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 修订心跳与进度条 (正在执行就地修订时展示) -->
    <transition name="fade">
      <div v-if="projectStore.revisingSeq !== null" class="revision-heartbeat-bar card">
        <div class="heartbeat-inner">
          <div class="hb-left">
            <span class="radar-pulse"></span>
            <div class="hb-title-box">
              <div class="hb-main-title">
                <strong>⚡ AI 智能修订重构中：第 {{ projectStore.revisingSeq }} 章（{{ revisionStages[revisionStageIndex]?.title || '重构方案论述' }}）· 已耗时 {{ revisionElapsedSeconds }}s</strong>
              </div>
              <div class="hb-desc">
                {{ revisionStages[revisionStageIndex]?.desc || '统筹上下文逻辑与专家诊断建议，执行段落级出版重构' }}
              </div>
            </div>
          </div>
          <div class="hb-right">
            <div class="hb-stepper-compact">
              <div
                v-for="(st, stIdx) in revisionStages"
                :key="st.id"
                class="stepper-item"
                :class="{
                  completed: revisionStageIndex > stIdx,
                  active: revisionStageIndex === stIdx,
                  pending: revisionStageIndex < stIdx,
                }"
              >
                <div class="stepper-circle">
                  <span v-if="revisionStageIndex > stIdx">✓</span>
                  <span v-else-if="revisionStageIndex === stIdx" class="spinner-mini"></span>
                  <span v-else>{{ stIdx + 1 }}</span>
                </div>
                <span class="stepper-label">{{ st.title }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- ═════════════════════════════════════════════════════════ -->
    <!-- 主体工作台：左侧全书多级标题导航 + 右侧 100% 满屏连贯正文画布 -->
    <!-- ═════════════════════════════════════════════════════════ -->
    <div class="workbench-main-layout">
      <!-- 左侧：全书多级标题目录导航 (Sidebar Outline Tree) -->
      <aside class="sidebar-nav-panel card">
        <div class="card-header sidebar-header">
          <div class="header-titles">
            <h3>📑 章节目录与导航</h3>
            <span class="proj-badge">{{ projectStore.currentProject?.name || "未选项目" }}</span>
          </div>
          <!-- 统计指示条 (100% 对齐 Step 3) -->
          <div class="stats-overview">
            <div class="stat-item">
              <span class="stat-label">总章节</span>
              <span class="stat-val">{{ totalChapters }} 章</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-label">已审阅</span>
              <span class="stat-val stat-success">{{ reviewedChaptersCount }} / {{ totalChapters }}</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-label">总字数 (正文)</span>
              <span class="stat-val">{{ totalWordCount.toLocaleString() }} 字</span>
            </div>
          </div>

          <!-- 💡 推荐写作顺序：流程胶囊提示 -->
          <div
            v-if="projectStore.writingOrder && projectStore.writingOrder.length > 0"
            class="writing-order-box"
            :title="projectStore.writingOrderReason || '推荐写作顺序'"
          >
            <div class="order-box-header">
              <span class="order-icon">💡</span>
              <span class="order-title">推荐写作顺序</span>
            </div>
            <div class="order-flow-chips">
              <span
                v-for="(seq, idx) in projectStore.writingOrder"
                :key="seq"
                class="order-node-wrap"
              >
                <span
                  class="order-chip"
                  :class="{
                    active: activeChapterSeq === seq,
                    completed: isChapterWritten(seq),
                    warning: (chapterIssuesCount[seq] || 0) > 0,
                  }"
                  @click="scrollToChapter(seq)"
                  :title="`第 ${seq} 章：${getChapterTitle(seq)}`"
                >
                  第 {{ seq }} 章
                </span>
                <span v-if="idx < projectStore.writingOrder.length - 1" class="flow-arrow">➔</span>
              </span>
            </div>
          </div>
        </div>

        <div class="outline-tree-scrollable">
          <div v-if="totalChapters === 0" class="empty-outline-tip">
            暂无章节目录，请先在步骤 2 生成大纲。
          </div>

          <div
            v-for="ch in projectStore.outlineChapters"
            :key="ch.seq"
            class="chapter-tree-node"
            :class="{
              'is-active': activeChapterSeq === ch.seq,
              'is-completed': isChapterWritten(ch.seq),
              'has-review': !!projectStore.chapterReviews[ch.seq],
              'has-warning': (chapterIssuesCount[ch.seq] || 0) > 0 || (chapterGapsCount[ch.seq] || 0) > 0,
              'is-unwritten-node': !isChapterWritten(ch.seq),
            }"
          >
            <!-- 章节卡片头部 -->
            <div
              class="chapter-node-row"
              @click="scrollToChapter(ch.seq)"
              :title="`第 ${ch.seq} 章：${ch.title}`"
            >
              <div class="row-left">
                <span class="ch-seq-tag">{{ ch.seq }}</span>
                <span class="ch-title-text">{{ ch.title }}</span>
              </div>

              <div class="row-right">
                <!-- 状态药丸 (100% 对齐 Step 3) -->
                <span
                  class="status-pill"
                  :class="isChapterWritten(ch.seq) ? 'completed' : 'idle'"
                >
                  {{ isChapterWritten(ch.seq) ? "已完成 ✓" : "待撰写" }}
                </span>

                <!-- 预警角标 (若有审阅问题) -->
                <span
                  v-if="(chapterIssuesCount[ch.seq] || 0) > 0"
                  class="warning-badge-pill"
                  :title="`第 ${ch.seq} 章存在 ${chapterIssuesCount[ch.seq]} 处待优化诊断，点击定位问题`"
                  @click.stop="openChapterIssuesDrawer(ch.seq, $event)"
                >
                  ⚠️ {{ chapterIssuesCount[ch.seq] }}
                </span>

                <!-- 子标题展开/折叠 -->
                <button
                  v-if="chapterSubheadings[ch.seq] && chapterSubheadings[ch.seq].length > 0"
                  class="collapse-toggle-icon"
                  :class="{ collapsed: isChapterCollapsed(ch.seq) }"
                  @click="toggleChapterCollapse(ch.seq, $event)"
                  :title="isChapterCollapsed(ch.seq) ? '展开子标题' : '收起子标题'"
                >
                  {{ isChapterCollapsed(ch.seq) ? '▶' : '▼' }}
                </button>
              </div>
            </div>

            <!-- 多级子标题列表 (节与小节: H2, H3, H4) -->
            <transition name="tree-expand">
              <div
                v-if="!isChapterCollapsed(ch.seq) && chapterSubheadings[ch.seq] && chapterSubheadings[ch.seq].length > 0"
                class="subheadings-subtree"
              >
                <div
                  v-for="sub in chapterSubheadings[ch.seq]"
                  :key="sub.id"
                  class="subheading-item-row"
                  :class="[
                    `level-${sub.level}`,
                    { 'is-active-heading': activeHeadingId === sub.id },
                  ]"
                  @click="scrollToSubheading(ch.seq, sub.id, sub, $event)"
                  :title="sub.title"
                >
                  <span class="sub-text">{{ sub.title }}</span>
                  <span
                    v-if="getSubheadingIssueCount(ch.seq, sub) > 0"
                    class="sub-issue-badge"
                    :title="`该小节存在 ${getSubheadingIssueCount(ch.seq, sub)} 处审阅问题，点击直达诊断卡片`"
                    @click.stop="openSubheadingIssuesDrawer(ch.seq, sub, $event)"
                  >
                    ⚠️ {{ getSubheadingIssueCount(ch.seq, sub) }}
                  </span>
                </div>
              </div>
            </transition>
          </div>
        </div>
      </aside>

      <!-- 右侧：100% 满屏连贯正文主画布 (Main Canvas Panel) -->
      <main class="main-canvas-panel card">
        <!-- ═════════════════════════════════════════════════════════ -->
        <!-- 模式 1: 最终排版正文 (rich) — 连贯全文 + contenteditable 就地编辑 -->
        <!-- ═════════════════════════════════════════════════════════ -->
        <div v-show="viewMode === 'rich'" class="canvas-rich-view">
          <div class="rich-view-header-bar">
            <div class="spec-label-box">
              <span class="spec-tag">📖 国家发改委与行业规程出版级排版 (10.5pt)</span>
              <span class="spec-sub">
                支持直接在下方排版文字上点击输入修改，300ms 自动落盘回存对应章节。
              </span>
            </div>
            <div class="spec-actions">
              <button class="btn btn-outline btn-xs" @click="copyFullBookMarkdown">
                📋 复制全书 Markdown
              </button>
            </div>
          </div>

          <div class="full-book-scroll-canvas" @click="handleCanvasClick">
            <div
              v-for="ch in projectStore.outlineChapters"
              :key="ch.seq"
              :id="`full-chapter-anchor-${ch.seq}`"
              class="full-book-chapter-block"
              :class="{ 'is-unwritten-block': !isChapterWritten(ch.seq) }"
            >
              <!-- 标准化章标题栏 (全书连贯预览标准化呈现章标题与字数标签) -->
              <div class="chapter-block-header">
                <div class="header-left">
                  <span class="ch-badge">第 {{ ch.seq }} 章</span>
                  <h3 class="ch-title">{{ ch.title }}</h3>
                </div>
                <div class="header-right">
                  <span v-if="!isChapterWritten(ch.seq)" class="ch-word-tag tag-unwritten">待撰写 · 0 字</span>
                  <span v-else class="ch-word-tag">{{ countContentChars(projectStore.chapters[ch.seq] || '').toLocaleString() }} 字 (正文)</span>
                </div>
              </div>

              <!-- 就地排版编辑器画布 (contenteditable) -->
              <div
                :id="`chapter-canvas-${ch.seq}`"
                class="rich-rendered-editor spec-typography"
                :class="{ 'is-empty-chapter': !isChapterWritten(ch.seq) }"
                contenteditable="true"
                :data-seq="ch.seq"
                @input="onChapterInput(ch.seq, $event)"
                @focus="onChapterFocus(ch.seq, $event)"
                @blur="onChapterBlur(ch.seq, $event)"
                data-placeholder="本章节暂未生成内容。可在此处直接输入排版文字，或返回步骤 3 自动写作..."
              ></div>
            </div>

            <div v-if="totalChapters === 0" class="canvas-empty-state">
              <h3>暂无章节正文</h3>
              <p>请先在步骤 2 生成大纲并在步骤 3 写作后，在此处进行出版级排版审阅。</p>
            </div>
          </div>
        </div>

        <!-- ═════════════════════════════════════════════════════════ -->
        <!-- 模式 2: 修订差异对比 (diff) — 全宽单栏内联段落级高亮 -->
        <!-- ═════════════════════════════════════════════════════════ -->
        <div v-show="viewMode === 'diff'" class="canvas-diff-view">
          <!-- 差异比对常驻操作栏 -->
          <div class="diff-sticky-header">
            <div class="diff-header-info">
              <div class="diff-title-row">
                <span class="diff-main-badge">🔍 全宽单栏内联 Diff 差异对比</span>
                <span v-if="projectStore.activeRevision" class="diff-ch-tag">
                  第 {{ projectStore.activeRevision.seq }} 章
                </span>
              </div>
            </div>

            <div class="diff-header-stats">
              <span class="diff-stat-pill pill-added">+ {{ currentDiffStats.addedLines }} 新增</span>
              <span class="diff-stat-pill pill-removed">- {{ currentDiffStats.removedLines }} 删除</span>
              <span class="diff-stat-pill pill-unchanged">= {{ currentDiffStats.unchangedLines }} 未修改</span>
            </div>

            <div class="diff-header-actions">
              <button
                class="btn btn-success"
                :disabled="!hasActiveRevision || projectStore.revisingSeq !== null"
                @click="handleApplyRevision"
                title="采纳本次 AI 修订结果并保存覆盖为最新正文"
              >
                ✅ 采纳全部修订并保存为正文
              </button>
              <button
                class="btn btn-outline"
                :disabled="!hasActiveRevision || projectStore.revisingSeq !== null"
                @click="handleDirectRevision(projectStore.activeRevision?.seq || activeChapterSeq || 1, projectStore.activeRevision?.instruction)"
                title="代入修改指令重新生成修订"
              >
                🔄 重新生成
              </button>
              <button
                class="btn btn-outline btn-danger-text"
                :disabled="!hasActiveRevision || projectStore.revisingSeq !== null"
                @click="handleDiscardRevision"
                title="放弃本次修订，恢复原有正文"
              >
                ↩ 放弃本次修订
              </button>
            </div>
          </div>

          <!-- 全宽内联 Diff 内容 -->
          <div class="diff-inline-scrollable spec-typography">
            <div v-if="hasActiveRevision && currentDiffLines.length > 0" class="diff-lines-wrapper">
              <div
                v-for="(line, lIdx) in currentDiffLines"
                :key="lIdx"
                class="diff-line-row"
                :class="`diff-line-${line.type}`"
              >
                <div class="diff-line-num old-num">{{ line.oldLineNumber || '' }}</div>
                <div class="diff-line-num new-num">{{ line.newLineNumber || '' }}</div>
                <div class="diff-line-sign">
                  <span v-if="line.type === 'added'">+</span>
                  <span v-else-if="line.type === 'removed'">-</span>
                  <span v-else>&nbsp;</span>
                </div>
                <div class="diff-line-content">
                  <ins v-if="line.type === 'added'">{{ line.text }}</ins>
                  <s v-else-if="line.type === 'removed'">{{ line.text }}</s>
                  <span v-else>{{ line.text }}</span>
                </div>
              </div>
            </div>

            <!-- 空白状态 -->
            <div v-else class="diff-empty-placeholder card">
              <div class="empty-icon">💡</div>
              <h4>当前暂无正在比对的修订版本</h4>
              <p>您可以点击顶栏「⚡ AI 一键智能修订」或在诊断抽屉中点击「⚡ 代入建议并一键修订」，系统将自动生成段落级 Diff 对比。</p>
              <button class="btn btn-primary" :disabled="projectStore.revisingSeq !== null" @click="handleDirectRevision(activeChapterSeq || 1)">
                ⚡ 立即发起 AI 智能修订
              </button>
            </div>
          </div>
        </div>

        <!-- ═════════════════════════════════════════════════════════ -->
        <!-- 模式 3: Markdown 源码 (source) -->
        <!-- ═════════════════════════════════════════════════════════ -->
        <div v-show="viewMode === 'source'" class="canvas-source-view">
          <div class="source-view-toolbar">
            <div class="source-info">
              <span>📝 Markdown 原生标记源码模式</span>
              <span class="source-divider">·</span>
              <span>全书共 <strong>{{ totalWordCount.toLocaleString() }}</strong> 字符 (正文)</span>
            </div>
            <div class="source-actions">
              <button class="btn btn-outline btn-xs" @click="copyFullBookMarkdown">
                📋 复制全书 Markdown
              </button>
            </div>
          </div>

          <div class="source-editor-scrollable">
            <div
              v-for="ch in projectStore.outlineChapters"
              :key="ch.seq"
              :id="`source-chapter-${ch.seq}`"
              class="source-chapter-card"
            >
              <div class="source-card-header">
                <span class="source-seq">第 {{ ch.seq }} 章</span>
                <span class="source-title">{{ ch.title }}</span>
                <span class="source-len">{{ countContentChars(projectStore.chapters[ch.seq] || '') }} 字符 (正文)</span>
              </div>
              <textarea
                class="source-textarea"
                :value="projectStore.chapters[ch.seq] || ''"
                @input="onSourceInput(ch.seq, $event)"
                :placeholder="`第 ${ch.seq} 章 Markdown 源码...`"
              ></textarea>
            </div>
          </div>
        </div>

        <!-- 底部全局向导步骤导航 -->
        <footer class="workbench-footer-nav">
          <button class="btn btn-secondary" @click="projectStore.setStep(3)">
            &larr; 上一步：章节写作
          </button>
          <div class="footer-center-summary">
            <span>健康达标状态：<strong>{{ healthStatus }}</strong></span>
            <span class="footer-divider">·</span>
            <span>合规达标度：<strong>{{ complianceRate }}%</strong></span>
          </div>
          <button class="btn btn-primary btn-lg" @click="projectStore.setStep(5)">
            下一步：成果导出 &rarr;
          </button>
        </footer>
      </main>
    </div>

    <!-- ═════════════════════════════════════════════════════════ -->
    <!-- 全高右侧抽屉 1: 📋 专家诊断报告 (Slide-over Drawer, 540px) -->
    <!-- ═════════════════════════════════════════════════════════ -->
    <transition name="slide-drawer">
      <div v-if="showDiagnosticDrawer" class="drawer-overlay" @click="showDiagnosticDrawer = false">
        <aside class="slide-drawer-panel" @click.stop>
          <div class="drawer-header">
            <div class="drawer-title-area">
              <div class="drawer-title-row">
                <h3>📋 专家诊断报告总台账</h3>
                <span
                  class="drawer-health-badge"
                  :class="{
                    'badge-pass': healthStatus === '达标',
                    'badge-warn': healthStatus === '待完善',
                    'badge-danger': healthStatus === '存在重大缺陷',
                  }"
                >
                  {{ healthStatus }}
                </span>
              </div>
              <span class="drawer-subtitle">
                依据国家发改委与行业工程编制规程要求进行全维体检
              </span>
            </div>
            <button class="drawer-close-btn" @click="showDiagnosticDrawer = false">✕</button>
          </div>

          <!-- 诊断报告综述卡片 -->
          <div class="drawer-summary-card">
            <div class="summary-header">
              <span class="summary-tag">💡 总体评估结论</span>
              <span class="summary-rate">达标度 <strong>{{ complianceRate }}%</strong></span>
            </div>
            <p class="summary-content">
              {{
                projectStore.fullBookReview?.summary ||
                "全书共 " +
                  totalChapters +
                  " 章。暂未运行全书专家审阅，点击下方按钮可一键生成全维度合规与数据自洽诊断报告。"
              }}
            </p>
            <div class="summary-actions">
              <button
                class="btn btn-primary btn-sm btn-block"
                :disabled="projectStore.batchReviewing"
                @click="handleRunFullBookReview(true)"
                title="重新运行全书审阅（覆盖所有章节）"
              >
                🚀 重新运行全书审阅
              </button>
              <button
                class="btn btn-warning btn-sm btn-block"
                :disabled="projectStore.revisingSeq !== null || completedChaptersCount === 0"
                @click="handleDirectRevision(activeChapterSeq || 1)"
                title="代入当前选定章节的专家诊断建议直接触发就地修订"
              >
                ⚡ 代入本章建议并一键修订
              </button>
            </div>
          </div>

          <!-- 抽屉子标签页切换 -->
          <div class="drawer-subtabs-nav">
            <button
              class="subtab-btn"
              :class="{ active: diagnosticTab === 'issues' }"
              @click="diagnosticTab = 'issues'"
            >
              ⚠️ 问题清单 ({{ allIssues.length }})
            </button>
            <button
              class="subtab-btn"
              :class="{ active: diagnosticTab === 'numerical' }"
              @click="diagnosticTab = 'numerical'"
            >
              📐 数值核验 ({{ allNumericalChecks.length }})
            </button>
            <button
              class="subtab-btn"
              :class="{ active: diagnosticTab === 'gaps' }"
              @click="diagnosticTab = 'gaps'"
            >
              📑 缺失资料 ({{ allDataGaps.length }})
            </button>
            <button
              class="subtab-btn"
              :class="{ active: diagnosticTab === 'evals' }"
              @click="diagnosticTab = 'evals'"
            >
              📊 各章评价 ({{ totalChapters }})
            </button>
            <button
              class="subtab-btn"
              :class="{ active: diagnosticTab === 'suggestions' }"
              @click="diagnosticTab = 'suggestions'"
            >
              💡 综合建议
            </button>
          </div>

          <!-- 抽屉滚动内容区 -->
          <div class="drawer-scroll-body">
            <!-- 1. 问题清单 -->
            <div v-if="diagnosticTab === 'issues'" class="tab-pane issues-pane">
              <div v-if="allIssues.length > 0" class="issues-list">
                <div
                  v-for="(issue, idx) in allIssues"
                  :key="idx"
                  :id="`issue-card-${issue.id || ('idx-' + idx)}`"
                  :data-issue-card-id="issue.id"
                  :data-chapter-seq="issue.chapterSeq"
                  class="issue-card"
                  :class="`severity-${issue.severity || 'warning'}`"
                >
                  <div class="issue-card-top">
                    <span class="severity-pill">{{
                      issue.severity === 'danger' || issue.severity === 'high'
                        ? '🔴 高风险'
                        : issue.severity === 'warning'
                        ? '🟡 警告'
                        : '🔵 优化提示'
                    }}</span>
                    <span v-if="issue.category" class="category-pill">{{ issue.category }}</span>
                    <span class="location-pill">{{ issue.location || '全书' }}</span>
                  </div>

                  <div class="issue-message-text">
                    {{ issue.message }}
                  </div>

                  <div v-if="issue.suggestion" class="issue-suggestion-box">
                    <strong>专家建议：</strong>{{ issue.suggestion }}
                  </div>

                  <div class="issue-actions-row">
                    <button
                      class="btn-text-link"
                      @click="locateIssueInCanvas(issue)"
                    >
                      🎯 点击定位正文段落 &rarr;
                    </button>
                    <button
                      class="btn-text-link link-primary"
                      :disabled="projectStore.revisingSeq !== null"
                      @click="handleDirectRevision(issue.chapterSeq || activeChapterSeq || 1, issue.suggestion || issue.message)"
                    >
                      ⚡ 代入建议并一键修订
                    </button>
                  </div>
                </div>
              </div>

              <div v-else class="drawer-empty-state">
                <span class="empty-icon">🎉</span>
                <p class="empty-title">全书未发现合规与数据自洽缺陷</p>
                <p class="empty-desc">各项工程论述、技术参数与发改委编制规程吻合良好。</p>
              </div>
            </div>

            <!-- 2. 跨章数值核验表 -->
            <div v-if="diagnosticTab === 'numerical'" class="tab-pane numerical-pane">
              <div v-if="allNumericalChecks.length > 0" class="numerical-table-wrapper">
                <table class="drawer-data-table">
                  <thead>
                    <tr>
                      <th style="width: 100px;">参数/指标</th>
                      <th>提取数值</th>
                      <th>核验结论</th>
                      <th>跨章说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(nc, idx) in allNumericalChecks" :key="idx">
                      <td><strong>{{ nc.parameter }}</strong></td>
                      <td><code>{{ nc.extracted_value }}</code></td>
                      <td>
                        <span
                          class="status-pill"
                          :class="nc.status === 'normal' ? 'pill-success' : 'pill-warning'"
                        >
                          {{ nc.status === 'normal' ? '✅ 自洽' : '⚠️ 需核验' }}
                        </span>
                      </td>
                      <td class="cell-note">{{ nc.note || '-' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div v-else class="drawer-empty-state">
                <span class="empty-icon">📏</span>
                <p class="empty-title">暂无数值核验数据</p>
                <p class="empty-desc">请点击上方「重新运行全书审阅」自动提取并勾稽全书数值。</p>
              </div>
            </div>

            <!-- 3. 缺失资料清单 -->
            <div v-if="diagnosticTab === 'gaps'" class="tab-pane gaps-pane">
              <div v-if="allDataGaps.length > 0" class="gaps-list">
                <div v-for="(gap, idx) in allDataGaps" :key="idx" class="gap-card">
                  <div class="gap-top">
                    <span class="gap-icon">📄</span>
                    <strong class="gap-title">{{ gap.gap }}</strong>
                  </div>
                  <div class="gap-meta">
                    <span>关联章节：{{ gap.chapterTitle || `第 ${gap.chapterSeq} 章` }}</span>
                  </div>
                  <div class="gap-action">
                    <button
                      class="btn btn-outline btn-xs"
                      :disabled="projectStore.revisingSeq !== null"
                      @click="handleDirectRevision(gap.chapterSeq || activeChapterSeq || 1, `依据规程要求，在正文中补充说明【${gap.gap}】的前置审批与支撑依据。`)"
                    >
                      ⚡ 代入建议并一键修订
                    </button>
                  </div>
                </div>
              </div>

              <div v-else class="drawer-empty-state">
                <span class="empty-icon">📁</span>
                <p class="empty-title">全书前置要件与底稿支撑完整</p>
                <p class="empty-desc">未发现缺失的关键审批批复与附表资料。</p>
              </div>
            </div>

            <!-- 4. 各章评价 -->
            <div v-if="diagnosticTab === 'evals'" class="tab-pane evals-pane">
              <div class="chapter-evals-grid">
                <div
                  v-for="ch in projectStore.outlineChapters"
                  :key="ch.seq"
                  class="eval-card"
                  @click="scrollToChapter(ch.seq)"
                >
                  <div class="eval-card-header">
                    <span class="eval-seq">第 {{ ch.seq }} 章</span>
                    <h5 class="eval-title">{{ ch.title }}</h5>
                    <span
                      class="eval-status"
                      :class="`status-${projectStore.chapterReviews[ch.seq]?.status || 'idle'}`"
                    >
                      {{ projectStore.chapterReviews[ch.seq]?.status || '未审阅' }}
                    </span>
                  </div>
                  <div class="eval-card-body">
                    <p class="eval-summary">
                      {{ projectStore.chapterReviews[ch.seq]?.summary || '暂无单章诊断小结' }}
                    </p>
                  </div>
                  <div class="eval-card-footer">
                    <span>字数：{{ countContentChars(projectStore.chapters[ch.seq] || '') }} (正文)</span>
                    <span>问题：{{ chapterIssuesCount[ch.seq] || 0 }} 处</span>
                    <button
                      class="btn btn-outline btn-xs"
                      @click.stop="handleRunSingleReview(ch.seq)"
                      title="针对本章单独运行专家体检"
                    >
                      🔍 重新审阅
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 5. 综合建议 -->
            <div v-if="diagnosticTab === 'suggestions'" class="tab-pane suggestions-pane">
              <div class="suggestions-list">
                <div
                  v-for="(sugg, idx) in projectStore.fullBookReview?.general_suggestions || [
                    '1. 严格对照国家发改委与行业工程编制规程，核对前后章节投资估算与建设规模数据自洽性；',
                    '2. 补充完善缺失的附表、附图与前置审批支撑性底稿；',
                    '3. 针对高亮批注与数据疑点小节进行专项润色与 AI 修订。',
                  ]"
                  :key="idx"
                  class="sugg-card"
                >
                  <span class="sugg-bullet">📌</span>
                  <p class="sugg-text">{{ sugg }}</p>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </transition>

    <!-- ═════════════════════════════════════════════════════════ -->
    <!-- 全高右侧抽屉 2: 📚 全书参考资料 (Slide-over Drawer, 540px) -->
    <!-- ═════════════════════════════════════════════════════════ -->
    <transition name="slide-drawer">
      <div v-if="showRefDrawer" class="drawer-overlay" @click="showRefDrawer = false">
        <aside class="slide-drawer-panel" @click.stop>
          <div class="drawer-header">
            <div class="drawer-title-area">
              <div class="drawer-title-row">
                <h3>📚 全书参考资料与行业规程台账</h3>
              </div>
              <span class="drawer-subtitle">
                共命中 {{ allReferences.length }} 份底稿与规程，全书累计引用 {{ totalRefCitations }} 处
              </span>
            </div>
            <button class="drawer-close-btn" @click="showRefDrawer = false">✕</button>
          </div>

          <!-- 资料分类过滤 Tab -->
          <div class="drawer-subtabs-nav">
            <button
              class="subtab-btn"
              :class="{ active: refFilterType === 'all' }"
              @click="refFilterType = 'all'"
            >
              全部 ({{ allReferences.length }})
            </button>
            <button
              class="subtab-btn"
              :class="{ active: refFilterType === 'material' }"
              @click="refFilterType = 'material'"
            >
              📄 底稿文件
            </button>
            <button
              class="subtab-btn"
              :class="{ active: refFilterType === 'standard' }"
              @click="refFilterType = 'standard'"
            >
              ⚖️ 标准规程
            </button>
            <button
              class="subtab-btn"
              :class="{ active: refFilterType === 'web' }"
              @click="refFilterType = 'web'"
            >
              🌐 网络检索
            </button>
          </div>

          <div class="drawer-scroll-body">
            <div v-if="filteredReferences.length > 0" class="ref-items-list">
              <div
                v-for="(refItem, rIdx) in filteredReferences"
                :key="rIdx"
                class="ref-card-item"
              >
                <div class="ref-card-top">
                  <span class="ref-type-badge" :class="`type-${refItem.type}`">
                    {{ refItem.typeLabel }}
                  </span>
                  <span class="ref-count-badge">引用 {{ refItem.count }} 次</span>
                </div>
                <div class="ref-card-title">{{ refItem.title }}</div>
                <div v-if="refItem.url" class="ref-card-link">
                  <a :href="refItem.url" target="_blank" rel="noopener noreferrer" class="ref-external-link">
                    🔗 {{ refItem.url }}
                  </a>
                </div>
                <div class="ref-card-raw"><code>{{ refItem.raw }}</code></div>
              </div>
            </div>

            <div v-else class="drawer-empty-state">
              <span class="empty-icon">📂</span>
              <p class="empty-title">暂无引用的底稿或标准规程</p>
              <p class="empty-desc">
                您可在正文中嵌入 <code>【源:文件名.docx】</code> 或 <code>【标:规程名】</code>，系统将在此自动汇总。
              </p>
            </div>
          </div>
        </aside>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.step4-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 14px 18px;
  background: #f8fafc;
  box-sizing: border-box;
  overflow: hidden;
  gap: 12px;
}

.alert-banner {
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  flex-shrink: 0;
  transition: all 0.2s ease;
}
.alert-banner.success {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #bbf7d0;
}
.alert-banner.error {
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}
.alert-banner.info {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #dbeafe;
}

.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

/* ═════════════════════════════════════════════════════════ */
/* 顶部工作台状态与全局操作区 (Header Toolbar) */
/* ═════════════════════════════════════════════════════════ */
.review-workbench-header {
  padding: 10px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-shrink: 0;
}

.header-left-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.project-title-box {
  display: flex;
  align-items: center;
  gap: 8px;
}
.proj-badge {
  background: #f1f5f9;
  color: #475569;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.workbench-main-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.health-badges-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.health-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid transparent;
}
.health-badge.health-passed {
  background: #ecfdf5;
  color: #047857;
  border-color: #a7f3d0;
}
.health-badge.health-warning {
  background: #fffbeb;
  color: #b45309;
  border-color: #fde68a;
}
.health-badge.health-danger {
  background: #fef2f2;
  color: #b91c1c;
  border-color: #fecaca;
}
.health-badge.health-pending {
  background: #f8fafc;
  color: #64748b;
  border-color: #e2e8f0;
}
.health-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}
.compliance-pct {
  font-size: 11px;
  opacity: 0.85;
  margin-left: 2px;
}

.meta-stat-pills {
  display: flex;
  align-items: center;
  gap: 6px;
}
.meta-pill {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: #475569;
}
.meta-pill strong {
  color: #0f172a;
}
.meta-pill.meta-pill-unwritten {
  color: #64748b;
  background: #f1f5f9;
  border-color: #cbd5e1;
}

/* 顶部中间 Tab */
.header-center-tabs {
  display: flex;
  justify-content: center;
}
.view-mode-tabs {
  display: flex;
  background: #f1f5f9;
  padding: 3px;
  border-radius: 8px;
  gap: 3px;
}
.tab-btn {
  border: none;
  background: transparent;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s ease;
}
.tab-btn:hover {
  color: #0f172a;
}
.tab-btn.active {
  background: #fff;
  color: #2563eb;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
.active-diff-indicator {
  color: #ef4444;
  font-size: 10px;
}

/* 顶部右侧按钮 */
.header-right-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn-review-hero {
  font-weight: 600;
  font-size: 12px;
  padding: 6px 14px;
}

.drawer-trigger-group {
  display: flex;
  align-items: center;
  gap: 6px;
}
.drawer-btn {
  font-size: 12px;
  padding: 5px 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.drawer-btn.active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
}
.count-badge {
  background: #f1f5f9;
  color: #475569;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 10px;
}
.count-badge.has-issues {
  background: #fee2e2;
  color: #b91c1c;
}

/* ═════════════════════════════════════════════════════════ */
/* 审阅心跳指示栏 (Heartbeat Bar) */
/* ═════════════════════════════════════════════════════════ */
.review-heartbeat-bar {
  padding: 10px 16px;
  background: linear-gradient(90deg, #eff6ff 0%, #f0fdf4 100%);
  border: 1px solid #bfdbfe;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.heartbeat-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.hb-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.radar-pulse {
  width: 10px;
  height: 10px;
  background: #3b82f6;
  border-radius: 50%;
  box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
  animation: pulse-ring 1.5s infinite;
  flex-shrink: 0;
}
@keyframes pulse-ring {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 8px rgba(59, 130, 246, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
  }
}
.hb-title-box {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.hb-main-title strong {
  font-size: 13px;
  color: #1e3a8a;
  line-height: 1.4;
}
.hb-desc {
  font-size: 11px;
  color: #3b82f6;
}
.hb-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.btn-stop-review {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 4px;
}

/* 审阅实时思考推演窗 */
.review-thought-stream-wrapper {
  margin-top: 2px;
}
.review-thought-card {
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  overflow: hidden;
  background: #ffffff;
}
.review-thought-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: #f8fafc;
  cursor: pointer;
  user-select: none;
  border-bottom: 1px solid #e2e8f0;
  transition: background 0.15s;
}
.review-thought-header:hover {
  background: #f1f5f9;
}
.review-thought-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
}
.review-thought-icon {
  font-size: 13px;
}
.thinking-wave {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-left: 4px;
}
.thinking-wave .dot {
  width: 4px;
  height: 4px;
  background: #3b82f6;
  border-radius: 50%;
  animation: wave-jump 1.2s infinite ease-in-out;
}
.thinking-wave .dot:nth-child(2) {
  animation-delay: 0.2s;
}
.thinking-wave .dot:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes wave-jump {
  0%, 80%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  40% {
    transform: translateY(-3px);
    opacity: 1;
  }
}
.review-thought-toggle-btn {
  background: none;
  border: none;
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
  cursor: pointer;
}
.review-thought-body {
  padding: 8px 12px;
  max-height: 140px;
  overflow-y: auto;
  background: #ffffff;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11.5px;
  line-height: 1.55;
  color: #334155;
}
.review-thought-body pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.review-thought-placeholder {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #64748b;
  font-size: 11.5px;
}
.placeholder-spinner {
  display: inline-block;
  animation: pulse-icon 1.5s infinite;
}
@keyframes pulse-icon {
  0%, 100% { opacity: 0.6; transform: scale(0.95); }
  50% { opacity: 1; transform: scale(1.05); }
}

/* 修订心跳与进度条 (轻量内联) */
.revision-heartbeat-bar {
  padding: 10px 16px;
  background: linear-gradient(90deg, #fffbeb 0%, #fef3c7 100%);
  border: 1px solid #fde68a;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.revision-heartbeat-bar .radar-pulse {
  background: #d97706;
  box-shadow: 0 0 0 0 rgba(217, 119, 6, 0.7);
  animation: pulse-ring-amber 1.5s infinite;
}
@keyframes pulse-ring-amber {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(217, 119, 6, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 8px rgba(217, 119, 6, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(217, 119, 6, 0);
  }
}
.revision-heartbeat-bar .hb-main-title strong {
  font-size: 13px;
  color: #92400e;
  line-height: 1.4;
}
.revision-heartbeat-bar .hb-desc {
  font-size: 11px;
  color: #b45309;
}
.hb-stepper-compact {
  display: flex;
  align-items: center;
  gap: 8px;
}
.hb-stepper-compact .stepper-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #94a3b8;
}
.hb-stepper-compact .stepper-item.active {
  color: #d97706;
  font-weight: 600;
}
.hb-stepper-compact .stepper-item.completed {
  color: #15803d;
}
.hb-stepper-compact .stepper-circle {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  background: #e2e8f0;
  color: #64748b;
}
.hb-stepper-compact .stepper-item.active .stepper-circle {
  background: #f59e0b;
  color: #fff;
}
.hb-stepper-compact .stepper-item.completed .stepper-circle {
  background: #22c55e;
  color: #fff;
}

/* ═════════════════════════════════════════════════════════ */
/* 主体工作台：双栏满屏布局 */
/* ═════════════════════════════════════════════════════════ */
.workbench-main-layout {
  display: flex;
  gap: 14px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* 左侧栏：全书多级标题导航 (宽度调整为 320px) */
.sidebar-nav-panel {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sidebar-header {
  padding: 14px 16px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #f8fafc;
}
.header-titles {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-titles h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}
.proj-badge {
  background: #e0e7ff;
  color: #4338ca;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.stats-overview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 6px 12px;
}
.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.stat-label {
  font-size: 11px;
  color: #64748b;
}
.stat-val {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}
.stat-success {
  color: #16a34a;
}
.stat-divider {
  width: 1px;
  height: 20px;
  background: #e2e8f0;
}

/* 推荐写作顺序流程胶囊指示 (100% 对齐 Step 3) */
.writing-order-box {
  background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.order-box-header {
  display: flex;
  align-items: center;
  gap: 5px;
}
.order-icon {
  font-size: 13px;
}
.order-title {
  font-size: 11.5px;
  font-weight: 600;
  color: #1e40af;
}
.order-flow-chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}
.order-node-wrap {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.order-chip {
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.15s ease;
}
.order-chip:hover {
  border-color: #3b82f6;
  color: #1d4ed8;
}
.order-chip.active {
  background: #3b82f6;
  color: #ffffff;
  border-color: #2563eb;
  font-weight: 600;
}
.order-chip.completed:not(.active) {
  background: #dcfce7;
  color: #15803d;
  border-color: #86efac;
}
.order-chip.warning:not(.active) {
  background: #fef3c7;
  color: #b45309;
  border-color: #fde68a;
}
.flow-arrow {
  font-size: 9px;
  color: #94a3b8;
}

.outline-tree-scrollable {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 transparent;
}
.outline-tree-scrollable::-webkit-scrollbar {
  width: 5px;
}
.outline-tree-scrollable::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}
.outline-tree-scrollable::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.empty-outline-tip {
  padding: 20px;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
}

/* 章节树节点：平铺一体化目录树（Flat Unified Tree），无独立卡片盒子 */
.chapter-tree-node {
  border: none;
  border-radius: 6px;
  background: transparent;
  overflow: hidden;
  transition: all 0.15s ease;
}
.chapter-tree-node.is-active {
  background: rgba(59, 130, 246, 0.06);
}
.chapter-tree-node.is-unwritten-node {
  opacity: 0.78;
}
.chapter-tree-node.is-unwritten-node:hover,
.chapter-tree-node.is-active.is-unwritten-node {
  opacity: 1;
}
.chapter-tree-node.is-unwritten-node .ch-title-text {
  color: #64748b;
}
.chapter-tree-node.has-warning {
  /* 平铺树下保持轻量提示 */
}

.chapter-node-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 8px;
  cursor: pointer;
  user-select: none;
  border-radius: 6px;
  background: transparent;
  transition: background 0.15s ease;
}
.chapter-node-row:hover {
  background: #f1f5f9;
}
.chapter-tree-node.is-active .chapter-node-row {
  background: #eff6ff;
}
.row-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.ch-seq-tag {
  background: #f1f5f9;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.chapter-tree-node.is-active .ch-seq-tag {
  background: #3b82f6;
  color: #fff;
}
.chapter-tree-node.is-completed:not(.is-active) .ch-seq-tag {
  background: #dcfce7;
  color: #15803d;
}
.ch-title-text {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
  white-space: normal;
  word-break: break-word;
  line-height: 1.35;
}

.row-right {
  display: flex;
  align-items: center;
  gap: 6px;
}
.status-pill {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 10px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  white-space: nowrap;
}
.status-pill.idle {
  background: #f1f5f9;
  color: #64748b;
}
.status-pill.writing {
  background: #fef3c7;
  color: #b45309;
}
.status-pill.completed {
  background: #dcfce7;
  color: #15803d;
}
.status-pill.error {
  background: #fee2e2;
  color: #b91c1c;
}

.badge-unwritten {
  font-size: 10px;
  font-weight: 600;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 1px 6px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}
.warning-badge-pill {
  font-size: 10px;
  font-weight: 700;
  color: #b45309;
  background: #fef3c7;
  border: 1px solid #fde68a;
  padding: 1px 5px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}
.pass-dot {
  font-size: 11px;
  color: #10b981;
  font-weight: 700;
}
.collapse-toggle-icon {
  background: transparent;
  border: none;
  font-size: 9px;
  color: #94a3b8;
  cursor: pointer;
  padding: 2px 4px;
}
.collapse-toggle-icon:hover {
  color: #475569;
}

/* 子标题层级：平铺多级目录，由外层单一全局垂直滚动条滚动 */
.subheadings-subtree {
  padding: 2px 0 4px 0;
  background: transparent;
  border-top: none;
}
.subheading-item-row {
  padding: 4px 8px 4px 20px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 11.5px;
  color: #64748b;
  border-radius: 4px;
  transition: all 0.12s ease;
}
.subheading-item-row:hover {
  background: #f1f5f9;
  color: #0f172a;
}
.subheading-item-row.level-3 {
  padding-left: 30px;
}
.subheading-item-row.level-4 {
  padding-left: 40px;
}
.subheading-item-row.is-active-heading {
  color: #2563eb;
  font-weight: 600;
  background: #eff6ff;
}
.sub-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sub-issue-badge {
  font-size: 9.5px;
  font-weight: 700;
  color: #b45309;
  background: #fef3c7;
  border: 1px solid #fde68a;
  padding: 0 4px;
  border-radius: 8px;
  margin-left: auto;
  flex-shrink: 0;
  white-space: nowrap;
}

/* ═════════════════════════════════════════════════════════ */
/* 右侧主画布 (100% 满屏可视高度) */
/* ═════════════════════════════════════════════════════════ */
.main-canvas-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* 模式 1: 排版正文视图 */
.canvas-rich-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.rich-view-header-bar {
  padding: 8px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.spec-label-box {
  display: flex;
  align-items: center;
  gap: 8px;
}
.spec-tag {
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
}
.spec-sub {
  font-size: 11px;
  color: #64748b;
}

.full-book-scroll-canvas {
  flex: 1;
  overflow-y: auto;
  padding: 24px 36px;
  background: #ffffff;
}

.full-book-chapter-block {
  margin-bottom: 28px;
  scroll-margin-top: 16px;
}

/* 全书连贯预览标准化章标题栏 */
.chapter-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  margin-bottom: 12px;
}
.chapter-block-header .header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.chapter-block-header .ch-badge {
  background: #3b82f6;
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
  flex-shrink: 0;
}
.chapter-block-header .ch-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}
.chapter-block-header .ch-word-tag {
  font-size: 11.5px;
  color: #64748b;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}
.chapter-block-header .ch-word-tag.tag-unwritten {
  color: #94a3b8;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  font-style: normal;
}

/* 10.5pt 工程咨询出版级排版规范 */
.spec-typography {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB",
    "Microsoft YaHei", sans-serif;
  font-size: 14px;
  line-height: 1.8;
  color: #1e293b;
}
.spec-typography h1,
.spec-typography h2,
.spec-typography h3,
.spec-typography h4 {
  color: #0f172a;
  margin-top: 20px;
  margin-bottom: 10px;
  font-weight: 700;
}
.spec-typography h1 {
  font-size: 20px;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 6px;
}
.spec-typography h2 {
  font-size: 17px;
}
.spec-typography h3 {
  font-size: 15px;
}
.spec-typography h4 {
  font-size: 14px;
}
.spec-typography p {
  margin-bottom: 12px;
  text-indent: 2em;
}
.spec-typography table {
  width: 100%;
  border-collapse: collapse;
  margin: 18px 0;
  font-size: 10.5pt;
  border-top: 2px solid #334155;
  border-bottom: 2px solid #334155;
  border-left: none;
  border-right: none;
}
.spec-typography th,
.spec-typography td {
  border: none;
  padding: 8px 12px;
  text-align: left;
  font-size: 10.5pt;
  line-height: 1.5;
}
.spec-typography th {
  background: #f8fafc;
  font-weight: 600;
  color: #1e293b;
  border-bottom: 1px solid #475569;
}
.spec-typography tr:hover {
  background: #f8fafc;
}

.rich-rendered-editor {
  min-height: 120px;
  padding: 10px 4px;
  outline: none;
  border-radius: 6px;
}
.rich-rendered-editor:focus {
  background: #fafafa;
}
.rich-rendered-editor:empty:before {
  content: attr(data-placeholder);
  color: #94a3b8;
  font-style: italic;
  font-size: 13px;
  display: block;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 6px;
}

/* 未编写章节占位引导卡片 */
.unwritten-chapter-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 32px 24px;
  background: #f8fafc;
  border: 1.5px dashed #cbd5e1;
  border-radius: 8px;
  margin: 8px 0;
  cursor: text;
  user-select: none;
  transition: all 0.2s ease;
}
.unwritten-chapter-placeholder:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
}
.unwritten-icon {
  font-size: 28px;
  margin-bottom: 10px;
  line-height: 1;
}
.unwritten-title {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 8px;
}
.unwritten-desc {
  font-size: 13px;
  color: #64748b;
  max-width: 580px;
  line-height: 1.6;
}

/* Step 4 正文审阅问题持久化高亮与批注标记 */
.review-issue-highlight {
  cursor: pointer;
  padding: 1px 4px;
  border-radius: 3px;
  transition: all 0.2s ease;
  font-weight: 500;
  display: inline;
}
.review-issue-highlight.severity-warning {
  background: #fef08a;
  border-bottom: 2px wavy #eab308;
  color: #713f12;
}
.review-issue-highlight.severity-warning:hover {
  background: #fde047;
}
.review-issue-highlight.severity-error,
.review-issue-highlight.severity-danger,
.review-issue-highlight.severity-high {
  background: #fecaca;
  border-bottom: 2px wavy #ef4444;
  color: #991b1b;
}
.review-issue-highlight.severity-error:hover,
.review-issue-highlight.severity-danger:hover,
.review-issue-highlight.severity-high:hover {
  background: #fca5a5;
}
.review-issue-highlight.severity-suggestion,
.review-issue-highlight.severity-info {
  background: #e0e7ff;
  border-bottom: 2px wavy #6366f1;
  color: #3730a3;
}
.review-issue-highlight.severity-suggestion:hover,
.review-issue-highlight.severity-info:hover {
  background: #c7d2fe;
}
.issue-card.issue-card-focused {
  outline: 2px solid #3b82f6;
  box-shadow: 0 0 14px rgba(59, 130, 246, 0.45);
  transform: scale(1.01);
  transition: all 0.2s ease;
}

/* 呼吸高亮动画 */
.heading-anchor-pulse {
  animation: anchor-pulse 1.5s ease-out;
}
@keyframes anchor-pulse {
  0% {
    background-color: #fef08a;
    box-shadow: 0 0 0 4px #fde047;
  }
  100% {
    background-color: transparent;
    box-shadow: 0 0 0 0 transparent;
  }
}

/* 审阅问题精准定位句子级呼吸波纹高亮 (持续 2.5s) */
.issue-highlight-pulse {
  animation: issuePulse 2.5s ease-out forwards;
  border-radius: 4px;
}
@keyframes issuePulse {
  0% {
    background-color: rgba(251, 191, 36, 0.6);
    box-shadow: 0 0 0 6px rgba(251, 191, 36, 0.4);
  }
  30% {
    background-color: rgba(251, 191, 36, 0.45);
    box-shadow: 0 0 0 8px rgba(251, 191, 36, 0.25);
  }
  65% {
    background-color: rgba(251, 191, 36, 0.25);
    box-shadow: 0 0 0 4px rgba(251, 191, 36, 0.15);
  }
  100% {
    background-color: transparent;
    box-shadow: 0 0 0 0 transparent;
  }
}



/* 模式 2: Diff 全宽单栏内联视图 */
.canvas-diff-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.diff-sticky-header {
  padding: 10px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-shrink: 0;
}
.diff-header-info {
  display: flex;
  align-items: center;
}
.diff-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.diff-main-badge {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}
.diff-ch-tag {
  background: #eff6ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
}

.diff-header-stats {
  display: flex;
  align-items: center;
  gap: 8px;
}
.diff-stat-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 4px;
}
.pill-added {
  background: #dcfce7;
  color: #15803d;
}
.pill-removed {
  background: #fee2e2;
  color: #b91c1c;
}
.pill-unchanged {
  background: #f1f5f9;
  color: #64748b;
}

.diff-header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.btn-danger-text {
  color: #b91c1c;
}

.diff-inline-scrollable {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background: #fff;
}
.diff-lines-wrapper {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
}
.diff-line-row {
  display: flex;
  align-items: flex-start;
  min-height: 22px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.4);
}
.diff-line-row.diff-line-added {
  background: #f0fdf4;
}
.diff-line-row.diff-line-removed {
  background: #fef2f2;
}

.diff-line-num {
  width: 44px;
  padding: 2px 6px;
  text-align: right;
  font-size: 11px;
  color: #94a3b8;
  user-select: none;
}
.diff-line-sign {
  width: 20px;
  text-align: center;
  font-weight: 700;
  user-select: none;
}
.diff-line-added .diff-line-sign {
  color: #16a34a;
}
.diff-line-removed .diff-line-sign {
  color: #dc2626;
}

.diff-line-content {
  flex: 1;
  padding: 2px 8px;
  white-space: pre-wrap;
  word-break: break-all;
}
.diff-line-added ins {
  background: #bbf7d0;
  text-decoration: none;
}
.diff-line-removed s {
  background: #fecaca;
  color: #991b1b;
}

.diff-empty-placeholder {
  margin: 40px auto;
  max-width: 460px;
  padding: 32px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.diff-empty-placeholder .empty-icon {
  font-size: 32px;
}

/* 模式 3: Markdown 源码视图 */
.canvas-source-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.source-view-toolbar {
  padding: 8px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.source-info {
  font-size: 12px;
  color: #475569;
}
.source-divider {
  margin: 0 6px;
  color: #cbd5e1;
}

.source-editor-scrollable {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.source-chapter-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  background: #fafafa;
}
.source-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}
.source-seq {
  font-weight: 700;
  color: #2563eb;
}
.source-title {
  font-weight: 600;
  color: #0f172a;
}
.source-len {
  margin-left: auto;
  color: #64748b;
  font-size: 11px;
}
.source-textarea {
  width: 100%;
  min-height: 160px;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 10px;
  box-sizing: border-box;
  resize: vertical;
}

/* 底部步骤向导 */
.workbench-footer-nav {
  padding: 10px 16px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.footer-center-summary {
  font-size: 12px;
  color: #475569;
}
.footer-divider {
  margin: 0 8px;
  color: #cbd5e1;
}

/* ═════════════════════════════════════════════════════════ */
/* 全高右侧抽屉 (Slide-over Drawer, 540px) */
/* ═════════════════════════════════════════════════════════ */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(2px);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}
.slide-drawer-panel {
  width: 540px;
  max-width: 90vw;
  height: 100vh;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.15);
  animation: slide-in-right 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes slide-in-right {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

.drawer-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  background: #f8fafc;
}
.drawer-title-area {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.drawer-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.drawer-title-row h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}
.drawer-health-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}
.badge-pass {
  background: #dcfce7;
  color: #15803d;
}
.badge-warn {
  background: #fef3c7;
  color: #b45309;
}
.badge-danger {
  background: #fee2e2;
  color: #b91c1c;
}
.drawer-subtitle {
  font-size: 12px;
  color: #64748b;
}
.drawer-close-btn {
  background: transparent;
  border: none;
  font-size: 16px;
  color: #64748b;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}
.drawer-close-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.drawer-summary-card {
  margin: 14px 20px 0 20px;
  padding: 12px 14px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
}
.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.summary-tag {
  font-size: 12px;
  font-weight: 700;
  color: #1e3a8a;
}
.summary-rate {
  font-size: 12px;
  color: #2563eb;
}
.summary-content {
  margin: 0 0 10px 0;
  font-size: 12px;
  line-height: 1.6;
  color: #1e293b;
}
.summary-actions .btn-block {
  width: 100%;
}

.drawer-subtabs-nav {
  display: flex;
  background: #f1f5f9;
  margin: 12px 20px 0 20px;
  padding: 3px;
  border-radius: 6px;
  gap: 2px;
}
.subtab-btn {
  flex: 1;
  border: none;
  background: transparent;
  padding: 6px 4px;
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}
.subtab-btn.active {
  background: #fff;
  color: #2563eb;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.drawer-scroll-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

/* 问题清单卡片 */
.issues-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.issue-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.issue-card.severity-danger {
  border-left: 4px solid #ef4444;
}
.issue-card.severity-warning {
  border-left: 4px solid #f59e0b;
}
.issue-card.severity-info {
  border-left: 4px solid #3b82f6;
}

.issue-card-top {
  display: flex;
  align-items: center;
  gap: 6px;
}
.severity-pill {
  font-size: 11px;
  font-weight: 700;
}
.category-pill {
  background: #f1f5f9;
  color: #475569;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
}
.location-pill {
  font-size: 11px;
  color: #64748b;
  margin-left: auto;
}
.issue-message-text {
  font-size: 13px;
  color: #0f172a;
  line-height: 1.5;
}
.issue-suggestion-box {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  color: #334155;
  line-height: 1.5;
}
.issue-actions-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}
.btn-text-link {
  background: transparent;
  border: none;
  color: #2563eb;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  padding: 0;
}
.btn-text-link:hover {
  text-decoration: underline;
}

/* 抽屉表格 */
.numerical-table-wrapper {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}
.drawer-data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.drawer-data-table th,
.drawer-data-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  text-align: left;
}
.drawer-data-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
}
.cell-note {
  font-size: 11px;
  color: #64748b;
}

/* 缺失资料卡片 */
.gaps-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.gap-card {
  border: 1px solid #fde68a;
  background: #fffbeb;
  border-radius: 6px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.gap-top {
  display: flex;
  align-items: center;
  gap: 6px;
}
.gap-icon {
  font-size: 14px;
}
.gap-title {
  font-size: 13px;
  color: #92400e;
}
.gap-meta {
  font-size: 11px;
  color: #b45309;
}
.gap-action {
  display: flex;
  justify-content: flex-end;
}

/* 各章评价网格 */
.chapter-evals-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.eval-card {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 10px;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s ease;
}
.eval-card:hover {
  border-color: #3b82f6;
  background: #f8fafc;
}
.eval-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.eval-seq {
  font-size: 11px;
  font-weight: 700;
  color: #2563eb;
}
.eval-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}
.eval-status {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
}
.eval-status.status-通过 {
  background: #dcfce7;
  color: #15803d;
}
.eval-status.status-需补充 {
  background: #fef3c7;
  color: #b45309;
}
.eval-summary {
  margin: 0;
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
}
.eval-card-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 6px;
  font-size: 11px;
  color: #94a3b8;
}

/* 综合建议 */
.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sugg-card {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}
.sugg-bullet {
  font-size: 14px;
}
.sugg-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #1e293b;
}

/* 参考资料列表 */
.ref-items-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ref-card-item {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 10px 12px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ref-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ref-type-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
}
.ref-type-badge.type-material {
  background: #eff6ff;
  color: #1d4ed8;
}
.ref-type-badge.type-standard {
  background: #ecfdf5;
  color: #047857;
}
.ref-type-badge.type-web {
  background: #fdf2f8;
  color: #9d174d;
}
.ref-count-badge {
  font-size: 11px;
  color: #64748b;
}
.ref-card-title {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}
.ref-card-link {
  font-size: 11px;
  word-break: break-all;
  margin: 2px 0;
}
.ref-external-link {
  color: #2563eb;
  text-decoration: underline;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.ref-external-link:hover {
  color: #1d4ed8;
}
.ref-card-raw code {
  font-size: 11px;
  color: #475569;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
}

.drawer-empty-state {
  text-align: center;
  padding: 40px 20px;
}
.drawer-empty-state .empty-icon {
  font-size: 32px;
}
.drawer-empty-state .empty-title {
  margin: 8px 0 4px 0;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}
.drawer-empty-state .empty-desc {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

/* 按钮通用 */
.btn {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
}
.btn-primary:hover {
  background: #1d4ed8;
}
.btn-secondary {
  background: #fff;
  border-color: #cbd5e1;
  color: #334155;
}
.btn-secondary:hover {
  background: #f1f5f9;
}
.btn-outline {
  background: #fff;
  border-color: #cbd5e1;
  color: #475569;
}
.btn-outline:hover {
  background: #f8fafc;
  color: #0f172a;
}
.btn-success {
  background: #16a34a;
  color: #fff;
}
.btn-success:hover {
  background: #15803d;
}
.btn-danger {
  background: #dc2626;
  color: #fff;
}
.btn-danger:hover {
  background: #b91c1c;
}
.btn-xs {
  padding: 3px 8px;
  font-size: 11px;
}
.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}
.btn-lg {
  padding: 8px 18px;
  font-size: 14px;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 审查模式切换胶囊样式 */
.review-mode-pills {
  display: flex;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 2px;
  border: 1px solid #e2e8f0;
  gap: 2px;
}
.mode-pill-btn {
  padding: 5px 10px;
  border-radius: 6px;
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}
.mode-pill-btn:hover {
  color: #1e293b;
}
.mode-pill-btn.active {
  background: #ffffff;
  color: #2563eb;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

/* 动画效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
