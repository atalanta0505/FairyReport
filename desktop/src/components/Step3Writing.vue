<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import {
  countContentChars,
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

const actionMessage = ref<{ type: "success" | "error"; text: string } | null>(null);
const showHintSection = ref<boolean>(false);
const showRefDrawer = ref<boolean>(false);
const chapterHints = ref<Record<number, string>>({});

const collapsedChapters = ref<Record<number, boolean>>({});
const showThoughtDetails = ref<boolean>(true);
const thoughtContentRef = ref<HTMLDivElement | null>(null);

const editorCanvasRef = ref<HTMLDivElement | null>(null);

let saveDebounceTimer: ReturnType<typeof setTimeout> | null = null;

const outlineHeadings = computed(() => extractOutlineHeadings(projectStore.outlineMd));

function isChapterCollapsed(seq: number): boolean {
  return !!collapsedChapters.value[seq];
}

function toggleChapterCollapse(seq: number, event?: MouseEvent) {
  if (event) {
    event.stopPropagation();
  }
  collapsedChapters.value[seq] = !collapsedChapters.value[seq];
}

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
  if (editorCanvasRef.value) {
    editorCanvasRef.value.innerHTML = markdownToHtml(
      currentChapterText.value,
      currentChapter.value?.seq,
      outlineHeadings.value,
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
      count += countContentChars(text);
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
  return countContentChars(currentChapterText.value);
});

const currentChapterReferences = computed<ReferenceItem[]>(() => {
  return extractReferences(currentChapterText.value);
});

const totalRefCitations = computed(() => {
  return currentChapterReferences.value.reduce((sum, item) => sum + item.count, 0);
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

// 提取当前所有章节的子标题树（过滤掉 H1 级别，因章节行已展示章标题）
const chapterSubHeadingsMap = computed<Record<number, SubHeading[]>>(() => {
  const map: Record<number, SubHeading[]> = {};
  for (const ch of projectStore.outlineChapters) {
    const text = projectStore.chapters[ch.seq];
    if (text && text.trim().length > 0) {
      map[ch.seq] = extractSubHeadings(text, ch.seq, outlineHeadings.value).filter((h) => h.level > 1);
    } else {
      map[ch.seq] = [];
    }
  }
  return map;
});

function getChapterTitle(seq: number): string {
  const found = projectStore.outlineChapters.find((c) => c.seq === seq);
  return found?.title || `第 ${seq} 章`;
}

// 监听章节切换，同步排版内容
watch(
  () => projectStore.selectedChapterSeq,
  () => {
    nextTick(() => {
      syncEditorContent();
    });
  },
);

// 自动平滑滚动与流式排版更新
watch(
  () => currentChapterText.value,
  (newVal) => {
    if (isCurrentChapterWriting.value) {
      if (editorCanvasRef.value) {
        editorCanvasRef.value.innerHTML = markdownToHtml(
          newVal,
          currentChapter.value?.seq,
          outlineHeadings.value,
        );
        nextTick(() => {
          if (editorCanvasRef.value) {
            editorCanvasRef.value.scrollTop = editorCanvasRef.value.scrollHeight;
          }
        });
      }
    }
  },
);

function selectChapter(seq: number) {
  projectStore.selectChapter(seq);
  collapsedChapters.value[seq] = false;
}

watch(
  () => projectStore.currentWritingSeq,
  (seq) => {
    if (seq) {
      collapsedChapters.value[seq] = false;
    }
  },
);

watch(
  () => projectStore.writingProgress?.thoughtText,
  () => {
    if (thoughtContentRef.value) {
      nextTick(() => {
        if (thoughtContentRef.value) {
          thoughtContentRef.value.scrollTop = thoughtContentRef.value.scrollHeight;
        }
      });
    }
  },
);

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
    showMsg("已启动全书推荐顺序断点智能续写任务...");
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

function copyCurrentChapterMarkdown() {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(currentChapterText.value);
    showMsg(`已复制第 ${projectStore.selectedChapterSeq} 章 Markdown 源码至剪贴板！`);
  }
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
      <!-- 左侧：全书目录导航与控制面板 (Flat 平铺一体化目录树) -->
      <aside class="sidebar-panel card">
        <div class="card-header sidebar-header">
          <div class="header-titles">
            <h3>📑 章节目录与导航</h3>
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
              <span class="stat-label">总字数 (正文)</span>
              <span class="stat-val">{{ totalWordCount.toLocaleString() }} 字</span>
            </div>
          </div>

          <!-- 💡 推荐写作顺序：流程胶囊提示 -->
          <div
            v-if="projectStore.writingOrder && projectStore.writingOrder.length > 0"
            class="writing-order-box"
            :title="projectStore.writingOrderReason || '推荐写作顺序'"
          >
            <div class="order-box-header">
              <span class="order-icon">💡</span>
              <span class="order-title">推荐写作顺序</span>
            </div>
            <div class="order-flow-chips">
              <span
                v-for="(seq, idx) in projectStore.writingOrder"
                :key="seq"
                class="order-node-wrap"
              >
                <span
                  class="order-chip"
                  :class="{
                    active: projectStore.selectedChapterSeq === seq,
                    completed: (projectStore.chapters[seq] || '').trim().length > 0,
                    writing: projectStore.currentWritingSeq === seq,
                  }"
                  @click="selectChapter(seq)"
                  :title="`第 ${seq} 章：${getChapterTitle(seq)}`"
                >
                  第 {{ seq }} 章
                </span>
                <span v-if="idx < projectStore.writingOrder.length - 1" class="flow-arrow">➔</span>
              </span>
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

        <!-- Flat 平铺一体化章节目录树 (单一定高全局平滑滚动，对齐 Step 4) -->
        <div class="outline-tree-scrollable">
          <div
            v-for="ch in projectStore.outlineChapters"
            :key="ch.seq"
            class="chapter-tree-node"
            :class="{
              'is-active': projectStore.selectedChapterSeq === ch.seq,
              'is-writing': projectStore.currentWritingSeq === ch.seq,
              'is-completed': (projectStore.chapters[ch.seq] || '').trim().length > 0,
            }"
          >
            <!-- 章节行 -->
            <div
              class="chapter-node-row"
              @click="selectChapter(ch.seq)"
              :title="`第 ${ch.seq} 章：${ch.title}`"
            >
              <div class="row-left">
                <span class="ch-seq-tag">{{ ch.seq }}</span>
                <span class="ch-title-text">{{ ch.title }}</span>
              </div>

              <div class="row-right">
                <!-- 状态徽标 -->
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
                      ? "撰写中…"
                      : (projectStore.chapters[ch.seq] || "").trim().length > 0
                      ? "已完成 ✓"
                      : projectStore.chapterStatuses[ch.seq] === 'error'
                      ? "异常"
                      : "未生成"
                  }}
                </span>

                <!-- 单章操作按钮 -->
                <button
                  class="ch-action-btn"
                  :title="projectStore.chapters[ch.seq] ? '重新生成该章' : '生成该章'"
                  :disabled="projectStore.batchWriting || projectStore.currentWritingSeq === ch.seq"
                  @click.stop="handleWriteSingleChapter(ch.seq)"
                >
                  ✍️
                </button>
                <button
                  v-if="(projectStore.chapters[ch.seq] || '').trim().length > 0"
                  class="ch-action-btn ch-action-danger"
                  title="清空该章"
                  :disabled="projectStore.batchWriting || projectStore.currentWritingSeq === ch.seq"
                  @click="handleClearChapter(ch.seq, $event)"
                >
                  🗑️
                </button>

                <!-- 子标题展开/折叠 -->
                <button
                  v-if="chapterSubHeadingsMap[ch.seq] && chapterSubHeadingsMap[ch.seq].length > 0"
                  class="collapse-toggle-icon"
                  :class="{ collapsed: isChapterCollapsed(ch.seq) }"
                  :title="isChapterCollapsed(ch.seq) ? '展开子标题' : '收起子标题'"
                  @click="toggleChapterCollapse(ch.seq, $event)"
                >
                  {{ isChapterCollapsed(ch.seq) ? '▶' : '▼' }}
                </button>
              </div>
            </div>

            <!-- 多级子标题列表 (平铺目录树，由外层单一全局垂直滚动条滚动) -->
            <transition name="tree-expand">
              <div
                v-if="!isChapterCollapsed(ch.seq) && chapterSubHeadingsMap[ch.seq] && chapterSubHeadingsMap[ch.seq].length > 0"
                class="subheadings-subtree"
              >
                <div
                  v-for="sub in chapterSubHeadingsMap[ch.seq]"
                  :key="sub.id"
                  class="subheading-item-row"
                  :class="`level-${sub.level}`"
                  :title="sub.title"
                  @click="handleSubHeadingClick(ch.seq, sub.id, $event)"
                >
                  <span class="sub-bullet">{{ sub.level === 2 ? '🔹' : sub.level === 3 ? '▪' : '▫' }}</span>
                  <span class="sub-text">{{ sub.title }}</span>
                </div>
              </div>
            </transition>
          </div>

          <div v-if="totalChapters === 0" class="empty-outline-tip">
            暂无章节目录，请返回步骤 2「模板与大纲」生成或编写大纲。
          </div>
        </div>
      </aside>

      <!-- 右侧：10.5pt 出版级排版所见即所得主画布 -->
      <main class="editor-panel card">
        <div class="card-header editor-header">
          <div class="editor-title-area">
            <div class="title-row">
              <span class="seq-tag" v-if="currentChapter">第 {{ currentChapter.seq }} 章</span>
              <h3 class="active-ch-title">{{ currentChapter?.title || "未选择章节" }}</h3>
            </div>
            <div class="editor-meta-row">
              <span class="meta-item">
                当前字数：<strong>{{ currentChapterWords.toLocaleString() }}</strong> 字 (正文)
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

          <!-- 右上角快捷操作组 (保留 Hint, 参考资料, 复制 Markdown 与流式生成操作) -->
          <div class="editor-actions">
            <button
              class="btn btn-outline"
              @click="showHintSection = !showHintSection"
              :class="{ active: showHintSection }"
              title="设置本章重点写作提示，注入 Prompt 进行针对性工程论述"
            >
              💡 {{ showHintSection ? "收起提示" : "写作提示 (Hint)" }}
            </button>

            <button
              class="btn btn-outline ref-drawer-btn"
              :class="{ active: showRefDrawer }"
              @click="showRefDrawer = !showRefDrawer"
              title="查看本章正文中命中的底稿文件与规程标准引用清单"
            >
              📚 参考资料 ({{ currentChapterReferences.length }})
            </button>

            <button
              class="btn btn-outline"
              @click="copyCurrentChapterMarkdown"
              title="复制当前章节排版 Markdown 源码至剪贴板"
            >
              📋 复制 Markdown
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
              {{ currentChapterWords > 0 ? "🔄 重新生成本章" : "✍️ 单章流式写作" }}
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
            <div class="canvas-spec-bar">
              <span class="spec-tag">📖 国家发改委与行业规程出版级排版 (10.5pt)</span>
              <span class="spec-tip">
                支持直接在排版文字上点击输入、改字与润色，流式打字机实时排版，300ms 自动落盘。
              </span>
            </div>

            <!-- 动态构思等待卡片：当正在流式写作且正文字数为 0 时展示 -->
            <transition name="fade">
              <div
                v-if="isCurrentChapterWriting && currentChapterWords === 0"
                class="thinking-state-container"
              >
                <div class="thinking-card-inner">
                  <!-- 顶部构思指示与秒级计时器 -->
                  <div class="thinking-top-row">
                    <div class="thinking-badge">
                      <span class="radar-pulse"></span>
                      <span class="thinking-badge-text">大模型深度推理与专业构思中</span>
                    </div>
                    <div class="thinking-elapsed-timer">
                      ⚡ 构思已耗时 <strong>{{ projectStore.writingProgress?.elapsedSeconds || 0 }}</strong> 秒
                    </div>
                  </div>

                  <!-- 流水线三段步进指示 -->
                  <div class="pipeline-stepper">
                    <!-- 步骤 1: RAG 检索 -->
                    <div
                      class="stepper-node"
                      :class="{
                        completed: projectStore.writingProgress?.stage !== 'rag',
                        active: projectStore.writingProgress?.stage === 'rag',
                      }"
                    >
                      <div class="stepper-badge">
                        <span v-if="projectStore.writingProgress?.stage !== 'rag'" class="stepper-check">✓</span>
                        <span v-else class="stepper-spinner"></span>
                      </div>
                      <div class="stepper-text">
                        <span class="stepper-title">三源知识检索</span>
                        <span class="stepper-desc">底稿数据 + 行业规程 + 百度联网 RAG</span>
                      </div>
                    </div>

                    <div class="stepper-line" :class="{ completed: projectStore.writingProgress?.stage !== 'rag' }"></div>

                    <!-- 步骤 2: 骨架锁定 -->
                    <div
                      class="stepper-node"
                      :class="{
                        completed: ['reasoning', 'writing'].includes(projectStore.writingProgress?.stage || ''),
                        active: projectStore.writingProgress?.stage === 'skeleton',
                        pending: projectStore.writingProgress?.stage === 'rag',
                      }"
                    >
                      <div class="stepper-badge">
                        <span v-if="['reasoning', 'writing'].includes(projectStore.writingProgress?.stage || '')" class="stepper-check">✓</span>
                        <span v-else-if="projectStore.writingProgress?.stage === 'skeleton'" class="stepper-spinner"></span>
                        <span v-else class="stepper-dot">2</span>
                      </div>
                      <div class="stepper-text">
                        <span class="stepper-title">骨架提取锁定</span>
                        <span class="stepper-desc">全层级大纲与结构骨架</span>
                      </div>
                    </div>

                    <div class="stepper-line" :class="{ completed: ['reasoning', 'writing'].includes(projectStore.writingProgress?.stage || '') }"></div>

                    <!-- 步骤 3: 深度推理 -->
                    <div
                      class="stepper-node"
                      :class="{
                        completed: projectStore.writingProgress?.stage === 'writing',
                        active: ['reasoning', 'writing'].includes(projectStore.writingProgress?.stage || ''),
                        pending: ['rag', 'skeleton'].includes(projectStore.writingProgress?.stage || ''),
                      }"
                    >
                      <div class="stepper-badge">
                        <span v-if="projectStore.writingProgress?.stage === 'writing'" class="stepper-check">✓</span>
                        <span v-else-if="projectStore.writingProgress?.stage === 'reasoning'" class="stepper-wave">
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

                  <!-- 动态状态消息栏 -->
                  <div class="thinking-message-bar">
                    <div class="sound-wave-indicator">
                      <span class="sw-bar b1"></span>
                      <span class="sw-bar b2"></span>
                      <span class="sw-bar b3"></span>
                      <span class="sw-bar b4"></span>
                      <span class="sw-bar b5"></span>
                    </div>
                    <span class="thinking-msg-text">
                      {{ projectStore.writingProgress?.message || '大模型正在深度思考与组织专业工程论证与数据表格...' }}
                    </span>
                  </div>

                  <!-- 思维链推演窗（可折叠查看思考细节） -->
                  <div v-if="projectStore.writingProgress?.thoughtText" class="thought-stream-card">
                    <div class="thought-stream-header" @click="showThoughtDetails = !showThoughtDetails">
                      <div class="thought-stream-title">
                        <span class="thought-icon">💭</span>
                        <span>思维链实时推演细节 ({{ projectStore.writingProgress.thoughtText.length }} 字符)</span>
                      </div>
                      <button class="thought-toggle-btn">
                        {{ showThoughtDetails ? '收起 ▲' : '展开 ▼' }}
                      </button>
                    </div>
                    <div v-show="showThoughtDetails" ref="thoughtContentRef" class="thought-stream-body">
                      <pre>{{ projectStore.writingProgress.thoughtText }}</pre>
                    </div>
                  </div>

                  <!-- 无单独思维链输出时的说明卡片 -->
                  <div v-else class="thought-placeholder-card">
                    <div class="placeholder-icon">✨</div>
                    <div class="placeholder-desc">
                      已提取并锁定本章全层级大纲骨架。大模型正结合工程底稿、行业规程与权威政务联网资料进行方案论证与指标校核计算，正文到达后将自动进入实时排版打字机输出...
                    </div>
                  </div>

                  <!-- 底部温馨提示 -->
                  <div class="thinking-notice-footer">
                    <span class="notice-icon">💡</span>
                    <span class="notice-text">
                      工程咨询报告专业性强、篇幅宏大，大模型深度组织论述需数十秒构思时间，请稍候。
                    </span>
                  </div>
                </div>
              </div>
            </transition>

            <!-- 纯净排版模式：就地 contenteditable 编辑画布 -->
            <div
              v-show="!isCurrentChapterWriting || currentChapterWords > 0"
              ref="editorCanvasRef"
              contenteditable="true"
              class="rich-rendered-editor"
              @input="onEditorInput"
              data-placeholder="点击上方「✍️ 单章流式写作」或「🚀 一键开始全书写作」，系统将结合工程底稿与标准规程自动打字机式流式生成章节排版正文；生成后可直接在文字上就地点击输入编辑..."
            ></div>
          </div>
        </div>

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
                    <div v-if="refItem.url" class="ref-card-link">
                      <a :href="refItem.url" target="_blank" rel="noopener noreferrer" class="ref-external-link">
                        🔗 {{ refItem.url }}
                      </a>
                    </div>
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
  grid-template-columns: 350px 1fr;
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
  height: calc(100vh - 165px);
  min-height: 0;
  overflow: hidden;
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

