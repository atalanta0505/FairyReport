<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import * as engineApi from "../lib/engineApi";
import {
  countContentChars,
  escapeHtml,
  extractIssueCandidateKeys,
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
import DiagnosticLedgerDrawer from "./review/DiagnosticLedgerDrawer.vue";
import ReferenceLedgerDrawer from "./shared/ReferenceLedgerDrawer.vue";

const engine = useEngineStore();
const settings = useSettingsStore();
const projectStore = useProjectStore();

// ── 右侧全高抽屉 (Slide-over Drawer, 540px) ──
const showDiagnosticDrawer = ref<boolean>(false);
const showRefDrawer = ref<boolean>(false);
const diagnosticTab = ref<"issues" | "numerical" | "gaps">("issues");
const diagnosticFilterScope = ref<"current" | "all">("current");
const refFilterType = ref<"all" | "material" | "standard" | "web">("all");

// ── 章节与小节目录展开 / 定位状态 ──
const activeHeadingId = ref<string | null>(null);
const collapsedChapters = ref<Record<number, boolean>>({});

// ── 全局操作通知 ──
const actionMessage = ref<{ type: "success" | "error" | "info"; text: string } | null>(null);

// ── 审阅动态心跳与计时器 ──
const reviewElapsedSeconds = ref<number>(0);
const showReviewThoughtDetails = ref<boolean>(true);
let reviewTimer: ReturnType<typeof setInterval> | null = null;

// ── 修订动态心跳与计时器 ──
const revisionElapsedSeconds = ref<number>(0);
const revisionStageIndex = ref<number>(0);
const showRevisionThoughtDetails = ref<boolean>(true);
let revisionTimer: ReturnType<typeof setInterval> | null = null;

const revisionStages = [
  { id: "locate", title: "锁定问题段落", desc: "精准提取缺陷段落与专家修改建议" },
  { id: "refine", title: "局部智能重构", desc: "依据行业规程与编制规范深化工艺参数与方案" },
  { id: "replace", title: "原位无缝替换", desc: "原位更新排版正文，自动清除问题高亮" },
];

const saveDebounceTimers: Record<number, ReturnType<typeof setTimeout>> = {};
const editorCanvasRef = ref<HTMLElement | null>(null);
const reviewThoughtBodyRef = ref<HTMLElement | null>(null);
const revisionThoughtBodyRef = ref<HTMLElement | null>(null);

const outlineHeadings = computed(() => extractOutlineHeadings(projectStore.outlineMd));

function showMsg(text: string, type: "success" | "error" | "info" = "success") {
  actionMessage.value = { type, text };
  setTimeout(() => {
    if (actionMessage.value?.text === text) {
      actionMessage.value = null;
    }
  }, 4000);
}

function getLLMConfig(): engineApi.LLMConfig {
  if (!settings.llmKey) {
    throw new Error("请先在右上角「设置」中配置 LLM API Key");
  }
  return {
    api_key: settings.llmKey,
    base_url: settings.llmBaseUrl || "https://api.deepseek.com",
    model: settings.llmModel || "deepseek-flash",
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

// ── 基础计算属性 ──
const totalChapters = computed(() => projectStore.outlineChapters.length);

const currentChapter = computed(() => {
  return (
    projectStore.outlineChapters.find((c) => c.seq === projectStore.selectedChapterSeq) ||
    projectStore.outlineChapters[0]
  );
});

const currentChapterText = computed(() => {
  if (!currentChapter.value) return "";
  return projectStore.chapters[currentChapter.value.seq] || "";
});

const currentChapterWords = computed(() => {
  return countContentChars(currentChapterText.value);
});

function findIssueTextPosition(text: string, issue: engineApi.ReviewIssue): number {
  if (!text) return 999999;
  const candidates = extractIssueCandidateKeys(issue);
  for (const cand of candidates) {
    if (!cand || cand.length < 2) continue;
    const idx = text.indexOf(cand);
    if (idx !== -1) return idx;
    const cleanCand = cand.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, "");
    if (cleanCand.length >= 4) {
      const cleanText = text.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, "");
      const cleanIdx = cleanText.indexOf(cleanCand);
      if (cleanIdx !== -1) return cleanIdx;
    }
  }
  if (issue.location) {
    const locKey = issue.location.replace(/^(?:第[一二三四五六七八九十百零\d]+章|\d+(?:\.\d+)*)\s*/, "").trim();
    if (locKey.length >= 2) {
      const idx = text.indexOf(locKey);
      if (idx !== -1) return idx;
    }
  }
  return 999999;
}

const currentChapterReview = computed<engineApi.ExpertReviewResult | null>(() => {
  if (!currentChapter.value) return null;
  return projectStore.chapterReviews[currentChapter.value.seq] || null;
});

const currentChapterIssues = computed<engineApi.ReviewIssue[]>(() => {
  const issues = [...(currentChapterReview.value?.issues || [])];
  const text = currentChapterText.value;
  return issues.sort((a, b) => {
    const posA = findIssueTextPosition(text, a);
    const posB = findIssueTextPosition(text, b);
    return posA - posB;
  });
});

const currentChapterIssuesCount = computed(() => {
  return currentChapterIssues.value.length;
});

const currentChapterReferences = computed<ReferenceItem[]>(() => {
  return extractReferences(currentChapterText.value);
});

function isChapterWritten(seq: number): boolean {
  return (projectStore.chapters[seq] || "").trim().length > 0;
}

const completedChaptersCount = computed(() => {
  let count = 0;
  for (const ch of projectStore.outlineChapters) {
    if (isChapterWritten(ch.seq)) count++;
  }
  return count;
});

const reviewedChaptersCount = computed(() => {
  let count = 0;
  for (const ch of projectStore.outlineChapters) {
    if (projectStore.chapterReviews[ch.seq]) count++;
  }
  return count;
});

const totalWordCount = computed(() => {
  let total = 0;
  for (const ch of projectStore.outlineChapters) {
    const text = projectStore.chapters[ch.seq] || "";
    total += countContentChars(text);
  }
  return total;
});

const chapterSubheadings = computed<Record<number, SubHeading[]>>(() => {
  const map: Record<number, SubHeading[]> = {};
  for (const ch of projectStore.outlineChapters) {
    const text = projectStore.chapters[ch.seq];
    if (text && text.trim().length > 0) {
      map[ch.seq] = extractSubHeadings(text, ch.seq, outlineHeadings.value).filter((h) => h.level > 1);
    } else {
      map[ch.seq] = [];
    }
  }
  return map;
});

const allIssues = computed<engineApi.ReviewIssue[]>(() => {
  const list: engineApi.ReviewIssue[] = [];
  for (const ch of projectStore.outlineChapters) {
    const r = projectStore.chapterReviews[ch.seq];
    if (r?.issues) {
      for (const issue of r.issues) {
        list.push({
          ...issue,
          chapterSeq: ch.seq,
          chapterTitle: ch.title,
        });
      }
    }
  }
  return list;
});

const allNumericalChecks = computed<engineApi.NumericalCheckItem[]>(() => {
  const list: engineApi.NumericalCheckItem[] = [];
  for (const ch of projectStore.outlineChapters) {
    const r = projectStore.chapterReviews[ch.seq];
    if (r?.numerical_checks) {
      for (const check of r.numerical_checks) {
        list.push({
          ...check,
          chapterSeq: ch.seq,
          chapterTitle: ch.title,
        });
      }
    }
  }
  return list;
});

const allDataGaps = computed<any[]>(() => {
  const list: any[] = [];
  for (const ch of projectStore.outlineChapters) {
    const r = projectStore.chapterReviews[ch.seq];
    if (r?.data_gap_checklist) {
      for (const gap of r.data_gap_checklist) {
        if (typeof gap === "string") {
          list.push({ chapterSeq: ch.seq, chapterTitle: ch.title, gap });
        } else if (typeof gap === "object" && gap !== null) {
          list.push({ chapterSeq: ch.seq, chapterTitle: ch.title, ...(gap as Record<string, any>) });
        }
      }
    }
  }
  return list;
});

function getChapterTitle(seq: number): string {
  const found = projectStore.outlineChapters.find((c) => c.seq === seq);
  return found?.title || `第 ${seq} 章`;
}

// ── 章节展开折叠状态 ──
function isChapterCollapsed(seq: number): boolean {
  if (collapsedChapters.value[seq] !== undefined) {
    return collapsedChapters.value[seq];
  }
  // 默认规则：当前选中章节展开，其他章节折叠收起
  return seq !== projectStore.selectedChapterSeq;
}

function toggleChapterCollapse(seq: number, e?: Event) {
  if (e) e.stopPropagation();
  collapsedChapters.value[seq] = !isChapterCollapsed(seq);
}

function selectChapter(seq: number) {
  if (projectStore.selectedChapterSeq !== seq) {
    projectStore.selectedChapterSeq = seq;
    collapsedChapters.value[seq] = false;
    nextTick(() => {
      syncEditorContent();
    });
  } else {
    collapsedChapters.value[seq] = false;
  }
}

// ── Step 4 正文审阅问题高亮与批注标记 ──
function applyIssueHighlightsToHtml(html: string, seq: number): string {
  const chapterReview = projectStore.chapterReviews[seq];
  const issues = chapterReview?.issues || [];
  return highlightIssuesInHtml(html, issues, seq);
}

function getUnwrittenPlaceholderHtml(seq: number, title: string): string {
  return `<div class="unwritten-chapter-placeholder"><div class="unwritten-icon">📝</div><div class="unwritten-title">第 ${seq} 章《${escapeHtml(title)}》暂未生成正文</div><div class="unwritten-desc">本章节大纲已就绪，当前内容为空。您可直接在此处点击输入排版正文，或返回【步骤 3 报告写作】进行 AI 一键撰写。</div></div>`;
}

// ── 同步排版正文到单章 contenteditable DOM ──
function syncEditorContent() {
  if (!editorCanvasRef.value || !currentChapter.value) return;
  const seq = currentChapter.value.seq;
  const text = projectStore.chapters[seq] || "";
  if (!text.trim()) {
    editorCanvasRef.value.innerHTML = getUnwrittenPlaceholderHtml(seq, currentChapter.value.title);
  } else {
    const rawHtml = markdownToHtml(text, seq, outlineHeadings.value);
    editorCanvasRef.value.innerHTML = applyIssueHighlightsToHtml(rawHtml, seq);
  }
}

// ── 监听选中章节切换，同步排版内容 ──
watch(
  () => projectStore.selectedChapterSeq,
  () => {
    nextTick(() => {
      syncEditorContent();
    });
  },
);

// ── 监听当前章节内容外部更新 ──
watch(
  () => currentChapterText.value,
  () => {
    nextTick(() => {
      syncEditorContent();
    });
  },
);

watch(
  () => projectStore.currentStep,
  (step) => {
    if (step === 4) {
      ensureStep4State();
      nextTick(() => {
        syncEditorContent();
      });
    }
  },
);

watch(
  () => projectStore.reviewProgress?.thoughtText,
  () => {
    if (reviewThoughtBodyRef.value) {
      nextTick(() => {
        if (reviewThoughtBodyRef.value) {
          reviewThoughtBodyRef.value.scrollTop = reviewThoughtBodyRef.value.scrollHeight;
        }
      });
    }
  },
);

watch(
  () => projectStore.revisionProgress?.thoughtText,
  () => {
    if (revisionThoughtBodyRef.value) {
      nextTick(() => {
        if (revisionThoughtBodyRef.value) {
          revisionThoughtBodyRef.value.scrollTop = revisionThoughtBodyRef.value.scrollHeight;
        }
      });
    }
  },
);

// ── 排版正文就地输入与 300ms 自动落盘 ──
function onEditorInput(e: Event) {
  const target = e.target as HTMLElement | null;
  if (!target || !currentChapter.value) return;
  const seq = currentChapter.value.seq;
  const md = htmlToMarkdown(target.innerHTML);
  projectStore.chapters = {
    ...projectStore.chapters,
    [seq]: md,
  };

  if (saveDebounceTimers[seq]) {
    clearTimeout(saveDebounceTimers[seq]);
  }
  saveDebounceTimers[seq] = setTimeout(async () => {
    if (engine.baseUrl) {
      try {
        await projectStore.saveChapter(engine.baseUrl, seq, md);
      } catch {
        // non-fatal
      }
    }
  }, 300);
}

// ── 画布交互：高亮问题点击、Mermaid 视图切换、引用定位 ──
function handleEditorCanvasClick(e: MouseEvent) {
  const target = e.target as HTMLElement | null;
  if (!target) return;

  // 1. Mermaid 视图切换与复制代码
  const toggleBtn = target.closest(".mermaid-btn-toggle-view") as HTMLElement | null;
  if (toggleBtn) {
    e.stopPropagation();
    e.preventDefault();
    const container = toggleBtn.closest(".mermaid-container") as HTMLElement | null;
    if (container) {
      const svgWrapper = container.querySelector(".mermaid-svg-wrapper") as HTMLElement | null;
      const codeWrapper = container.querySelector(".mermaid-code-wrapper") as HTMLElement | null;
      const btnText = toggleBtn.querySelector(".btn-text");
      const btnIcon = toggleBtn.querySelector(".btn-icon");

      if (codeWrapper?.style.display === "none" || !codeWrapper?.style.display) {
        if (svgWrapper) svgWrapper.style.display = "none";
        if (codeWrapper) codeWrapper.style.display = "block";
        if (btnText) btnText.textContent = "图表视图";
        if (btnIcon) btnIcon.textContent = "📊";
      } else {
        if (svgWrapper) svgWrapper.style.display = "block";
        if (codeWrapper) codeWrapper.style.display = "none";
        if (btnText) btnText.textContent = "源码视图";
        if (btnIcon) btnIcon.textContent = "💻";
      }
    }
    return;
  }

  const copyBtn = target.closest(".mermaid-btn-copy") as HTMLElement | null;
  if (copyBtn) {
    e.stopPropagation();
    e.preventDefault();
    const code = copyBtn.getAttribute("data-code");
    if (code && navigator.clipboard) {
      navigator.clipboard.writeText(code);
      showMsg("已复制 Mermaid 流程图源码至剪贴板！", "success");
    }
    return;
  }

  // 2. 引用标记点击联动抽屉
  const refTag = target.closest(".inline-ref-tag") as HTMLElement | null;
  if (refTag) {
    e.stopPropagation();
    e.preventDefault();
    const title = refTag.getAttribute("data-ref-title");
    const type = refTag.getAttribute("data-ref-type") as "material" | "standard" | "web" | null;
    if (title) {
      openRefDrawerAndFocusCard(title, type || undefined);
    }
    return;
  }

  // 3. 审阅问题高亮标记点击联动诊断抽屉
  const issueMark = target.closest(".issue-highlight-mark") as HTMLElement | null;
  if (issueMark) {
    e.stopPropagation();
    e.preventDefault();
    const issueId = issueMark.getAttribute("data-issue-id");
    if (issueId) {
      openDiagnosticDrawerAndFocusIssue(issueId);
    }
  }
}

// ── 抽屉与定位联动 ──
function openDiagnosticDrawerAndFocusIssue(issueId: string) {
  showDiagnosticDrawer.value = true;
  diagnosticTab.value = "issues";
  nextTick(() => {
    const card = document.getElementById(`issue-card-${issueId}`);
    if (card) {
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      card.classList.remove("issue-card-pulse");
      void card.offsetWidth;
      card.classList.add("issue-card-pulse");
      setTimeout(() => {
        card.classList.remove("issue-card-pulse");
      }, 2000);
    }
  });
}

/**
 * 彻底升级：问题清单段落/句子级多级穿透绝对精准定位与呼吸高亮脉冲联动
 */
async function locateIssueInCanvas(issue: engineApi.ReviewIssue) {
  if (issue.chapterSeq && issue.chapterSeq !== projectStore.selectedChapterSeq) {
    selectChapter(issue.chapterSeq);
    await nextTick();
    await new Promise((r) => setTimeout(r, 60));
  }

  await nextTick();
  if (!editorCanvasRef.value) return;

  const canvas = editorCanvasRef.value;
  let targetEl: HTMLElement | null = null;

  // ── 第 1 级：精确查找带 issue-id 的 mark 标签 ──
  if (issue.id) {
    const mark = canvas.querySelector(
      `.issue-highlight-mark[data-issue-id="${issue.id}"], mark[data-issue-id="${issue.id}"]`
    );
    if (mark) {
      targetEl = mark as HTMLElement;
    }
  }

  // ── 第 2 级：遍历正文所有块级元素 (p, td, tr, li, h2..h6, blockquote)，多算法模糊匹配 quote / snippet ──
  const quote = (issue.quote || issue.snippet || "").trim();
  if (!targetEl && quote) {
    const blocks = Array.from(
      canvas.querySelectorAll<HTMLElement>("p, td, tr, li, h2, h3, h4, h5, h6, blockquote")
    );

    // 2.1 精确包含
    for (const b of blocks) {
      if (b.textContent && b.textContent.includes(quote)) {
        targetEl = b;
        break;
      }
    }

    // 2.2 泛化正则匹配（去除所有中英文标点与空白）
    if (!targetEl) {
      const cleanQuote = quote.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, "");
      if (cleanQuote.length >= 4) {
        for (const b of blocks) {
          const cleanBlock = (b.textContent || "").replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, "");
          if (
            cleanBlock.includes(cleanQuote) ||
            (cleanQuote.length >= 10 && cleanBlock.includes(cleanQuote.slice(0, 10)))
          ) {
            targetEl = b;
            break;
          }
        }
      }
    }

    // 2.3 前缀滑动窗口（8~16 字符）
    if (!targetEl && quote.length >= 8) {
      const cleanQuote = quote.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, "");
      const windowSizes = [16, 12, 8];
      for (const wSize of windowSizes) {
        if (cleanQuote.length >= wSize) {
          for (let i = 0; i <= cleanQuote.length - wSize; i += 4) {
            const sub = cleanQuote.slice(i, i + wSize);
            for (const b of blocks) {
              const cleanBlock = (b.textContent || "").replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, "");
              if (cleanBlock.includes(sub)) {
                targetEl = b;
                break;
              }
            }
            if (targetEl) break;
          }
        }
        if (targetEl) break;
      }
    }
  }

  // ── 第 3 级：若无 quote，在正文块级元素中匹配核心数值或 location 子标题名 ──
  if (!targetEl) {
    const blocks = Array.from(
      canvas.querySelectorAll<HTMLElement>("p, td, tr, li, h2, h3, h4, h5, h6, blockquote")
    );
    const msg = issue.description || issue.message || "";

    // 3.1 提取核心数值（如 3500万元、18.5% 等）
    const numMatches = msg.match(
      /\d+(?:\.\d+)?(?:%|万元|亿元|万|亿|m³|m²|km|kW|MW|GW|吨|人|年|h|t)?/g
    );
    if (numMatches && numMatches.length > 0) {
      const validNums = numMatches.filter((n) => n.length >= 2 && !/^202\d$/.test(n));
      const numsToSearch = validNums.length > 0 ? validNums : numMatches;
      for (const num of numsToSearch) {
        for (const b of blocks) {
          if (b.textContent && b.textContent.includes(num)) {
            targetEl = b;
            break;
          }
        }
        if (targetEl) break;
      }
    }

    // 3.2 匹配 location 关键词或标题
    if (!targetEl && issue.location) {
      const locKey = issue.location
        .replace(/^(?:第[一二三四五六七八九十百零\d]+章|\d+(?:\.\d+)*)\s*/, "")
        .trim();
      if (locKey.length >= 2) {
        for (const b of blocks) {
          if (b.textContent && b.textContent.includes(locKey)) {
            targetEl = b;
            break;
          }
        }
      }
    }
  }

  if (targetEl) {
    targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
    targetEl.classList.remove("issue-canvas-pulse");
    void targetEl.offsetWidth;
    targetEl.classList.add("issue-canvas-pulse");
    setTimeout(() => {
      targetEl?.classList.remove("issue-canvas-pulse");
    }, 2500);
    showMsg(`已定位到正文诊断位置：「${issue.location || targetEl.tagName.toLowerCase()}」`, "success");
  } else {
    canvas.scrollTo({ top: 0, behavior: "smooth" });
    showMsg(`已切换至第 ${issue.chapterSeq || projectStore.selectedChapterSeq} 章正文视口`, "info");
  }
}

