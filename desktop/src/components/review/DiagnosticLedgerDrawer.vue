<script setup lang="ts">
import type * as engineApi from "../../lib/engineApi";

defineProps<{
  open: boolean;
  filterScope: "current" | "all";
  activeTab: "issues" | "numerical" | "gaps";
  chapterSeq?: number;
  chapterTitle?: string;
  currentChapterIssues: engineApi.ReviewIssue[];
  allIssues: engineApi.ReviewIssue[];
  allNumericalChecks: engineApi.NumericalCheckItem[];
  allDataGaps: any[];
  revisingSeq: number | null;
  revisingIssueId: string | null;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "update:filterScope", val: "current" | "all"): void;
  (e: "update:activeTab", val: "issues" | "numerical" | "gaps"): void;
  (e: "locate-issue", issue: engineApi.ReviewIssue): void;
  (e: "fix-issue", issue: engineApi.ReviewIssue): void;
}>();
</script>

<template>
  <transition name="drawer-fade">
    <div v-if="open" class="ref-drawer-overlay" @click="emit('close')">
      <div class="ref-drawer-panel diagnostic-drawer-panel" @click.stop>
        <div class="drawer-header">
          <div class="drawer-title-box">
            <h4>📋 投资项目编制规范专家诊断总台账</h4>
            <span class="drawer-sub"
              >第 {{ chapterSeq }} 章：{{ chapterTitle }} · 全书累计
              {{ allIssues.length }} 项建议</span
            >
          </div>
          <button class="drawer-close-btn" @click="emit('close')">✕</button>
        </div>

        <div class="drawer-scope-tabs">
          <button
            class="scope-tab-btn"
            :class="{ active: filterScope === 'current' }"
            @click="emit('update:filterScope', 'current')"
          >
            📌 当前章 ({{ currentChapterIssues.length }})
          </button>
          <button
            class="scope-tab-btn"
            :class="{ active: filterScope === 'all' }"
            @click="emit('update:filterScope', 'all')"
          >
            🌐 全书诊断 ({{ allIssues.length }})
          </button>
        </div>

        <div class="diagnostic-nav-tabs">
          <button
            class="diag-tab-btn"
            :class="{ active: activeTab === 'issues' }"
            @click="emit('update:activeTab', 'issues')"
          >
            ⚠️ 审阅问题 ({{
              filterScope === "current" ? currentChapterIssues.length : allIssues.length
            }})
          </button>
          <button
            class="diag-tab-btn"
            :class="{ active: activeTab === 'numerical' }"
            @click="emit('update:activeTab', 'numerical')"
          >
            🔢 数值校核 ({{ allNumericalChecks.length }})
          </button>
          <button
            class="diag-tab-btn"
            :class="{ active: activeTab === 'gaps' }"
            @click="emit('update:activeTab', 'gaps')"
          >
            🧩 缺项排查 ({{ allDataGaps.length }})
          </button>
        </div>

        <div class="drawer-body-scrollable">
          <div v-if="activeTab === 'issues'" class="diag-section-list">
            <div
              v-for="(issue, idx) in filterScope === 'current' ? currentChapterIssues : allIssues"
              :key="issue.id || idx"
              :id="`issue-card-${issue.id || idx}`"
              class="diag-issue-card"
              :class="`severity-${issue.severity || 'medium'}`"
            >
              <div class="issue-card-top">
                <div class="issue-tag-group">
                  <span class="severity-pill" :class="issue.severity || 'medium'">
                    {{
                      issue.severity === "critical"
                        ? "🔴 严重"
                        : issue.severity === "high"
                        ? "🟠 重大"
                        : issue.severity === "medium"
                        ? "🟡 一般"
                        : "🔵 提示"
                    }}
                  </span>
                  <span class="dim-pill">{{ issue.dimension || issue.category || "编制规范" }}</span>
                  <span v-if="issue.chapterSeq" class="ch-scope-pill"
                    >第 {{ issue.chapterSeq }} 章</span
                  >
                </div>
                <div class="issue-actions-top">
                  <button
                    class="btn btn-outline btn-xs"
                    @click="emit('locate-issue', issue)"
                    title="在正文画布中高亮定位该问题"
                  >
                    📍 定位正文
                  </button>
                  <button
                    class="btn btn-primary btn-xs"
                    :disabled="revisingSeq !== null"
                    @click="emit('fix-issue', issue)"
                    title="针对该问题执行外科手术式局部精准修复"
                  >
                    <span
                      v-if="
                        revisingIssueId ===
                        (issue.id || issue.quote || issue.description || 'single')
                      "
                      class="spinner-inline"
                    ></span>
                    ⚡ 局部修复
                  </button>
                </div>
              </div>

              <div class="issue-desc-box">
                <strong>{{ issue.description || issue.message }}</strong>
              </div>

              <div v-if="issue.snippet || issue.quote" class="issue-snippet-box">
                <span class="snippet-label">原文片段：</span>
                <span class="snippet-text">“{{ issue.snippet || issue.quote }}”</span>
              </div>

              <div class="issue-sug-box">
                <span class="sug-icon">💡</span>
                <span class="sug-text"
                  ><strong>优化建议：</strong
                  >{{
                    issue.suggestion || "请根据投资项目编制规范与行业规程补充详实论证。"
                  }}</span
                >
              </div>
            </div>

            <div
              v-if="
                (filterScope === 'current' ? currentChapterIssues.length : allIssues.length) === 0
              "
              class="empty-diag-state"
            >
              <div class="empty-icon">🟢</div>
              <div class="empty-title">当前暂无审阅诊断问题</div>
              <div class="empty-desc">
                符合投资项目编制规程与行业规范，或者请点击上方「🔍 审阅本章」执行深度体检。
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'numerical'" class="diag-section-list">
            <div
              v-for="(numItem, idx) in allNumericalChecks"
              :key="idx"
              class="num-check-card"
            >
              <div class="num-card-top">
                <span class="num-indicator-name">{{
                  numItem.indicator_name || numItem.parameter
                }}</span>
                <span
                  class="num-consistent-pill"
                  :class="{
                    'is-inconsistent': !numItem.is_consistent && numItem.status === 'abnormal',
                  }"
                >
                  {{
                    numItem.is_consistent || numItem.status === "normal"
                      ? "✓ 数值自洽"
                      : "⚠️ 数值存疑"
                  }}
                </span>
              </div>
              <div class="num-values-row">
                <div class="val-box">
                  <span class="val-lbl">正文提及值</span>
                  <span class="val-txt">{{
                    numItem.mentioned_value || numItem.extracted_value || "—"
                  }}</span>
                </div>
                <div class="val-box">
                  <span class="val-lbl">底稿参考值</span>
                  <span class="val-txt">{{ numItem.reference_value || "—" }}</span>
                </div>
              </div>
              <div v-if="numItem.notes || numItem.note" class="num-notes-box">
                {{ numItem.notes || numItem.note }}
              </div>
            </div>
            <div v-if="allNumericalChecks.length === 0" class="empty-diag-state">
              <div class="empty-icon">🔢</div>
              <div class="empty-title">暂无数值校核数据</div>
              <div class="empty-desc">
                执行全书审阅后，系统将自动比对全书核心经济技术指标与投资估算数值。
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'gaps'" class="diag-section-list">
            <div v-for="(gap, idx) in allDataGaps" :key="idx" class="data-gap-card">
              <div class="gap-top">
                <span class="gap-icon">🧩</span>
                <span class="gap-title">{{ typeof gap === "string" ? gap : gap.gap }}</span>
              </div>
              <div v-if="gap.chapterTitle" class="gap-ch-tag">
                第 {{ gap.chapterSeq }} 章：{{ gap.chapterTitle }}
              </div>
            </div>
            <div v-if="allDataGaps.length === 0" class="empty-diag-state">
              <div class="empty-icon">🧩</div>
              <div class="empty-title">暂无缺项提示</div>
              <div class="empty-desc">全书各章节编制要素完整，未发现重大缺项。</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.ref-drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.4);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}