/* 推荐写作顺序流程胶囊指示 */
.writing-order-box {
  background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.order-box-header {
  display: flex;
  align-items: center;
  gap: 5px;
}
.order-icon {
  font-size: 13px;
}
.order-title {
  font-size: 11.5px;
  font-weight: 600;
  color: #1e40af;
}
.order-flow-chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}
.order-node-wrap {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.order-chip {
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.15s ease;
}
.order-chip:hover {
  border-color: #3b82f6;
  color: #1d4ed8;
}
.order-chip.active {
  background: #3b82f6;
  color: #ffffff;
  border-color: #2563eb;
  font-weight: 600;
}
.order-chip.completed:not(.active) {
  background: #dcfce7;
  color: #15803d;
  border-color: #86efac;
}
.order-chip.writing:not(.active) {
  background: #fef3c7;
  color: #b45309;
  border-color: #fde68a;
}
.flow-arrow {
  font-size: 9px;
  color: #94a3b8;
}

.global-actions {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  background: #fff;
}

/* Flat 平铺一体化目录树 (单一定高全局滚动) */
.outline-tree-scrollable {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 transparent;
}
.outline-tree-scrollable::-webkit-scrollbar {
  width: 5px;
}
.outline-tree-scrollable::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}
.outline-tree-scrollable::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.empty-outline-tip {
  padding: 24px 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
}