function openRefDrawerAndFocusCard(refTitle: string, refType?: "material" | "standard" | "web" | "all") {
  showRefDrawer.value = true;
  if (refType && refType !== "all") {
    refFilterType.value = refType;
  } else {
    refFilterType.value = "all";
  }
  nextTick(() => {
    const allCards = document.querySelectorAll(".ref-drawer-panel .ref-card-item");
    let targetCard: HTMLElement | null = null;
    for (const card of allCards) {
      const cardTitle = card.getAttribute("data-ref-title");
      if (
        cardTitle === refTitle ||
        (cardTitle && refTitle && (cardTitle.includes(refTitle) || refTitle.includes(cardTitle)))
      ) {
        targetCard = card as HTMLElement;
        break;
      }
    }
    if (targetCard) {
      targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
      targetCard.classList.remove("ref-card-pulse");
      void targetCard.offsetWidth;
      targetCard.classList.add("ref-card-pulse");
      setTimeout(() => {
        targetCard?.classList.remove("ref-card-pulse");
      }, 2000);
    }
  });
}

function locateRefInCanvas(title: string) {
  if (!editorCanvasRef.value) return;
  const tags = editorCanvasRef.value.querySelectorAll(".inline-ref-tag");
  let targetTag: HTMLElement | null = null;
  for (const tag of tags) {
    const t = tag.getAttribute("data-ref-title");
    if (t === title || (t && title && (t.includes(title) || title.includes(t)))) {
      targetTag = tag as HTMLElement;
      break;
    }
  }
  if (targetTag) {
    targetTag.scrollIntoView({ behavior: "smooth", block: "center" });
    targetTag.classList.remove("inline-ref-pulse");
    void targetTag.offsetWidth;
    targetTag.classList.add("inline-ref-pulse");
    setTimeout(() => {
      targetTag?.classList.remove("inline-ref-pulse");
    }, 2000);
    showMsg(`已定位到正文引用位置：「${title}」`, "success");
  } else {
    showMsg(`未在当前正文视口中找到「${title}」引用标记`, "error");
  }
}