.ref-drawer-panel {
  width: 540px;
  max-width: 90vw;
  height: 100%;
  background: #ffffff;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
}
.drawer-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.drawer-title-box h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}
.drawer-sub {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
  display: block;
}
.drawer-close-btn {
  background: transparent;
  border: none;
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}
.drawer-close-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}
.drawer-scope-tabs,
.diagnostic-nav-tabs {
  display: flex;
  padding: 8px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  gap: 8px;
}
.scope-tab-btn,
.diag-tab-btn {
  background: transparent;
  border: 1px solid #cbd5e1;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s ease;
}
.scope-tab-btn.active,
.diag-tab-btn.active {
  background: #3b82f6;
  border-color: #2563eb;
  color: #ffffff;
  font-weight: 600;
}
.drawer-body-scrollable {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.diag-section-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.diag-issue-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s ease;
}
.diag-issue-card.severity-critical,
.diag-issue-card.severity-error {
  border-left: 4px solid #ef4444;
}
.diag-issue-card.severity-high {
  border-left: 4px solid #f97316;
}
.diag-issue-card.severity-medium,
.diag-issue-card.severity-warning {
  border-left: 4px solid #eab308;
}
.diag-issue-card.severity-low,
.diag-issue-card.severity-suggestion {
  border-left: 4px solid #3b82f6;
}
.issue-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.issue-tag-group {
  display: flex;
  align-items: center;
  gap: 6px;
}
.severity-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
}
.dim-pill {
  background: #f1f5f9;
  color: #475569;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
}
.ch-scope-pill {
  background: #e0e7ff;
  color: #4338ca;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
}
.issue-actions-top {
  display: flex;
  align-items: center;
  gap: 6px;
}
.btn-xs {
  padding: 3px 8px;
  font-size: 11px;
}
.issue-desc-box {
  font-size: 13px;
  color: #0f172a;
  line-height: 1.5;
}
.issue-snippet-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 12px;
  color: #475569;
}
.snippet-label {
  font-weight: 600;
  color: #64748b;
}
.issue-sug-box {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12.5px;
  color: #166534;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}
.num-check-card,
.data-gap-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.num-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.num-indicator-name {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}
.num-consistent-pill {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #dcfce7;
  color: #15803d;
  font-weight: 600;
}
.num-consistent-pill.is-inconsistent {
  background: #fee2e2;
  color: #991b1b;
}
.num-values-row {
  display: flex;
  gap: 16px;
  background: #f8fafc;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 12px;
}
.val-lbl {
  color: #64748b;
  margin-right: 4px;
}
.val-txt {
  font-weight: 600;
  color: #0f172a;
}
.num-notes-box {
  font-size: 12px;
  color: #64748b;
}
.gap-top {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}
.gap-ch-tag {
  font-size: 11.5px;
  color: #64748b;
}
.empty-diag-state {
  text-align: center;
  padding: 40px 10px;
}
</style>
