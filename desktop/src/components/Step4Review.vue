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
  extractOutlineHeadings,
  extractReferences,
  extractSubHeadings,
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

// ── AI 智能修订弹窗 / 浮层 ──
const showRevisionModal = ref<boolean>(false);
const revisionInstruction = ref<string>("");
const targetRevisionSeq = ref<number>(1);

// ── 章节与小节目录展开 / 定位状态 ──
const activeChapterSeq = ref<number>(1);
const activeHeadingId = ref<string | null>(null);
const chapterCollapsedMap = ref<Record<number, boolean>>({});

// ── 全局操作通知 ──
const actionMessage = ref<{ type: "success" | "error" | "info"; text: string } | null>(null);

// ── 审阅动态心跳与计时器 ──
const reviewElapsedSeconds = ref<number>(0);
const reviewStageIndex = ref<number>(0);
let reviewTimer: ReturnType<typeof setInterval> | null = null;

const reviewStages = [
  { id: "params", title: "关键参数抽取", desc: "提取投资估算、规模与关键工程技术指标" },
  { id: "compliance", title: "规程合规审查", desc: "对照国家发改委与行业编制规程标准" },
  { id: "consistency", title: "跨章数值自洽", desc: "排查全书前后章节数据勾稽与量纲自洽性" },
  { id: "report", title: "诊断报告生成", desc: "综合生成专家评审意见、批注与资料缺口" },
];

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