async function handleOpenWebUrl(url?: string) {
  if (!url) {
    showMsg("暂无对应的有效网页链接", "info");
    return;
  }
  try {
    const { open } = await import("@tauri-apps/plugin-shell");
    await open(url);
  } catch {
    try {
      if (engine.baseUrl) {
        await engineApi.openWebUrl(engine.baseUrl, url);
      } else {
        window.open(url, "_blank");
      }
    } catch {
      window.open(url, "_blank");
    }
  }
}

async function scrollToSubheading(seq: number, headingId: string, sub: SubHeading, e?: Event) {
  if (e) e.stopPropagation();
  if (projectStore.selectedChapterSeq !== seq) {
    selectChapter(seq);
    await nextTick();
    await new Promise((r) => setTimeout(r, 60));
  }
  activeHeadingId.value = headingId;
  nextTick(() => {
    if (!editorCanvasRef.value) return;
    const headings = editorCanvasRef.value.querySelectorAll("h1, h2, h3, h4, h5, h6");
    for (const h of headings) {
      if (h.textContent?.trim().includes(sub.title.trim())) {
        h.scrollIntoView({ behavior: "smooth", block: "center" });
        h.classList.remove("heading-pulse");
        void (h as HTMLElement).offsetWidth;
        h.classList.add("heading-pulse");
        setTimeout(() => {
          h.classList.remove("heading-pulse");
        }, 2000);
        break;
      }
    }
  });
}

