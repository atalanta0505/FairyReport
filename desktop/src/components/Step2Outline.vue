<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useEngineStore } from "../stores/engine";
import { useProjectStore } from "../stores/project";
import { useSettingsStore } from "../stores/settings";

const engine = useEngineStore();
const settings = useSettingsStore();
const projectStore = useProjectStore();

const actionMessage = ref<{ type: "success" | "error"; text: string } | null>(null);

function showMsg(text: string, type: "success" | "error" = "success") {
  actionMessage.value = { type, text };
  setTimeout(() => {
    if (actionMessage.value?.text === text) {
      actionMessage.value = null;
    }
  }, 4000);
}

async function ensureStep2State() {
  if (engine.baseUrl && projectStore.templates.length === 0) {
    try {
      await projectStore.loadTemplates(engine.baseUrl);
    } catch (e) {
      showMsg(`加载模板失败: ${(e as Error).message}`, "error");
    }
  }
  if (projectStore.currentProject?.name && !projectStore.outlineMd) {
    try {
      await projectStore.loadOutline(engine.baseUrl, projectStore.currentProject.name);
    } catch {
      // ignore
    }
  }
}

onMounted(ensureStep2State);

watch(
  () => projectStore.currentStep,
  (step) => {
    if (step === 2) {
      ensureStep2State();
    }
  },
);

watch(
  () => projectStore.currentProject?.name,
  (projectName) => {
    if (projectName && projectStore.currentStep === 2) {
      projectStore.loadOutline(engine.baseUrl, projectName).catch(() => {});
    }
  },
);

watch(
  () => engine.baseUrl,
  (url) => {
    if (url && projectStore.currentStep === 2) {
      ensureStep2State();
    }
  },
);

const currentTemplate = computed(() => {
  return projectStore.templates.find((t) => t.report_type === projectStore.reportType);
});

const wordCount = computed(() => {
  return projectStore.outlineMd ? projectStore.outlineMd.length : 0;
});

const lineCount = computed(() => {
  return projectStore.outlineMd ? projectStore.outlineMd.split("\n").length : 0;
});

function onSelectTemplate(reportType: string) {
  projectStore.setReportType(reportType, engine.baseUrl);
}

async function handleGenerateOutline() {
  if (!engine.baseUrl) {
    showMsg("本地引擎未就绪，请等待引擎启动", "error");
    return;
  }
  if (!settings.llmKey) {
    showMsg("请先在右上角「设置」中配置 LLM API Key（如 DeepSeek Key）", "error");
    return;
  }

  try {
    await projectStore.generateOutline(engine.baseUrl, {
      api_key: settings.llmKey,
      base_url: settings.llmBaseUrl || "https://api.deepseek.com/v1",
      model: settings.llmModel || "deepseek-v4-flash",
    });
    showMsg("大纲智能生成成功！您可以在下方进行自由编辑与调整。");
  } catch (err) {
    showMsg(`生成大纲失败: ${(err as Error).message}`, "error");
  }
}

function onOutlineInput(e: Event) {
  const target = e.target as HTMLTextAreaElement;
  projectStore.setOutlineMd(target.value, engine.baseUrl);
}

function prevStep() {
  projectStore.setStep(1);
}

function nextStep() {
  if (!projectStore.outlineMd.trim()) {
    showMsg("请先生成或输入大纲内容后再进入下一步", "error");
    return;
  }
  projectStore.setStep(3);
}
</script>

