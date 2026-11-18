<script setup lang="ts">
import { computed } from "vue";
import {
  getReferencesSummary,
  type ReferenceItem,
  type ReferencesSummary,
} from "../../lib/markdown";

const props = withDefaults(
  defineProps<{
    open: boolean;
    filterType: "all" | "material" | "standard" | "web";
    chapterSeq?: number;
    chapterTitle?: string;
    references: ReferenceItem[];
    fixedOverlay?: boolean;
  }>(),
  {
    fixedOverlay: false,
  },
);

const emit = defineEmits<{
  (e: "close"): void;
  (e: "update:filterType", val: "all" | "material" | "standard" | "web"): void;
  (e: "locate", title: string): void;
  (e: "open-url", url?: string): void;
}>();

const refSummary = computed<ReferencesSummary>(() => {
  return getReferencesSummary(props.references);
});

const filteredReferences = computed(() => {
  if (props.filterType === "all") return props.references;
  return props.references.filter((r) => r.type === props.filterType);
});
</script>

<template>
  <transition name="drawer-fade">
    <div
      v-if="open"
      class="ref-drawer-overlay"
      :class="{ 'is-fixed': fixedOverlay }"
      @click="emit('close')"
    >
      <div class="ref-drawer-panel" @click.stop>
        <div class="drawer-header">
          <div class="drawer-title-box">
            <h4>📚 本章参考资料来源台账</h4>
            <span class="drawer-sub">第 {{ chapterSeq }} 章：{{ chapterTitle }}</span>
          </div>
          <button class="drawer-close-btn" @click="emit('close')">✕</button>
        </div>

        <div class="drawer-summary-grid">
          <div class="summary-stat-card type-material">
            <div class="stat-card-header">
              <span class="stat-icon">📄</span>
              <span class="stat-label">项目底稿</span>
            </div>
            <div class="stat-card-values">
              <span class="stat-count"><strong>{{ refSummary.material.count }}</strong> 份</span>
              <span class="stat-citations">引用 <strong>{{ refSummary.material.citations }}</strong> 处</span>
            </div>
          </div>
          <div class="summary-stat-card type-standard">
            <div class="stat-card-header">
              <span class="stat-icon">⚖️</span>
              <span class="stat-label">标准规程</span>
            </div>
            <div class="stat-card-values">
              <span class="stat-count"><strong>{{ refSummary.standard.count }}</strong> 项</span>
              <span class="stat-citations">引用 <strong>{{ refSummary.standard.citations }}</strong> 处</span>
            </div>
          </div>
          <div class="summary-stat-card type-web">
            <div class="stat-card-header">
              <span class="stat-icon">🌐</span>
              <span class="stat-label">权威联网</span>
            </div>
            <div class="stat-card-values">
              <span class="stat-count"><strong>{{ refSummary.web.count }}</strong> 条</span>
              <span class="stat-citations">引用 <strong>{{ refSummary.web.citations }}</strong> 处</span>
            </div>
          </div>
        </div>

        <div class="drawer-subtabs-nav">
          <button
            class="subtab-btn"
            :class="{ active: filterType === 'all' }"
            @click="emit('update:filterType', 'all')"
          >
            全部 ({{ references.length }})
          </button>
          <button
            class="subtab-btn"
            :class="{ active: filterType === 'material' }"
            @click="emit('update:filterType', 'material')"
          >
            📄 项目底稿 ({{ refSummary.material.count }})
          </button>
          <button
            class="subtab-btn"
            :class="{ active: filterType === 'standard' }"
            @click="emit('update:filterType', 'standard')"
          >
            ⚖️ 标准规程 ({{ refSummary.standard.count }})
          </button>
          <button
            class="subtab-btn"
            :class="{ active: filterType === 'web' }"
            @click="emit('update:filterType', 'web')"
          >
            🌐 权威联网 ({{ refSummary.web.count }})
          </button>
        </div>

        <div class="drawer-body">
          <div v-if="filteredReferences.length > 0" class="ref-items-list">
            <div
              v-for="(refItem, rIdx) in filteredReferences"
              :key="rIdx"
              class="ref-card-item"
              :data-ref-title="refItem.title"
              :data-ref-type="refItem.type"
            >
              <div class="ref-card-top">
                <span class="ref-type-tag" :class="`type-${refItem.type}`">
                  {{ refItem.typeLabel }}
                </span>
                <div class="ref-card-top-right">
                  <span class="ref-count-tag">引用 {{ refItem.count }} 处</span>
                  <button
                    class="btn-locate-ref"
                    title="在正文画布中定位并呼吸高亮首个引用位置"
                    @click="emit('locate', refItem.title)"
                  >
                    🎯 定位正文出处
                  </button>
                </div>
              </div>
              <div class="ref-card-title">
                <a
                  v-if="refItem.type === 'web' && refItem.url"
                  href="#"
                  class="ref-title-link"
                  title="点击直接在浏览器中打开权威原网页"
                  @click.prevent="emit('open-url', refItem.url)"
                >
                  {{ refItem.title }} <span class="ext-icon">↗</span>
                </a>
                <span v-else>{{ refItem.title }}</span>
              </div>
              <div v-if="refItem.raw" class="ref-card-raw"><code>{{ refItem.raw }}</code></div>
            </div>
          </div>

          <div v-else class="ref-empty-state">
            <span class="empty-icon">📂</span>
            <p class="empty-title">
              {{
                filterType === "all"
                  ? "本章正文中暂未引用任何参考资料"
                  : filterType === "material"
                  ? "本章暂无项目底稿资料引用"
                  : filterType === "standard"
                  ? "本章暂无行业标准规程引用"
                  : "本章暂无权威联网检索引用"
              }}
            </p>
            <p class="empty-desc">
              您可在正文中嵌入 <code>【源:文件名.docx】</code>、<code>【标:规范名】</code> 或
              <code>【网:信息源】</code> 标记数据出处，系统将在此自动汇总与联动。
            </p>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
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
.ref-drawer-overlay.is-fixed {
  position: fixed;
  z-index: 1000;
}
.ref-drawer-panel {
  width: 420px;
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
  background: #f8fafc;
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
  font-size: 11.5px;
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
  background: #e2e8f0;
  color: #0f172a;
}
.drawer-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}
.summary-stat-card {
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  border: 1px solid transparent;
}
.summary-stat-card.type-material {
  background: #eff6ff;
  border-color: #bfdbfe;
}
.summary-stat-card.type-standard {
  background: #fefce8;
  border-color: #fef08a;
}
.summary-stat-card.type-web {
  background: #ecfdf5;
  border-color: #a7f3d0;
}
.stat-card-header {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 700;
}
.summary-stat-card.type-material .stat-label {
  color: #1d4ed8;
}
.summary-stat-card.type-standard .stat-label {
  color: #a16207;
}
.summary-stat-card.type-web .stat-label {
  color: #047857;
}
.stat-card-values {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.stat-count {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
}
.stat-citations {
  font-size: 10px;
  color: #64748b;
}
.drawer-subtabs-nav {
  display: flex;
  gap: 4px;
  padding: 8px 14px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  overflow-x: auto;
}
.subtab-btn {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 3px 9px;
  font-size: 11px;
  color: #475569;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}
.subtab-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}
.subtab-btn.active {
  background: #2563eb;
  border-color: #1d4ed8;
  color: #fff;
  font-weight: 600;
}
.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 14px;
}
.ref-items-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ref-card-item {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: all 0.2s ease;
}
.ref-card-pulse {
  animation: refCardPulse 2s cubic-bezier(0.2, 0.8, 0.2, 1) !important;
}
@keyframes refCardPulse {
  0% {
    background-color: #fef08a !important;
    box-shadow: 0 0 0 4px rgba(234, 179, 8, 0.5) !important;
    border-color: #eab308 !important;
  }
  50% {
    background-color: #fef9c3 !important;
    box-shadow: 0 0 0 2px rgba(234, 179, 8, 0.25) !important;
    border-color: #eab308 !important;
  }
  100% {
    background-color: #ffffff;
    box-shadow: none;
  }
}
.ref-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ref-card-top-right {
  display: flex;
  align-items: center;
  gap: 6px;
}
.btn-locate-ref {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  color: #0284c7;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-locate-ref:hover {
  background: #0284c7;
  color: #fff;
  border-color: #0284c7;
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
  background: #d1fae5;
  color: #065f46;
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
</style>