// ── 全书审阅与单章审阅核心逻辑 ──
async function handleRunFullBookReview(forceAll = false) {
  if (projectStore.revisingSeq !== null) {
    showMsg("当前正在执行智能修订，请等待修订完成后再执行全书审阅", "error");
    return;
  }
  if (!engine.baseUrl) {
    showMsg("本地引擎未就绪", "error");
    return;
  }
  let llmConfig: engineApi.LLMConfig;
  try {
    llmConfig = getLLMConfig();
  } catch (err: any) {
    showMsg(err.message, "error");
    return;
  }

  reviewElapsedSeconds.value = 0;
  if (reviewTimer) clearInterval(reviewTimer);
  reviewTimer = setInterval(() => {
    reviewElapsedSeconds.value += 1;
  }, 1000);

  try {
    showMsg("🚀 已启动全书专家审阅，正在按行业规程与工程编制标准逐章深度体检...", "info");
    await projectStore.runFullBookReview(engine.baseUrl, llmConfig, forceAll, "all");
    showMsg("全书专家审阅完成！已自动汇总专家诊断总台账。", "success");
    syncEditorContent();
  } catch (err: any) {
    showMsg(`审阅失败: ${err.message}`, "error");
  } finally {
    if (reviewTimer) {
      clearInterval(reviewTimer);
      reviewTimer = null;
    }
  }
}

async function handleReviewSingleChapter(seq: number) {
  if (projectStore.revisingSeq !== null) {
    showMsg("当前正在执行智能修订，请等待修订完成后再执行审阅", "error");
    return;
  }
  if (projectStore.reviewingSeq !== null) {
    showMsg("当前正在审阅中，请勿重复点击", "error");
    return;
  }
  if (!engine.baseUrl) {
    showMsg("本地引擎未就绪", "error");
    return;
  }
  const text = projectStore.chapters[seq] || "";
  if (!text.trim()) {
    showMsg(`第 ${seq} 章暂无正文内容，无法执行审阅`, "error");
    return;
  }
  let llmConfig: engineApi.LLMConfig;
  try {
    llmConfig = getLLMConfig();
  } catch (err: any) {
    showMsg(err.message, "error");
    return;
  }

  reviewElapsedSeconds.value = 0;
  if (reviewTimer) clearInterval(reviewTimer);
  reviewTimer = setInterval(() => {
    reviewElapsedSeconds.value += 1;
  }, 1000);

  try {
    showMsg(`正在对第 ${seq} 章执行高标准专家诊断质检...`, "info");
    await projectStore.runChapterReview(engine.baseUrl, seq, "all", llmConfig);
    showMsg(`第 ${seq} 章审阅完成！`, "success");
    syncEditorContent();
    diagnosticFilterScope.value = "current";
    diagnosticTab.value = "issues";
    showDiagnosticDrawer.value = true;
  } catch (err: any) {
    showMsg(`单章审阅失败: ${err.message}`, "error");
  } finally {
    if (reviewTimer) {
      clearInterval(reviewTimer);
      reviewTimer = null;
    }
  }
}

function handleStopReview() {
  projectStore.stopBatchReview();
  showMsg("已停止全书审阅任务", "info");
}

// ── AI 外科手术式精准修订与单条修复 ──
const hasSnapshot = computed(() => {
  const seq = currentChapter.value?.seq;
  return !!(seq && projectStore.chapterSnapshots[seq]);
});

function isChapterReviewed(seq: number): boolean {
  return !!projectStore.chapterReviews[seq];
}

function getChapterIssuesCount(seq: number): number {
  return projectStore.chapterReviews[seq]?.issues?.length || 0;
}

/** 章节状态徽标 4 态计算规范：①待撰写 ②已撰写 ③已审阅共XX个问题 ④已修改X/Y个问题 */
function getChapterStatusInfo(seq: number): { text: string; cssClass: string } {
  if (projectStore.reviewingSeq === seq) {
    return { text: "审阅中…", cssClass: "reviewing" };
  }
  if (projectStore.revisingSeq === seq) {
    return { text: "修订中…", cssClass: "reviewing" };
  }
  if (!isChapterWritten(seq)) {
    return { text: "待撰写", cssClass: "unwritten" };
  }
  if (!isChapterReviewed(seq)) {
    return { text: "已撰写", cssClass: "unreviewed" };
  }

  const review = projectStore.chapterReviews[seq];
  const remaining = review?.issues?.length || 0;
  let total = review?.initial_issues_count;
  if (total === undefined || total < remaining) {
    total = remaining;
    if (review) review.initial_issues_count = total;
  }

  const modified = Math.max(0, total - remaining);

  if (modified === 0) {
    return {
      text: `已审阅共${total}个问题`,
      cssClass: total === 0 ? "reviewed" : "has-issues",
    };
  }

  return {
    text: `已修改${modified}/${total}个问题`,
    cssClass: modified >= total ? "reviewed" : "part-modified",
  };
}

