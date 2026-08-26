<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
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
  htmlToMarkdown,
  markdownToHtml,
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

// 全局操作通知
const actionMessage = ref<{ type: "success" | "error" | "info"; text: string } | null>(null);

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
  );
});

const currentDiffBlocks = computed<DiffBlock[]>(() => {
  if (!hasActiveRevisionForCurrent.value || !projectStore.activeRevision) {
    return [];
  }
  return computeDiffBlocks(
    projectStore.activeRevision.originalText,
    projectStore.activeRevision.revisedText,
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
  );
});

// 全书连续拼接 Markdown
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
  try {
    const label =
      mode === "all"
        ? "全维专家审阅"
        : mode === "compliance"
        ? "合规审查"
        : mode === "numeric"
        ? "数值核验"
        : "技术审校";
    showMsg(`正在对第 ${seq} 章启动「${label}」，请稍候...`, "info");
    const result = await projectStore.runChapterReview(engine.baseUrl, seq, mode, llmConfig);
    isDiagnosticExpanded.value = true;
    showMsg(`第 ${seq} 章「${label}」完成！得分：${result.score ?? 85} 分，状态：${result.status}`);
  } catch (err) {
    showMsg(`审阅失败：${(err as Error).message}`, "error");
  }
}

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

  try {
    showMsg(`正在对第 ${seq} 章执行 AI 定向修订并生成 Diff 对比...`, "info");
    await projectStore.runChapterRevision(engine.baseUrl, seq, instruction, llmConfig);
    showMsg(`第 ${seq} 章修订完成！已进入 Diff 差异比对工作台。`);
  } catch (err) {
    showMsg(`修订失败：${(err as Error).message}`, "error");
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

async function handleBatchReviewAll() {
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
    return text && text.trim().length > 0 && !projectStore.chapterReviews[ch.seq];
  });

  if (unreviewed.length === 0) {
    showMsg("暂无可批量审阅的未审阅章节（需已完成正文且尚未审阅）", "info");
    return;
  }

  showMsg(`已启动 ${unreviewed.length} 个章节的批量全维审阅任务...`, "info");
  for (const ch of unreviewed) {
    try {
      await projectStore.runChapterReview(engine.baseUrl, ch.seq, "all", llmConfig);
    } catch (e) {
      // ignore
    }
  }
  showMsg("批量审阅任务全部完成！");
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
            </div>

            <!-- 操作按钮组 -->
            <div class="header-action-group">
              <button
                class="btn btn-outline"
                :disabled="!currentChapterText.trim() || isReviewingCurrent"
                @click="handleRunReview('all')"
                title="对本章执行政策合规、数值计算、技术方案与文字全维专家审查"
              >
                <span v-if="isReviewingCurrent" class="spinner-inline"></span>
                🔍 全维专家审阅
              </button>
              <button
                class="btn btn-outline"
                :disabled="!currentChapterText.trim() || isReviewingCurrent"
                @click="handleRunReview('numeric')"
                title="提取并专项核验工程参数、投资估算与指标自洽性"
              >
                📏 数值校验
              </button>
              <button
                class="btn btn-outline"
                :disabled="!currentChapterText.trim() || isReviewingCurrent"
                @click="handleRunReview('compliance')"
                title="审查法律法规、规范标准与前置审批要件合规性"
              >
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
            </div>
          </div>

          <div class="card-body chapter-workbench-body">
            <!-- 可折叠专家诊断与批注卡片 -->
            <div v-if="currentChapterReview" class="diagnostic-panel" :class="{ collapsed: !isDiagnosticExpanded }">
              <div class="diagnostic-header" @click="isDiagnosticExpanded = !isDiagnosticExpanded">
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
                    {{ currentChapterReview.status }}
                  </span>
                  <span class="score-pill">得分：{{ currentChapterReview.score ?? 85 }} / 100</span>
                </div>
                <div class="diag-header-right">
                  <span class="toggle-arrow">{{ isDiagnosticExpanded ? '▲ 收起' : '▼ 展开' }}</span>
                </div>
              </div>

              <!-- 展开时的诊断详情 -->
              <div v-show="isDiagnosticExpanded" class="diagnostic-content">
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
                  <div v-else class="empty-sub-tip">✓ 未发现明显合规或技术硬伤问题，质量优良。</div>
                </div>

                <!-- 2. 数值核验表 -->
                <div v-if="diagnosticSubTab === 'numerical'" class="diag-tab-content">
                  <table v-if="currentChapterReview.numerical_checks && currentChapterReview.numerical_checks.length > 0" class="diag-table">
                    <thead>
                      <tr>
                        <th>参数/指标</th>
                        <th>提取数值</th>
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

            <!-- AI 定向修订意图输入条 -->
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

            <!-- ═════════════════════════════════════════════════════════════ -->
            <!-- 核心展示区域：Diff 差异对比模式 VS 常规排版就地编辑模式 -->
            <!-- ═════════════════════════════════════════════════════════════ -->

            <!-- 状态 A：Diff 差异对比工作台（当 activeRevision 处于激活状态时） -->
            <div v-if="hasActiveRevisionForCurrent" class="diff-workbench-container">
              <div class="diff-toolbar">
                <div class="diff-toolbar-left">
                  <span class="diff-title-badge">⚡ AI 修订 Diff 差异对比</span>
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

              <!-- 左右双栏 Diff 视图 -->
              <div v-if="diffViewMode === 'sideBySide'" class="diff-view-side-by-side">
                <div class="diff-side-column side-original">
                  <div class="diff-column-header">原文正文（修改前）</div>
                  <div class="diff-column-content">
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
                  <div class="diff-column-header">修订后正文（建议采纳）</div>
                  <div class="diff-column-content">
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

              <!-- 单栏内联 Diff 视图 -->
              <div v-else class="diff-view-inline">
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
                    <span class="inline-code">{{ line.text }}</span>
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
        <!-- 视图 3：全局质量与偏离度看板 -->
        <!-- ═════════════════════════════════════════════════════════════════ -->
        <section v-else-if="viewTab === 'dashboard'" class="workbench-section dashboard-section">
          <div class="card-header dashboard-header">
            <div class="dash-title-area">
              <h3>📊 全局报告质量与审阅健康度看板</h3>
              <p class="dash-subtitle">全方位统计各章节完成度、字数偏离度、合规审查与专家打分分布。</p>
            </div>
            <div class="dash-actions">
              <button class="btn btn-primary" @click="handleBatchReviewAll">
                🚀 批量全维审阅所有未审阅章节
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
                  <span class="kpi-label">待修正问题数</span>
                  <span class="kpi-val" :class="{ 'text-warning': totalIssuesCount > 0 }">{{ totalIssuesCount }} 项</span>
                </div>
              </div>
            </div>

            <!-- 各章节矩阵看板表格 -->
            <div class="dashboard-table-card">
              <h4 class="table-title">章节全维质量矩阵明细</h4>
              <table class="dashboard-matrix-table">
                <thead>
                  <tr>
                    <th style="width: 60px;">序号</th>
                    <th>章节标题</th>
                    <th>实际字数</th>
                    <th>审阅状态</th>
                    <th>专家评分</th>
                    <th>问题数</th>
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
          </div>
        </section>

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
  align-items: center;
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

