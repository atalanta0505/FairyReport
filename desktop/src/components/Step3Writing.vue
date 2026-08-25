<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { extractSubHeadings, htmlToMarkdown, markdownToHtml, type SubHeading } from "../lib/markdown";
import { useEngineStore } from "../stores/engine";
import { useProjectStore } from "../stores/project";
import { useSettingsStore } from "../stores/settings";

const engine = useEngineStore();
const settings = useSettingsStore();
const projectStore = useProjectStore();

const actionMessage = ref<{ type: "success" | "error"; text: string } | null>(null);
const showHintSection = ref<boolean>(false);
const chapterHints = ref<Record<number, string>>({});
const viewMode = ref<"rich" | "source">("rich");

const editorCanvasRef = ref<HTMLDivElement | null>(null);
const editorTextareaRef = ref<HTMLTextAreaElement | null>(null);

let saveDebounceTimer: ReturnType<typeof setTimeout> | null = null;

function showMsg(text: string, type: "success" | "error" = "success") {
  actionMessage.value = { type, text };
  setTimeout(() => {
    if (actionMessage.value?.text === text) {
      actionMessage.value = null;
    }
  }, 4000);
}

async function ensureStep3State() {
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
    } catch {
      // ignore
    }
  }
}

function syncEditorContent() {
  if (editorCanvasRef.value && viewMode.value === "rich") {
    editorCanvasRef.value.innerHTML = markdownToHtml(
      currentChapterText.value,
      currentChapter.value?.seq,
    );
  }
}

onMounted(async () => {
  await ensureStep3State();
  nextTick(() => {
    syncEditorContent();
  });
});

watch(
  () => projectStore.currentStep,
  (step) => {
    if (step === 3) {
      ensureStep3State();
      nextTick(() => {
        syncEditorContent();
      });
    }
  },
);

watch(
  () => projectStore.currentProject?.name,
  (projectName) => {
    if (projectName && projectStore.currentStep === 3) {
      projectStore
        .loadChapters(engine.baseUrl, projectName)
        .then(() => {
          syncEditorContent();
        })
        .catch(() => {});
    }
  },
);

// 统计
const totalChapters = computed(() => projectStore.outlineChapters.length);

const completedCount = computed(() => {
  return projectStore.outlineChapters.filter((ch) => {
    const text = projectStore.chapters[ch.seq];
    return text && text.trim().length > 0;
  }).length;
});