async function handleFixSingleIssue(issue: engineApi.ReviewIssue) {
  if (!engine.baseUrl) {
    showMsg("本地引擎未就绪", "error");
    return;
  }
  let llmConfig: engineApi.LLMConfig;
  try {
    llmConfig = getLLMConfig();
  } catch (err: any) {
    showMsg(err.message, "error");
    return;
  }

  const seq = issue.chapterSeq || projectStore.selectedChapterSeq;
  revisionElapsedSeconds.value = 0;
  if (revisionTimer) clearInterval(revisionTimer);
  revisionTimer = setInterval(() => {
    revisionElapsedSeconds.value += 1;
  }, 1000);

  projectStore.revisingSeq = seq;
  projectStore.revisingIssueId = issue.id || issue.quote || "single";
  projectStore.revisionProgress = {
    seq,
    stage: "refine",
    message: `正在修复问题「${issue.dimension || issue.category || "规范"}」：${issue.description || issue.message}`,
    elapsedSeconds: 0,
    thoughtText: `AI 专家正在分析该项修改建议：「${issue.suggestion || issue.description || "完善论述与参数自洽性"}」，执行外科手术式段落精准重构与原位替换...`,
  };

  try {
    showMsg(`⚡ 正在对问题「${issue.dimension || issue.category || "规范"}」执行外科手术式精准修补...`, "info");
    await projectStore.runParagraphRevision(engine.baseUrl, seq, issue, llmConfig);
    showMsg("✅ 该问题已完成外科手术式精准修复，正文已原位更新！", "success");
    syncEditorContent();
  } catch (err: any) {
    showMsg(`修复失败: ${err.message}`, "error");
  } finally {
    if (revisionTimer) {
      clearInterval(revisionTimer);
      revisionTimer = null;
    }
    projectStore.revisingSeq = null;
    projectStore.revisingIssueId = null;
    projectStore.revisionProgress = null;
  }
}

async function handleDirectRevision(seq?: number, customInstruction?: string) {
  if (projectStore.reviewingSeq !== null) {
    showMsg("当前正在审阅中，请等待审阅完成后再执行智能修订", "error");
    return;
  }
  if (projectStore.revisingSeq !== null) {
    showMsg("当前正在执行智能修订中，请勿重复点击", "error");
    return;
  }
  if (!engine.baseUrl) {
    showMsg("本地引擎未就绪", "error");
    return;
  }
  let llmConfig: engineApi.LLMConfig;
  try {
    llmConfig = getLLMConfig();
  } catch (err: any) {
    showMsg(err.message, "error");
    return;
  }

  const targetSeq = seq !== undefined ? seq : projectStore.selectedChapterSeq;
  const originalText = projectStore.chapters[targetSeq] || "";
  if (!originalText.trim()) {
    showMsg(`第 ${targetSeq} 章暂无正文，无法执行修订`, "error");
    return;
  }

  if (!isChapterReviewed(targetSeq)) {
    showMsg("请先点击「审阅本章」完成体检诊断后，再执行智能修订", "error");
    return;
  }

  const currentIssues = [...(projectStore.chapterReviews[targetSeq]?.issues || [])];
  if (currentIssues.length === 0 && !customInstruction) {
    showMsg("本章无待修改的诊断问题", "info");
    return;
  }

  revisionElapsedSeconds.value = 0;
  revisionStageIndex.value = 0;
  if (revisionTimer) clearInterval(revisionTimer);
  revisionTimer = setInterval(() => {
    revisionElapsedSeconds.value += 1;
    if (projectStore.revisionProgress) {
      projectStore.revisionProgress.elapsedSeconds = revisionElapsedSeconds.value;
    }
    if (revisionElapsedSeconds.value % 3 === 0 && revisionStageIndex.value < revisionStages.length - 1) {
      revisionStageIndex.value += 1;
    }
  }, 1000);

  try {
    if (currentIssues.length > 0 && !customInstruction) {
      const totalIssues = currentIssues.length;
      showMsg(`⚡ 已启动按序号逐项流水线智能修订（共 ${totalIssues} 项）...`, "info");

      for (let idx = 0; idx < totalIssues; idx++) {
        const issue = currentIssues[idx];
        const issueTitle = `[${issue.dimension || issue.category || "规范"}] ${issue.description || issue.message}`;
        showMsg(`⚡ 正在按序号修复 (${idx + 1}/${totalIssues})：${issueTitle}...`, "info");

        projectStore.revisingSeq = targetSeq;
        projectStore.revisingIssueId = issue.id || String(idx);
        projectStore.revisionProgress = {
          seq: targetSeq,
          stage: "refine",
          message: `正在按序号修复 (${idx + 1}/${totalIssues})：${issueTitle}`,
          elapsedSeconds: revisionElapsedSeconds.value,
          thoughtText: `【正在修复第 ${idx + 1}/${totalIssues} 项】\n● 审查维度：${issue.dimension || issue.category || "规范合规性"}\n● 缺陷描述：${issue.description || issue.message}\n● 专家建议：${issue.suggestion || "完善论述与参数依据"}\n\nAI 专家正在锁定目标段落，依照投资项目编制规程与行业规范执行外科手术式段落精准重构与原位无缝替换...`,
        };

        await projectStore.runParagraphRevision(engine.baseUrl, targetSeq, issue, llmConfig);
        syncEditorContent();
      }

      showMsg(`🎉 第 ${targetSeq} 章共 ${totalIssues} 项问题已全部按序号修复完毕！正文已原位更新并自动销号。`, "success");
    } else {
      let instruction = customInstruction || "请依据投资项目高质量编制规范与行业工程规程，进一步深化工程参数论述与规范表格排版。";
      showMsg(`⚡ 正在对第 ${targetSeq} 章执行流式 AI 智能重构修订...`, "info");
      await projectStore.runChapterRevisionStream(engine.baseUrl, targetSeq, instruction, llmConfig);
      showMsg(`🎉 第 ${targetSeq} 章 AI 修订完成！正文已更新并自动销号。`, "success");
      syncEditorContent();
    }
  } catch (err: any) {
    showMsg(`修订失败: ${err.message}`, "error");
  } finally {
    if (revisionTimer) {
      clearInterval(revisionTimer);
      revisionTimer = null;
    }
    projectStore.revisingSeq = null;
    projectStore.revisingIssueId = null;
    projectStore.revisionProgress = null;
  }
}

async function handleUndoRevision(seq?: number) {
  if (!engine.baseUrl) return;
  const targetSeq = seq !== undefined ? seq : (currentChapter.value?.seq || projectStore.selectedChapterSeq);
  try {
    await projectStore.undoChapterRevision(engine.baseUrl, targetSeq);
    showMsg(`已撤销第 ${targetSeq} 章的修改，恢复至修改前版本！`, "success");
    syncEditorContent();
  } catch (err: any) {
    showMsg(`撤销失败: ${err.message}`, "error");
  }
}

function copyCurrentChapterMarkdown() {
  if (navigator.clipboard && currentChapterText.value) {
    navigator.clipboard.writeText(currentChapterText.value);
    showMsg(`已复制第 ${projectStore.selectedChapterSeq} 章 Markdown 源码至剪贴板！`, "success");
  }
}

onMounted(async () => {
  await ensureStep4State();
  nextTick(() => {
    syncEditorContent();
  });
});

