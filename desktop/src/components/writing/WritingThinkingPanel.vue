<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import type { ChapterWritingProgress } from "../../stores/project";

const props = defineProps<{
  visible: boolean;
  progress: ChapterWritingProgress | null;
}>();

const showThoughtDetails = ref(true);
const thoughtContentRef = ref<HTMLElement | null>(null);

watch(
  () => props.progress?.thoughtText,
  async () => {
    if (showThoughtDetails.value && thoughtContentRef.value) {
      await nextTick();
      thoughtContentRef.value.scrollTop = thoughtContentRef.value.scrollHeight;
    }
  },
);
</script>

<template>
  <transition name="fade">
    <div v-if="visible" class="thinking-state-container">
      <div class="thinking-card-inner">
        <div class="thinking-top-row">
          <div class="thinking-badge">
            <span class="radar-pulse"></span>
            <span class="thinking-badge-text">大模型深度推理与专业构思中 (纯中文)</span>
          </div>
          <div class="thinking-elapsed-timer">
            ⚡ 构思已耗时 <strong>{{ progress?.elapsedSeconds || 0 }}</strong> 秒
          </div>
        </div>

        <div class="pipeline-stepper">
          <div
            class="stepper-node"
            :class="{
              completed: progress?.stage !== 'rag',
              active: progress?.stage === 'rag',
            }"
          >
            <div class="stepper-badge">
              <span v-if="progress?.stage !== 'rag'" class="stepper-check">✓</span>
              <span v-else class="stepper-spinner"></span>
            </div>
            <div class="stepper-text">
              <span class="stepper-title">三源知识检索</span>
              <span class="stepper-desc">底稿数据 + 行业规程 + 百度联网 RAG</span>
            </div>
          </div>

          <div class="stepper-line" :class="{ completed: progress?.stage !== 'rag' }"></div>

          <div
            class="stepper-node"
            :class="{
              completed: ['reasoning', 'writing'].includes(progress?.stage || ''),
              active: progress?.stage === 'skeleton',
              pending: progress?.stage === 'rag',
            }"
          >
            <div class="stepper-badge">
              <span
                v-if="['reasoning', 'writing'].includes(progress?.stage || '')"
                class="stepper-check"
                >✓</span
              >
              <span v-else-if="progress?.stage === 'skeleton'" class="stepper-spinner"></span>
              <span v-else class="stepper-dot">2</span>
            </div>
            <div class="stepper-text">
              <span class="stepper-title">骨架提取锁定</span>
              <span class="stepper-desc">全层级大纲与结构骨架</span>
            </div>
          </div>

          <div
            class="stepper-line"
            :class="{ completed: ['reasoning', 'writing'].includes(progress?.stage || '') }"
          ></div>

          <div
            class="stepper-node"
            :class="{
              completed: progress?.stage === 'writing',
              active: ['reasoning', 'writing'].includes(progress?.stage || ''),
              pending: ['rag', 'skeleton'].includes(progress?.stage || ''),
            }"
          >
            <div class="stepper-badge">
              <span v-if="progress?.stage === 'writing'" class="stepper-check">✓</span>
              <span v-else-if="progress?.stage === 'reasoning'" class="stepper-wave">
                <span class="wave-bar wb-1"></span>
                <span class="wave-bar wb-2"></span>
                <span class="wave-bar wb-3"></span>
              </span>
              <span v-else class="stepper-dot">3</span>
            </div>
            <div class="stepper-text">
              <span class="stepper-title">专业论证推演</span>
              <span class="stepper-desc">工程技术方案与规范表格</span>
            </div>
          </div>
        </div>

        <div class="thinking-message-bar">
          <div class="sound-wave-indicator">
            <span class="sw-bar b1"></span>
            <span class="sw-bar b2"></span>
            <span class="sw-bar b3"></span>
            <span class="sw-bar b4"></span>
            <span class="sw-bar b5"></span>
          </div>
          <span class="thinking-msg-text">
            {{ progress?.message || "思维推演中 (纯中文)..." }}
          </span>
        </div>

        <div v-if="progress?.thoughtText" class="thought-stream-card">
          <div class="thought-stream-header" @click="showThoughtDetails = !showThoughtDetails">
            <div class="thought-stream-title">
              <span class="thought-icon">💡</span>
              <span
                >深度技术推演与工程构思过程 (纯中文) ({{ progress.thoughtText.length }} 字符)</span
              >
            </div>
            <button class="thought-toggle-btn">
              {{ showThoughtDetails ? "收起 ▲" : "展开 ▼" }}
            </button>
          </div>
          <div v-show="showThoughtDetails" ref="thoughtContentRef" class="thought-stream-body">
            <pre>{{ progress.thoughtText }}</pre>
          </div>
        </div>

        <div v-else class="thought-placeholder-card">
          <div class="placeholder-icon">✨</div>
          <div class="placeholder-desc">
            已提取并锁定本章全层级大纲骨架。大模型正结合工程底稿、行业规程与权威政务联网资料进行纯中文深度推演与指标校核计算，正文到达后将自动进入实时排版打字机输出...
          </div>
        </div>

        <div class="thinking-notice-footer">
          <span class="notice-icon">💡</span>
          <span class="notice-text">
            项目研究报告专业性强、篇幅宏大，大模型深度组织论述需数十秒构思时间，请稍候。
          </span>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.thinking-state-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 36px 24px;
  min-height: 480px;
  background: radial-gradient(circle at 50% 30%, #f8fafc 0%, #f1f5f9 100%);
  overflow-y: auto;
}
.thinking-card-inner {
  width: 100%;
  max-width: 680px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.02);
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.thinking-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.thinking-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
  font-size: 13px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 20px;
}
.radar-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2563eb;
  box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.7);
  animation: radarPulse 1.8s infinite;
}
@keyframes radarPulse {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 8px rgba(37, 99, 235, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(37, 99, 235, 0);
  }
}
.thinking-elapsed-timer {
  font-size: 12.5px;
  color: #475569;
  font-weight: 500;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 4px 10px;
  border-radius: 6px;
}
.thinking-elapsed-timer strong {
  color: #d97706;
  font-size: 14px;
  font-weight: 700;
}
.pipeline-stepper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  gap: 8px;
}
.stepper-node {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.stepper-badge {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  background: #e2e8f0;
  color: #64748b;
  transition: all 0.2s ease;
}
.stepper-node.completed .stepper-badge {
  background: #dcfce7;
  color: #16a34a;
}
.stepper-node.active .stepper-badge {
  background: #dbeafe;
  color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}
.stepper-check {
  font-size: 13px;
  font-weight: 800;
}
.stepper-dot {
  font-size: 11px;
}
.stepper-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #2563eb;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.stepper-wave {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 12px;
}
.wave-bar {
  width: 2px;
  height: 100%;
  background: #2563eb;
  border-radius: 1px;
  animation: waveBar 0.8s ease-in-out infinite alternate;
}
.wb-1 {
  animation-delay: 0s;
}
.wb-2 {
  animation-delay: 0.2s;
}
.wb-3 {
  animation-delay: 0.4s;
}
@keyframes waveBar {
  0% {
    height: 3px;
  }
  100% {
    height: 12px;
  }
}
.stepper-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 1px;
}
.stepper-title {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.stepper-node.active .stepper-title {
  color: #1d4ed8;
}
.stepper-node.completed .stepper-title {
  color: #15803d;
}
.stepper-desc {
  font-size: 10.5px;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.stepper-line {
  flex: 0 0 20px;
  height: 2px;
  background: #e2e8f0;
  border-radius: 1px;
}
.stepper-line.completed {
  background: #86efac;
}
.thinking-message-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fffbeb;
  border: 1px solid #fef3c7;
  padding: 10px 14px;
  border-radius: 8px;
}
.sound-wave-indicator {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 16px;
  flex-shrink: 0;
}
.sw-bar {
  width: 3px;
  background: #d97706;
  border-radius: 1px;
  animation: soundWave 1s ease-in-out infinite alternate;
}
.b1 {
  height: 6px;
  animation-delay: 0s;
}
.b2 {
  height: 14px;
  animation-delay: 0.2s;
}
.b3 {
  height: 10px;
  animation-delay: 0.4s;
}
.b4 {
  height: 16px;
  animation-delay: 0.1s;
}
.b5 {
  height: 8px;
  animation-delay: 0.3s;
}
@keyframes soundWave {
  0% {
    transform: scaleY(0.4);
  }
  100% {
    transform: scaleY(1.2);
  }
}
.thinking-msg-text {
  font-size: 12.5px;
  color: #92400e;
  font-weight: 500;
  line-height: 1.4;
}
.thought-stream-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  background: #fafafa;
}
.thought-stream-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f1f5f9;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}
.thought-stream-header:hover {
  background: #e2e8f0;
}
.thought-stream-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}
.thought-icon {
  font-size: 13px;
}
.thought-toggle-btn {
  background: none;
  border: none;
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
  cursor: pointer;
}
.thought-stream-body {
  padding: 10px 14px;
  max-height: 180px;
  overflow-y: auto;
  background: #ffffff;
  border-top: 1px solid #e2e8f0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11.5px;
  line-height: 1.6;
  color: #475569;
}
.thought-stream-body pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.thought-placeholder-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
}
.placeholder-icon {
  font-size: 16px;
  flex-shrink: 0;
}
.placeholder-desc {
  font-size: 11.5px;
  color: #64748b;
  line-height: 1.5;
}
.thinking-notice-footer {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.5;
  border-top: 1px solid #f1f5f9;
  padding-top: 10px;
}
.notice-icon {
  flex-shrink: 0;
}
.notice-text {
  flex: 1;
}
</style>