.chapter-tree-node {
  border: none;
  border-radius: 6px;
  background: transparent;
  overflow: hidden;
  transition: all 0.15s ease;
  flex-shrink: 0;
  min-height: 38px;
}
.chapter-tree-node.is-active {
  background: rgba(59, 130, 246, 0.06);
}

.chapter-node-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 8px;
  cursor: pointer;
  user-select: none;
  border-radius: 6px;
  background: transparent;
  transition: background 0.15s ease;
  gap: 6px;
}
.chapter-node-row:hover {
  background: #f1f5f9;
}
.chapter-tree-node.is-active .chapter-node-row {
  background: #eff6ff;
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
.chapter-tree-node.is-completed:not(.is-active) .ch-seq-tag {
  background: #dcfce7;
  color: #15803d;
}

.ch-title-text {
  font-size: 12.5px;
  font-weight: 600;
  color: #1e293b;
  white-space: normal;
  word-break: break-word;
  line-height: 1.35;
}
.chapter-tree-node.is-active .ch-title-text {
  color: #1d4ed8;
}

.row-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.status-pill {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 10px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  white-space: nowrap;
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

.ch-action-btn {
  background: none;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  padding: 2px 4px;
  font-size: 11px;
  transition: all 0.15s;
}
.ch-action-btn:hover:not(:disabled) {
  background: #e2e8f0;
  border-color: #cbd5e1;
}
.ch-action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.ch-action-danger:hover:not(:disabled) {
  background: #fee2e2;
  border-color: #fca5a5;
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
  padding: 2px 0 4px 0;
  background: transparent;
}
.subheading-item-row {
  padding: 3px 8px 3px 26px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 11.5px;
  color: #64748b;
  border-radius: 4px;
  transition: all 0.12s ease;
}
.subheading-item-row:hover {
  background: #f1f5f9;
  color: #0f172a;
}
.subheading-item-row.level-3 {
  padding-left: 36px;
}
.subheading-item-row.level-4 {
  padding-left: 46px;
}
.sub-bullet {
  font-size: 9px;
  flex-shrink: 0;
  opacity: 0.6;
}
.sub-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 右侧编辑器面板 */
.editor-panel {
  display: flex;
  flex-direction: column;
  min-height: 640px;
  position: relative;
  overflow: hidden;
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
  gap: 8px;
  flex-shrink: 0;
}

.editor-body {
  flex: 1;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
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

.canvas-spec-bar {
  padding: 8px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 10px;
}
.spec-tag {
  font-size: 11px;
  font-weight: 700;
  color: #1e40af;
  background: #dbeafe;
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;
}
.spec-tip {
  font-size: 11px;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 动态构思指示卡片 */
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

/* 流水线步进指示 */
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

/* 动态状态消息栏 */
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

/* 思维链推演窗 */
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

/* 无思维链说明卡片 */
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

/* 底部温馨提示 */
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

/* 排版模式就地富文本编辑画布样式 */
.rich-rendered-editor {
  flex: 1;
  padding: 28px 36px;
  min-height: 480px;
  max-height: calc(100vh - 250px);
  overflow-y: auto;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "WenQuanYi Micro Hei", sans-serif;
  font-size: 10.5pt;
  line-height: 1.8;
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
.rich-rendered-editor :deep(h1) {
  font-size: 16pt;
  font-weight: 700;
  color: #0f172a;
  margin: 24px 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid #e2e8f0;
  scroll-margin-top: 16px;
}
.rich-rendered-editor :deep(h2) {
  font-size: 14pt;
  font-weight: 600;
  color: #1e293b;
  margin: 20px 0 10px 0;
  padding-bottom: 4px;
  border-bottom: 1px solid #f1f5f9;
  scroll-margin-top: 16px;
}
.rich-rendered-editor :deep(h3) {
  font-size: 12pt;
  font-weight: 600;
  color: #334155;
  margin: 16px 0 8px 0;
  scroll-margin-top: 16px;
}
.rich-rendered-editor :deep(h4) {
  font-size: 10.5pt;
  font-weight: 600;
  color: #475569;
  margin: 12px 0 6px 0;
  scroll-margin-top: 16px;
}
.rich-rendered-editor :deep(p) {
  font-size: 10.5pt;
  font-weight: 400;
  color: #334155;
  line-height: 1.8;
  margin: 0 0 14px 0;
  text-indent: 2em;
  text-align: justify;
}
.rich-rendered-editor :deep(strong) {
  font-weight: 600;
  color: #0f172a;
}
.rich-rendered-editor :deep(em) {
  font-style: italic;
  color: #475569;
}
.rich-rendered-editor :deep(blockquote) {
  margin: 14px 0;
  padding: 10px 16px;
  background: #f8fafc;
  border-left: 4px solid #3b82f6;
  border-radius: 0 6px 6px 0;
  color: #475569;
  font-size: 10.5pt;
}
.rich-rendered-editor :deep(blockquote p) {
  margin: 0;
  text-indent: 0;
  font-size: 10.5pt;
}
.rich-rendered-editor :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 18px 0;
  font-size: 10.5pt;
  border-top: 2px solid #334155;
  border-bottom: 2px solid #334155;
  border-left: none;
  border-right: none;
}
.rich-rendered-editor :deep(th),
.rich-rendered-editor :deep(td) {
  border: none;
  padding: 8px 12px;
  text-align: left;
  font-size: 10.5pt;
  line-height: 1.5;
}
.rich-rendered-editor :deep(th) {
  background: #f8fafc;
  font-weight: 600;
  color: #1e293b;
  border-bottom: 1px solid #475569;
}
.rich-rendered-editor :deep(tr:nth-child(even)) {
  background: transparent;
}
.rich-rendered-editor :deep(tr:hover) {
  background: #f8fafc;
}
.rich-rendered-editor :deep(ul),
.rich-rendered-editor :deep(ol) {
  margin: 0 0 14px 0;
  padding-left: 24px;
  color: #334155;
}
.rich-rendered-editor :deep(li) {
  font-size: 10.5pt;
  font-weight: 400;
  margin-bottom: 6px;
  line-height: 1.8;
}
.rich-rendered-editor :deep(pre) {
  background: #0f172a;
  color: #e2e8f0;
  padding: 12px 16px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 14px 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}
.rich-rendered-editor :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  background: #f1f5f9;
  color: #0969da;
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 0.9em;
}
.rich-rendered-editor :deep(pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
}
.rich-rendered-editor :deep(hr) {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 20px 0;
}
.rich-rendered-editor :deep(.ref-badge) {
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
.rich-rendered-editor :deep(.heading-anchor-pulse),
:deep(.heading-anchor-pulse) {
  animation: headingPulse 1.5s ease-out forwards;
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

.tree-expand-enter-active,
.tree-expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.tree-expand-enter-from,
.tree-expand-leave-to {
  opacity: 0;
  transform: translateY(-4px);
  max-height: 0;
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
.ref-card-link {
  font-size: 11px;
  word-break: break-all;
  margin: 2px 0;
}
.ref-external-link {
  color: #2563eb;
  text-decoration: underline;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.ref-external-link:hover {
  color: #1d4ed8;
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

.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity 0.2s ease;
}
.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}
</style>