onUnmounted(() => {
  if (reviewTimer) clearInterval(reviewTimer);
  if (revisionTimer) clearInterval(revisionTimer);
  for (const t of Object.values(saveDebounceTimers)) {
    clearTimeout(t);
  }
});
</script>

<template>
  <div class="step4-container">
    <!-- 全局操作通知条 -->
    <transition name="fade">
      <div v-if="actionMessage" :class="['alert-banner', actionMessage.type]">
        {{ actionMessage.text }}
      </div>
    </transition>

    <!-- ═════════════════════════════════════════════════════════ -->
    <!-- 主体工作台：左右架构像素级对齐 Step 3 -->
    <!-- ═════════════════════════════════════════════════════════ -->
    <div class="writing-layout">
      <!-- 左侧：全书目录导航与控制面板 (Flat 平铺一体化目录树) -->
      <aside class="sidebar-panel card">
        <div class="card-header sidebar-header">
          <div class="header-titles">
            <h3>📑 章节目录与导航</h3>
            <span class="proj-badge">{{ projectStore.currentProject?.name || "未选项目" }}</span>
          </div>
          <!-- 统计指示条 -->
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
                    active: projectStore.selectedChapterSeq === seq,
                    completed: isChapterWritten(seq),
                    reviewing: projectStore.reviewingSeq === seq,
                  }"
                  @click="selectChapter(seq)"
                  :title="`第 ${seq} 章：${getChapterTitle(seq)}`"
                >
                  第 {{ seq }} 章
                </span>
                <span v-if="idx < projectStore.writingOrder.length - 1" class="flow-arrow">➔</span>
              </span>
            </div>
          </div>
        </div>

        <!-- 全局审阅主操作区 -->
        <div class="global-actions">
          <button
            v-if="projectStore.batchReviewing"
            class="btn btn-danger btn-block"
            @click="handleStopReview"
          >
            ⏹ 停止全书审阅
          </button>
          <button
            v-else
            class="btn btn-primary btn-block"
            :disabled="completedChaptersCount === 0 || projectStore.reviewingSeq !== null || projectStore.revisingSeq !== null"
            @click="handleRunFullBookReview(false)"
          >
            🚀 一键全书审阅
          </button>
        </div>

        <!-- Flat 平铺一体化章节目录树 (无边框平铺列表，去除预警角标) -->
        <div class="outline-tree-scrollable">
          <div
            v-for="ch in projectStore.outlineChapters"
            :key="ch.seq"
            class="chapter-tree-node"
            :class="{
              'is-active': projectStore.selectedChapterSeq === ch.seq,
              'is-reviewing': projectStore.reviewingSeq === ch.seq,
              'is-completed': isChapterWritten(ch.seq),
            }"
          >
            <!-- 章节行 -->
            <div
              class="chapter-node-row"
              @click="selectChapter(ch.seq)"
              :title="`第 ${ch.seq} 章：${ch.title}`"
            >
              <div class="row-left">
                <span class="ch-seq-tag">{{ ch.seq }}</span>
                <span class="ch-title-text">{{ ch.title }}</span>
              </div>

              <div class="row-right">
                <!-- 状态徽标 (4 态标准流转) -->
                <span
                  class="status-pill"
                  :class="getChapterStatusInfo(ch.seq).cssClass"
                >
                  <span v-if="projectStore.reviewingSeq === ch.seq || projectStore.revisingSeq === ch.seq" class="spinner-inline"></span>
                  {{ getChapterStatusInfo(ch.seq).text }}
                </span>

                <!-- 单章操作按钮 -->
                <button
                  class="ch-action-btn"
                  title="审阅该章"
                  :disabled="projectStore.batchReviewing || projectStore.reviewingSeq !== null || projectStore.revisingSeq !== null || !isChapterWritten(ch.seq)"
                  @click.stop="handleReviewSingleChapter(ch.seq)"
                >
                  🔍
                </button>

                <!-- 子标题展开/折叠 -->
                <button
                  v-if="chapterSubheadings[ch.seq] && chapterSubheadings[ch.seq].length > 0"
                  class="collapse-toggle-icon"
                  :class="{ collapsed: isChapterCollapsed(ch.seq) }"
                  :title="isChapterCollapsed(ch.seq) ? '展开子标题' : '收起子标题'"
                  @click="toggleChapterCollapse(ch.seq, $event)"
                >
                  {{ isChapterCollapsed(ch.seq) ? '▶' : '▼' }}
                </button>
              </div>
            </div>

            <!-- 多级子标题列表 (仅当前激活选中的章节高亮并展开其子标题，其它章节默认折叠收起) -->
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
                  :title="sub.title"
                  @click="scrollToSubheading(ch.seq, sub.id, sub, $event)"
                >
                  <span class="sub-bullet">{{ sub.level === 2 ? '🔹' : sub.level === 3 ? '▪' : '▫' }}</span>
                  <span class="sub-text">{{ sub.title }}</span>
                </div>
              </div>
            </transition>
          </div>

          <div v-if="totalChapters === 0" class="empty-outline-tip">
            暂无章节目录，请先在步骤 2 生成大纲。
          </div>
        </div>
      </aside>

      <!-- 右侧：单章聚焦出版级排版与审阅主画布 (结构对齐 Step 3) -->
      <main class="editor-panel card">
        <div class="card-header editor-header">
          <div class="editor-title-area">
            <div class="title-row">
              <span class="seq-tag" v-if="currentChapter">第 {{ currentChapter.seq }} 章</span>
              <h3 class="active-ch-title">{{ currentChapter?.title || "未选择章节" }}</h3>
            </div>
            <div class="editor-meta-row">
              <span class="meta-item">
                本章字数：<strong>{{ currentChapterWords.toLocaleString() }}</strong> 字 (正文)
              </span>
              <span class="meta-item-divider">·</span>
              <span
                class="meta-item status-text"
                :class="{
                  'stat-passed': currentChapterReview && currentChapterIssuesCount === 0,
                  'stat-warning': currentChapterIssuesCount > 0,
                  'stat-idle': !currentChapterReview,
                }"
              >
                {{
                  projectStore.reviewingSeq === currentChapter?.seq
                    ? "⚡ 正在专家深度质检中..."
                    : currentChapterReview
                    ? currentChapterIssuesCount === 0
                      ? "🟢 已修改 ✓"
                      : `🟡 存在 ${currentChapterIssuesCount} 处待核建议`
                    : isChapterWritten(currentChapter?.seq || 1)
                    ? "⏳ 待专家审阅"
                    : "待在步骤 3 撰写生成"
                }}
              </span>
            </div>
          </div>

          <!-- 右上角核心操作组 (单章审阅、AI智能修订、撤销、抽屉与复制) -->
          <div class="editor-actions">
            <button
              class="btn btn-outline"
              :disabled="!isChapterWritten(currentChapter?.seq || 1) || projectStore.reviewingSeq !== null || projectStore.revisingSeq !== null"
              @click="handleReviewSingleChapter(currentChapter?.seq || 1)"
              title="针对本章执行高标准专家诊断质检"
            >
              🔍 审阅本章
            </button>

            <button
              class="btn btn-primary"
              :disabled="!isChapterReviewed(currentChapter?.seq || 1) || getChapterIssuesCount(currentChapter?.seq || 1) === 0 || projectStore.revisingSeq !== null || projectStore.reviewingSeq !== null"
              @click="handleDirectRevision(currentChapter?.seq)"
              :title="!isChapterReviewed(currentChapter?.seq || 1) ? '请先点击「审阅本章」执行诊断体检' : (getChapterIssuesCount(currentChapter?.seq || 1) === 0 ? '本章无待修改的诊断问题' : '代入本章专家诊断建议，一键执行外科手术式精准修补')"
            >
              <span v-if="projectStore.revisingSeq === currentChapter?.seq" class="spinner-inline"></span>
              ⚡ AI 智能修订
            </button>

            <button
              v-if="hasSnapshot"
              class="btn btn-outline btn-undo"
              @click="handleUndoRevision(currentChapter?.seq)"
              title="撤销本次智能修改，恢复至修改前的原版正文"
            >
              ↩️ 撤销修改
            </button>

            <button
              class="btn btn-outline drawer-btn"
              :class="{ active: showDiagnosticDrawer }"
              @click="showDiagnosticDrawer = !showDiagnosticDrawer"
              title="打开全高右侧专家诊断总台账抽屉"
            >
              📋 专家诊断报告 ({{ allIssues.length }})
            </button>

            <button
              class="btn btn-outline drawer-btn"
              :class="{ active: showRefDrawer }"
              @click="showRefDrawer = !showRefDrawer"
              title="打开全高右侧参考资料来源抽屉"
            >
              📚 参考资料 ({{ currentChapterReferences.length }})
            </button>

            <button
              class="btn btn-outline"
              @click="copyCurrentChapterMarkdown"
              title="复制当前章节排版 Markdown 源码至剪贴板"
            >
              📄 复制 Markdown
            </button>
          </div>
        </div>

        <!-- 审阅心跳与进度条 (正在执行全书审阅或单章审阅时内联展示) -->
        <transition name="fade">
          <div v-if="projectStore.batchReviewing || projectStore.reviewingSeq !== null" class="review-heartbeat-bar">
            <div class="heartbeat-inner">
              <div class="hb-left">
                <span class="radar-pulse"></span>
                <div class="hb-title-box">
                  <div class="hb-main-title">
                    <strong v-if="projectStore.batchReviewing">⚡ 正在深度审阅 第 {{ projectStore.reviewProgress?.currentIndex || 1 }}/{{ projectStore.reviewProgress?.totalTarget || 1 }} 章：《{{ projectStore.reviewProgress?.currentTitle || '当前章节' }}》（进度 {{ projectStore.reviewProgress?.percent || 0 }}%）· 已耗时 {{ reviewElapsedSeconds }}s</strong>
                    <strong v-else>⚡ 正在深度审阅 第 {{ projectStore.reviewingSeq }} 章：《{{ currentChapter?.title || '当前章节' }}》· 已耗时 {{ reviewElapsedSeconds }}s</strong>
                  </div>
                  <div class="hb-desc">
                    <span v-if="projectStore.batchReviewing">已完成 {{ projectStore.reviewProgress?.currentIndex ? projectStore.reviewProgress.currentIndex - 1 : 0 }} 章，累计发现 {{ projectStore.reviewProgress?.completedIssuesCount || 0 }} 处优化建议 · 依照投资项目编制规程与行业规范进行系统体检</span>
                    <span v-else>对本章节正文论述、关键工程技术参数与数值前后自洽性进行全维度高标准专家体检</span>
                  </div>
                </div>
              </div>
              <div class="hb-right">
                <button
                  v-if="projectStore.batchReviewing"
                  class="btn btn-danger btn-sm btn-stop-review"
                  @click="handleStopReview"
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
                    <span class="review-thought-icon">🔬</span>
                    <span>专家深度质检与规程校核过程 (纯中文) <span v-if="projectStore.reviewProgress?.thoughtText">({{ projectStore.reviewProgress.thoughtText.length }} 字符)</span></span>
                    <span class="thinking-wave">
                      <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                    </span>
                  </div>
                  <button class="review-thought-toggle-btn" type="button">
                    {{ showReviewThoughtDetails ? '收起 ▲' : '展开 ▼' }}
                  </button>
                </div>
                <div v-show="showReviewThoughtDetails" ref="reviewThoughtBodyRef" class="review-thought-body">
                  <pre v-if="projectStore.reviewProgress?.thoughtText">{{ projectStore.reviewProgress.thoughtText }}</pre>
                  <div v-else class="review-thought-placeholder">
                    <span class="placeholder-spinner">🔍</span>
                    <span>思维推演中 (纯中文)... AI 专家正在对照投资项目编制规程与行业规范深度核查章节参数指标与数据自洽性...</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>

        <!-- 修订心跳与进度条 (正在执行就地修订时内联展示) -->
        <transition name="fade">
          <div v-if="projectStore.revisingSeq !== null" class="revision-heartbeat-bar">
            <div class="heartbeat-inner">
              <div class="hb-left">
                <span class="radar-pulse"></span>
                <div class="hb-title-box">
                  <div class="hb-main-title">
                    <strong>⚡ AI 智能修订重构中：第 {{ projectStore.revisingSeq }} 章（{{ revisionStages[revisionStageIndex]?.title || '局部智能重构' }}）· 已耗时 {{ revisionElapsedSeconds }}s</strong>
                  </div>
                  <div class="hb-desc">
                    {{ projectStore.revisionProgress?.message || revisionStages[revisionStageIndex]?.desc || '统筹上下文逻辑与专家诊断建议，流式执行工程出版级精准重构' }}
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

            <!-- 实时 AI 修订思考推演窗 -->
            <div class="review-thought-stream-wrapper">
              <div class="review-thought-card">
                <div class="review-thought-header" @click="showRevisionThoughtDetails = !showRevisionThoughtDetails">
                  <div class="review-thought-title">
                    <span class="review-thought-icon">⚡</span>
                    <span>AI 专家智能修订推演过程 (纯中文) <span v-if="projectStore.revisionProgress?.thoughtText">({{ projectStore.revisionProgress.thoughtText.length }} 字符)</span></span>
                    <span class="thinking-wave">
                      <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                    </span>
                  </div>
                  <button class="review-thought-toggle-btn" type="button">
                    {{ showRevisionThoughtDetails ? '收起 ▲' : '展开 ▼' }}
                  </button>
                </div>
                <div v-show="showRevisionThoughtDetails" ref="revisionThoughtBodyRef" class="review-thought-body">
                  <pre v-if="projectStore.revisionProgress?.thoughtText">{{ projectStore.revisionProgress.thoughtText }}</pre>
                  <div v-else class="review-thought-placeholder">
                    <span class="placeholder-spinner">⚡</span>
                    <span>思维推演中 (纯中文)... AI 专家正在对照投资项目编制规程与行业规范重构论述与关键技术参数...</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>

        <!-- 主工作画布容器 -->
        <div class="card-body editor-body">
          <!-- 纯净出版级排版正文画布 — 单章聚焦 + contenteditable 就地编辑 -->
          <div class="writing-canvas">
            <div class="canvas-spec-bar">
              <span class="spec-tag">📖 行业规程与工程编制出版级排版 (10.5pt)</span>
              <span class="spec-tip">
                支持直接在排版文字上点击输入修改，300ms 自动落盘。点击黄色高亮诊断标记可联动右侧修改建议或一键局部精准修复。
              </span>
            </div>

            <!-- 单章排版正文编辑画布 -->
            <div
              ref="editorCanvasRef"
              contenteditable="true"
              class="rich-rendered-editor spec-typography"
              @input="onEditorInput"
              @click="handleEditorCanvasClick"
              data-placeholder="本章节暂未生成正文。可直接在此处点击输入排版文字，或返回步骤 3 进行 AI 一键写作..."
            ></div>
          </div>
        </div>

        <DiagnosticLedgerDrawer
          :open="showDiagnosticDrawer"
          v-model:filter-scope="diagnosticFilterScope"
          v-model:active-tab="diagnosticTab"
          :chapter-seq="currentChapter?.seq"
          :chapter-title="currentChapter?.title"
          :current-chapter-issues="currentChapterIssues"
          :all-issues="allIssues"
          :all-numerical-checks="allNumericalChecks"
          :all-data-gaps="allDataGaps"
          :revising-seq="projectStore.revisingSeq"
          :revising-issue-id="projectStore.revisingIssueId"
          @close="showDiagnosticDrawer = false"
          @locate-issue="locateIssueInCanvas"
          @fix-issue="handleFixSingleIssue"
        />

        <ReferenceLedgerDrawer
          :open="showRefDrawer"
          v-model:filter-type="refFilterType"
          :chapter-seq="currentChapter?.seq"
          :chapter-title="currentChapter?.title"
          :references="currentChapterReferences"
          fixed-overlay
          @close="showRefDrawer = false"
          @locate="locateRefInCanvas"
          @open-url="handleOpenWebUrl"
        />
      </main>
    </div>

    <!-- 底部流转按钮 -->
    <div class="bottom-nav">
      <button class="btn btn-secondary btn-lg" @click="projectStore.setStep(3)">
        &larr; 上一步：报告写作
      </button>
      <button
        class="btn btn-primary btn-lg"
        :disabled="completedChaptersCount === 0"
        @click="projectStore.setStep(5)"
      >
        下一步：导出报告 &rarr;
      </button>
    </div>
  </div>
