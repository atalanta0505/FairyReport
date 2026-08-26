<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import {
  computeDiffBlocks,
  computeDiffStats,
  computeLineDiff,
  type DiffBlock,
  type DiffLine,
  type DiffStats,
} from "../lib/diff";
import {
  extractOutlineHeadings,
  extractReferences,
  htmlToMarkdown,
  markdownToHtml,
  type ReferenceItem,
} from "../lib/markdown";
import { useEngineStore } from "../stores/engine";
import { useProjectStore } from "../stores/project";
import { useSettingsStore } from "../stores/settings";

const engine = useEngineStore();
const settings = useSettingsStore();
const projectStore = useProjectStore();

// 视图切换：chapter(章节精审) | preview(全书预览) | dashboard(质量看板)
const viewTab = ref<"chapter" | "preview" | "dashboard">("chapter");

// 章节编辑器视图：rich(排版就地编辑) | source(源码编辑)
const editorMode = ref<"rich" | "source">("rich");

// Diff 差异对比视图模式：sideBySide(左右双栏) | inline(单栏内联)
const diffViewMode = ref<"sideBySide" | "inline">("sideBySide");

// 专家诊断卡片展开/收起
const isDiagnosticExpanded = ref<boolean>(true);
const diagnosticSubTab = ref<"issues" | "numerical" | "gaps" | "suggestions">("issues");

// AI 修订输入框与快捷提示
const showRevisionPromptBar = ref<boolean>(false);
const revisionInstruction = ref<string>("");

// 参考资料来源清单抽屉展开/收起
const showRefDrawer = ref<boolean>(false);

// 全局操作通知
const actionMessage = ref<{ type: "success" | "error" | "info"; text: string } | null>(null);

// 审阅动态心跳与计时器
const reviewElapsedSeconds = ref<number>(0);
const reviewStageIndex = ref<number>(0);
let reviewTimer: ReturnType<typeof setInterval> | null = null;

const reviewStages = [
  { id: "params", title: "关键参数抽取", desc: "提取投资、规模与关键工程技术指标" },
  { id: "compliance", title: "规程合规审查", desc: "对照国家发改委与水利行业标准规程" },
  { id: "consistency", title: "数值前后自洽", desc: "排查跨章节数据勾稽与量纲自洽性" },
  { id: "report", title: "诊断报告生成", desc: "综合生成专家评审意见与批注" },
];

// 修订动态心跳与计时器
const revisionElapsedSeconds = ref<number>(0);
const revisionStageIndex = ref<number>(0);
let revisionTimer: ReturnType<typeof setInterval> | null = null;

const revisionStages = [
  { id: "context", title: "解析上下文", desc: "分析章节脉络与专家修改指令" },
  { id: "restructure", title: "重构方案论述", desc: "依据规程深化工艺与分项估算" },
  { id: "polish", title: "技术规范润色", desc: "压制套话，规范工程术语与数据" },
  { id: "diff", title: "生成 Diff 对比", desc: "构建精准差异比对视图" },
];

// 双栏 Diff 联动滚动同步锁
const originalColRef = ref<HTMLDivElement | null>(null);
const revisedColRef = ref<HTMLDivElement | null>(null);
let isSyncingScroll = false;

const editorCanvasRef = ref<HTMLDivElement | null>(null);
let saveDebounceTimer: ReturnType<typeof setTimeout> | null = null;

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
    } catch {
      // ignore
    }
  }
}

function syncEditorContent() {
  if (editorCanvasRef.value && editorMode.value === "rich") {
    editorCanvasRef.value.innerHTML = markdownToHtml(
      currentChapterText.value,
      currentChapter.value?.seq,
      outlineHeadings.value,
    );
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
});

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
  () => projectStore.selectedChapterSeq,
  () => {
    nextTick(() => {
      syncEditorContent();
    });
  },
);

watch(editorMode, (mode) => {
  if (mode === "rich") {
    nextTick(() => {
      syncEditorContent();
    });
  }
});

// 计算属性
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

const reviewedCount = computed(() => {
  let count = 0;
  for (const ch of projectStore.outlineChapters) {
    if (projectStore.chapterReviews[ch.seq]) {
      count++;
    }
  }
  return count;
});

const totalIssuesCount = computed(() => {
  let count = 0;
  for (const r of Object.values(projectStore.chapterReviews)) {
    if (r?.issues) {
      count += r.issues.length;
    }
  }
  return count;
});

const passCount = computed(() => {
  let count = 0;
  for (const r of Object.values(projectStore.chapterReviews)) {
    if (r?.status === "通过") {
      count++;
    }
  }
  return count;
});

const passRate = computed(() => {
  if (totalChapters.value === 0) return 0;
  return Math.round((passCount.value / totalChapters.value) * 100);
});

const overallAverageScore = computed(() => {
  const scores: number[] = [];
  for (const r of Object.values(projectStore.chapterReviews)) {
    if (typeof r?.score === "number") {
      scores.push(r.score);
    }
  }
  if (scores.length === 0) return 0;
  return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
});

const currentChapter = computed(() => {
  return (
    projectStore.outlineChapters.find((c) => c.seq === projectStore.selectedChapterSeq) ||
    projectStore.outlineChapters[0] ||
    null
  );
});

const currentChapterText = computed({
  get: () => {
    const seq = projectStore.selectedChapterSeq;
    return projectStore.chapters[seq] || "";
  },
  set: (val: string) => {
    projectStore.saveChapter(engine.baseUrl, projectStore.selectedChapterSeq, val);
  },
});

const currentChapterReview = computed(() => {
  return projectStore.chapterReviews[projectStore.selectedChapterSeq] || null;
});

const isReviewingCurrent = computed(() => {
  return projectStore.reviewingSeq === projectStore.selectedChapterSeq;
});

const isRevisingCurrent = computed(() => {
  return projectStore.revisingSeq === projectStore.selectedChapterSeq;
});

// 本章参考资料列表与总引用频次
const currentChapterReferences = computed<ReferenceItem[]>(() => {
  return extractReferences(currentChapterText.value);
});

const totalRefCitations = computed(() => {
  return currentChapterReferences.value.reduce((sum, item) => sum + item.count, 0);
});

// Diff 对比计算
const hasActiveRevisionForCurrent = computed(() => {
  return (
    projectStore.activeRevision !== null &&
    projectStore.activeRevision.seq === projectStore.selectedChapterSeq
  );
});

const currentDiffLines = computed<DiffLine[]>(() => {
  if (!hasActiveRevisionForCurrent.value || !projectStore.activeRevision) {
    return [];
  }
  return computeLineDiff(
    projectStore.activeRevision.originalText,
    projectStore.activeRevision.revisedText,
    outlineHeadings.value,
  );
});

const currentDiffBlocks = computed<DiffBlock[]>(() => {
  if (!hasActiveRevisionForCurrent.value || !projectStore.activeRevision) {
    return [];
  }
  return computeDiffBlocks(
    projectStore.activeRevision.originalText,
    projectStore.activeRevision.revisedText,
    outlineHeadings.value,
  );
});