.header-action-group,
.preview-actions,
.dash-actions {
  display: flex;
  gap: 8px;
}

.chapter-workbench-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 专家诊断卡片 */
.diagnostic-panel {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}
.diagnostic-header {
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
}
.diagnostic-panel.collapsed .diagnostic-header {
  border-bottom: none;
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
.toggle-arrow {
  font-size: 12px;
  color: #64748b;
}

.diagnostic-content {
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
}
.diag-tab-btn {
  border: none;
  background: none;
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 4px;
  cursor: pointer;
  color: #64748b;
  font-weight: 500;
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
  padding: 4px 8px;
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

/* AI 修订指令条 */
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

/* Diff 工作台 */
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

.diff-view-side-by-side {
  display: flex;
  height: 480px;
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
}
.diff-column-content {
  flex: 1;
  overflow-y: auto;
  font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.5;
}

.diff-line-row {
  display: flex;
  padding: 1px 0;
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
  background: #f8fafc;
  color: transparent;
  user-select: none;
}
.line-num {
  width: 40px;
  text-align: right;
  padding-right: 8px;
  color: #94a3b8;
  user-select: none;
  font-size: 11px;
}
.line-code {
  flex: 1;
  white-space: pre-wrap;
  word-break: break-all;
  padding-right: 8px;
}

.diff-view-inline {
  height: 480px;
  overflow-y: auto;
  font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.5;
}
.diff-inline-row {
  display: flex;
  padding: 1px 0;
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
  width: 36px;
  text-align: right;
  padding-right: 6px;
  color: #94a3b8;
  font-size: 11px;
  user-select: none;
}
.inline-sign {
  width: 16px;
  text-align: center;
  font-weight: 700;
  user-select: none;
}
.inline-code {
  flex: 1;
  white-space: pre-wrap;
  word-break: break-all;
  padding-right: 8px;
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
</style>
