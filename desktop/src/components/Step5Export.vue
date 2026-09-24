<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import {
  assignGlobalRefNumbers,
  convertRefsToNumberedCitations,
  countContentChars,
  generateBibliographySection,
  type GlobalRefEntry,
} from "../lib/markdown";
import * as engineApi from "../lib/engineApi";
import { useEngineStore } from "../stores/engine";
import { useProjectStore } from "../stores/project";

const engine = useEngineStore();
const projectStore = useProjectStore();

const exportingDocx = ref(false);
const exportingMd = ref(false);
const exportDocxResultPath = ref("");
const exportDocxResultSize = ref(0);
const exportMdResultPath = ref("");
const exportMdResultSize = ref(0);
const exportError = ref("");
const toastMessage = ref("");
const toastType = ref<"success" | "error" | "info">("info");
let toastTimer: any = null;

// ── 导出前上下文与自洽性核验状态 ──
const verifyingContext = ref(false);
const verificationResult = ref<engineApi.ContextVerifyResponse | null>(null);
const verificationFilter = ref<"all" | "conflict" | "warning" | "pass">("all");
const verificationError = ref("");
const showConflictModal = ref(false);
const pendingExportType = ref<"docx" | "md" | null>(null);

function showMsg(msg: string, type: "success" | "error" | "info" = "info") {
  toastMessage.value = msg;
  toastType.value = type;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toastMessage.value = "";
  }, 4000);
}

// ── 全书章节序列与排序 ──
const orderedSeqs = computed(() => {
  if (projectStore.outlineChapters.length > 0) {
    return projectStore.outlineChapters.map((c) => c.seq);
  }
  return Object.keys(projectStore.chapters)
    .map(Number)
    .filter((n) => !isNaN(n))
    .sort((a, b) => a - b);
});

// ── 全书总字数 ──
const totalWordCount = computed(() => {
  let count = 0;
  for (const seq of orderedSeqs.value) {
    const text = projectStore.chapters[seq] || "";
    count += countContentChars(text);
  }
  return count;
});

// ── 已生成正文的章节数 ──
const writtenChaptersCount = computed(() => {
  return orderedSeqs.value.filter((seq) => (projectStore.chapters[seq] || "").trim().length > 0).length;
});

// ── 全书全局引用按首次出现顺序编号与统计 ──
const globalRefAnalysis = computed(() => {
  return assignGlobalRefNumbers(projectStore.chapters, orderedSeqs.value);
});

const globalRefEntries = computed<GlobalRefEntry[]>(() => {
  return globalRefAnalysis.value.refEntries;
});

const refSummary = computed(() => {
  const entries = globalRefEntries.value;
  return {
    total: entries.length,
    material: entries.filter((e) => e.type === "material").length,
    standard: entries.filter((e) => e.type === "standard").length,
    web: entries.filter((e) => e.type === "web").length,
  };
});

// ── 生成全书合并 Markdown（文内替换为 [1][2]... 编号，文末附《参考文献》章） ──
function buildFullReportNumberedMarkdown(): string {
  const { labelToNumber, refEntries } = globalRefAnalysis.value;
  const sections: string[] = [];

  for (const seq of orderedSeqs.value) {
    const rawText = projectStore.chapters[seq] || "";
    if (rawText.trim()) {
      const numberedText = convertRefsToNumberedCitations(rawText, labelToNumber);
      sections.push(numberedText.trim());
    }
  }

  const bibSection = generateBibliographySection(refEntries);
  if (bibSection.trim()) {
    sections.push(bibSection.trim());
  }

  return sections.join("\n\n---\n\n");
}

// ── 过滤核验项目 ──
const filteredVerificationItems = computed(() => {
  if (!verificationResult.value) return [];
  if (verificationFilter.value === "conflict") {
    return verificationResult.value.items.filter((i) => i.status === "conflict");
  }
  if (verificationFilter.value === "warning") {
    return verificationResult.value.items.filter((i) => i.status === "warning");
  }
  if (verificationFilter.value === "pass") {
    return verificationResult.value.items.filter((i) => i.status === "pass");
  }
  return verificationResult.value.items;
});