const currentDiffStats = computed<DiffStats>(() => {
  if (!hasActiveRevisionForCurrent.value || !projectStore.activeRevision) {
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

// 全书跨章指标比对汇总表
const allNumericalChecks = computed(() => {
  const list: {
    chapterSeq: number;
    chapterTitle: string;
    parameter: string;
    extracted_value: string;
    status: string;
    note: string;
  }[] = [];

  for (const ch of projectStore.outlineChapters) {
    const rev = projectStore.chapterReviews[ch.seq];
    if (rev?.numerical_checks && rev.numerical_checks.length > 0) {
      for (const nc of rev.numerical_checks) {
        list.push({
          chapterSeq: ch.seq,
          chapterTitle: ch.title,
          parameter: nc.parameter,
          extracted_value: nc.extracted_value,
          status: nc.status,
          note: nc.note || "",
        });
      }
    }
  }
  return list;
});

// 全书缺失资料总台账
const allDataGaps = computed(() => {
  const list: {
    chapterSeq: number;
    chapterTitle: string;
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

// 全书连续拼接 Markdown 与 HTML
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

const fullBookHtml = computed(() => {
  return markdownToHtml(fullBookMarkdown.value, undefined, outlineHeadings.value);
});

// 交互操作
function selectChapter(seq: number) {
  projectStore.selectChapter(seq);
  viewTab.value = "chapter";
}

function onEditorInput(e: Event) {
  const target = e.target as HTMLElement;
  const html = target.innerHTML;
  const md = htmlToMarkdown(html);

  if (saveDebounceTimer) {
    clearTimeout(saveDebounceTimer);
  }
  saveDebounceTimer = setTimeout(() => {
    if (engine.baseUrl && projectStore.selectedChapterSeq) {
      projectStore.saveChapter(engine.baseUrl, projectStore.selectedChapterSeq, md);
    }
  }, 300);
}

function onSourceInput(e: Event) {
  const target = e.target as HTMLTextAreaElement;
  currentChapterText.value = target.value;
}

// 左右双栏 Diff 同步滚动比例联动
function onOriginalScroll(e: Event) {
  if (isSyncingScroll) return;
  isSyncingScroll = true;
  const source = e.target as HTMLElement;
  if (revisedColRef.value && source) {
    const maxScroll = source.scrollHeight - source.clientHeight;
    const pct = maxScroll > 0 ? source.scrollTop / maxScroll : 0;
    const targetMax = revisedColRef.value.scrollHeight - revisedColRef.value.clientHeight;
    revisedColRef.value.scrollTop = pct * targetMax;
  }
  requestAnimationFrame(() => {
    isSyncingScroll = false;
  });
}

function onRevisedScroll(e: Event) {
  if (isSyncingScroll) return;
  isSyncingScroll = true;
  const source = e.target as HTMLElement;
  if (originalColRef.value && source) {
    const maxScroll = source.scrollHeight - source.clientHeight;
    const pct = maxScroll > 0 ? source.scrollTop / maxScroll : 0;
    const targetMax = originalColRef.value.scrollHeight - originalColRef.value.clientHeight;
    originalColRef.value.scrollTop = pct * targetMax;
  }
  requestAnimationFrame(() => {
    isSyncingScroll = false;
  });
}

// 专家审阅
async function handleRunReview(mode: "all" | "compliance" | "numeric" | "technical" = "all") {
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

  const seq = projectStore.selectedChapterSeq;
  const label =
    mode === "all"
      ? "全维专家审阅"
      : mode === "compliance"
      ? "合规审查"
      : mode === "numeric"
      ? "数值核验"
      : "技术审校";

  // 启动审阅前摇计时器与阶段轮播
  reviewElapsedSeconds.value = 0;
  reviewStageIndex.value = 0;
  if (reviewTimer) clearInterval(reviewTimer);
  reviewTimer = setInterval(() => {
    reviewElapsedSeconds.value += 1;
    // 每 3 秒步进一个阶段（循环轮播）
    reviewStageIndex.value = Math.min(3, Math.floor(reviewElapsedSeconds.value / 3));
  }, 1000);

  try {
    showMsg(`正在对第 ${seq} 章启动「${label}」，请稍候...`, "info");
    const result = await projectStore.runChapterReview(engine.baseUrl, seq, mode, llmConfig);
    isDiagnosticExpanded.value = true;
    showMsg(`第 ${seq} 章「${label}」完成！得分：${result.score ?? 85} 分，状态：${result.status}`);
  } catch (err) {
    showMsg(`审阅失败：${(err as Error).message}`, "error");
  } finally {
    if (reviewTimer) {
      clearInterval(reviewTimer);
      reviewTimer = null;
    }
  }
}

// AI 定向修订
async function handleRunRevision(customInstruction?: string) {
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

  const seq = projectStore.selectedChapterSeq;
  const instruction = customInstruction || revisionInstruction.value;
  if (!instruction.trim()) {
    showMsg("请输入修改指令或点击建议填入", "error");
    return;
  }

  // 启动修订前摇计时器与阶段轮播
  revisionElapsedSeconds.value = 0;
  revisionStageIndex.value = 0;
  if (revisionTimer) clearInterval(revisionTimer);
  revisionTimer = setInterval(() => {
    revisionElapsedSeconds.value += 1;
    revisionStageIndex.value = Math.min(3, Math.floor(revisionElapsedSeconds.value / 3));
  }, 1000);

  try {
    showMsg(`正在对第 ${seq} 章执行 AI 定向修订并生成 Diff 对比...`, "info");
    await projectStore.runChapterRevision(engine.baseUrl, seq, instruction, llmConfig);
    showMsg(`第 ${seq} 章修订完成！已进入 Diff 差异比对工作台。`);
  } catch (err) {
    showMsg(`修订失败：${(err as Error).message}`, "error");
  } finally {
    if (revisionTimer) {
      clearInterval(revisionTimer);
      revisionTimer = null;
    }
  }
}

async function handleApplyRevision() {
  if (!projectStore.activeRevision) return;
  const seq = projectStore.activeRevision.seq;
  await projectStore.applyRevision(engine.baseUrl, seq);
  syncEditorContent();
  showMsg(`已采纳第 ${seq} 章的修订并保存为最新正文！`);
}

function handleDiscardRevision() {
  projectStore.discardRevision();
  syncEditorContent();
  showMsg("已放弃本次修订结果，恢复原正文。", "info");
}

function fillRevisionInstruction(text: string) {
  showRevisionPromptBar.value = true;
  revisionInstruction.value = text;
}

// 批量全书体检
async function handleBatchReviewAll(forceAll = false) {
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

  const unreviewed = projectStore.outlineChapters.filter((ch) => {
    const text = projectStore.chapters[ch.seq];
    return text && text.trim().length > 0 && (forceAll || !projectStore.chapterReviews[ch.seq]);
  });

  if (unreviewed.length === 0) {
    showMsg("全书所有已写章节均已完成专家审阅。如需重新体检请使用强制模式。", "info");
    return;
  }

  try {
    showMsg(`已启动 ${unreviewed.length} 个章节的批量全书体检任务...`, "info");
    await projectStore.runAllChaptersReview(engine.baseUrl, llmConfig, forceAll);
    showMsg("全书一键综合体检完成！可在质量看板中查阅全书健康矩阵。");
  } catch (err) {
    showMsg(`批量体检中断：${(err as Error).message}`, "error");
  }
}

function handleStopBatchReview() {
  projectStore.stopBatchReview();
  showMsg("已中止批量全书体检", "info");
}

function copyFullBookText() {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(fullBookMarkdown.value);
    showMsg("已复制全书排版 Markdown 全文至剪贴板！");
  }
}

function jumpToPreviewAnchor(seq: number) {
  const el = document.getElementById(`full-chapter-anchor-${seq}`);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}
</script>

<template>
  <div class="step4-container">
    <!-- 顶部操作与状态提示条 -->
    <transition name="fade">
      <div v-if="actionMessage" :class="['alert-banner', actionMessage.type]">
        {{ actionMessage.text }}
      </div>
    </transition>

    <!-- 主工作区布局 -->
    <div class="review-layout">
      <!-- 左侧：章节目录与评审导航 -->
      <aside class="sidebar-panel card">
        <div class="card-header sidebar-header">
          <div class="header-titles">
            <h3>专家审阅与修改</h3>
            <span class="proj-badge">{{ projectStore.currentProject?.name || "未选项目" }}</span>
          </div>

          <!-- 全书一键综合体检快捷入口 -->
          <div class="batch-review-bar">
            <button
              v-if="projectStore.batchReviewing"
              class="btn btn-danger btn-block btn-sm"
              @click="handleStopBatchReview"
            >
              ⏹ 停止全书体检
            </button>
            <button
              v-else
              class="btn btn-primary btn-block btn-sm batch-btn"
              :disabled="completedChaptersCount === 0"
              @click="handleBatchReviewAll(false)"
              title="在后台自动对所有未审阅章节执行全维深度体检"
            >
              🚀 全书一键综合体检
            </button>
          </div>

          <!-- 全局质量指标小看板 -->
          <div class="quality-mini-board">
            <div class="mini-stat-card">
              <span class="mini-stat-val">{{ reviewedCount }}/{{ totalChapters }}</span>
              <span class="mini-stat-lbl">已审阅</span>
            </div>
            <div class="mini-stat-card">
              <span class="mini-stat-val" :class="{ 'stat-warning': totalIssuesCount > 0 }">{{ totalIssuesCount }}</span>
              <span class="mini-stat-lbl">待修正项</span>
            </div>
            <div class="mini-stat-card">
              <span class="mini-stat-val" :class="passRate >= 80 ? 'stat-success' : 'stat-warning'">{{ passRate }}%</span>
              <span class="mini-stat-lbl">达标率</span>
            </div>
          </div>

          <!-- 三大视图切换 Tab -->
          <div class="view-tabs-row">
            <button
              class="view-tab-btn"
              :class="{ active: viewTab === 'chapter' }"
              @click="viewTab = 'chapter'"
            >
              📋 章节精审
            </button>
            <button
              class="view-tab-btn"
              :class="{ active: viewTab === 'preview' }"
              @click="viewTab = 'preview'"
            >
              📄 全书预览
            </button>
            <button
              class="view-tab-btn"
              :class="{ active: viewTab === 'dashboard' }"
              @click="viewTab = 'dashboard'"
            >
              📊 质量看板
            </button>
          </div>
        </div>

        <!-- 章节列表导航（在章节精审与全书预览时可用） -->
        <div class="chapter-list">
          <div
            v-for="ch in projectStore.outlineChapters"
            :key="ch.seq"
            class="chapter-review-card"
            :class="{
              active: viewTab === 'chapter' && projectStore.selectedChapterSeq === ch.seq,
              hasReview: !!projectStore.chapterReviews[ch.seq],
              reviewPassed: projectStore.chapterReviews[ch.seq]?.status === '通过',
              reviewNeedsSupplement: projectStore.chapterReviews[ch.seq]?.status === '需补充',
              reviewWarning: projectStore.chapterReviews[ch.seq]?.status === '风险警告',
              hasRevision: projectStore.activeRevision?.seq === ch.seq,
            }"
            @click="viewTab === 'preview' ? jumpToPreviewAnchor(ch.seq) : selectChapter(ch.seq)"
          >
            <div class="ch-card-top">
              <span class="ch-seq">{{ ch.seq }}</span>
              <span class="ch-title" :title="ch.title">{{ ch.title }}</span>
            </div>

            <div class="ch-card-meta">
              <span class="ch-words">{{ (projectStore.chapters[ch.seq] || "").length }} 字</span>

              <!-- 审阅状态微徽章 -->
              <span
                v-if="projectStore.chapterReviews[ch.seq]"
                class="review-badge"
                :class="
                  projectStore.chapterReviews[ch.seq].status === '通过'
                    ? 'badge-success'
                    : projectStore.chapterReviews[ch.seq].status === '需补充'
                    ? 'badge-warning'
                    : 'badge-danger'
                "
              >
                {{ projectStore.chapterReviews[ch.seq].status === '通过' ? '✅ 达标' : projectStore.chapterReviews[ch.seq].status }}
                ({{ projectStore.chapterReviews[ch.seq].score ?? 85 }}分)
              </span>
              <span v-else class="review-badge badge-idle">未审阅</span>

              <span v-if="projectStore.activeRevision?.seq === ch.seq" class="diff-active-tag">
                Diff 对比中
              </span>
            </div>
          </div>

          <div v-if="totalChapters === 0" class="empty-tip">
            暂无章节目录，请先在步骤 2 生成大纲并在步骤 3 写作。
          </div>
        </div>
      </aside>

      <!-- 右侧：主工作台 -->
      <main class="main-workbench card">
        <!-- ═════════════════════════════════════════════════════════════════ -->
        <!-- 视图 1：章节精审工作台 -->
        <!-- ═════════════════════════════════════════════════════════════════ -->
        <section v-if="viewTab === 'chapter'" class="workbench-section">
          <!-- 顶部操作栏 -->
          <div class="card-header chapter-workbench-header">
            <div class="workbench-title-area">
              <div class="title-line">
                <span class="ch-tag" v-if="currentChapter">第 {{ currentChapter.seq }} 章</span>
                <h3 class="current-title">{{ currentChapter?.title || "未选择章节" }}</h3>
              </div>
              <div class="meta-line">
                <span class="meta-item">正文字数：<strong>{{ currentChapterText.length.toLocaleString() }}</strong> 字</span>
                <span class="meta-divider">|</span>
                <span class="meta-item" v-if="currentChapterReview">
                  诊断结论：<strong :class="currentChapterReview.status === '通过' ? 'text-success' : 'text-warning'">{{ currentChapterReview.status }}</strong>
                  （{{ currentChapterReview.score ?? 85 }} 分）
                </span>
                <span class="meta-item text-muted" v-else>尚未进行专家审阅</span>
              </div>
              <!-- 功能定位与使用场景提示 -->
              <div class="review-mode-hints">
                <span class="hint-tag hint-all" title="全科综合评分 0~100 分，全维审查政策合规、数值计算、技术方案与文字表述">
                  🔍 全维：全科综合 (0~100分)
                </span>
                <span class="hint-tag hint-numeric" title="关键指标自洽性排查，专项核验投资估算、产能指标与跨段落数据勾稽">
                  📏 数值：关键指标自洽排查
                </span>
                <span class="hint-tag hint-compliance" title="国家发改委与水利行业规程符合性审查，核实法规标准与审批要件">
                  ⚖️ 合规：发改委/水利规程审查
                </span>
              </div>
            </div>

            <!-- 操作按钮组 -->
            <div class="header-action-group">
              <button
                class="btn btn-outline"
                :disabled="!currentChapterText.trim() || isReviewingCurrent"
                @click="handleRunReview('all')"
                title="全科综合（0~100 分），全维审查政策合规、数值计算、技术方案与文字表述"
              >
                <span v-if="isReviewingCurrent && projectStore.reviewingMode === 'all'" class="spinner-inline"></span>
                🔍 全维专家审阅
              </button>
              <button
                class="btn btn-outline"
                :disabled="!currentChapterText.trim() || isReviewingCurrent"
                @click="handleRunReview('numeric')"
                title="关键指标自洽性排查，提取并专项核验工程参数、投资估算与指标前后自洽"
              >
                <span v-if="isReviewingCurrent && projectStore.reviewingMode === 'numeric'" class="spinner-inline"></span>
                📏 数值校验
              </button>
              <button
                class="btn btn-outline"
                :disabled="!currentChapterText.trim() || isReviewingCurrent"
                @click="handleRunReview('compliance')"
                title="国家发改委与水利规程符合性审查，核实法规、规范标准与前置审批要件"
              >
                <span v-if="isReviewingCurrent && projectStore.reviewingMode === 'compliance'" class="spinner-inline"></span>
                ⚖️ 合规审查
              </button>
              <button
                class="btn btn-primary"
                :class="{ active: showRevisionPromptBar }"
                :disabled="!currentChapterText.trim() || isRevisingCurrent"
                @click="showRevisionPromptBar = !showRevisionPromptBar"
              >
                🔧 AI 定向修订
              </button>
              <!-- 参考资料抽屉入口 -->
              <button
                class="btn btn-outline ref-drawer-btn"
                :class="{ active: showRefDrawer }"
                @click="showRefDrawer = !showRefDrawer"
                title="查看本章正文中命中的底稿文件与规程标准引用清单"
              >
                📚 参考资料 ({{ currentChapterReferences.length }})
              </button>
            </div>
          </div>

          <div class="card-body chapter-workbench-body">
            <!-- ═════════════════════════════════════════════════════════ -->
            <!-- 审阅动态心跳与阶段轮播进度卡片（消除卡死感） -->
            <!-- ═════════════════════════════════════════════════════════ -->
            <transition name="fade">
              <div v-if="isReviewingCurrent" class="heartbeat-card review-heartbeat">
                <div class="heartbeat-header">
                  <div class="hb-badge">
                    <span class="radar-pulse"></span>
                    <span class="hb-title">专家深度审阅诊断进行中</span>
                  </div>
                  <div class="hb-timer">
                    ⏱️ 已审阅 <strong>{{ reviewElapsedSeconds }}</strong> 秒...
                  </div>
                </div>

                <!-- 4 阶段进度条指示器 -->
                <div class="pipeline-stepper">
                  <div
                    v-for="(stage, idx) in reviewStages"
                    :key="stage.id"
                    class="stepper-node"
                    :class="{
                      completed: reviewStageIndex > idx,
                      active: reviewStageIndex === idx,
                      pending: reviewStageIndex < idx,
                    }"
                  >
                    <div class="stepper-badge">
                      <span v-if="reviewStageIndex > idx" class="stepper-check">✓</span>
                      <span v-else-if="reviewStageIndex === idx" class="stepper-spinner"></span>
                      <span v-else class="stepper-dot">{{ idx + 1 }}</span>
                    </div>
                    <div class="stepper-text">
                      <span class="stepper-title">{{ stage.title }}</span>
                      <span class="stepper-desc">{{ stage.desc }}</span>
                    </div>
                    <div v-if="idx < reviewStages.length - 1" class="stepper-line" :class="{ completed: reviewStageIndex > idx }"></div>
                  </div>
                </div>

                <div class="hb-status-msg">
                  💡 当前正在执行：{{ reviewStages[reviewStageIndex]?.title }} · {{ reviewStages[reviewStageIndex]?.desc }}
                </div>
              </div>
            </transition>

            <!-- ═════════════════════════════════════════════════════════ -->
            <!-- 修订动态心跳与阶段轮播进度卡片 -->
            <!-- ═════════════════════════════════════════════════════════ -->
            <transition name="fade">
              <div v-if="isRevisingCurrent" class="heartbeat-card revision-heartbeat">
                <div class="heartbeat-header">
                  <div class="hb-badge">
                    <span class="radar-pulse revision-pulse"></span>
                    <span class="hb-title">AI 定向修订重构中</span>
                  </div>
                  <div class="hb-timer">
                    ⚡ 已修订 <strong>{{ revisionElapsedSeconds }}</strong> 秒...
                  </div>
                </div>

                <!-- 4 阶段修订进度条 -->
                <div class="pipeline-stepper">
                  <div
                    v-for="(stage, idx) in revisionStages"
                    :key="stage.id"
                    class="stepper-node"
                    :class="{
                      completed: revisionStageIndex > idx,
                      active: revisionStageIndex === idx,
                      pending: revisionStageIndex < idx,
                    }"
                  >
                    <div class="stepper-badge">
                      <span v-if="revisionStageIndex > idx" class="stepper-check">✓</span>
                      <span v-else-if="revisionStageIndex === idx" class="stepper-spinner"></span>
                      <span v-else class="stepper-dot">{{ idx + 1 }}</span>
                    </div>
                    <div class="stepper-text">
                      <span class="stepper-title">{{ stage.title }}</span>
                      <span class="stepper-desc">{{ stage.desc }}</span>
                    </div>
                    <div v-if="idx < revisionStages.length - 1" class="stepper-line" :class="{ completed: revisionStageIndex > idx }"></div>
                  </div>
                </div>

                <div class="hb-status-msg">
                  ✍️ 当前进展：{{ revisionStages[revisionStageIndex]?.title }} · {{ revisionStages[revisionStageIndex]?.desc }}
                </div>
              </div>
            </transition>

            <!-- ═════════════════════════════════════════════════════════ -->
            <!-- 专家诊断与批注卡片（自适应排版 + 44px 收起胶囊） -->
            <!-- ═════════════════════════════════════════════════════════ -->
            <div v-if="currentChapterReview" class="diagnostic-panel" :class="{ isCollapsed: !isDiagnosticExpanded }">
              <!-- 展开态完整卡片 -->
              <div v-if="isDiagnosticExpanded" class="diagnostic-expanded-box">
                <div class="diagnostic-header" @click="isDiagnosticExpanded = false">
                  <div class="diag-header-left">
                    <span class="diag-icon">🩺</span>
                    <span class="diag-title">专家诊断与批注报告</span>
                    <span
                      class="status-pill"
                      :class="
                        currentChapterReview.status === '通过'
                          ? 'pill-success'
                          : currentChapterReview.status === '需补充'
                          ? 'pill-warning'
                          : 'pill-danger'
                      "
                    >
                      {{ currentChapterReview.status === '通过' ? '✅ 达标通过' : currentChapterReview.status }}
                    </span>
                    <span class="score-pill">综合评分：{{ currentChapterReview.score ?? 85 }} / 100</span>
                  </div>
                  <div class="diag-header-right">
                    <button class="btn-xs-text collapse-btn" @click.stop="isDiagnosticExpanded = false">
                      ▲ 收起诊断详情
                    </button>
                  </div>
                </div>

                <!-- 展开时的诊断详情（自适应滚动排版，彻底解决底部截断） -->
                <div class="diagnostic-content-scrollable">
                  <div class="diag-summary-box" v-if="currentChapterReview.summary">
                    <strong>诊断摘要：</strong>{{ currentChapterReview.summary }}
                  </div>

                  <!-- 诊断子 Tab -->
                  <div class="diag-subtabs">
                    <button
                      class="diag-tab-btn"
                      :class="{ active: diagnosticSubTab === 'issues' }"
                      @click="diagnosticSubTab = 'issues'"
                    >
                      ⚠️ 问题清单 ({{ currentChapterReview.issues?.length || 0 }})
                    </button>
                    <button
                      class="diag-tab-btn"
                      :class="{ active: diagnosticSubTab === 'numerical' }"
                      @click="diagnosticSubTab = 'numerical'"
                    >
                      📐 数值核验表 ({{ currentChapterReview.numerical_checks?.length || 0 }})
                    </button>
                    <button
                      class="diag-tab-btn"
                      :class="{ active: diagnosticSubTab === 'gaps' }"
                      @click="diagnosticSubTab = 'gaps'"
                    >
                      📦 缺失资料清单 ({{ currentChapterReview.data_gap_checklist?.length || 0 }})
                    </button>
                    <button
                      class="diag-tab-btn"
                      :class="{ active: diagnosticSubTab === 'suggestions' }"
                      @click="diagnosticSubTab = 'suggestions'"
                    >
                      💡 综合修改建议
                    </button>
                  </div>

                  <!-- 1. 问题清单 -->
                  <div v-if="diagnosticSubTab === 'issues'" class="diag-tab-content">
                    <div v-if="currentChapterReview.issues && currentChapterReview.issues.length > 0" class="issues-list">
                      <div
                        v-for="(issue, idx) in currentChapterReview.issues"
                        :key="issue.id || idx"
                        class="issue-card"
                        :class="`sev-${issue.severity}`"
                      >
                        <div class="issue-top">
                          <span class="issue-badge" :class="`badge-${issue.severity}`">
                            {{ issue.severity === 'error' ? '🚨 严重错误' : issue.severity === 'warning' ? '⚠️ 警告' : '💡 优化建议' }}
                          </span>
                          <span class="issue-category">{{ issue.category }}</span>
                          <span class="issue-location" v-if="issue.location">📍 {{ issue.location }}</span>
                          <button
                            class="btn-xs-text fill-intent-btn"
                            @click="fillRevisionInstruction(`针对 ${issue.location || '本段'}：${issue.suggestion || issue.message}`)"
                            title="将本条建议代入 AI 修订意图输入框"
                          >
                            代入修订 ✍️
                          </button>
                        </div>
                        <div class="issue-msg">{{ issue.message }}</div>
                        <div class="issue-sugg" v-if="issue.suggestion">
                          <strong>修改建议：</strong>{{ issue.suggestion }}
                        </div>
                      </div>
                    </div>
                    <div v-else class="empty-sub-tip">✓ 未发现明显合规或技术硬伤问题，质量达标。</div>
                  </div>

                  <!-- 2. 数值核验表 -->
                  <div v-if="diagnosticSubTab === 'numerical'" class="diag-tab-content">
                    <table v-if="currentChapterReview.numerical_checks && currentChapterReview.numerical_checks.length > 0" class="diag-table">
                      <thead>
                        <tr>
                          <th>参数/指标名称</th>
                          <th>正文提取数值</th>
                          <th>核验状态</th>
                          <th>核验说明与依据</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(nc, idx) in currentChapterReview.numerical_checks" :key="idx">
                          <td><strong>{{ nc.parameter }}</strong></td>
                          <td><code>{{ nc.extracted_value }}</code></td>
                          <td>
                            <span class="status-dot-pill" :class="`st-${nc.status}`">
                              {{ nc.status === 'normal' ? '✅ 正常自洽' : nc.status === 'abnormal' ? '⚠️ 存在矛盾' : '⏳ 待复核' }}
                            </span>
                          </td>
                          <td>{{ nc.note }}</td>
                        </tr>
                      </tbody>
                    </table>
                    <div v-else class="empty-sub-tip">未提取到关键数值或本章暂无独立技术参数表。</div>
                  </div>

                  <!-- 3. 缺失资料清单 -->
                  <div v-if="diagnosticSubTab === 'gaps'" class="diag-tab-content">
                    <div v-if="currentChapterReview.data_gap_checklist && currentChapterReview.data_gap_checklist.length > 0" class="gaps-list">
                      <div v-for="(gap, idx) in currentChapterReview.data_gap_checklist" :key="idx" class="gap-item">
                        <span class="gap-bullet">📄</span>
                        <span class="gap-text">{{ gap }}</span>
                        <button
                          class="btn-xs-text"
                          @click="fillRevisionInstruction(`补充关于「${gap}」的分析与说明`)"
                        >
                          代入修订
                        </button>
                      </div>
                    </div>
                    <div v-else class="empty-sub-tip">✓ 底稿资料齐全，无需补充前置文件。</div>
                  </div>

                  <!-- 4. 综合建议 -->
                  <div v-if="diagnosticSubTab === 'suggestions'" class="diag-tab-content">
                    <div class="suggestions-box" v-if="currentChapterReview.suggestions">
                      <pre class="suggestions-pre">{{ currentChapterReview.suggestions }}</pre>
                      <button
                        class="btn btn-secondary btn-sm"
                        @click="fillRevisionInstruction(currentChapterReview.suggestions)"
                      >
                        一键代入全部综合建议至修订意图 ✍️
                      </button>
                    </div>
                    <div v-else class="empty-sub-tip">无额外综合修改建议。</div>
                  </div>
                </div>
              </div>

              <!-- 收起态：44px 易点击通栏胶囊条 -->
              <div
                v-else
                class="diagnostic-capsule-collapsed"
                @click="isDiagnosticExpanded = true"
                title="点击展开专家诊断详情"
              >
                <div class="capsule-left">
                  <span class="capsule-icon">🩺</span>
                  <span
                    class="status-pill"
                    :class="
                      currentChapterReview.status === '通过'
                        ? 'pill-success'
                        : currentChapterReview.status === '需补充'
                        ? 'pill-warning'
                        : 'pill-danger'
                    "
                  >
                    {{ currentChapterReview.status === '通过' ? '✅ 达标' : currentChapterReview.status }}
                  </span>
                  <span class="score-pill-sm">{{ currentChapterReview.score ?? 85 }}分</span>
                  <span class="capsule-summary-snippet" :title="currentChapterReview.summary">
                    {{ currentChapterReview.summary || "诊断报告已就绪" }}
                  </span>
                </div>
                <div class="capsule-right">
                  <span class="expand-action-text">[ ▼ 展开诊断详情 ]</span>
                </div>
              </div>
            </div>

            <!-- ═════════════════════════════════════════════════════════ -->
            <!-- AI 定向修订意图输入条 -->
            <!-- ═════════════════════════════════════════════════════════ -->
            <transition name="slide">
              <div v-if="showRevisionPromptBar" class="revision-prompt-box">
                <div class="prompt-header">
                  <span class="prompt-title">🔧 AI 定向修订指令工作台</span>
                  <div class="preset-pills">
                    <span class="preset-pill" @click="revisionInstruction = '请严格对照合规要求，强化政策与规程条文支撑，修正引用的标准编号。'">
                      ⚖️ 强化政策规范
                    </span>
                    <span class="preset-pill" @click="revisionInstruction = '请对各项投资估算、产能与工程量指标进行前后文自洽性修正，补全量纲。'">
                      📐 修正数据矛盾
                    </span>
                    <span class="preset-pill" @click="revisionInstruction = '压制空泛套话，深化工艺路线与多方案客观比选论述，充实技术细节。'">
                      🛡️ 压制空洞套话
                    </span>
                    <span class="preset-pill" @click="revisionInstruction = '根据专家诊断中的问题点全面修改完善本章正文。'">
                      🩺 按专家诊断修正
                    </span>
                  </div>
                </div>
                <div class="prompt-input-row">
                  <textarea
                    class="prompt-textarea"
                    v-model="revisionInstruction"
                    placeholder="请输入对本章节的具体修改指令（如：补充投资估算分项表格、调整第三节工艺比选理由等）..."
                  ></textarea>
                  <button
                    class="btn btn-primary run-revise-btn"
                    :disabled="isRevisingCurrent || !revisionInstruction.trim()"
                    @click="handleRunRevision()"
                  >
                    <span v-if="isRevisingCurrent" class="spinner-inline"></span>
                    🚀 生成修订并在下方 Diff 对比
                  </button>
                </div>
              </div>
            </transition>

            <!-- ═════════════════════════════════════════════════════════ -->
            <!-- 核心展示区域：Diff 差异对比模式 VS 常规排版就地编辑模式 -->
            <!-- ═════════════════════════════════════════════════════════ -->

            <!-- 状态 A：Diff 差异对比工作台（当 activeRevision 激活时） -->
            <div v-if="hasActiveRevisionForCurrent" class="diff-workbench-container">
              <div class="diff-toolbar">
                <div class="diff-toolbar-left">
                  <span class="diff-title-badge">⚡ AI 修订 Diff 差异对比工作台</span>
                  <div class="diff-stats-pills">
                    <span class="diff-pill pill-added">+{{ currentDiffStats.addedLines }} 行新增</span>
                    <span class="diff-pill pill-removed">-{{ currentDiffStats.removedLines }} 行删除</span>
                    <span class="diff-pill pill-unchanged">{{ currentDiffStats.unchangedLines }} 行未变</span>
                  </div>
                </div>
                <div class="diff-toolbar-right">
                  <div class="diff-mode-switcher">
                    <button
                      class="mode-btn"
                      :class="{ active: diffViewMode === 'sideBySide' }"
                      @click="diffViewMode = 'sideBySide'"
                    >
                      双栏左右对比
                    </button>
                    <button
                      class="mode-btn"
                      :class="{ active: diffViewMode === 'inline' }"
                      @click="diffViewMode = 'inline'"
                    >
                      单栏内联高亮
                    </button>
                  </div>
                </div>
              </div>

              <!-- 左右双栏 Diff 视图（带实时比例同步滚动 Sync Scroll） -->
              <div v-if="diffViewMode === 'sideBySide'" class="diff-view-side-by-side">
                <div class="diff-side-column side-original">
                  <div class="diff-column-header">
                    <span>原文正文（修改前）</span>
                    <span class="sync-indicator">↕ 比例联动中</span>
                  </div>
                  <div
                    ref="originalColRef"
                    class="diff-column-content water-spec-typography"
                    @scroll="onOriginalScroll"
                  >
                    <div
                      v-for="(block, bIdx) in currentDiffBlocks"
                      :key="bIdx"
                      class="diff-block"
                      :class="`block-${block.type}`"
                    >
                      <div
                        v-for="(line, lIdx) in block.oldLines"
                        :key="lIdx"
                        class="diff-line-row line-removed"
                      >
                        <span class="line-num">{{ line.lineNumber || ' ' }}</span>
                        <span class="line-code">{{ line.text || ' ' }}</span>
                      </div>
                      <div v-if="block.type === 'added'" class="diff-line-placeholder">
                        <span class="line-num">&nbsp;</span>
                        <span class="line-code">&nbsp;</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="diff-side-column side-revised">
                  <div class="diff-column-header">
                    <span>修订后正文（建议采纳）</span>
                    <span class="sync-indicator">↕ 比例联动中</span>
                  </div>
                  <div
                    ref="revisedColRef"
                    class="diff-column-content water-spec-typography"
                    @scroll="onRevisedScroll"
                  >
                    <div
                      v-for="(block, bIdx) in currentDiffBlocks"
                      :key="bIdx"
                      class="diff-block"
                      :class="`block-${block.type}`"
                    >
                      <div
                        v-for="(line, lIdx) in block.newLines"
                        :key="lIdx"
                        class="diff-line-row line-added"
                      >
                        <span class="line-num">{{ line.lineNumber || ' ' }}</span>
                        <span class="line-code">{{ line.text || ' ' }}</span>
                      </div>
                      <div v-if="block.type === 'removed'" class="diff-line-placeholder">
                        <span class="line-num">&nbsp;</span>
                        <span class="line-code">&nbsp;</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 单栏内联 Diff 视图（段落级删除线与浅绿高亮） -->
              <div v-else class="diff-view-inline water-spec-typography">
                <div class="diff-inline-content">
                  <div
                    v-for="(line, idx) in currentDiffLines"
                    :key="idx"
                    class="diff-inline-row"
                    :class="`inline-${line.type}`"
                  >
                    <span class="inline-line-num old-num">{{ line.oldLineNumber || '' }}</span>
                    <span class="inline-line-num new-num">{{ line.newLineNumber || '' }}</span>
                    <span class="inline-sign">
                      {{ line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' ' }}
                    </span>
                    <span class="inline-code" :class="{ 'strike-del': line.type === 'removed' }">
                      {{ line.text }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Diff 采纳/放弃操作底栏 -->
              <div class="diff-bottom-actions">
                <div class="diff-instruction-preview">
                  <strong>本次修订意图：</strong>{{ projectStore.activeRevision?.instruction }}
                </div>
                <div class="diff-action-btns">
                  <button class="btn btn-secondary" @click="handleDiscardRevision">
                    ↩ 放弃本次修订
                  </button>
                  <button class="btn btn-outline" @click="handleRunRevision()">
                    🔄 重新生成修订
                  </button>
                  <button class="btn btn-primary" @click="handleApplyRevision">
                    ✅ 采纳修订并更新为正文
                  </button>
                </div>
              </div>
            </div>

            <!-- 状态 B：常规单栏排版就地可编辑画布（非 Diff 状态） -->
            <div v-else class="canvas-wrapper">
              <div class="editor-sub-toolbar">
                <div class="sub-left">
                  <span class="sub-label">
                    {{ editorMode === 'rich' ? '📖 单栏排版就地编辑器 (10.5pt 水利标准规范)' : '📝 Markdown 源码编辑器' }}
                  </span>
                  <span class="sub-tip">
                    {{ editorMode === 'rich' ? '支持直接点击排版正文就地润色，防抖自动保存。' : '可查阅和编辑 Markdown 原生格式。' }}
                  </span>
                </div>
                <div class="sub-right">
                  <div class="view-mode-group">
                    <button
                      class="mode-btn"
                      :class="{ active: editorMode === 'rich' }"
                      @click="editorMode = 'rich'"
                    >
                      👁️ 排版视图
                    </button>
                    <button
                      class="mode-btn"
                      :class="{ active: editorMode === 'source' }"
                      @click="editorMode = 'source'"
                    >
                      📝 源码视图
                    </button>
                  </div>
                </div>
              </div>

              <!-- 排版就地编辑画布 -->
              <div
                v-show="editorMode === 'rich'"
                ref="editorCanvasRef"
                class="rich-editor-canvas markdown-body"
                contenteditable="true"
                spellcheck="false"
                @input="onEditorInput"
              ></div>

              <!-- Markdown 源码编辑器 -->
              <textarea
                v-show="editorMode === 'source'"
                class="source-editor-textarea"
                :value="currentChapterText"
                @input="onSourceInput"
                placeholder="暂无正文内容，请在步骤 3 写作或使用 AI 修订..."
              ></textarea>
            </div>
          </div>
        </section>

        <!-- ═════════════════════════════════════════════════════════════════ -->
        <!-- 视图 2：全书连贯预览工作台 -->
        <!-- ═════════════════════════════════════════════════════════════════ -->
        <section v-else-if="viewTab === 'preview'" class="workbench-section full-preview-section">
          <div class="card-header preview-header">
            <div class="preview-title-area">
              <h3>📄 全书连贯排版预览</h3>
              <div class="preview-meta">
                <span>共 <strong>{{ totalChapters }}</strong> 章</span>
                <span>·</span>
                <span>已完成 <strong>{{ completedChaptersCount }}</strong> 章</span>
                <span>·</span>
                <span>全书总字数：<strong>{{ totalWordCount.toLocaleString() }}</strong> 字</span>
              </div>
            </div>
            <div class="preview-actions">
              <button class="btn btn-outline" @click="copyFullBookText">
                📋 复制全书 Markdown
              </button>
              <button class="btn btn-primary" @click="projectStore.setStep(5)">
                成果导出 &rarr;
              </button>
            </div>
          </div>

          <div class="card-body full-preview-body">
            <div class="full-preview-canvas markdown-body" v-html="fullBookHtml"></div>
          </div>
        </section>

        <!-- ═════════════════════════════════════════════════════════════════ -->
        <!-- 视图 3：全局质量与偏离度看板（全书跨章一致性体检总览） -->
        <!-- ═════════════════════════════════════════════════════════════════ -->
        <section v-else-if="viewTab === 'dashboard'" class="workbench-section dashboard-section">
          <div class="card-header dashboard-header">
            <div class="dash-title-area">
              <h3>📊 全局报告质量与审阅健康度看板</h3>
              <p class="dash-subtitle">集中展示全书章节质量达标矩阵、跨章指标自洽比对表与全书缺失资料总台账。</p>
            </div>
            <div class="dash-actions">
              <button
                v-if="projectStore.batchReviewing"
                class="btn btn-danger"
                @click="handleStopBatchReview"
              >
                ⏹ 停止全书体检
              </button>
              <button
                v-else
                class="btn btn-primary"
                @click="handleBatchReviewAll(true)"
              >
                🚀 重新执行全书全维体检
              </button>
            </div>
          </div>

          <div class="card-body dashboard-body">
            <!-- 统计指标网格 -->
            <div class="dashboard-kpi-grid">
              <div class="kpi-card">
                <span class="kpi-icon">🏆</span>
                <div class="kpi-info">
                  <span class="kpi-label">全书综合健康分</span>
                  <span class="kpi-val text-primary">{{ overallAverageScore > 0 ? overallAverageScore : '-' }} <small v-if="overallAverageScore > 0">/ 100</small></span>
                </div>
              </div>

              <div class="kpi-card">
                <span class="kpi-icon">📋</span>
                <div class="kpi-info">
                  <span class="kpi-label">审阅覆盖率</span>
                  <span class="kpi-val">{{ reviewedCount }} / {{ totalChapters }} 章 ({{ Math.round((reviewedCount / (totalChapters || 1)) * 100) }}%)</span>
                </div>
              </div>

              <div class="kpi-card">
                <span class="kpi-icon">✅</span>
                <div class="kpi-info">
                  <span class="kpi-label">质量达标率</span>
                  <span class="kpi-val text-success">{{ passRate }}%</span>
                </div>
              </div>

              <div class="kpi-card">
                <span class="kpi-icon">⚠️</span>
                <div class="kpi-info">
                  <span class="kpi-label">待修正问题总数</span>
                  <span class="kpi-val" :class="{ 'text-warning': totalIssuesCount > 0 }">{{ totalIssuesCount }} 项</span>
                </div>
              </div>
            </div>

            <!-- 1. 各章节矩阵看板表格 -->
            <div class="dashboard-table-card">
              <h4 class="table-title">📑 章节全维质量矩阵明细</h4>
              <table class="dashboard-matrix-table">
                <thead>
                  <tr>
                    <th style="width: 60px;">序号</th>
                    <th>章节标题</th>
                    <th>实际字数</th>
                    <th>审阅状态</th>
                    <th>专家评分</th>
                    <th>问题项数</th>
                    <th>缺失资料</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="ch in projectStore.outlineChapters" :key="ch.seq">
                    <td class="text-center font-bold">{{ ch.seq }}</td>
                    <td><strong>{{ ch.title }}</strong></td>
                    <td>{{ (projectStore.chapters[ch.seq] || "").length.toLocaleString() }} 字</td>
                    <td>
                      <span
                        v-if="projectStore.chapterReviews[ch.seq]"
                        class="status-dot-pill"
                        :class="
                          projectStore.chapterReviews[ch.seq].status === '通过'
                            ? 'st-normal'
                            : projectStore.chapterReviews[ch.seq].status === '需补充'
                            ? 'st-pending'
                            : 'st-abnormal'
                        "
                      >
                        {{ projectStore.chapterReviews[ch.seq].status }}
                      </span>
                      <span v-else class="text-muted">未审阅</span>
                    </td>
                    <td>
                      <strong v-if="projectStore.chapterReviews[ch.seq]?.score !== undefined">
                        {{ projectStore.chapterReviews[ch.seq].score }} 分
                      </strong>
                      <span v-else class="text-muted">-</span>
                    </td>
                    <td>
                      <span v-if="projectStore.chapterReviews[ch.seq]?.issues?.length" class="badge-issues">
                        {{ projectStore.chapterReviews[ch.seq].issues?.length }} 项
                      </span>
                      <span v-else class="text-muted">0</span>
                    </td>
                    <td>
                      <span v-if="projectStore.chapterReviews[ch.seq]?.data_gap_checklist?.length" class="badge-gaps">
                        {{ projectStore.chapterReviews[ch.seq].data_gap_checklist?.length }} 项缺口
                      </span>
                      <span v-else class="text-muted">无</span>
                    </td>
                    <td>
                      <button class="btn btn-outline btn-xs" @click="selectChapter(ch.seq)">
                        进入精审 🔍
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- 2. 跨章关键指标自洽比对表 -->
            <div class="dashboard-table-card">
              <h4 class="table-title">📐 跨章关键指标前后自洽性比对表</h4>
              <table v-if="allNumericalChecks.length > 0" class="dashboard-matrix-table">
                <thead>
                  <tr>
                    <th style="width: 100px;">所属章节</th>
                    <th>参数/指标名称</th>
                    <th>提取数值</th>
                    <th>自洽状态</th>
                    <th>核验说明与依据</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, idx) in allNumericalChecks" :key="idx">
                    <td>第 {{ item.chapterSeq }} 章</td>
                    <td><strong>{{ item.parameter }}</strong></td>
                    <td><code>{{ item.extracted_value }}</code></td>
                    <td>
                      <span class="status-dot-pill" :class="`st-${item.status}`">
                        {{ item.status === 'normal' ? '✅ 正常自洽' : item.status === 'abnormal' ? '⚠️ 存在矛盾' : '⏳ 待复核' }}
                      </span>
                    </td>
                    <td>{{ item.note }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty-table-tip">暂无提取到的跨章数值核验数据，请先对章节执行审阅。</div>
            </div>

            <!-- 3. 全书缺失资料总台账 -->
            <div class="dashboard-table-card">
              <h4 class="table-title">📦 全书缺失资料与前置要件总台账</h4>
              <table v-if="allDataGaps.length > 0" class="dashboard-matrix-table">
                <thead>
                  <tr>
                    <th style="width: 100px;">关联章节</th>
                    <th>缺失资料 / 前置审批文件名称</th>
                    <th>建议处置方案</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(gapItem, idx) in allDataGaps" :key="idx">
                    <td>第 {{ gapItem.chapterSeq }} 章</td>
                    <td><strong class="text-warning">📄 {{ gapItem.gap }}</strong></td>
                    <td>建议在底稿库中补充该要件或使用定向修订补充说明</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty-table-tip">✓ 全书底稿资料完整，无待补前置要件。</div>
            </div>
          </div>
        </section>

        <!-- ═════════════════════════════════════════════════════════ -->
        <!-- 参考资料来源抽屉 (Drawer) -->
        <!-- ═════════════════════════════════════════════════════════ -->
        <transition name="drawer-fade">
          <div v-if="showRefDrawer" class="ref-drawer-overlay" @click="showRefDrawer = false">
            <div class="ref-drawer-panel" @click.stop>
              <div class="drawer-header">
                <div class="drawer-title-box">
                  <h4>📚 本章参考资料来源台账</h4>
                  <span class="drawer-sub">第 {{ currentChapter?.seq }} 章：{{ currentChapter?.title }}</span>
                </div>
                <button class="drawer-close-btn" @click="showRefDrawer = false">✕</button>
              </div>

              <div class="drawer-summary-bar">
                <span>共命中 <strong>{{ currentChapterReferences.length }}</strong> 份底稿与标准规程</span>
                <span>·</span>
                <span>累计引用 <strong>{{ totalRefCitations }}</strong> 处</span>
              </div>

              <div class="drawer-body">
                <div v-if="currentChapterReferences.length > 0" class="ref-items-list">
                  <div
                    v-for="(refItem, rIdx) in currentChapterReferences"
                    :key="rIdx"
                    class="ref-card-item"
                  >
                    <div class="ref-card-top">
                      <span
                        class="ref-type-tag"
                        :class="`type-${refItem.type}`"
                      >
                        {{ refItem.typeLabel }}
                      </span>
                      <span class="ref-count-tag">引用 {{ refItem.count }} 次</span>
                    </div>
                    <div class="ref-card-title">{{ refItem.title }}</div>
                    <div class="ref-card-raw"><code>{{ refItem.raw }}</code></div>
                  </div>
                </div>

                <div v-else class="ref-empty-state">
                  <span class="empty-icon">📂</span>
                  <p class="empty-title">本章正文中暂未引用底稿标签</p>
                  <p class="empty-desc">
                    您可在正文中嵌入 <code>【源:文件名.docx】</code> 或 <code>【标:规范名】</code> 标记数据与论述来源，系统将在此自动汇总。
                  </p>
                </div>
              </div>
            </div>
          </div>
        </transition>

        <!-- 底部向导导航栏 -->
        <footer class="wizard-footer">
          <button class="btn btn-secondary" @click="projectStore.setStep(3)">
            &larr; 上一步：章节写作
          </button>
          <button class="btn btn-primary" @click="projectStore.setStep(5)">
            下一步：成果导出 &rarr;
          </button>
        </footer>
      </main>
    </div>
  </div>
</template>

<style scoped>
.step4-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
  background: #f8fafc;
  box-sizing: border-box;
}

.alert-banner {
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 12px;
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

.review-layout {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

/* 左侧栏 */
.sidebar-panel {
  width: 340px;
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
}

.header-titles {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-titles h3 {
  margin: 0;
  font-size: 15px;
  color: #0f172a;
  font-weight: 700;
}
.proj-badge {
  background: #f1f5f9;
  color: #475569;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.batch-review-bar {
  display: flex;
}
.batch-btn {
  font-size: 12px;
  padding: 6px 10px;
}

.quality-mini-board {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}
.mini-stat-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 6px 8px;
  text-align: center;
  display: flex;
  flex-direction: column;
}
.mini-stat-val {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}
.mini-stat-lbl {
  font-size: 11px;
  color: #64748b;
}
.stat-success {
  color: #15803d;
}
.stat-warning {
  color: #d97706;
}

.view-tabs-row {
  display: flex;
  gap: 4px;
  background: #f1f5f9;
  padding: 3px;
  border-radius: 6px;
}
.view-tab-btn {
  flex: 1;
  border: none;
  background: none;
  font-size: 12px;
  padding: 5px 4px;
  border-radius: 4px;
  cursor: pointer;
  color: #64748b;
  font-weight: 500;
  transition: all 0.15s;
}
.view-tab-btn.active {
  background: #fff;
  color: #2563eb;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.chapter-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chapter-review-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  background: #fff;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.chapter-review-card:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}
.chapter-review-card.active {
  border-color: #2563eb;
  background: #eff6ff;
}
.chapter-review-card.hasRevision {
  border-color: #f59e0b;
}

.ch-card-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ch-seq {
  width: 20px;
  height: 20px;
  background: #e2e8f0;
  color: #334155;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.chapter-review-card.active .ch-seq {
  background: #2563eb;
  color: #fff;
}
.ch-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ch-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}
.ch-words {
  color: #64748b;
}
.review-badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}
.badge-success {
  background: #dcfce7;
  color: #15803d;
}
.badge-warning {
  background: #fef3c7;
  color: #b45309;
}
.badge-danger {
  background: #fee2e2;
  color: #b91c1c;
}
.badge-idle {
  background: #f1f5f9;
  color: #64748b;
}
.diff-active-tag {
  background: #fef3c7;
  color: #b45309;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 600;
  font-size: 10px;
}

/* 主工作台 */
.main-workbench {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.workbench-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chapter-workbench-header,
.preview-header,
.dashboard-header {
  padding: 14px 20px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.workbench-title-area {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.title-line {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ch-tag {
  background: #eff6ff;
  color: #2563eb;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.current-title {
  margin: 0;
  font-size: 16px;
  color: #0f172a;
  font-weight: 700;
}
.meta-line {
  font-size: 12px;
  color: #64748b;
  display: flex;
  gap: 8px;
}
.meta-divider {
  color: #cbd5e1;
}

/* 审阅模式功能说明提示标签条 */
.review-mode-hints {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  flex-wrap: wrap;
}
.hint-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e2e8f0;
}
.hint-all {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
}
.hint-numeric {
  background: #f0fdf4;
  border-color: #bbf7d0;
  color: #15803d;
}
.hint-compliance {
  background: #faf5ff;
  border-color: #e9d5ff;
  color: #7e22ce;
}

.header-action-group,
.preview-actions,
.dash-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ref-drawer-btn.active {
  background: #eff6ff;
  border-color: #2563eb;
  color: #2563eb;
}

.chapter-workbench-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ═════════════════════════════════════════════════════════ */
/* 审阅与修订前摇动态进度心跳 */
/* ═════════════════════════════════════════════════════════ */
.heartbeat-card {
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  animation: pulse-border 2s infinite ease-in-out;
}
.review-heartbeat {
  background: #eff6ff;
  border: 1px solid #93c5fd;
}
.revision-heartbeat {
  background: #f0fdf4;
  border: 1px solid #86efac;
}
@keyframes pulse-border {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.2);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.15);
  }
}

.heartbeat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.hb-badge {
  display: flex;
  align-items: center;
  gap: 8px;
}
.hb-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e3a8a;
}
.hb-timer {
  font-size: 12px;
  color: #1e40af;
}

.radar-pulse {
  width: 10px;
  height: 10px;
  background: #2563eb;
  border-radius: 50%;
  display: inline-block;
  position: relative;
}
.radar-pulse::after {
  content: "";
  position: absolute;
  top: -4px;
  left: -4px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid #2563eb;
  animation: radar-wave 1.2s infinite ease-out;
}
.revision-pulse {
  background: #16a34a;
}
.revision-pulse::after {
  border-color: #16a34a;
}
@keyframes radar-wave {
  0% {
    transform: scale(0.6);
    opacity: 1;
  }
  100% {
    transform: scale(1.6);
    opacity: 0;
  }
}

.pipeline-stepper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: #fff;
  padding: 8px 12px;
  border-radius: 6px;
}
.stepper-node {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}
.stepper-badge {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}
.stepper-node.active .stepper-badge {
  background: #2563eb;
  color: #fff;
}
.stepper-node.completed .stepper-badge {
  background: #10b981;
  color: #fff;
}
.stepper-text {
  display: flex;
  flex-direction: column;
}
.stepper-title {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
}
.stepper-desc {
  font-size: 10px;
  color: #64748b;
}
.stepper-line {
  flex: 1;
  height: 2px;
  background: #e2e8f0;
  margin: 0 4px;
}
.stepper-line.completed {
  background: #10b981;
}
.stepper-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.hb-status-msg {
  font-size: 11px;
  color: #475569;
}

/* ═════════════════════════════════════════════════════════ */
/* 专家诊断卡片自适应重构 */
/* ═════════════════════════════════════════════════════════ */
.diagnostic-panel {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.diagnostic-expanded-box {
  display: flex;
  flex-direction: column;
}

.diagnostic-header {
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  user-select: none;
}
.diag-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.diag-icon {
  font-size: 16px;
}
.diag-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}
.status-pill {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}
.pill-success {
  background: #dcfce7;
  color: #15803d;
}
.pill-warning {
  background: #fef3c7;
  color: #b45309;
}
.pill-danger {
  background: #fee2e2;
  color: #b91c1c;
}
.score-pill {
  background: #eff6ff;
  color: #1d4ed8;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

/* 彻底解决底部截断：自适应最大高度与垂直滚动 */
.diagnostic-content-scrollable {
  max-height: 480px;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.diag-summary-box {
  background: #f1f5f9;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  color: #334155;
  line-height: 1.5;
}

.diag-subtabs {
  display: flex;
  gap: 6px;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 6px;
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 2;
}
.diag-tab-btn {
  border: none;
  background: none;
  padding: 5px 10px;
  font-size: 12px;
  border-radius: 4px;
  cursor: pointer;
  color: #64748b;
  font-weight: 500;
  transition: all 0.15s;
}
.diag-tab-btn.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}

.issues-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.issue-card {
  border-left: 3px solid #cbd5e1;
  background: #f8fafc;
  padding: 8px 12px;
  border-radius: 0 6px 6px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.issue-card.sev-error {
  border-left-color: #ef4444;
  background: #fef2f2;
}
.issue-card.sev-warning {
  border-left-color: #f59e0b;
  background: #fffbeb;
}
.issue-card.sev-suggestion {
  border-left-color: #3b82f6;
  background: #eff6ff;
}

.issue-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.issue-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
}
.issue-badge.badge-error {
  background: #fee2e2;
  color: #b91c1c;
}
.issue-badge.badge-warning {
  background: #fef3c7;
  color: #b45309;
}
.issue-badge.badge-suggestion {
  background: #dbeafe;
  color: #1d4ed8;
}
.issue-category {
  font-size: 11px;
  color: #64748b;
}
.issue-location {
  font-size: 11px;
  color: #475569;
}
.fill-intent-btn {
  margin-left: auto;
}
.issue-msg {
  font-size: 12px;
  color: #0f172a;
  font-weight: 500;
}
.issue-sugg {
  font-size: 11px;
  color: #475569;
}

.diag-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.diag-table th,
.diag-table td {
  border: 1px solid #e2e8f0;
  padding: 6px 10px;
  text-align: left;
}
.diag-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
}

.status-dot-pill {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}
.st-normal {
  background: #dcfce7;
  color: #15803d;
}
.st-abnormal {
  background: #fee2e2;
  color: #b91c1c;
}
.st-pending {
  background: #fef3c7;
  color: #b45309;
}

.gaps-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.gap-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  background: #f8fafc;
  border-radius: 4px;
  font-size: 12px;
}
.gap-text {
  flex: 1;
  color: #334155;
}

