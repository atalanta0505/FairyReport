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
import * as engineApi from "../lib/engineApi";
import { useEngineStore } from "../stores/engine";
import { useProjectStore } from "../stores/project";
import { useSettingsStore } from "../stores/settings";
import ReferenceLedgerDrawer from "./shared/ReferenceLedgerDrawer.vue";
import WritingThinkingPanel from "./writing/WritingThinkingPanel.vue";

const engine = useEngineStore();
const settings = useSettingsStore();
const projectStore = useProjectStore();

const actionMessage = ref<{ type: "success" | "error"; text: string } | null>(null);
const showHintSection = ref<boolean>(false);
const showRefDrawer = ref<boolean>(false);
const refFilterType = ref<"all" | "material" | "standard" | "web">("all");
const chapterHints = ref<Record<number, string>>({});

const collapsedChapters = ref<Record<number, boolean>>({});
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
    const seq = currentChapter.value?.seq || projectStore.selectedChapterSeq || 1;
    return projectStore.chapters[seq] || "";
  },
  set: (val: string) => {
    const seq = currentChapter.value?.seq || projectStore.selectedChapterSeq || 1;
    projectStore.saveChapter(engine.baseUrl, seq, val);
  },
});

const currentChapterWords = computed(() => {
  return countContentChars(currentChapterText.value);
});

const currentChapterReferences = computed<ReferenceItem[]>(() => {
  return extractReferences(currentChapterText.value);
});

function openRefDrawerAndFocusCard(refTitle: string, refType?: "material" | "standard" | "web" | "all") {
  showRefDrawer.value = true;
  if (refType && refType !== "all") {
    refFilterType.value = refType;
  } else {
    refFilterType.value = "all";
  }
  nextTick(() => {
    const allCards = document.querySelectorAll(".ref-drawer-panel .ref-card-item");
    let targetCard: HTMLElement | null = null;
    for (const card of allCards) {
      const cardTitle = card.getAttribute("data-ref-title");
      if (cardTitle === refTitle || (cardTitle && refTitle && (cardTitle.includes(refTitle) || refTitle.includes(cardTitle)))) {
        targetCard = card as HTMLElement;
        break;
      }
    }
    if (targetCard) {
      targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
      targetCard.classList.remove("ref-card-pulse");
      void targetCard.offsetWidth;
      targetCard.classList.add("ref-card-pulse");
      setTimeout(() => {
        targetCard?.classList.remove("ref-card-pulse");
      }, 2000);
    }
  });
}

function locateRefInCanvas(title: string) {
  if (!editorCanvasRef.value) return;
  const tags = editorCanvasRef.value.querySelectorAll(".inline-ref-tag");
  let targetTag: HTMLElement | null = null;
  for (const tag of tags) {
    const t = tag.getAttribute("data-ref-title");
    if (t === title || (t && title && (t.includes(title) || title.includes(t)))) {
      targetTag = tag as HTMLElement;
      break;
    }
  }
  if (targetTag) {
    targetTag.scrollIntoView({ behavior: "smooth", block: "center" });
    targetTag.classList.remove("inline-ref-pulse");
    void targetTag.offsetWidth;
    targetTag.classList.add("inline-ref-pulse");
    setTimeout(() => {
      targetTag?.classList.remove("inline-ref-pulse");
    }, 2000);
    showMsg(`已定位到正文引用位置：「${title}」`, "success");
  } else {
    showMsg(`未在当前正文视口中找到「${title}」引用标记`, "error");
  }
}