// ── 触发自洽性核验 ──
async function runContextVerification(manual = false) {
  if (!engine.baseUrl) {
    if (manual) showMsg("本地引擎未就绪，请等待引擎连接", "error");
    return;
  }
  if (!projectStore.currentProject) {
    if (manual) showMsg("未选中项目", "error");
    return;
  }
  if (writtenChaptersCount.value === 0) {
    if (manual) showMsg("全书尚无章节正文，请先在步骤 3 写作或步骤 4 审阅中完善内容", "error");
    return;
  }

  verifyingContext.value = true;
  verificationError.value = "";
  try {
    const res = await engineApi.verifyContext(engine.baseUrl, {
      project: projectStore.currentProject.name,
      report_type: projectStore.reportType || "",
      chapters: projectStore.chapters,
    });
    verificationResult.value = res;
    if (manual) {
      showMsg("✅ 自洽性核验完成！", "success");
    }
  } catch (err: any) {
    console.error("Context verification failed:", err);
    let msg = err.message || "";
    if (err.status === 404 || msg.includes("404")) {
      msg = "当前运行的本地引擎版本过旧（缺少自洽性核验接口 404），请重新打包或重启最新引擎。";
    }
    verificationError.value = msg;
    if (manual) {
      showMsg(`自洽性核验失败: ${msg}`, "error");
    }
  } finally {
    verifyingContext.value = false;
  }
}

onMounted(() => {
  if (engine.baseUrl && projectStore.currentProject && writtenChaptersCount.value > 0) {
    runContextVerification(false);
  }
});

// 监听引擎就绪或章节数据载入，全自动静默执行核验，无需用户手动点按
watch(
  [() => engine.baseUrl, () => projectStore.currentProject?.name, writtenChaptersCount],
  ([url, proj, count]) => {
    if (url && proj && count > 0 && !verificationResult.value && !verifyingContext.value) {
      runContextVerification(false);
    }
  },
  { immediate: true },
);

// ── 定位至问题章节修改 ──
function jumpToChapter(seq: number) {
  projectStore.selectedChapterSeq = seq;
  projectStore.setStep(4);
}

// ── 执行 Word (.docx) 导出 ──
async function executeExportDocx() {
  if (!engine.baseUrl) {
    showMsg("本地引擎未就绪", "error");
    return;
  }
  if (!projectStore.currentProject) {
    showMsg("未选中项目", "error");
    return;
  }
  if (writtenChaptersCount.value === 0) {
    showMsg("全书尚无章节正文，请先在步骤 3 写作或步骤 4 审阅中完善内容", "error");
    return;
  }

  exportingDocx.value = true;
  exportError.value = "";
  exportDocxResultPath.value = "";

  try {
    const res = await engineApi.exportDocx(engine.baseUrl, {
      project: projectStore.currentProject.name,
      title: projectStore.currentProject.name,
      subtitle: "（ 初 稿 ）",
      chapters: projectStore.chapters,
      include_refs: true,
      include_cover: true,
      include_toc: true,
      author_org: "中国联合工程设计研究院有限公司",
      qualification: "资信证书编号：ZX11120240088",
    });

    exportDocxResultPath.value = res.path;
    exportDocxResultSize.value = res.size_bytes;
    showMsg("🎉 Word (.docx) 成果报告导出成功！已自动完成全书引用学术编号与文末参考文献章生成。", "success");
  } catch (err: any) {
    exportError.value = err.message || "导出失败";
    showMsg(`Word 导出失败: ${exportError.value}`, "error");
  } finally {
    exportingDocx.value = false;
  }
}

// ── 一键导出 Word (.docx)（含自洽性门禁拦截） ──
function handleExportDocx() {
  if (verificationResult.value && verificationResult.value.conflicts_count > 0) {
    pendingExportType.value = "docx";
    showConflictModal.value = true;
    return;
  }
  executeExportDocx();
}

// ── 执行 Markdown (.md) 导出 ──
async function executeExportMd() {
  if (!engine.baseUrl) {
    showMsg("本地引擎未就绪", "error");
    return;
  }
  if (!projectStore.currentProject) {
    showMsg("未选中项目", "error");
    return;
  }
  if (writtenChaptersCount.value === 0) {
    showMsg("全书尚无章节正文，请先在步骤 3 写作或步骤 4 审阅中完善内容", "error");
    return;
  }

  exportingMd.value = true;
  exportError.value = "";
  exportMdResultPath.value = "";

  try {
    const res = await engineApi.exportMd(engine.baseUrl, {
      project: projectStore.currentProject.name,
      title: projectStore.currentProject.name,
      chapters: projectStore.chapters,
      include_refs: true,
    });

    exportMdResultPath.value = res.path;
    exportMdResultSize.value = res.size_bytes;
    showMsg("🎉 Markdown (.md) 成果文件导出成功！已自动完成全书引用学术编号与文末参考文献章生成。", "success");
  } catch (err: any) {
    exportError.value = err.message || "导出失败";
    showMsg(`Markdown 导出失败: ${exportError.value}`, "error");
  } finally {
    exportingMd.value = false;
  }
}