.suggestions-pre {
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 12px;
  color: #334155;
  line-height: 1.6;
  margin: 0 0 10px 0;
}
.empty-sub-tip {
  color: #64748b;
  font-size: 12px;
  padding: 10px 0;
}

/* 44px 收起态通栏胶囊卡片 */
.diagnostic-capsule-collapsed {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  cursor: pointer;
  background: #fff;
  transition: all 0.15s ease;
  user-select: none;
}
.diagnostic-capsule-collapsed:hover {
  background: #f8fafc;
}
.capsule-left {
  display: flex;
  align-items: center;
  gap: 10px;
  overflow: hidden;
}
.capsule-icon {
  font-size: 16px;
}
.score-pill-sm {
  background: #eff6ff;
  color: #1d4ed8;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}
.capsule-summary-snippet {
  font-size: 12px;
  color: #475569;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 450px;
}
.capsule-right {
  display: flex;
  align-items: center;
}
.expand-action-text {
  font-size: 12px;
  font-weight: 600;
  color: #2563eb;
  padding: 4px 10px;
  background: #eff6ff;
  border-radius: 4px;
}
.expand-action-text:hover {
  background: #dbeafe;
}

/* ═════════════════════════════════════════════════════════ */
/* AI 修订指令条 */
/* ═════════════════════════════════════════════════════════ */
.revision-prompt-box {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.prompt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.prompt-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e40af;
}
.preset-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.preset-pill {
  background: #fff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.preset-pill:hover {
  background: #dbeafe;
}

.prompt-input-row {
  display: flex;
  gap: 12px;
}
.prompt-textarea {
  flex: 1;
  height: 60px;
  border: 1px solid #93c5fd;
  border-radius: 6px;
  padding: 8px;
  font-size: 12px;
  resize: vertical;
  font-family: inherit;
}
.run-revise-btn {
  width: 160px;
  font-size: 12px;
  flex-shrink: 0;
}

/* ═════════════════════════════════════════════════════════ */
/* Diff 工作台与水利排版样式 */
/* ═════════════════════════════════════════════════════════ */
.diff-workbench-container {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.diff-toolbar {
  padding: 8px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.diff-toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.diff-title-badge {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}
.diff-stats-pills {
  display: flex;
  gap: 6px;
}
.diff-pill {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
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

.diff-mode-switcher,
.view-mode-group {
  display: flex;
  background: #e2e8f0;
  padding: 2px;
  border-radius: 4px;
}
.mode-btn {
  border: none;
  background: none;
  padding: 3px 8px;
  font-size: 11px;
  cursor: pointer;
  border-radius: 3px;
  color: #475569;
}
.mode-btn.active {
  background: #fff;
  color: #2563eb;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

/* 水利规范 10.5pt 排版规范 */
.water-spec-typography {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "WenQuanYi Micro Hei", sans-serif;
  font-size: 14px; /* 10.5pt 约为 14px */
  line-height: 1.8;
  color: #1e293b;
}

.diff-view-side-by-side {
  display: flex;
  height: 500px;
  overflow: hidden;
}
.diff-side-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}
.diff-side-column.side-original {
  border-right: 1px solid #e2e8f0;
}
.diff-column-header {
  padding: 6px 12px;
  background: #f1f5f9;
  font-size: 11px;
  font-weight: 700;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sync-indicator {
  font-size: 10px;
  color: #94a3b8;
  font-weight: normal;
}
.diff-column-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.diff-line-row {
  display: flex;
  padding: 2px 0;
}
.diff-line-row.line-removed {
  background: #fee2e2;
  color: #991b1b;
}
.diff-line-row.line-added {
  background: #dcfce7;
  color: #166534;
}
.diff-line-placeholder {
  background: #fafafa;
  color: transparent;
  user-select: none;
}
.line-num {
  width: 44px;
  text-align: right;
  padding-right: 10px;
  color: #94a3b8;
  user-select: none;
  font-size: 11px;
  font-family: "JetBrains Mono", Consolas, monospace;
}
.line-code {
  flex: 1;
  white-space: pre-wrap;
  word-break: break-all;
  padding-right: 12px;
}

.diff-view-inline {
  height: 500px;
  overflow-y: auto;
  padding: 8px 0;
}
.diff-inline-row {
  display: flex;
  padding: 2px 0;
}
.diff-inline-row.inline-added {
  background: #dcfce7;
  color: #166534;
}
.diff-inline-row.inline-removed {
  background: #fee2e2;
  color: #991b1b;
}
.inline-line-num {
  width: 40px;
  text-align: right;
  padding-right: 6px;
  color: #94a3b8;
  font-size: 11px;
  font-family: "JetBrains Mono", Consolas, monospace;
  user-select: none;
}
.inline-sign {
  width: 18px;
  text-align: center;
  font-weight: 700;
  user-select: none;
}
.strike-del {
  text-decoration: line-through;
}

.diff-bottom-actions {
  padding: 10px 14px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.diff-instruction-preview {
  font-size: 12px;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.diff-action-btns {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* 常规画布 */
.canvas-wrapper {
  display: flex;
  flex-direction: column;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  min-height: 460px;
  overflow: hidden;
}
.editor-sub-toolbar {
  padding: 6px 12px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sub-label {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  margin-right: 8px;
}
.sub-tip {
  font-size: 11px;
  color: #64748b;
}

.rich-editor-canvas {
  padding: 24px 32px;
  min-height: 420px;
  outline: none;
  font-size: 14px;
  line-height: 1.8;
  color: #1e293b;
  overflow-y: auto;
}
.source-editor-textarea {
  width: 100%;
  height: 420px;
  border: none;
  padding: 16px 20px;
  font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
  box-sizing: border-box;
}

/* ═════════════════════════════════════════════════════════ */
/* 参考资料来源抽屉 (Drawer) */
/* ═════════════════════════════════════════════════════════ */
.ref-drawer-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.4);
  z-index: 100;
  display: flex;
  justify-content: flex-end;
}
.ref-drawer-panel {
  width: 380px;
  max-width: 90%;
  height: 100%;
  background: #fff;
  box-shadow: -4px 0 16px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  animation: slide-in 0.2s ease-out;
}
@keyframes slide-in {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

.drawer-header {
  padding: 14px 16px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.drawer-title-box h4 {
  margin: 0 0 2px 0;
  font-size: 14px;
  color: #0f172a;
  font-weight: 700;
}
.drawer-sub {
  font-size: 11px;
  color: #64748b;
}
.drawer-close-btn {
  background: none;
  border: none;
  font-size: 16px;
  color: #94a3b8;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}
.drawer-close-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.drawer-summary-bar {
  background: #eff6ff;
  padding: 8px 16px;
  font-size: 12px;
  color: #1e40af;
  border-bottom: 1px solid #dbeafe;
  display: flex;
  gap: 6px;
}

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}
.ref-items-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ref-card-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ref-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ref-type-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
}
.type-material {
  background: #dbeafe;
  color: #1d4ed8;
}
.type-standard {
  background: #fef3c7;
  color: #b45309;
}
.type-web {
  background: #e0e7ff;
  color: #4338ca;
}
.type-other {
  background: #f1f5f9;
  color: #475569;
}
.ref-count-tag {
  font-size: 11px;
  color: #64748b;
}
.ref-card-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  word-break: break-all;
}
.ref-card-raw {
  font-size: 11px;
  color: #64748b;
}

.ref-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
  text-align: center;
}
.empty-icon {
  font-size: 36px;
  margin-bottom: 8px;
}
.empty-title {
  margin: 0 0 6px 0;
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}
.empty-desc {
  margin: 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
}

/* 全书预览 */
.full-preview-section {
  display: flex;
  flex-direction: column;
}
.full-preview-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 40px;
  background: #fff;
}
.preview-title-area h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 700;
}
.preview-meta {
  font-size: 12px;
  color: #64748b;
  display: flex;
  gap: 6px;
}

/* 全局质量看板 */
.dashboard-section {
  display: flex;
  flex-direction: column;
}
.dash-title-area h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 700;
}
.dash-subtitle {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}
.dashboard-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dashboard-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.kpi-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.kpi-icon {
  font-size: 24px;
}
.kpi-info {
  display: flex;
  flex-direction: column;
}
.kpi-label {
  font-size: 12px;
  color: #64748b;
}
.kpi-val {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.dashboard-table-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.table-title {
  margin: 0;
  padding: 12px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}
.dashboard-matrix-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.dashboard-matrix-table th,
.dashboard-matrix-table td {
  padding: 10px 14px;
  border-bottom: 1px solid #f1f5f9;
  text-align: left;
}
.dashboard-matrix-table th {
  background: #fafafa;
  color: #475569;
  font-weight: 600;
}
.badge-issues {
  background: #fee2e2;
  color: #b91c1c;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}
.badge-gaps {
  background: #fef3c7;
  color: #b45309;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}
.empty-table-tip {
  padding: 20px;
  color: #64748b;
  font-size: 13px;
  text-align: center;
}

/* 底栏 */
.wizard-footer {
  padding: 12px 20px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  background: #fff;
  border-radius: 0 0 10px 10px;
}

/* 按钮通用 */
.btn {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
}
.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}
.btn-secondary {
  background: #f1f5f9;
  color: #334155;
  border-color: #cbd5e1;
}
.btn-secondary:hover:not(:disabled) {
  background: #e2e8f0;
}
.btn-outline {
  background: #fff;
  color: #334155;
  border-color: #cbd5e1;
}
.btn-outline:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #94a3b8;
}
.btn-outline.active {
  background: #eff6ff;
  border-color: #2563eb;
  color: #2563eb;
}
.btn-danger {
  background: #ef4444;
  color: #fff;
}
.btn-danger:hover:not(:disabled) {
  background: #dc2626;
}
.btn-block {
  width: 100%;
  justify-content: center;
}
.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}
.btn-xs {
  padding: 2px 8px;
  font-size: 11px;
}
.btn-xs-text {
  background: none;
  border: none;
  color: #2563eb;
  font-size: 11px;
  cursor: pointer;
  padding: 0;
}
.btn-xs-text:hover {
  text-decoration: underline;
}

.spinner-inline {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity 0.2s ease;
}
.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}
</style>