const totalWordCount = computed(() => {
  let count = 0;
  for (const text of Object.values(projectStore.chapters)) {
    if (text) {
      count += text.length;
    }
  }
  return count;
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

const currentChapterWords = computed(() => {
  return currentChapterText.value.length;
});

const currentChapterStatus = computed(() => {
  return (
    projectStore.chapterStatuses[projectStore.selectedChapterSeq] ||
    (currentChapterText.value.trim().length > 0 ? "completed" : "idle")
  );
});

const isCurrentChapterWriting = computed(() => {
  return (
    projectStore.currentWritingSeq === projectStore.selectedChapterSeq ||
    currentChapterStatus.value === "writing"
  );
});

// 提取当前所有章节的子标题树
const chapterSubHeadingsMap = computed<Record<number, SubHeading[]>>(() => {
  const map: Record<number, SubHeading[]> = {};
  for (const ch of projectStore.outlineChapters) {
    const text = projectStore.chapters[ch.seq];
    if (text && text.trim().length > 0) {
      map[ch.seq] = extractSubHeadings(text, ch.seq);
    } else {
      map[ch.seq] = [];
    }
  }
  return map;
});

// 监听章节切换，同步排版内容
watch(
  () => projectStore.selectedChapterSeq,
  () => {
    nextTick(() => {
      syncEditorContent();
    });
  },
);

// 监听视图切换
watch(viewMode, (mode) => {
  if (mode === "rich") {
    nextTick(() => {
      syncEditorContent();
    });
  }
});

// 自动平滑滚动与流式排版更新
watch(
  () => currentChapterText.value,
  (newVal) => {
    if (isCurrentChapterWriting.value) {
      if (viewMode.value === "rich" && editorCanvasRef.value) {
        editorCanvasRef.value.innerHTML = markdownToHtml(newVal, currentChapter.value?.seq);
        nextTick(() => {
          if (editorCanvasRef.value) {
            editorCanvasRef.value.scrollTop = editorCanvasRef.value.scrollHeight;
          }
        });
      }
      if (editorTextareaRef.value) {
        nextTick(() => {
          if (editorTextareaRef.value) {
            editorTextareaRef.value.scrollTop = editorTextareaRef.value.scrollHeight;
          }
        });
      }
    }
  },
);

function selectChapter(seq: number) {
  projectStore.selectChapter(seq);
}

function switchViewMode(mode: "rich" | "source") {
  if (viewMode.value === mode) return;
  viewMode.value = mode;
}

// 富文本就地输入处理：提取 HTML 转换为 Markdown 防抖落盘
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

// 点击左侧子标题平滑定位跳转与高亮呼吸
async function handleSubHeadingClick(seq: number, headingId: string, event: MouseEvent) {
  event.stopPropagation();

  // 若当前未选中该章，先切换章节
  if (projectStore.selectedChapterSeq !== seq) {
    selectChapter(seq);
    await nextTick();
    await new Promise((r) => setTimeout(r, 60));
  }

  // 确保在排版视图下进行精准定位
  if (viewMode.value !== "rich") {
    viewMode.value = "rich";
    await nextTick();
    syncEditorContent();
    await new Promise((r) => setTimeout(r, 60));
  }

  const targetEl = document.getElementById(headingId);
  if (targetEl) {
    targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
    targetEl.classList.remove("heading-anchor-pulse");
    // 强制触发 reflow 使动画可重复播放
    void targetEl.offsetWidth;
    targetEl.classList.add("heading-anchor-pulse");
    setTimeout(() => {
      targetEl.classList.remove("heading-anchor-pulse");
    }, 1500);
  }
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

async function handleWriteSingleChapter(seq?: number) {
  const targetSeq = seq !== undefined ? seq : projectStore.selectedChapterSeq;
  if (!engine.baseUrl) {
    showMsg("本地引擎未就绪，请等待引擎启动", "error");
    return;
  }

  let llmConfig;
  try {
    llmConfig = getLLMConfig();
  } catch (e) {
    showMsg((e as Error).message, "error");
    return;
  }

  try {
    const hint = chapterHints.value[targetSeq] || "";
    await projectStore.writeSingleChapterStream(engine.baseUrl, targetSeq, llmConfig, hint);
    syncEditorContent();
    showMsg(`第 ${targetSeq} 章流式生成完成！`);
  } catch (err) {
    showMsg(`生成章节失败: ${(err as Error).message}`, "error");
  }
}

async function handleWriteAllChapters() {
  if (!engine.baseUrl) {
    showMsg("本地引擎未就绪，请等待引擎启动", "error");
    return;
  }

  let llmConfig;
  try {
    llmConfig = getLLMConfig();
  } catch (e) {
    showMsg((e as Error).message, "error");
    return;
  }

  try {
    showMsg("已启动全书章节顺序流式写作任务...");
    await projectStore.writeAllChapters(engine.baseUrl, llmConfig);
    syncEditorContent();
    showMsg("全书所有章节流式写作完成！");
  } catch (err) {
    showMsg(`批量写作中断: ${(err as Error).message}`, "error");
  }
}

function handleStopWriting() {
  projectStore.stopWriting();
  syncEditorContent();
  showMsg("已中止当前写作任务", "error");
}

async function handleClearChapter(seq: number, event?: MouseEvent) {
  if (event) {
    event.stopPropagation();
  }
  await projectStore.deleteChapter(engine.baseUrl, seq);
  syncEditorContent();
  showMsg(`已清空第 ${seq} 章内容`);
}

function onChapterTextInput(e: Event) {
  const target = e.target as HTMLTextAreaElement;
  currentChapterText.value = target.value;
}

function prevStep() {
  projectStore.setStep(2);
}

function nextStep() {
  if (completedCount.value === 0 && totalWordCount.value === 0) {
    showMsg("请至少生成或撰写一个章节后再进入下一步审阅修改", "error");
    return;
  }
  projectStore.setStep(4);
}
</script>

<template>
  <div class="step3-container">
    <!-- 全局操作消息条 -->
    <transition name="fade">
      <div v-if="actionMessage" :class="['alert-banner', actionMessage.type]">
        {{ actionMessage.text }}
      </div>
    </transition>

    <!-- 主流写作双栏布局 -->
    <div class="writing-layout">
      <!-- 左侧：章节目录与控制面板 -->
      <aside class="sidebar-panel card">
        <div class="card-header sidebar-header">
          <div class="header-titles">
            <h3>章节目录与导航</h3>
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
              <span class="stat-label">已完成</span>
              <span class="stat-val stat-success">{{ completedCount }} / {{ totalChapters }}</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-label">总字数</span>
              <span class="stat-val">{{ totalWordCount.toLocaleString() }} 字</span>
            </div>
          </div>
        </div>

        <!-- 全局写作主操作区 -->
        <div class="global-actions">
          <button
            v-if="projectStore.batchWriting"
            class="btn btn-danger btn-block"
            @click="handleStopWriting"
          >
            ⏹ 停止全书写作
          </button>
          <button
            v-else
            class="btn btn-primary btn-block"
            :disabled="totalChapters === 0 || isCurrentChapterWriting"
            @click="handleWriteAllChapters"
          >
            🚀 一键开始全书写作
          </button>
        </div>

        <!-- 章节列表与多级标题导航 -->
        <div class="chapter-list">
          <div
            v-for="ch in projectStore.outlineChapters"
            :key="ch.seq"
            class="chapter-item-container"
          >
            <div
              class="chapter-card"
              :class="{
                active: projectStore.selectedChapterSeq === ch.seq,
                writing: projectStore.currentWritingSeq === ch.seq,
                completed: projectStore.chapters[ch.seq] && projectStore.chapters[ch.seq].trim().length > 0,
              }"
              @click="selectChapter(ch.seq)"
            >
              <div class="chapter-card-main">
                <div class="chapter-card-top">
                  <span class="ch-seq-circle">{{ ch.seq }}</span>
                  <span class="ch-title" :title="ch.title">{{ ch.title }}</span>
                </div>
                <div class="chapter-card-meta">
                  <span class="ch-words">{{ (projectStore.chapters[ch.seq] || "").length }} 字</span>
                  <span
                    class="status-pill"
                    :class="
                      projectStore.currentWritingSeq === ch.seq
                        ? 'writing'
                        : (projectStore.chapters[ch.seq] || '').trim().length > 0
                        ? 'completed'
                        : projectStore.chapterStatuses[ch.seq] === 'error'
                        ? 'error'
                        : 'idle'
                    "
                  >
                    <span v-if="projectStore.currentWritingSeq === ch.seq" class="spinner-inline"></span>
                    {{
                      projectStore.currentWritingSeq === ch.seq
                        ? "正在撰写中…"
                        : (projectStore.chapters[ch.seq] || "").trim().length > 0
                        ? "已完成 ✓"
                        : projectStore.chapterStatuses[ch.seq] === 'error'
                        ? "生成异常"
                        : "未生成"
                    }}
                  </span>
                </div>
              </div>

              <!-- 卡片悬停快速操作 -->
              <div class="chapter-card-actions">
                <button
                  class="icon-btn"
                  :title="projectStore.chapters[ch.seq] ? '重新生成该章' : '生成该章'"
                  :disabled="projectStore.batchWriting || projectStore.currentWritingSeq === ch.seq"
                  @click.stop="handleWriteSingleChapter(ch.seq)"
                >
                  ✍️
                </button>
                <button
                  v-if="projectStore.chapters[ch.seq]"
                  class="icon-btn icon-btn-danger"
                  title="清空该章"
                  :disabled="projectStore.batchWriting || projectStore.currentWritingSeq === ch.seq"
                  @click="handleClearChapter(ch.seq, $event)"
                >
                  🗑️
                </button>
              </div>
            </div>

            <!-- 该章节已存在内容时的多级子标题目录列表 -->
            <div
              v-if="chapterSubHeadingsMap[ch.seq] && chapterSubHeadingsMap[ch.seq].length > 0"
              class="subheadings-tree"
            >
              <div
                v-for="sub in chapterSubHeadingsMap[ch.seq]"
                :key="sub.id"
                class="subheading-item"
                :class="`level-${sub.level}`"
                :title="sub.title"
                @click="handleSubHeadingClick(ch.seq, sub.id, $event)"
              >
                <span class="subheading-bullet">{{ sub.level === 1 ? '📌' : sub.level === 2 ? '🔹' : '▪' }}</span>
                <span class="subheading-text">{{ sub.title }}</span>
              </div>
            </div>
          </div>

          <div v-if="totalChapters === 0" class="empty-list-tip">
            暂无章节目录，请返回步骤 2「模板与大纲」生成或编写大纲。
          </div>
        </div>
      </aside>

      <!-- 右侧：单栏排版就地可编辑主画布 -->
      <main class="editor-panel card">
        <div class="card-header editor-header">
          <div class="editor-title-area">
            <div class="title-row">
              <span class="seq-tag" v-if="currentChapter">第 {{ currentChapter.seq }} 章</span>
              <h3 class="active-ch-title">{{ currentChapter?.title || "未选择章节" }}</h3>
            </div>
            <div class="editor-meta-row">
              <span class="meta-item">
                当前字数：<strong>{{ currentChapterWords.toLocaleString() }}</strong> 字
              </span>
              <span class="meta-item-divider">·</span>
              <span class="meta-item status-text" :class="currentChapterStatus">
                {{
                  isCurrentChapterWriting
                    ? "⚡ 实时流式生成中..."
                    : currentChapterWords > 0
                    ? "✓ 已落盘保存，可直接在下方排版正文上点击就地编辑润色"
                    : "等待生成"
                }}
              </span>
            </div>
          </div>

          <!-- 右上角单章写作操作与视图切换 -->
          <div class="editor-actions">
            <button
              class="btn btn-outline"
              @click="showHintSection = !showHintSection"
              :class="{ active: showHintSection }"
            >
              💡 {{ showHintSection ? "收起提示" : "写作提示 (Hint)" }}
            </button>

            <button
              v-if="isCurrentChapterWriting"
              class="btn btn-danger"
              @click="handleStopWriting"
            >
              ⏹ 停止生成
            </button>
            <button
              v-else
              class="btn btn-primary"
              :disabled="!currentChapter || projectStore.batchWriting"
              @click="handleWriteSingleChapter()"
            >
              {{ currentChapterWords > 0 ? "🔄 重新流式生成本章" : "✍️ 单章流式写作" }}
            </button>
          </div>
        </div>

        <div class="card-body editor-body">
          <!-- 写作提示折叠框 -->
          <transition name="slide">
            <div v-if="showHintSection" class="hint-container">
              <div class="hint-title">
                <span>🎯 本章重点写作提示（Writing Hint）</span>
                <span class="hint-sub">可输入本章需要特别强调的工程参数、指标或论述重点，生成时将自动融合注入 Prompt。</span>
              </div>
              <textarea
                class="hint-textarea"
                placeholder="例如：重点补充 2025 年洪水调度安全监测数据，并结合规程第 4.2 条进行分析论述..."
                v-model="chapterHints[projectStore.selectedChapterSeq]"
              ></textarea>
            </div>
          </transition>

          <!-- 单栏排版就地可编辑画布区 -->
          <div class="writing-canvas">
            <div class="canvas-toolbar">
              <div class="toolbar-left">
                <span class="toolbar-label">
                  {{ viewMode === 'rich' ? '📖 单栏排版就地编辑器' : '📝 Markdown 源码编辑器' }}
                </span>
                <span class="toolbar-tip">
                  {{
                    viewMode === 'rich'
                      ? '支持直接在排版文字上点击输入、改字与润色，流式打字机实时排版，300ms 自动落盘。'
                      : '纯文本 Markdown 源码编辑模式，可直接查阅与编辑原生 Markdown 标记。'
                  }}
                </span>
              </div>
              <div class="toolbar-right">
                <div class="view-mode-group">
                  <button
                    class="mode-btn"
                    :class="{ active: viewMode === 'rich' }"
                    @click="switchViewMode('rich')"
                    title="切换至单栏排版就地编辑器"
                  >
                    👁️ 排版视图
                  </button>
                  <button
                    class="mode-btn"
                    :class="{ active: viewMode === 'source' }"
                    @click="switchViewMode('source')"
                    title="切换至 Markdown 源码视图"
                  >
                    📝 源码视图
                  </button>
                </div>
              </div>
            </div>

            <!-- 排版模式：就地 contenteditable 编辑画布 -->
            <div
              v-show="viewMode === 'rich'"
              ref="editorCanvasRef"
              contenteditable="true"
              class="rich-rendered-editor"
              @input="onEditorInput"
              data-placeholder="点击上方「✍️ 单章流式写作」或「🚀 一键开始全书写作」，系统将结合工程底稿与标准规程自动打字机式流式生成章节排版正文；生成后可直接在文字上就地点击输入编辑..."
            ></div>

            <!-- 源码模式：纯文本 textarea -->
            <textarea
              v-show="viewMode === 'source'"
              ref="editorTextareaRef"
              class="writing-textarea"
              placeholder="点击上方「✍️ 单章流式写作」或「🚀 一键开始全书写作」，系统将结合工程底稿与标准规程自动流式生成 Markdown 章节正文..."
              :value="currentChapterText"
              @input="onChapterTextInput"
            ></textarea>
          </div>
        </div>
      </main>
    </div>

    <!-- 底部流转按钮 -->
    <div class="bottom-nav">
      <button class="btn btn-secondary btn-lg" @click="prevStep">
        &larr; 上一步：模板与大纲
      </button>
      <button
        class="btn btn-primary btn-lg"
        :disabled="completedCount === 0 && totalWordCount === 0"
        @click="nextStep"
      >
        下一步：审阅修改 &rarr;
      </button>
    </div>
  </div>
</template>

<style scoped>
.step3-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 20px 24px 48px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.alert-banner {
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.4;
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

.writing-layout {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 18px;
  min-height: 680px;
}

.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-header {
  padding: 14px 18px;
  border-bottom: 1px solid #f1f5f9;
  background: #fafafa;
}

/* 左侧栏 */
.sidebar-panel {
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 160px);
}

.sidebar-header {
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
  font-weight: 600;
  color: #1e293b;
}

.proj-badge {
  background: #e0e7ff;
  color: #4338ca;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stats-overview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 6px 12px;
}
.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.stat-label {
  font-size: 11px;
  color: #64748b;
}
.stat-val {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}
.stat-success {
  color: #16a34a;
}
.stat-divider {
  width: 1px;
  height: 20px;
  background: #e2e8f0;
}

.global-actions {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  background: #fff;
}

.chapter-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chapter-item-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chapter-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s ease;
}
.chapter-card:hover {
  border-color: #93c5fd;
  background: #f8fafc;
}
.chapter-card.active {
  border-color: #2563eb;
  background: #eff6ff;
  box-shadow: 0 0 0 1px #2563eb;
}
.chapter-card.writing {
  border-color: #f59e0b;
  background: #fffbeb;
}

.chapter-card-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chapter-card-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ch-seq-circle {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #e2e8f0;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}
.chapter-card.active .ch-seq-circle {
  background: #2563eb;
  color: #fff;
}
.chapter-card.completed .ch-seq-circle {
  background: #dcfce7;
  color: #15803d;
}

.ch-title {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chapter-card.active .ch-title {
  color: #1d4ed8;
  font-weight: 600;
}

.chapter-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 28px;
}
.ch-words {
  font-size: 11px;
  color: #64748b;
}

.status-pill {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}
.status-pill.idle {
  background: #f1f5f9;
  color: #64748b;
}
.status-pill.writing {
  background: #fef3c7;
  color: #b45309;
}
.status-pill.completed {
  background: #dcfce7;
  color: #15803d;
}
.status-pill.error {
  background: #fee2e2;
  color: #b91c1c;
}

.chapter-card-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
}

.icon-btn {
  background: none;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  padding: 3px 6px;
  font-size: 12px;
  transition: all 0.15s;
}
.icon-btn:hover:not(:disabled) {
  background: #e2e8f0;
  border-color: #cbd5e1;
}
.icon-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.icon-btn-danger:hover:not(:disabled) {
  background: #fee2e2;
  border-color: #fca5a5;
}

/* 左侧多级子标题目录树 */
.subheadings-tree {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 6px 6px 14px;
  margin-left: 12px;
  border-left: 2px solid #e2e8f0;
}

.subheading-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}
.subheading-item:hover {
  background: #eff6ff;
  color: #2563eb;
}
.subheading-item.level-1 {
  font-weight: 600;
  color: #1e293b;
}
.subheading-item.level-2 {
  padding-left: 10px;
}
.subheading-item.level-3 {
  padding-left: 18px;
  font-size: 11.5px;
  color: #64748b;
}
.subheading-item.level-4 {
  padding-left: 26px;
  font-size: 11px;
  color: #94a3b8;
}