// ── 一键导出 Markdown (.md)（含自洽性门禁拦截） ──
function handleExportMd() {
  if (verificationResult.value && verificationResult.value.conflicts_count > 0) {
    pendingExportType.value = "md";
    showConflictModal.value = true;
    return;
  }
  executeExportMd();
}

// ── 确认强制导出 ──
function confirmForceExport() {
  showConflictModal.value = false;
  if (pendingExportType.value === "docx") {
    executeExportDocx();
  } else if (pendingExportType.value === "md") {
    executeExportMd();
  }
  pendingExportType.value = null;
}

// ── 复制全书 Markdown 源码（学术编号版） ──
async function copyFullMarkdown() {
  const md = buildFullReportNumberedMarkdown();
  if (!md.trim()) {
    showMsg("暂无可复制的正文内容", "error");
    return;
  }
  try {
    await navigator.clipboard.writeText(md);
    showMsg("📋 全书排版终稿（含学术编号 [1][2] 与文末参考文献章）已复制至剪贴板！", "success");
  } catch {
    showMsg("剪贴板访问失败，请手动复制", "error");
  }
}

// ── 打开成果所在目录（直接在系统资源管理器中高亮选中导出的文件） ──
async function openExportFolder(filePath?: string) {
  if (!engine.baseUrl) return;
  try {
    await engineApi.openExportFolder(
      engine.baseUrl,
      filePath,
      projectStore.currentProject?.name,
    );
  } catch (err: any) {
    showMsg(`打开导出文件夹失败: ${err.message}`, "error");
  }
}

// ── 在系统默认浏览器中打开外部链接 ──
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

// ── 下载成果文件至本地电脑（远程云端引擎模式） ──
async function handleDownloadExport(filePath?: string) {
  if (!engine.baseUrl || !filePath) return;
  const downloadUrl = engineApi.getExportDownloadUrl(engine.baseUrl, filePath);
  try {
    const { open } = await import("@tauri-apps/plugin-shell");
    await open(downloadUrl);
    showMsg("📥 正在通过浏览器下载成果文件，请注意查看浏览器的下载目录！", "success");
  } catch {
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = filePath.replace(/^.*[\\\/]/, "");
    a.target = "_blank";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showMsg("📥 正在下载成果文件...", "success");
  }
}
</script>