</template>

<style scoped>
.step4-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 20px 24px 48px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.btn-undo {
  color: #d97706;
  border-color: #fcd34d;
  background: #fffbeb;
}
.btn-undo:hover {
  background: #fef3c7;
  border-color: #f59e0b;
}

/* 右侧主工作画布 */
.editor-panel {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 165px);
  min-height: 0;
  position: relative;
  overflow: hidden;
}

.status-text.stat-passed {
  color: #16a34a;
  font-weight: 600;
}
.status-text.stat-warning {
  color: #d97706;
  font-weight: 600;
}

.editor-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  position: relative;
}

/* 审阅与修订心跳条 (内联在主画布顶部) */
.review-heartbeat-bar,
.revision-heartbeat-bar {
  margin: 12px 18px 0;
  padding: 12px 16px;
  background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
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
  gap: 12px;
}
.radar-pulse {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #3b82f6;
  box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
  animation: pulse-ring 1.5s infinite;
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
.hb-main-title {
  font-size: 13px;
  color: #1e3a8a;
}
.hb-desc {
  font-size: 11.5px;
  color: #475569;
  margin-top: 2px;
}
.review-thought-stream-wrapper {
  margin-top: 4px;
}
.review-thought-card {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  overflow: hidden;
}
.review-thought-header {
  padding: 6px 10px;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}
.review-thought-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  font-weight: 600;
  color: #334155;
}
.review-thought-toggle-btn {
  background: transparent;
  border: none;
  font-size: 11px;
  color: #3b82f6;
  cursor: pointer;
}
.review-thought-body {
  padding: 8px 12px;
  max-height: 160px;
  overflow-y: auto;
  font-size: 11.5px;
  line-height: 1.5;
  background: #fdfdfd;
}
.review-thought-body pre {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  color: #334155;
}
.review-thought-placeholder {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
}