<template>
  <div class="step2-container">
    <!-- 全局操作消息条 -->
    <transition name="fade">
      <div v-if="actionMessage" :class="['alert-banner', actionMessage.type]">
        {{ actionMessage.text }}
      </div>
    </transition>

    <!-- 1. 报告模板选择卡片 -->
    <div class="card template-card">
      <div class="card-header">
        <div class="title-with-badge">
          <h3>报告类型与模板选择</h3>
          <span class="badge">
            当前项目：{{ projectStore.currentProject?.name || "未选择项目" }}
          </span>
        </div>
      </div>

      <div class="card-body">
        <p class="section-desc">
          请选择本次编制的标准报告类型。系统将根据行业规程规范与模板标准自动构建报告结构体系：
        </p>

        <!-- 14 种标准报告模板网格 -->
        <div class="templates-grid">
          <div
            v-for="t in projectStore.templates"
            :key="t.report_type"
            class="template-item"
            :class="{ active: projectStore.reportType === t.report_type }"
            @click="onSelectTemplate(t.report_type)"
          >
            <div class="template-item-top">
              <span class="template-icon">📄</span>
              <span class="template-name">{{ t.report_type }}</span>
            </div>
          </div>
        </div>

        <!-- 模板说明提示 -->
        <div v-if="currentTemplate?.notes" class="template-notes-box">
          <span class="notes-icon">💡</span>
          <span class="notes-text"><strong>模板规范提示：</strong>{{ currentTemplate.notes }}</span>
        </div>
      </div>
    </div>

    <!-- 2. AI 大纲生成与在线编辑器卡片 -->
    <div class="card outline-editor-card">
      <div class="card-header">
        <div class="title-with-badge">
          <h3>报告大纲（Markdown 编辑与结构树）</h3>
          <span class="count-badge" v-if="projectStore.outlineChapters.length > 0">
            已识别 {{ projectStore.outlineChapters.length }} 个核心章节
          </span>
        </div>
        <div class="header-actions">
          <button
            class="btn btn-primary"
            :disabled="projectStore.generatingOutline"
            @click="handleGenerateOutline"
          >
            <span v-if="projectStore.generatingOutline" class="btn-loading">
              <span class="spinner-sm"></span> 正在智能生成大纲...
            </span>
            <span v-else>
              {{ projectStore.outlineMd ? "🪄 重新生成大纲" : "🪄 AI 智能生成大纲" }}
            </span>
          </button>
        </div>
      </div>

      <div class="card-body outline-body">
        <!-- 生成中遮罩提示 -->
        <div v-if="projectStore.generatingOutline" class="generating-banner">
          <div class="spinner"></div>
          <div>
            <strong>AI 正在结合项目资料与通用规范生成报告大纲...</strong>
            <p>基于 {{ projectStore.reportType }} 规范自动规划章节层级与标准结构体系，请稍候。</p>
          </div>
        </div>

        <!-- 双栏编辑器：左侧 Markdown 原文，右侧实时章节树 -->
        <div class="editor-split-view">
          <!-- 左侧：多行 Markdown 编辑区 -->
          <div class="editor-pane">
            <div class="pane-header">
              <span class="pane-title">📝 Markdown 大纲源码</span>
              <span class="pane-stats">{{ lineCount }} 行 · {{ wordCount }} 字</span>
            </div>
            <textarea
              class="outline-textarea"
              placeholder="# 第一章 概述&#10;## 1.1 项目背景&#10;## 1.2 编制依据&#10;# 第二章 ..."
              :value="projectStore.outlineMd"
              @input="onOutlineInput"
            ></textarea>
          </div>

          <!-- 右侧：章节树形结构实时预览 -->
          <div class="preview-pane">
            <div class="pane-header">
              <span class="pane-title">📑 章节目录预览</span>
              <span class="pane-stats">共 {{ projectStore.outlineChapters.length }} 章</span>
            </div>
            <div class="chapter-tree-list">
              <div
                v-for="ch in projectStore.outlineChapters"
                :key="ch.seq"
                class="chapter-tree-item"
              >
                <span class="chapter-seq-badge">{{ ch.seq }}</span>
                <span class="chapter-title-text" :title="ch.title">{{ ch.title }}</span>
              </div>
              <div v-if="projectStore.outlineChapters.length === 0" class="empty-chapters">
                暂无章节，请点击上方「AI 智能生成大纲」或在左侧输入标准章标题（如 <code># 第一章 xxx</code>）。
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部流转按钮 -->
    <div class="bottom-nav">
      <button class="btn btn-secondary btn-lg" @click="prevStep">
        &larr; 上一步：项目与资料
      </button>
      <button
        class="btn btn-primary btn-lg"
        :disabled="!projectStore.outlineMd.trim()"
        @click="nextStep"
      >
        下一步：章节写作 &rarr;
      </button>
    </div>
  </div>
</template>

<style scoped>
.step2-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px 20px 48px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.alert-banner {
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.4;
  margin-bottom: 4px;
}
.alert-banner.success {
  background: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}
.alert-banner.error {
  background: #ffebee;
  color: #c62828;
  border: 1px solid #ffcdd2;
}

.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 12px;
}

.badge {
  background: #e0e7ff;
  color: #4338ca;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
}

.type-badge {
  background: #f1f5f9;
  color: #0369a1;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 12px;
  font-weight: 500;
}

.count-badge {
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
}

.card-body {
  padding: 20px;
}

.section-desc {
  margin: 0 0 14px 0;
  font-size: 13px;
  color: #64748b;
}

/* 14 种模板网格 */
.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}

.template-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
  cursor: pointer;
  background: #fff;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 6px;
}
.template-item:hover {
  border-color: #93c5fd;
  background: #f8fafc;
}
.template-item.active {
  border-color: #2b6cff;
  background: #eff6ff;
  box-shadow: 0 0 0 1px #2b6cff;
}

.template-item-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.template-icon {
  font-size: 16px;
}
.template-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}
.template-item.active .template-name {
  color: #1d4ed8;
}

.template-item-meta {
  display: flex;
  justify-content: flex-end;
}
.words-limit {
  font-size: 11px;
  color: #64748b;
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 4px;
}
.template-item.active .words-limit {
  background: #dbeafe;
  color: #1e40af;
}

.template-notes-box {
  margin-top: 14px;
  padding: 10px 14px;
  background: #fffbeb;
  border: 1px solid #fef3c7;
  border-radius: 6px;
  font-size: 12px;
  color: #92400e;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 大纲编辑器双栏 */
.outline-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.generating-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 18px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  color: #1e40af;
}
.generating-banner p {
  margin: 4px 0 0 0;
  font-size: 12px;
  color: #3b82f6;
}

.editor-split-view {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 16px;
  min-height: 420px;
}

.editor-pane, .preview-pane {
  display: flex;
  flex-direction: column;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}

.pane-header {
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pane-title {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}
.pane-stats {
  font-size: 11px;
  color: #94a3b8;
}

.outline-textarea {
  flex: 1;
  padding: 14px;
  border: none;
  resize: vertical;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #0f172a;
  outline: none;
  background: #fafafa;
  min-height: 380px;
}
.outline-textarea:focus {
  background: #fff;
}

.chapter-tree-list {
  flex: 1;
  padding: 12px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chapter-tree-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
}
.chapter-seq-badge {
  background: #2563eb;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
}
.chapter-title-text {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-chapters {
  padding: 40px 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.6;
}
.empty-chapters code {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  color: #334155;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn {
  padding: 7px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary {
  background: #2b6cff;
  color: #fff;
}
.btn-primary:hover:not(:disabled) {
  background: #1d57e0;
}
.btn-secondary {
  background: #f1f5f9;
  color: #334155;
  border-color: #cbd5e1;
}
.btn-secondary:hover:not(:disabled) {
  background: #e2e8f0;
}
.btn-lg {
  padding: 10px 24px;
  font-size: 15px;
}

.btn-loading {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #bae6fd;
  border-top-color: #0284c7;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}
.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.bottom-nav {
  display: flex;
  justify-content: space-between;
  padding-top: 8px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