// ── 同步排版正文到各章节 contenteditable DOM ──
function syncAllChaptersHtml() {
  for (const ch of projectStore.outlineChapters) {
    const el = document.getElementById(`chapter-canvas-${ch.seq}`);
    if (el) {
      const text = projectStore.chapters[ch.seq] || "";
      el.innerHTML = markdownToHtml(text, ch.seq, outlineHeadings.value);
    }
  }
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

watch(viewMode, (mode) => {
  if (mode === "rich") {
    nextTick(() => {
      syncAllChaptersHtml();
    });
  }
});

// ── 全书统计与计算属性 ──
const totalChapters = computed(() => projectStore.outlineChapters.length);

const completedChaptersCount = computed(() => {
  return projectStore.outlineChapters.filter((ch) => {
    const text = projectStore.chapters[ch.seq];
    return text && text.trim().length > 0;
  }).length;
});

const totalWordCount = computed(() => {
  let count = 0;
  for (const text of Object.values(projectStore.chapters)) {
    if (text) count += text.length;
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
  return !!chapterCollapsedMap.value[seq];
}

function toggleChapterCollapse(seq: number, e?: Event) {
  if (e) e.stopPropagation();
  chapterCollapsedMap.value[seq] = !chapterCollapsedMap.value[seq];
}

function expandAllChapters() {
  for (const ch of projectStore.outlineChapters) {
    chapterCollapsedMap.value[ch.seq] = false;
  }
}

function collapseAllChapters() {
  for (const ch of projectStore.outlineChapters) {
    chapterCollapsedMap.value[ch.seq] = true;
  }
}

async function scrollToChapter(seq: number) {
  activeChapterSeq.value = seq;
  activeHeadingId.value = null;
  if (viewMode.value !== "rich" && viewMode.value !== "source") {
    viewMode.value = "rich";
    await nextTick();
    syncAllChaptersHtml();
  }
  await nextTick();
  const anchorId =
    viewMode.value === "source" ? `source-chapter-${seq}` : `full-chapter-anchor-${seq}`;
  const el = document.getElementById(anchorId);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    el.classList.remove("heading-anchor-pulse");
    void el.offsetWidth;
    el.classList.add("heading-anchor-pulse");
    setTimeout(() => {
      el.classList.remove("heading-anchor-pulse");
    }, 1500);
  }
}

async function scrollToSubheading(seq: number, headingId: string, e?: Event) {
  if (e) e.stopPropagation();
  activeChapterSeq.value = seq;
  activeHeadingId.value = headingId;
  if (viewMode.value !== "rich") {
    viewMode.value = "rich";
    await nextTick();
    syncAllChaptersHtml();
    await new Promise((r) => setTimeout(r, 60));
  }
  const el = document.getElementById(headingId);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    el.classList.remove("heading-anchor-pulse");
    void el.offsetWidth;
    el.classList.add("heading-anchor-pulse");
    setTimeout(() => {
      el.classList.remove("heading-anchor-pulse");
    }, 1500);
  } else {
    scrollToChapter(seq);
  }
}

// ── 就地排版编辑输入 (contenteditable 防抖 300ms 自动落盘) ──
function onChapterInput(seq: number, e: Event) {
  const target = e.target as HTMLElement;
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
async function handleRunFullBookReview(forceAll = false) {
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
  reviewStageIndex.value = 0;
  if (reviewTimer) clearInterval(reviewTimer);
  reviewTimer = setInterval(() => {
    reviewElapsedSeconds.value += 1;
    reviewStageIndex.value = Math.min(3, Math.floor(reviewElapsedSeconds.value / 3));
  }, 1000);

  try {
    showMsg("已启动「全书全维专家审阅」，正在全面体检合规与数据自洽...", "info");
    const fullData = await projectStore.runFullBookReview(engine.baseUrl, llmConfig, forceAll);
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
  mode: "all" | "compliance" | "numeric" | "technical" = "all",
) {
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
  reviewStageIndex.value = 0;
  if (reviewTimer) clearInterval(reviewTimer);
  reviewTimer = setInterval(() => {
    reviewElapsedSeconds.value += 1;
    reviewStageIndex.value = Math.min(3, Math.floor(reviewElapsedSeconds.value / 3));
  }, 1000);

  try {
    showMsg(`正在对第 ${seq} 章执行专家审阅...`, "info");
    const res = await projectStore.runChapterReview(engine.baseUrl, seq, mode, llmConfig);
    showMsg(`第 ${seq} 章审阅完成！结论：${res.status}，发现 ${res.issues?.length || 0} 处问题。`);
    // 重新整合全书总档案
    await projectStore.runFullBookReview(engine.baseUrl, llmConfig, false);
  } catch (err) {
    showMsg(`单章审阅失败：${(err as Error).message}`, "error");
  } finally {
    if (reviewTimer) {
      clearInterval(reviewTimer);
      reviewTimer = null;
    }
  }
}

// ── AI 定向修订 ──
function openRevisionModal(seq?: number, defaultInstruction?: string) {
  targetRevisionSeq.value = seq || activeChapterSeq.value || 1;
  revisionInstruction.value = defaultInstruction || "";
  showRevisionModal.value = true;
}

const presetInstructions = [
  "对照国家发改委与行业工程编制规程要求，补齐章节合规论证与前置要件说明",
  "核对并对齐前后章节投资估算、规模参数与关键工程技术指标",
  "补充节能减排、环境保护与社会稳定风险分析专项论述",
  "压制套话与空洞修辞，规范 10.5pt 工程咨询出版级专业术语与数据表格",
  "补充附表、附图与前置审批支撑性依据，规范数据引证格式",
];

function applyPresetInstruction(preset: string) {
  revisionInstruction.value = preset;
}

async function handleExecuteRevision() {
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

  const seq = targetRevisionSeq.value;
  const instruction = revisionInstruction.value.trim();
  if (!instruction) {
    showMsg("请输入修订指令或点击预设建议", "error");
    return;
  }

  revisionElapsedSeconds.value = 0;
  revisionStageIndex.value = 0;
  if (revisionTimer) clearInterval(revisionTimer);
  revisionTimer = setInterval(() => {
    revisionElapsedSeconds.value += 1;
    revisionStageIndex.value = Math.min(3, Math.floor(revisionElapsedSeconds.value / 3));
  }, 1000);

  try {
    showMsg(`正在对第 ${seq} 章执行 AI 智能修订并生成 Diff...`, "info");
    await projectStore.runChapterRevision(engine.baseUrl, seq, instruction, llmConfig);
    showRevisionModal.value = false;
    viewMode.value = "diff";
    showMsg(`第 ${seq} 章 AI 修订已就绪！已进入全宽单栏内联 Diff 差异对比视图。`);
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

// ── 定位问题到正文 ──
async function locateIssueInCanvas(locationText?: string, chapterSeq?: number) {
  let targetSeq = chapterSeq;
  if (!targetSeq && locationText) {
    const m = locationText.match(/第\s*([一二三四五六七八九十百零\d]+)\s*章/);
    if (m) {
      targetSeq = Number(m[1]) || 1;
    }
  }
  if (!targetSeq) targetSeq = 1;

  await scrollToChapter(targetSeq);
  showMsg(`已定位至第 ${targetSeq} 章对应段落`, "info");
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
            <span class="meta-pill" title="全书总字数">
              <strong>{{ totalWordCount.toLocaleString() }}</strong> 字
            </span>
            <span class="meta-pill" title="已完成编写章节数">
              <strong>{{ completedChaptersCount }} / {{ totalChapters }}</strong> 章已撰写
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
        <!-- 核心行动按钮 -->
        <button
          v-if="!projectStore.batchReviewing"
          class="btn btn-primary btn-review-hero"
          :disabled="completedChaptersCount === 0"
          @click="handleRunFullBookReview(false)"
          title="一键对全书执行规程符合性审查、跨章数据前后自洽核验与资料完整度体检"
        >
          🚀 全书全维专家审阅
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
          :disabled="completedChaptersCount === 0"
          @click="openRevisionModal()"
          title="设定工程修改指令，由大模型针对全书或指定章节执行智能定向重构与润色"
        >
          ✍️ AI智能修订
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
              <strong>全书全维专家深度审阅进行中...</strong>
              <span class="hb-desc">正在依照国家发改委与行业工程编制规程对全书进行系统体检</span>
            </div>
          </div>
          <div class="hb-stepper">
            <div
              v-for="(stage, sIdx) in reviewStages"
              :key="stage.id"
              class="stepper-item"
              :class="{
                completed: reviewStageIndex > sIdx,
                active: reviewStageIndex === sIdx,
                pending: reviewStageIndex < sIdx,
              }"
            >
              <div class="stepper-circle">
                <span v-if="reviewStageIndex > sIdx">✓</span>
                <span v-else-if="reviewStageIndex === sIdx" class="spinner-mini"></span>
                <span v-else>{{ sIdx + 1 }}</span>
              </div>
              <span class="stepper-label">{{ stage.title }}</span>
            </div>
          </div>
          <div class="hb-right">
            <span class="hb-timer">⏱️ 已耗时 <strong>{{ reviewElapsedSeconds }}</strong> 秒</span>
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
        <div class="nav-panel-header">
          <div class="nav-header-title">
            <h4>📑 全书多级目录导航</h4>
            <span class="nav-count">{{ totalChapters }} 章</span>
          </div>
          <div class="nav-quick-actions">
            <button class="btn-text-action" @click="expandAllChapters" title="展开全部章节的多级子标题">
              ⊞ 全部展开
            </button>
            <span class="action-divider">|</span>
            <button class="btn-text-action" @click="collapseAllChapters" title="收起全部章节的多级子标题">
              ⊟ 全部收起
            </button>
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
              'has-review': !!projectStore.chapterReviews[ch.seq],
              'has-warning': (chapterIssuesCount[ch.seq] || 0) > 0 || (chapterGapsCount[ch.seq] || 0) > 0,
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
                <!-- 预警小黄点 / 小红点 -->
                <span
                  v-if="(chapterIssuesCount[ch.seq] || 0) > 0"
                  class="warning-dot"
                  :title="`第 ${ch.seq} 章存在 ${chapterIssuesCount[ch.seq]} 处待优化诊断`"
                ></span>
                <span
                  v-else-if="projectStore.chapterReviews[ch.seq]?.status === '通过'"
                  class="pass-dot"
                  title="第该章专家体检合格"
                >✓</span>

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
                  @click="scrollToSubheading(ch.seq, sub.id, $event)"
                  :title="sub.title"
                >
                  <span class="sub-bullet">{{ sub.level === 2 ? '🔹' : sub.level === 3 ? '▪' : '▫' }}</span>
                  <span class="sub-text">{{ sub.title }}</span>
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

          <div class="full-book-scroll-canvas">
            <div
              v-for="ch in projectStore.outlineChapters"
              :key="ch.seq"
              :id="`full-chapter-anchor-${ch.seq}`"
              class="full-book-chapter-block"
            >
              <!-- 优雅章节分节头部 -->
              <div class="chapter-block-header">
                <div class="ch-header-left">
                  <span class="chapter-seq-circle">第 {{ ch.seq }} 章</span>
                  <h3 class="chapter-block-title">{{ ch.title }}</h3>
                  <span class="chapter-word-count">
                    {{ (projectStore.chapters[ch.seq] || '').length.toLocaleString() }} 字
                  </span>

                  <!-- 诊断状态 Badge -->
                  <span
                    v-if="projectStore.chapterReviews[ch.seq]"
                    class="chapter-review-badge"
                    :class="`status-${projectStore.chapterReviews[ch.seq].status}`"
                  >
                    {{
                      projectStore.chapterReviews[ch.seq].status === '通过'
                        ? '✅ 达标'
                        : projectStore.chapterReviews[ch.seq].status
                    }}
                  </span>
                  <span v-else class="chapter-review-badge status-idle">
                    未审阅
                  </span>

                  <!-- 预警提示 -->
                  <span
                    v-if="(chapterIssuesCount[ch.seq] || 0) > 0"
                    class="chapter-issues-tag"
                    title="点击可前往右侧抽屉查阅具体问题与建议"
                    @click="showDiagnosticDrawer = true"
                  >
                    ⚠️ {{ chapterIssuesCount[ch.seq] }} 处待核
                  </span>
                </div>

                <div class="ch-header-right">
                  <button
                    class="btn btn-outline btn-xs"
                    @click="openRevisionModal(ch.seq)"
                    title="针对本章设置修改指令进行 AI 修订"
                  >
                    ✍️ 本章AI修订
                  </button>
                  <button
                    class="btn btn-outline btn-xs"
                    @click="handleRunSingleReview(ch.seq)"
                    title="针对本章单独运行专家体检"
                  >
                    🔍 重新审阅
                  </button>
                </div>
              </div>

              <!-- 就地排版编辑器画布 (contenteditable) -->
              <div
                :id="`chapter-canvas-${ch.seq}`"
                class="rich-rendered-editor spec-typography"
                contenteditable="true"
                :data-seq="ch.seq"
                @input="onChapterInput(ch.seq, $event)"
                data-placeholder="本章节暂未生成内容。可在此处直接输入排版文字，或返回步骤 3 自动写作..."
              ></div>

              <!-- 优雅章节分界线 -->
              <div class="chapter-divider-rule">
                <span class="rule-line"></span>
                <span class="rule-label">第 {{ ch.seq }} 章 完</span>
                <span class="rule-line"></span>
              </div>
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
              <div v-if="projectStore.activeRevision" class="diff-instruction-summary">
                <strong>修改指令：</strong>{{ projectStore.activeRevision.instruction }}
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
                :disabled="!hasActiveRevision"
                @click="handleApplyRevision"
                title="采纳本次 AI 修订结果并保存覆盖为最新正文"
              >
                ✅ 采纳全部修订并保存
              </button>
              <button
                class="btn btn-outline"
                :disabled="!hasActiveRevision"
                @click="openRevisionModal(projectStore.activeRevision?.seq || 1, projectStore.activeRevision?.instruction)"
                title="调整修改指令重新生成"
              >
                🔄 重新生成
              </button>
              <button
                class="btn btn-outline btn-danger-text"
                :disabled="!hasActiveRevision"
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
              <p>您可以点击顶栏「✍️ AI智能修订」或在各章节头部点击「✍️ 本章AI修订」，系统将自动生成段落级 Diff 对比。</p>
              <button class="btn btn-primary" @click="openRevisionModal(activeChapterSeq || 1)">
                立即发起 AI 智能修订
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
              <span>全书共 <strong>{{ totalWordCount.toLocaleString() }}</strong> 字符</span>
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
                <span class="source-len">{{ (projectStore.chapters[ch.seq] || '').length }} 字符</span>
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
              >
                🚀 重新运行全书全维专家审阅
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
                      @click="locateIssueInCanvas(issue.location, issue.chapterSeq)"
                    >
                      🎯 点击定位正文段落 &rarr;
                    </button>
                    <button
                      class="btn-text-link link-primary"
                      @click="openRevisionModal(issue.chapterSeq || 1, issue.suggestion || issue.message)"
                    >
                      ✍️ 填入AI修订指令
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
                      @click="openRevisionModal(gap.chapterSeq || 1, `依据规程要求，在正文中补充说明【${gap.gap}】的前置审批与支撑依据。`)"
                    >
                      ✍️ 填入AI修订指令
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
                    <span>字数：{{ (projectStore.chapters[ch.seq] || '').length }}</span>
                    <span>问题：{{ chapterIssuesCount[ch.seq] || 0 }} 处</span>
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

    <!-- ═════════════════════════════════════════════════════════ -->
    <!-- AI 智能修订弹窗 (Revision Modal) -->
    <!-- ═════════════════════════════════════════════════════════ -->
    <transition name="fade">
      <div v-if="showRevisionModal" class="modal-overlay" @click="showRevisionModal = false">
        <div class="revision-modal-card" @click.stop>
          <div class="modal-header">
            <div class="modal-title-box">
              <h3>✍️ AI 智能定向修订</h3>
              <span class="modal-sub">依据国家发改委与行业编制规程，对正文进行方案深化、数据校核与专业润色</span>
            </div>
            <button class="modal-close-btn" @click="showRevisionModal = false">✕</button>
          </div>

          <div class="modal-body">
            <!-- 修订目标章节选择 -->
            <div class="form-group">
              <label class="form-label">🎯 修订目标章节：</label>
              <select v-model="targetRevisionSeq" class="form-select">
                <option
                  v-for="ch in projectStore.outlineChapters"
                  :key="ch.seq"
                  :value="ch.seq"
                >
                  第 {{ ch.seq }} 章：{{ ch.title }}
                </option>
              </select>
            </div>

            <!-- 快捷预设指令 Chips -->
            <div class="form-group">
              <label class="form-label">💡 常用工程咨询修改预设：</label>
              <div class="preset-chips-list">
                <button
                  v-for="(preset, pIdx) in presetInstructions"
                  :key="pIdx"
                  class="preset-chip"
                  @click="applyPresetInstruction(preset)"
                >
                  {{ preset }}
                </button>
              </div>
            </div>

            <!-- 自定义修订指令输入框 -->
            <div class="form-group">
              <label class="form-label">📝 定向修改指令 (Instruction)：</label>
              <textarea
                v-model="revisionInstruction"
                class="revision-textarea"
                rows="4"
                placeholder="例如：依据国家发改委投资估算编制要求，统一第 2 章与第 7 章的投资估算数据口径，并补充节能环保合规论述..."
              ></textarea>
            </div>

            <!-- 修订执行中阶段动态心跳 -->
            <div v-if="projectStore.revisingSeq !== null" class="modal-heartbeat-box">
              <div class="hb-title-row">
                <span class="radar-pulse"></span>
                <strong>AI 智能修订重构中... (已耗时 {{ revisionElapsedSeconds }} 秒)</strong>
              </div>
              <div class="hb-stepper">
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

          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showRevisionModal = false">取消</button>
            <button
              class="btn btn-primary"
              :disabled="!revisionInstruction.trim() || projectStore.revisingSeq !== null"
              @click="handleExecuteRevision"
            >
              {{ projectStore.revisingSeq !== null ? '⚡ 正在智能修订中...' : '🚀 开始执行 AI 修订' }}
            </button>
          </div>
        </div>
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
}
.radar-pulse {
  width: 10px;
  height: 10px;
  background: #3b82f6;
  border-radius: 50%;
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
.hb-title-box {
  display: flex;
  flex-direction: column;
}
.hb-title-box strong {
  font-size: 13px;
  color: #1e3a8a;
}
.hb-desc {
  font-size: 11px;
  color: #3b82f6;
}

.hb-stepper {
  display: flex;
  align-items: center;
  gap: 12px;
}
.stepper-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
}
.stepper-item.active {
  color: #1d4ed8;
  font-weight: 600;
}
.stepper-item.completed {
  color: #059669;
  font-weight: 500;
}
.stepper-circle {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}
.stepper-item.active .stepper-circle {
  background: #3b82f6;
  color: #fff;
}
.stepper-item.completed .stepper-circle {
  background: #10b981;
  color: #fff;
}
.spinner-mini {
  width: 10px;
  height: 10px;
  border: 2px solid #fff;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.hb-timer {
  font-size: 12px;
  color: #475569;
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

/* 左侧栏：全书多级标题导航 */
.sidebar-nav-panel {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.nav-panel-header {
  padding: 12px 14px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
}
.nav-header-title {
  display: flex;
  align-items: center;
  gap: 6px;
}
.nav-header-title h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}
.nav-count {
  font-size: 11px;
  color: #64748b;
  background: #e2e8f0;
  padding: 1px 6px;
  border-radius: 10px;
}
.nav-quick-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}
.btn-text-action {
  background: transparent;
  border: none;
  font-size: 11px;
  color: #2563eb;
  cursor: pointer;
  padding: 2px 4px;
}
.btn-text-action:hover {
  text-decoration: underline;
}
.action-divider {
  color: #cbd5e1;
  font-size: 11px;
}

.outline-tree-scrollable {
  flex: 1;
  overflow-y: auto;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.empty-outline-tip {
  padding: 20px;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
}

/* 章节树节点 */
.chapter-tree-node {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
  overflow: hidden;
  transition: all 0.15s ease;
}
.chapter-tree-node.is-active {
  border-color: #3b82f6;
  box-shadow: 0 0 0 1px #3b82f6;
}
.chapter-tree-node.has-warning {
  border-left: 3px solid #f59e0b;
}

.chapter-node-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  cursor: pointer;
  user-select: none;
  background: #fff;
  transition: background 0.15s ease;
}
.chapter-node-row:hover {
  background: #f8fafc;
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
.ch-title-text {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-right {
  display: flex;
  align-items: center;
  gap: 6px;
}
.warning-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f59e0b;
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

/* 子标题层级 */
.subheadings-subtree {
  padding: 2px 0 6px 0;
  background: #fafafa;
  border-top: 1px solid #f1f5f9;
}
.subheading-item-row {
  padding: 4px 10px 4px 28px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 11px;
  color: #64748b;
  transition: all 0.12s ease;
}
.subheading-item-row:hover {
  background: #f1f5f9;
  color: #0f172a;
}
.subheading-item-row.level-3 {
  padding-left: 40px;
}
.subheading-item-row.level-4 {
  padding-left: 52px;
}
.subheading-item-row.is-active-heading {
  color: #2563eb;
  font-weight: 600;
  background: #eff6ff;
}
.sub-bullet {
  font-size: 8px;
  opacity: 0.6;
}
.sub-text {
  overflow: hidden;
  text-overflow: ellipsis;
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
  margin-bottom: 36px;
  scroll-margin-top: 16px;
}

.chapter-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 16px;
}
.ch-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.chapter-seq-circle {
  background: #2563eb;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}
.chapter-block-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}
.chapter-word-count {
  font-size: 12px;
  color: #64748b;
}
.chapter-review-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}
.chapter-review-badge.status-通过 {
  background: #dcfce7;
  color: #15803d;
}
.chapter-review-badge.status-需补充 {
  background: #fef3c7;
  color: #b45309;
}
.chapter-review-badge.status-风险警告 {
  background: #fee2e2;
  color: #b91c1c;
}
.chapter-review-badge.status-idle {
  background: #f1f5f9;
  color: #64748b;
}
.chapter-issues-tag {
  background: #fef2f2;
  color: #b91c1c;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
}
.chapter-issues-tag:hover {
  text-decoration: underline;
}

.ch-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
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
  margin: 16px 0;
  font-size: 13px;
}
.spec-typography th,
.spec-typography td {
  border: 1px solid #cbd5e1;
  padding: 8px 12px;
  text-align: left;
}
.spec-typography th {
  background: #f1f5f9;
  font-weight: 600;
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

.chapter-divider-rule {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 28px 0 16px 0;
}
.rule-line {
  flex: 1;
  height: 1px;
  background: #e2e8f0;
}
.rule-label {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
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
  flex-direction: column;
  gap: 4px;
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
.diff-instruction-summary {
  font-size: 12px;
  color: #475569;
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

/* ═════════════════════════════════════════════════════════ */
/* AI 修订弹窗 (Revision Modal) */
/* ═════════════════════════════════════════════════════════ */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(3px);
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
}
.revision-modal-card {
  width: 580px;
  max-width: 92vw;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  background: #f8fafc;
}
.modal-title-box h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}
.modal-sub {
  font-size: 12px;
  color: #64748b;
}
.modal-close-btn {
  background: transparent;
  border: none;
  font-size: 16px;
  color: #64748b;
  cursor: pointer;
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-label {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}
.form-select {
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
}
.preset-chips-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.preset-chip {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11px;
  color: #334155;
  cursor: pointer;
  text-align: left;
  line-height: 1.4;
  transition: all 0.12s ease;
}
.preset-chip:hover {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
}

.revision-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.5;
  box-sizing: border-box;
  resize: vertical;
  outline: none;
}
.revision-textarea:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.modal-heartbeat-box {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.hb-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #15803d;
}

.modal-footer {
  padding: 12px 20px;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
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
