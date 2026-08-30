<script setup lang="ts">
import { computed, ref } from "vue";
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

const exporting = ref(false);
const exportResultPath = ref("");
const exportResultSize = ref(0);
const exportError = ref("");
const toastMessage = ref("");
const toastType = ref<"success" | "error" | "info">("info");
let toastTimer: any = null;

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

// ── 一键导出 Word (.docx) ──
async function handleExportDocx() {
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

  exporting.value = true;
  exportError.value = "";
  exportResultPath.value = "";

  try {
    const res = await engineApi.exportDocx(engine.baseUrl, {
      project: projectStore.currentProject.name,
      title: projectStore.currentProject.name,
      chapters: projectStore.chapters,
      include_refs: true,
    });

    exportResultPath.value = res.path;
    exportResultSize.value = res.size_bytes;
    showMsg("🎉 Word 成果报告导出成功！已自动完成全书引用学术编号与文末参考文献章生成。", "success");
  } catch (err: any) {
    exportError.value = err.message || "导出失败";
    showMsg(`导出失败: ${exportError.value}`, "error");
  } finally {
    exporting.value = false;
  }
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

// ── 打开成果所在目录 ──
async function openExportFolder() {
  if (!engine.baseUrl || !projectStore.currentProject) return;
  try {
    await engineApi.openProjectDir(engine.baseUrl, projectStore.currentProject.name);
  } catch (err: any) {
    showMsg(`打开目录失败: ${err.message}`, "error");
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
      <!-- 左侧：全书概览与一键导出卡片 -->
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

        <!-- 核心导出操作卡片 -->
        <div class="action-card">
          <div class="action-card-header">
            <div class="action-card-title">
              <span class="action-icon">📄</span>
              <span>标准化 Word 报告文档 (.docx)</span>
            </div>
            <span class="badge-recommended">标准交付推荐</span>
          </div>

          <p class="action-desc">
            系统将在导出时自动扫描全书正文，将所有参考资料标签（项目底稿、国家与行业规程标准、权威联网）按其在全书首次出现的先后顺序统一编号为 <code>[1]</code>、<code>[2]</code>、<code>[3]</code>...，并在报告文末自动作为最后一章生成符合学术期刊与国家标准著录格式的《参考文献》章。
          </p>

          <div class="action-buttons-row">
            <button
              class="btn btn-primary btn-lg"
              :disabled="exporting || writtenChaptersCount === 0"
              @click="handleExportDocx"
            >
              <span v-if="exporting" class="spinner-inline"></span>
              {{ exporting ? '⚡ 正在执行全书引用排序与 Word 文档排版导出...' : '🚀 一键导出 Word 报告 (.docx)' }}
            </button>

            <button class="btn btn-outline" @click="copyFullMarkdown">
              📋 复制全书 Markdown（含学术编号）
            </button>
          </div>

          <!-- 导出成功结果卡片 -->
          <div v-if="exportResultPath" class="export-success-box">
            <div class="success-top">
              <span class="success-icon">🎉</span>
              <div class="success-info">
                <strong>Word 成果报告导出成功！</strong>
                <div class="success-path" :title="exportResultPath">{{ exportResultPath }}</div>
                <div class="success-meta">
                  文件大小：{{ (exportResultSize / 1024).toFixed(1) }} KB · 全书引用已按首次出现顺序编号
                </div>
              </div>
            </div>
            <div class="success-actions">
              <button class="btn btn-secondary btn-sm" @click="openExportFolder">
                📂 打开成果导出文件夹
              </button>
            </div>
          </div>

          <div v-if="exportError" class="export-error-box">
            ⚠️ 导出错误：{{ exportError }}
          </div>
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
                  <span class="entry-title-text">{{ entry.title }}</span>
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
</style>