.subheading-bullet {
  font-size: 10px;
  flex-shrink: 0;
  opacity: 0.7;
}

.subheading-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-list-tip {
  padding: 30px 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.5;
}

/* 右侧编辑器面板 */
.editor-panel {
  display: flex;
  flex-direction: column;
  min-height: 640px;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.editor-title-area {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.seq-tag {
  background: #eff6ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}
.active-ch-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
}
.meta-item-divider {
  color: #cbd5e1;
}
.status-text.writing {
  color: #d97706;
  font-weight: 500;
}
.status-text.completed {
  color: #16a34a;
}

.editor-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.editor-body {
  flex: 1;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* Hint 区域 */
.hint-container {
  background: #fffbeb;
  border: 1px solid #fef3c7;
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.hint-title {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  font-weight: 600;
  color: #92400e;
}
.hint-sub {
  font-weight: normal;
  font-size: 11px;
  color: #b45309;
}
.hint-textarea {
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.5;
  color: #451a03;
  background: #fff;
  resize: vertical;
  min-height: 56px;
  outline: none;
}
.hint-textarea:focus {
  border-color: #f59e0b;
}

/* 单栏排版就地可编辑主画布 */
.writing-canvas {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.02);
}

.canvas-toolbar {
  padding: 8px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.toolbar-label {
  font-size: 12.5px;
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
}
.toolbar-tip {
  font-size: 11px;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toolbar-right {
  flex-shrink: 0;
}
.view-mode-group {
  display: inline-flex;
  background: #e2e8f0;
  padding: 2px;
  border-radius: 6px;
}
.mode-btn {
  background: transparent;
  border: none;
  padding: 4px 10px;
  font-size: 11.5px;
  font-weight: 500;
  color: #64748b;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.mode-btn.active {
  background: #fff;
  color: #1d4ed8;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}

/* 排版模式就地富文本编辑画布样式 */
.rich-rendered-editor {
  flex: 1;
  padding: 24px 32px;
  min-height: 480px;
  max-height: calc(100vh - 250px);
  overflow-y: auto;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "WenQuanYi Micro Hei", sans-serif;
  font-size: 15px;
  line-height: 1.85;
  color: #1e293b;
  background: #ffffff;
  outline: none;
  word-break: break-word;
}
.rich-rendered-editor:focus {
  background: #ffffff;
}
.rich-rendered-editor:empty:before {
  content: attr(data-placeholder);
  color: #94a3b8;
  font-size: 14px;
  line-height: 1.8;
  font-style: italic;
  display: block;
}

/* 深度排版元素样式 */
:deep(.rich-rendered-editor h1) {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  margin: 24px 0 14px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid #e2e8f0;
  scroll-margin-top: 16px;
}
:deep(.rich-rendered-editor h2) {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 20px 0 10px 0;
  padding-bottom: 6px;
  border-bottom: 1px solid #f1f5f9;
  scroll-margin-top: 16px;
}
:deep(.rich-rendered-editor h3) {
  font-size: 16px;
  font-weight: 600;
  color: #334155;
  margin: 16px 0 8px 0;
  scroll-margin-top: 16px;
}
:deep(.rich-rendered-editor h4) {
  font-size: 15px;
  font-weight: 600;
  color: #475569;
  margin: 12px 0 6px 0;
  scroll-margin-top: 16px;
}
:deep(.rich-rendered-editor p) {
  margin: 0 0 14px 0;
  color: #334155;
  text-align: justify;
}
:deep(.rich-rendered-editor strong) {
  font-weight: 700;
  color: #0f172a;
}
:deep(.rich-rendered-editor em) {
  font-style: italic;
  color: #475569;
}
:deep(.rich-rendered-editor blockquote) {
  margin: 14px 0;
  padding: 10px 16px;
  background: #f8fafc;
  border-left: 4px solid #3b82f6;
  border-radius: 0 6px 6px 0;
  color: #475569;
  font-size: 14px;
}
:deep(.rich-rendered-editor blockquote p) {
  margin: 0;
}
:deep(.rich-rendered-editor table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 14px;
}
:deep(.rich-rendered-editor th),
:deep(.rich-rendered-editor td) {
  border: 1px solid #cbd5e1;
  padding: 8px 12px;
  text-align: left;
}
:deep(.rich-rendered-editor th) {
  background: #f1f5f9;
  font-weight: 600;
  color: #1e293b;
}
:deep(.rich-rendered-editor tr:nth-child(even)) {
  background: #f8fafc;
}
:deep(.rich-rendered-editor ul),
:deep(.rich-rendered-editor ol) {
  margin: 0 0 14px 0;
  padding-left: 24px;
  color: #334155;
}
:deep(.rich-rendered-editor li) {
  margin-bottom: 6px;
  line-height: 1.7;
}
:deep(.rich-rendered-editor pre) {
  background: #0f172a;
  color: #e2e8f0;
  padding: 12px 16px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 14px 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}
:deep(.rich-rendered-editor code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  background: #f1f5f9;
  color: #0969da;
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 0.9em;
}
:deep(.rich-rendered-editor pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
}
:deep(.rich-rendered-editor hr) {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 20px 0;
}
:deep(.rich-rendered-editor .ref-badge) {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  background: #e0e7ff;
  color: #3730a3;
  font-size: 11px;
  font-weight: 500;
  padding: 1px 7px;
  border-radius: 12px;
  margin: 0 2px;
  vertical-align: baseline;
  user-select: none;
}

/* 锚点定位呼吸高亮动画 */
@keyframes headingPulse {
  0% {
    background-color: rgba(254, 240, 138, 0.95);
    box-shadow: 0 0 0 6px rgba(254, 240, 138, 0.6);
    border-radius: 4px;
  }
  50% {
    background-color: rgba(254, 240, 138, 0.5);
    box-shadow: 0 0 0 3px rgba(254, 240, 138, 0.3);
    border-radius: 4px;
  }
  100% {
    background-color: transparent;
    box-shadow: none;
  }
}
:deep(.heading-anchor-pulse) {
  animation: headingPulse 1.5s ease-out forwards;
}

/* 源码模式 textarea */
.writing-textarea {
  flex: 1;
  border: none;
  padding: 20px 24px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 14px;
  line-height: 1.8;
  color: #0f172a;
  background: #ffffff;
  outline: none;
  resize: none;
  min-height: 480px;
  max-height: calc(100vh - 250px);
}
.writing-textarea:focus {
  background: #ffffff;
}

/* 按钮通用 */
.btn {
  padding: 7px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-block {
  width: 100%;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
}
.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}
.btn-danger {
  background: #dc2626;
  color: #fff;
}
.btn-danger:hover:not(:disabled) {
  background: #b91c1c;
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
  color: #475569;
  border-color: #cbd5e1;
}
.btn-outline:hover:not(:disabled) {
  background: #f8fafc;
  color: #1e293b;
}
.btn-outline.active {
  background: #fef3c7;
  color: #92400e;
  border-color: #fde68a;
}
.btn-lg {
  padding: 10px 24px;
  font-size: 15px;
}

.spinner-inline {
  width: 10px;
  height: 10px;
  border: 2px solid #d97706;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
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

.slide-enter-active,
.slide-leave-active {
  transition: all 0.25s ease;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