/* 修订步进器 */
.hb-stepper-compact {
  display: flex;
  align-items: center;
  gap: 12px;
}
.stepper-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: #64748b;
}
.stepper-item.completed {
  color: #16a34a;
  font-weight: 600;
}
.stepper-item.active {
  color: #2563eb;
  font-weight: 600;
}
.stepper-circle {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
}
.stepper-item.completed .stepper-circle {
  background: #dcfce7;
  color: #15803d;
}
.stepper-item.active .stepper-circle {
  background: #dbeafe;
  color: #1d4ed8;
}

/* 排版正文画布 */
.writing-canvas {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  background: #ffffff;
}

.canvas-spec-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 18px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
  font-size: 11.5px;
  color: #64748b;
}
.spec-tag {
  font-weight: 600;
  color: #1e293b;
}

.unwritten-chapter-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}
.unwritten-icon {
  font-size: 36px;
  margin-bottom: 12px;
}
.unwritten-title {
  font-size: 16px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 8px;
}
.unwritten-desc {
  font-size: 13px;
  color: #94a3b8;
  max-width: 480px;
}

/* ═════════════════════════════════════════════════════════ */
/* 定位脉冲高亮特效 (2.5 秒金黄色呼吸脉冲波纹) */
/* ═════════════════════════════════════════════════════════ */
:deep(.issue-card-pulse) {
  animation: card-pulse-anim 2s ease;
}
@keyframes card-pulse-anim {
  0% {
    box-shadow: 0 0 0 0 rgba(234, 179, 8, 0.8);
    transform: scale(1.02);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(234, 179, 8, 0);
    transform: scale(1);
  }
  100% {
    box-shadow: none;
  }
}

:deep(.issue-canvas-pulse) {
  animation: canvas-issue-pulse 2.5s ease !important;
  border-radius: 4px;
}
@keyframes canvas-issue-pulse {
  0% {
    background-color: rgba(250, 204, 21, 0.55) !important;
    box-shadow: 0 0 0 5px rgba(234, 179, 8, 0.65) !important;
    transform: scale(1.01);
  }
  30% {
    background-color: rgba(254, 240, 138, 0.75) !important;
    box-shadow: 0 0 0 10px rgba(234, 179, 8, 0.3) !important;
    transform: scale(1);
  }
  60% {
    background-color: rgba(254, 240, 138, 0.4) !important;
    box-shadow: 0 0 0 5px rgba(234, 179, 8, 0.15) !important;
  }
  100% {
    background-color: transparent !important;
    box-shadow: none !important;
  }
}

:deep(.ref-card-pulse) {
  animation: ref-card-anim 2s ease;
}
@keyframes ref-card-anim {
  0% {
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.8);
    transform: scale(1.02);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(59, 130, 246, 0);
    transform: scale(1);
  }
  100% {
    box-shadow: none;
  }
}

:deep(.inline-ref-pulse) {
  animation: inline-ref-anim 2s ease !important;
}
@keyframes inline-ref-anim {
  0% {
    transform: scale(1.1);
    box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.6);
  }
  100% {
    transform: scale(1);
    box-shadow: none;
  }
}

:deep(.heading-pulse) {
  animation: heading-pulse-anim 2s ease;
}
@keyframes heading-pulse-anim {
  0% {
    background-color: #dbeafe;
    color: #1d4ed8;
  }
  100% {
    background-color: transparent;
  }
}
</style>