<template>
  <div class="step5-container">
    <!-- 全局提示 Toast -->
    <transition name="toast-fade">
      <div v-if="toastMessage" class="global-toast" :class="toastType">
        <span class="toast-icon">
          {{ toastType === 'success' ? '✓' : toastType === 'error' ? '✕' : 'ℹ' }}
        </span>
        <span class="toast-text">{{ toastMessage }}</span>
      </div>
    </transition>

    <div class="step5-header">
      <div class="header-left">
        <h2 class="step5-title">📦 成果格式化导出与交付</h2>
        <p class="step5-subtitle">
          项目《{{ projectStore.currentProject?.name || '未命名' }}》· 已完成多维专家质检与全书合规修订
        </p>
      </div>
      <div class="header-right">
        <button class="btn btn-secondary" @click="projectStore.setStep(4)">
          &larr; 返回步骤 4：审阅修改
        </button>
      </div>
    </div>

    <div class="step5-grid">
      <!-- 左侧：全书概览与双格式导出卡片 -->
      <div class="export-main-col">
        <!-- 统计面板 -->
        <div class="stats-card">
          <div class="stat-item">
            <div class="stat-num">{{ writtenChaptersCount }} / {{ orderedSeqs.length }}</div>
            <div class="stat-lbl">完成章节数</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-num">{{ totalWordCount.toLocaleString() }}</div>
            <div class="stat-lbl">全书总字数 (纯正文)</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-num">{{ refSummary.total }}</div>
            <div class="stat-lbl">全书引用文献数</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-num">GB/T 7714</div>
            <div class="stat-lbl">著录规范标准</div>
          </div>
        </div>

        <!-- 0. 导出前上下文与自洽性复核卡片 (意见 1 落地) -->
        <div class="consistency-card">
          <div class="consistency-header">
            <div class="consistency-title-area">
              <span class="consistency-icon">📋</span>
              <div class="consistency-title-text">
                <h3>导出前修改上下文与自洽性复核</h3>
                <p class="consistency-sub">
                  智能核验跨章节工程技术经济指标自洽性、底稿规程出处溯源闭环与上下游逻辑呼应
                </p>
              </div>
            </div>
            <div class="consistency-header-actions">
              <div
                v-if="verificationResult"
                class="score-badge"
                :class="{
                  'score-pass': verificationResult.score >= 90,
                  'score-warn': verificationResult.score >= 70 && verificationResult.score < 90,
                  'score-danger': verificationResult.score < 70
                }"
              >
                <span class="score-prefix">综合自洽度</span>
                <span class="score-val">{{ verificationResult.score }}分</span>
              </div>
              <button
                class="btn btn-secondary btn-sm"
                :disabled="verifyingContext"
                @click="runContextVerification(true)"
              >
                <span v-if="verifyingContext" class="spinner-inline dark"></span>
                {{ verifyingContext ? '核验中...' : '🔄 重新核验' }}
              </button>
            </div>
          </div>

          <!-- 摘要提示 -->
          <div
            v-if="verificationResult"
            class="consistency-summary"
            :class="{
              'summary-pass': verificationResult.conflicts_count === 0 && verificationResult.warnings_count === 0,
              'summary-warn': verificationResult.conflicts_count === 0 && verificationResult.warnings_count > 0,
              'summary-danger': verificationResult.conflicts_count > 0
            }"
          >
            {{ verificationResult.summary }}
          </div>
          <div v-else-if="verifyingContext" class="consistency-loading">
            <span class="spinner-inline dark"></span> 正在深度核验跨章节数据一致性与引用出处链...
          </div>
          <div v-else-if="verificationError" class="consistency-summary summary-danger">
            ⚠️ 自洽性核验未完成：{{ verificationError }}
          </div>
          <div v-else class="consistency-empty">
            尚未执行自洽性复核，点击右上角「🔄 重新核验」启动检测。
          </div>

          <!-- 过滤器 Tab -->
          <div v-if="verificationResult && verificationResult.items.length > 0" class="verification-tabs">
            <button
              class="vtab-btn"
              :class="{ active: verificationFilter === 'all' }"
              @click="verificationFilter = 'all'"
            >
              全部 ({{ verificationResult.items.length }})
            </button>
            <button
              v-if="verificationResult.conflicts_count > 0"
              class="vtab-btn vtab-conflict"
              :class="{ active: verificationFilter === 'conflict' }"
              @click="verificationFilter = 'conflict'"
            >
              🚨 数据矛盾 ({{ verificationResult.conflicts_count }})
            </button>
            <button
              v-if="verificationResult.warnings_count > 0"
              class="vtab-btn vtab-warn"
              :class="{ active: verificationFilter === 'warning' }"
              @click="verificationFilter = 'warning'"
            >
              ⚠️ 关联预警 ({{ verificationResult.warnings_count }})
            </button>
            <button
              v-if="verificationResult.passed_count > 0"
              class="vtab-btn vtab-pass"
              :class="{ active: verificationFilter === 'pass' }"
              @click="verificationFilter = 'pass'"
            >
              ✅ 自洽通过 ({{ verificationResult.passed_count }})
            </button>
          </div>

          <!-- 诊断清单 -->
          <div v-if="verificationResult && filteredVerificationItems.length > 0" class="verification-list">
            <div
              v-for="item in filteredVerificationItems"
              :key="item.id"
              class="vitem-card"
              :class="`vitem-${item.status}`"
            >
              <div class="vitem-main">
                <div class="vitem-top">
                  <span class="vitem-status-icon">
                    {{ item.status === 'conflict' ? '🚨' : item.status === 'warning' ? '⚠️' : item.status === 'pass' ? '✅' : 'ℹ️' }}
                  </span>
                  <strong class="vitem-title">{{ item.title }}</strong>
                  <span class="vitem-tag" :class="`tag-${item.type}`">
                    {{ item.type === 'indicator' ? '核心指标' : item.type === 'citation' ? '出处溯源' : '上下游逻辑' }}
                  </span>
                </div>
                <div class="vitem-desc">{{ item.description }}</div>
                <div v-if="item.suggestion" class="vitem-sug">
                  💡 <strong>修改建议：</strong>{{ item.suggestion }}
                </div>
              </div>

              <!-- 涉及章节与快速定位按钮 -->
              <div v-if="item.affected_chapters && item.affected_chapters.length > 0" class="vitem-actions">
                <span class="vitem-chs-label">涉及章节：</span>
                <div class="vitem-chs-btns">
                  <button
                    v-for="chSeq in item.affected_chapters"
                    :key="chSeq"
                    class="btn btn-outline btn-xs"
                    @click="jumpToChapter(chSeq)"
                    title="点击立即跳转至步骤 4 对应章节进行修改"
                  >
                    📍 定位第 {{ chSeq }} 章修改
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 1. Word 文档 (.docx) 导出卡片 -->
        <div class="action-card">
          <div class="action-card-header">
            <div class="action-card-title">
              <span class="action-icon">📄</span>
              <span>标准化 Word 报告文档 (.docx)</span>
            </div>
            <span class="badge-recommended">标准交付推荐</span>
          </div>

          <p class="action-desc">
            依据投资项目编制规程排版标准，将全书引用按首次出现顺序编号为 <code>[1]</code>、<code>[2]</code>...，并在文末生成独立《参考文献》章（学术标准著录格式）。
          </p>

          <div class="action-buttons-row">
            <button
              class="btn btn-primary btn-lg"
              :disabled="exportingDocx || writtenChaptersCount === 0"
              @click="handleExportDocx"
            >
              <span v-if="exportingDocx" class="spinner-inline"></span>
              {{ exportingDocx ? '⚡ 正在生成 Word 文档...' : '🚀 一键导出 Word 报告 (.docx)' }}
            </button>
          </div>

          <!-- Word 导出成功结果卡片 -->
          <div v-if="exportDocxResultPath" class="export-success-box">
            <div class="success-top">
              <span class="success-icon">🎉</span>
              <div class="success-info">
                <strong>Word 报告已成功导出！</strong>
                <div class="success-path" :title="exportDocxResultPath">{{ exportDocxResultPath }}</div>
                <div class="success-meta">
                  文件大小：{{ (exportDocxResultSize / 1024).toFixed(1) }} KB · 全书引用已按首次出现顺序编号
                </div>
              </div>
            </div>
            <div class="success-actions">
              <button
                v-if="engine.isRemote"
                class="btn btn-primary btn-sm"
                @click="handleDownloadExport(exportDocxResultPath)"
              >
                ⬇️ 下载 Word 报告到本地
              </button>
              <button
                v-else
                class="btn btn-secondary btn-sm"
                @click="openExportFolder(exportDocxResultPath)"
              >
                📂 打开导出文件夹并选中文件
              </button>
            </div>
          </div>
        </div>

        <!-- 2. Markdown 报告 (.md) 导出卡片 -->
        <div class="action-card">
          <div class="action-card-header">
            <div class="action-card-title">
              <span class="action-icon">📝</span>
              <span>Markdown 纯文本报告 (.md)</span>
            </div>
            <span class="badge-secondary">通用排版格式</span>
          </div>

          <p class="action-desc">
            导出全书合并后的 Markdown 终稿文件，正文引用已统一替换为 <code>[1]</code>、<code>[2]</code>... 学术编号，文末附带规范的《参考文献》总表。
          </p>

          <div class="action-buttons-row">
            <button
              class="btn btn-secondary btn-lg"
              :disabled="exportingMd || writtenChaptersCount === 0"
              @click="handleExportMd"
            >
              <span v-if="exportingMd" class="spinner-inline"></span>
              {{ exportingMd ? '⚡ 正在生成 Markdown 文件...' : '💾 一键导出 Markdown 报告 (.md)' }}
            </button>

            <button class="btn btn-outline" @click="copyFullMarkdown">
              📋 复制全书 Markdown 源码
            </button>
          </div>

          <!-- MD 导出成功结果卡片 -->
          <div v-if="exportMdResultPath" class="export-success-box">
            <div class="success-top">
              <span class="success-icon">🎉</span>
              <div class="success-info">
                <strong>Markdown 文件已成功导出！</strong>
                <div class="success-path" :title="exportMdResultPath">{{ exportMdResultPath }}</div>
                <div class="success-meta">
                  文件大小：{{ (exportMdResultSize / 1024).toFixed(1) }} KB · 纯文本 UTF-8 编码
                </div>
              </div>
            </div>
            <div class="success-actions">
              <button
                v-if="engine.isRemote"
                class="btn btn-primary btn-sm"
                @click="handleDownloadExport(exportMdResultPath)"
              >
                ⬇️ 下载 Markdown 报告到本地
              </button>
              <button
                v-else
                class="btn btn-secondary btn-sm"
                @click="openExportFolder(exportMdResultPath)"
              >
                📂 打开导出文件夹并选中文件
              </button>
            </div>
          </div>
        </div>

        <div v-if="exportError" class="export-error-box">
          ⚠️ 导出错误：{{ exportError }}
        </div>
      </div>

      <!-- 右侧：全书参考文献全局编号总览表 -->
      <div class="export-side-col">
        <div class="ref-table-card">
          <div class="ref-table-header">
            <div class="ref-table-title">
              <span>📚 全书参考文献排序清单</span>
              <span class="ref-count-pill">{{ globalRefEntries.length }} 篇</span>
            </div>
            <div class="ref-table-subtitle">
              按全书首次出现顺序编号，文末将自动生成本清单
            </div>
          </div>

          <div class="ref-table-scrollable">
            <div
              v-for="entry in globalRefEntries"
              :key="entry.number"
              class="ref-entry-row"
            >
              <div class="ref-number-badge">[{{ entry.number }}]</div>
              <div class="ref-entry-info">
                <div class="ref-entry-title">
                  <span
                    class="ref-type-tag"
                    :class="`type-${entry.type}`"
                  >
                    {{ entry.type === 'standard' ? '规程标准' : entry.type === 'web' ? '联网检索' : '项目资料' }}
                  </span>
                  <a
                    v-if="entry.type === 'web' && entry.url"
                    href="#"
                    class="entry-title-link"
                    title="点击直接在浏览器中打开权威原网页"
                    @click.prevent="handleOpenWebUrl(entry.url)"
                  >
                    {{ entry.title }} <span class="ext-icon">↗</span>
                  </a>
                  <span v-else class="entry-title-text">{{ entry.title }}</span>
                </div>
                <div class="ref-entry-sub">
                  首次引用于第 {{ entry.firstChapterSeq }} 章 · 全书累计引用 {{ entry.count }} 次
                </div>
              </div>
            </div>

            <div v-if="globalRefEntries.length === 0" class="empty-ref-state">
              <div class="empty-icon">📚</div>
              <div class="empty-title">全书暂未检测到外部资料引用标记</div>
              <div class="empty-desc">在正文中使用【源:...】、【标:...】或【网:...】即可自动生成编号。</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 冲突拦截确认模态框 -->
    <div v-if="showConflictModal" class="modal-backdrop" @click.self="showConflictModal = false">
      <div class="modal-card">
        <div class="modal-header danger">
          <span class="modal-icon">⚠️</span>
          <h3>存在未消除的跨章节核心数据矛盾</h3>
        </div>
        <div class="modal-body">
          <p>
            系统检测到全书存在 <strong>{{ verificationResult?.conflicts_count }}</strong> 处跨章节核心技术经济指标矛盾（如总投资、用地等前后数据打架）。
          </p>
          <p class="modal-tip">
            直接导出未经对齐的成果可能导致初稿数据矛盾或专家对报告自洽性提出重大质询。建议先返回对应章节核对修改。
          </p>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showConflictModal = false">
            取消并检查
          </button>
          <button
            v-if="verificationResult?.items.find(i => i.status === 'conflict')?.affected_chapters[0]"
            class="btn btn-primary"
            @click="jumpToChapter(verificationResult!.items.find(i => i.status === 'conflict')!.affected_chapters[0]); showConflictModal = false;"
          >
            📍 定位到第 {{ verificationResult!.items.find(i => i.status === 'conflict')!.affected_chapters[0] }} 章修改
          </button>
          <button class="btn btn-outline-danger" @click="confirmForceExport">
            仍要强制导出
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.step5-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 24px 32px 64px;
  min-height: calc(100vh - 56px);
  box-sizing: border-box;
}