async function handleOpenWebUrl(url?: string) {
  if (!url) {
    showMsg("暂无对应的有效网页链接", "error");
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

function handleEditorCanvasClick(e: MouseEvent) {
  const target = e.target as HTMLElement | null;
  if (!target) return;

  // Mermaid 切换视图与复制代码工具栏交互
  const toggleBtn = target.closest(".mermaid-btn-toggle-view") as HTMLElement | null;
  if (toggleBtn) {
    e.stopPropagation();
    e.preventDefault();
    const container = toggleBtn.closest(".mermaid-container") as HTMLElement | null;
    if (container) {
      const svgWrapper = container.querySelector(".mermaid-svg-wrapper") as HTMLElement | null;
      const codeWrapper = container.querySelector(".mermaid-code-wrapper") as HTMLElement | null;
      const btnText = toggleBtn.querySelector(".btn-text");
      const btnIcon = toggleBtn.querySelector(".btn-icon");

      if (svgWrapper && codeWrapper) {
        const isSvgVisible = svgWrapper.style.display !== "none";
        if (isSvgVisible) {
          svgWrapper.style.display = "none";
          codeWrapper.style.display = "block";
          if (btnText) btnText.textContent = "源码模式";
          if (btnIcon) btnIcon.textContent = "💻";
        } else {
          svgWrapper.style.display = "flex";
          codeWrapper.style.display = "none";
          if (btnText) btnText.textContent = "矢量拓扑";
          if (btnIcon) btnIcon.textContent = "👁️";
        }
      }
    }
    return;
  }

  const copyBtn = target.closest(".mermaid-btn-copy") as HTMLElement | null;
  if (copyBtn) {
    e.stopPropagation();
    e.preventDefault();
    const container = copyBtn.closest(".mermaid-container") as HTMLElement | null;
    const code = container?.getAttribute("data-mermaid-code") || "";
    if (code) {
      navigator.clipboard.writeText(code).then(() => {
        showMsg("已复制 Mermaid 流程图源码至剪贴板", "success");
      }).catch(() => {
        showMsg("复制失败，请手动选择复制", "error");
      });
    }
    return;
  }

  const refTag = target.closest(".inline-ref-tag") as HTMLElement | null;
  if (refTag) {
    const refType = (refTag.getAttribute("data-ref-type") || "all") as "material" | "standard" | "web" | "all";
    const refTitle = refTag.getAttribute("data-ref-title") || "";
    openRefDrawerAndFocusCard(refTitle, refType);
  }
}

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

const isWritingActive = computed(() => {
  return (
    projectStore.isWritingAnyChapter ||
    isCurrentChapterWriting.value ||
    projectStore.batchWriting ||
    projectStore.currentWritingSeq !== null ||
    projectStore.writingProgress !== null ||
    Object.values(projectStore.chapterStatuses).some((s) => s === "writing")
  );
});

const isThinkingStage = computed(() => {
  return (
    isCurrentChapterWriting.value &&
    projectStore.writingProgress?.stage !== "writing" &&
    (!currentChapterText.value || currentChapterText.value.trim().length === 0)
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

// 富文本就地输入处理：提取 HTML 转换为 Markdown 立即更新响应式状态并防抖落盘
function onEditorInput(e: Event) {
  const target = e.target as HTMLElement;
  const html = target.innerHTML;
  const md = htmlToMarkdown(html);

  // 1. 实时更新响应式 store，字数统计与状态 0ms 实时跳动
  if (projectStore.selectedChapterSeq) {
    projectStore.chapters = {
      ...projectStore.chapters,
      [projectStore.selectedChapterSeq]: md,
    };
  }

  // 2. 300ms 防抖持久化落盘
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
    base_url: settings.llmBaseUrl || "https://api.deepseek.com",
    model: settings.llmModel || "deepseek-flash",
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
  if (isWritingActive.value) {
    showMsg("当前章节正在流式撰写中，请等待撰写完成或点击「停止写作」后再返回上一步", "error");
    return;
  }
  projectStore.setStep(2);
}

function nextStep() {
  if (isWritingActive.value) {
    showMsg("当前章节正在流式撰写中，请等待撰写完成或点击「停止写作」后再进入下一步审阅修改", "error");
    return;
  }
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
                本章字数：<strong>{{ currentChapterWords.toLocaleString() }}</strong> 字 (正文)
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
              <span class="spec-tag">📖 行业规程与工程编制出版级排版 (10.5pt)</span>
              <span class="spec-tip">
                支持直接在排版文字上点击输入、改字与润色，流式打字机实时排版，300ms 自动落盘。
              </span>
            </div>

            <!-- 动态构思等待卡片：当正在深度构思且正文字数为 0 时展示 -->
            <WritingThinkingPanel
              :visible="isThinkingStage"
              :progress="projectStore.writingProgress"
            />

            <!-- 纯净排版模式：就地 contenteditable 编辑画布 -->
            <div
              v-show="!isThinkingStage"
              ref="editorCanvasRef"
              contenteditable="true"
              class="rich-rendered-editor"
              @input="onEditorInput"
              @click="handleEditorCanvasClick"
              data-placeholder="点击上方「✍️ 单章流式写作」或「🚀 一键开始全书写作」，系统将结合工程底稿与标准规程自动打字机式流式生成章节排版正文；生成后可直接在文字上就地点击输入编辑..."
            ></div>
          </div>
        </div>

        <ReferenceLedgerDrawer
          :open="showRefDrawer"
          v-model:filter-type="refFilterType"
          :chapter-seq="currentChapter?.seq"
          :chapter-title="currentChapter?.title"
          :references="currentChapterReferences"
          @close="showRefDrawer = false"
          @locate="locateRefInCanvas"
          @open-url="handleOpenWebUrl"
        />
      </main>
    </div>

    <!-- 底部流转按钮 -->
    <div class="bottom-nav">
      <button
        class="btn btn-secondary btn-lg"
        :disabled="isWritingActive"
        @click="prevStep"
        :title="isWritingActive ? '正在流式生成中，请等待完成或点击「停止写作」' : ''"
      >
        &larr; 上一步：模板与大纲
      </button>
      <button
        class="btn btn-primary btn-lg"
        :disabled="isWritingActive || (completedCount === 0 && totalWordCount === 0)"
        @click="nextStep"
        :title="isWritingActive ? '正在流式生成中，请等待完成或点击「停止写作」' : ''"
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

/* 右侧编辑器面板 */
.editor-panel {
  display: flex;
  flex-direction: column;
  min-height: 640px;
  position: relative;
  overflow: hidden;
}

.status-text.writing {
  color: #d97706;
  font-weight: 500;
}
.status-text.completed {
  color: #16a34a;
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

/* Step 3 画布高度微调 */
.rich-rendered-editor {
  padding: 28px 36px;
  min-height: 480px;
  max-height: calc(100vh - 250px);
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

@keyframes inlineRefPulse {
  0% {
    background-color: #fef08a !important;
    box-shadow: 0 0 0 6px rgba(234, 179, 8, 0.6) !important;
    transform: scale(1.08);
  }
  50% {
    background-color: #fef9c3 !important;
    box-shadow: 0 0 0 3px rgba(234, 179, 8, 0.3) !important;
    transform: scale(1.04);
  }
  100% {
    box-shadow: none !important;
    transform: scale(1);
  }
}
.rich-rendered-editor :deep(.inline-ref-pulse),
:deep(.inline-ref-pulse) {
  animation: inlineRefPulse 2s cubic-bezier(0.2, 0.8, 0.2, 1) !important;
}
</style>