.step5-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.step5-title {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 4px;
}

.step5-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.step5-grid {
  display: grid;
  grid-template-columns: 1fr 420px;
  gap: 24px;
  align-items: start;
}

.export-main-col {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-card {
  display: flex;
  align-items: center;
  justify-content: space-around;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.stat-item {
  text-align: center;
}

.stat-num {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 4px;
}

.stat-lbl {
  font-size: 12px;
  color: #64748b;
}

.stat-divider {
  width: 1px;
  height: 36px;
  background: #e2e8f0;
}

.action-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 28px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.action-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.action-card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.action-icon {
  font-size: 22px;
}

.badge-recommended {
  background: #ecfdf5;
  color: #059669;
  border: 1px solid #a7f3d0;
  padding: 3px 10px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
}

.action-desc {
  font-size: 14px;
  color: #475569;
  line-height: 1.7;
  margin: 0 0 24px;
}

.action-desc code {
  background: #f1f5f9;
  color: #0f172a;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.action-buttons-row {
  display: flex;
  gap: 14px;
  align-items: center;
}

.export-success-box {
  margin-top: 24px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 10px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.success-top {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.success-icon {
  font-size: 24px;
}

.success-info strong {
  font-size: 15px;
  color: #15803d;
  display: block;
  margin-bottom: 4px;
}

.success-path {
  font-size: 12px;
  color: #334155;
  font-family: monospace;
  word-break: break-all;
  background: rgba(255, 255, 255, 0.7);
  padding: 4px 8px;
  border-radius: 4px;
  margin-bottom: 4px;
}

.success-meta {
  font-size: 12px;
  color: #166534;
}

.export-error-box {
  margin-top: 20px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 13px;
}

.ref-table-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.ref-table-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.ref-table-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 4px;
}

.ref-count-pill {
  background: #e2e8f0;
  color: #475569;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.ref-table-subtitle {
  font-size: 12px;
  color: #64748b;
}

.ref-table-scrollable {
  max-height: 520px;
  overflow-y: auto;
  padding: 8px 12px;
}

.ref-entry-row {
  display: flex;
  gap: 12px;
  padding: 10px 8px;
  border-bottom: 1px solid #f1f5f9;
  align-items: flex-start;
}

.ref-entry-row:last-child {
  border-bottom: none;
}

.ref-number-badge {
  font-size: 13px;
  font-weight: 700;
  color: #2563eb;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 2px 6px;
  border-radius: 4px;
  min-width: 32px;
  text-align: center;
}

.ref-entry-info {
  flex: 1;
  min-width: 0;
}

.ref-entry-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.ref-type-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.ref-type-tag.type-standard {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.ref-type-tag.type-web {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.ref-type-tag.type-material {
  background: #f5f3ff;
  color: #6d28d9;
  border: 1px solid #ddd6fe;
}

.entry-title-text {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.entry-title-link {
  font-size: 13px;
  font-weight: 600;
  color: #0369a1;
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.entry-title-link:hover {
  color: #0284c7;
  text-decoration: underline;
}

.ext-icon {
  font-size: 11px;
  opacity: 0.75;
  flex-shrink: 0;
}

.ref-entry-sub {
  font-size: 11px;
  color: #94a3b8;
}

.empty-ref-state {
  text-align: center;
  padding: 48px 16px;
}

.empty-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.empty-title {
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 4px;
}

.empty-desc {
  font-size: 12px;
  color: #94a3b8;
}

/* 按钮样式 */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
  border-color: #1d4ed8;
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

.btn-lg {
  padding: 10px 22px;
  font-size: 15px;
}

.btn-sm {
  padding: 5px 12px;
  font-size: 12px;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.spinner-inline {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Toast */
.global-toast {
  position: fixed;
  top: 68px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 20px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 9999;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  font-size: 14px;
  font-weight: 500;
}

.global-toast.success {
  background: #10b981;
  color: #fff;
}

.global-toast.error {
  background: #ef4444;
  color: #fff;
}

.global-toast.info {
  background: #3b82f6;
  color: #fff;
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.25s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, -10px);
}

/* 自洽性复核卡片 (意见 1 落地) */
.consistency-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.consistency-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.consistency-title-area {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.consistency-icon {
  font-size: 24px;
  line-height: 1;
}

.consistency-title-text h3 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.consistency-sub {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.4;
}

.consistency-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.score-badge {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 9999px;
  font-weight: 600;
  font-size: 13px;
}

.score-badge.score-pass {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.score-badge.score-warn {
  background: #fffbeb;
  color: #92400e;
  border: 1px solid #fde68a;
}

.score-badge.score-danger {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.score-val {
  font-size: 16px;
  font-weight: 700;
}

.consistency-summary {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13.5px;
  line-height: 1.5;
  font-weight: 500;
}

.summary-pass {
  background: #f0fdf4;
  color: #166534;
  border: 1px solid #bbf7d0;
}

.summary-warn {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fef3c7;
}

.summary-danger {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fee2e2;
}

.consistency-loading {
  font-size: 13px;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}

.spinner-inline.dark {
  border: 2px solid rgba(15, 23, 42, 0.2);
  border-top-color: #0f172a;
}

.consistency-empty {
  font-size: 13px;
  color: #94a3b8;
  font-style: italic;
}

.verification-tabs {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 8px;
}

.vtab-btn {
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s ease;
}

.vtab-btn:hover {
  background: #f1f5f9;
}

.vtab-btn.active {
  background: #0f172a;
  color: #ffffff;
  border-color: #0f172a;
  font-weight: 600;
}

.vtab-btn.vtab-conflict.active {
  background: #ef4444;
  border-color: #ef4444;
}

.vtab-btn.vtab-warn.active {
  background: #f59e0b;
  border-color: #f59e0b;
}

.vtab-btn.vtab-pass.active {
  background: #10b981;
  border-color: #10b981;
}

.verification-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 380px;
  overflow-y: auto;
  padding-right: 4px;
}

.vitem-card {
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
}

.vitem-card.vitem-conflict {
  background: #fff1f2;
  border: 1px solid #fecdd3;
}

.vitem-card.vitem-warning {
  background: #fffbeb;
  border: 1px solid #fef3c7;
}

.vitem-card.vitem-pass {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.vitem-card.vitem-info {
  background: #f0f9ff;
  border: 1px solid #e0f2fe;
}

.vitem-top {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.vitem-status-icon {
  font-size: 14px;
}

.vitem-title {
  color: #1e293b;
  font-size: 13.5px;
}

.vitem-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.vitem-tag.tag-indicator {
  background: #e0e7ff;
  color: #3730a3;
}

.vitem-tag.tag-citation {
  background: #e0f2fe;
  color: #0369a1;
}

.vitem-tag.tag-logic {
  background: #f3e8ff;
  color: #6b21a8;
}

.vitem-desc {
  color: #334155;
  line-height: 1.5;
}

.vitem-sug {
  background: rgba(255, 255, 255, 0.75);
  border-left: 3px solid #f59e0b;
  padding: 6px 10px;
  border-radius: 0 4px 4px 0;
  color: #78350f;
  font-size: 12px;
  line-height: 1.45;
}

.vitem-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
  padding-top: 6px;
  border-top: 1px dashed rgba(0, 0, 0, 0.08);
}

.vitem-chs-label {
  font-size: 12px;
  color: #64748b;
}

.vitem-chs-btns {
  display: flex;
  gap: 6px;
}

.btn-xs {
  padding: 2px 8px;
  font-size: 11.5px;
  border-radius: 4px;
}

/* Modal */
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.modal-card {
  background: #ffffff;
  border-radius: 12px;
  width: 90%;
  max-width: 520px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: modal-in 0.2s ease-out;
}

@keyframes modal-in {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-header h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
}

.modal-header.danger h3 {
  color: #991b1b;
}

.modal-icon {
  font-size: 24px;
}

.modal-body {
  font-size: 13.5px;
  color: #334155;
  line-height: 1.6;
}

.modal-body p {
  margin: 0 0 10px;
}

.modal-tip {
  color: #64748b;
  font-size: 12.5px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

.btn-outline-danger {
  background: transparent;
  color: #dc2626;
  border: 1px solid #fca5a5;
}

.btn-outline-danger:hover:not(:disabled) {
  background: #fef2f2;
  border-color: #ef4444;
}
</style>
