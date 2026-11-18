import * as engineApi from "../../lib/engineApi";
import type { LLMConfig } from "../../lib/engineApi";
import { extractOutlineHeadings, normalizeMarkdown } from "../../lib/markdown";
import { loadChaptersFromLocal, saveChaptersToLocal } from "../projectStorage";
import type { ChapterRunStatus, ProjectStoreState } from "./types";

export function createWritingSlice(state: ProjectStoreState) {
  const {
    currentProject,
    reportType,
    outlineMd,
    outlineChapters,
    writingOrder,
    chapters,
    chapterStatuses,
    selectedChapterSeq,
    batchWriting,
    currentWritingSeq,
    writingProgress,
    lastBaseUrl,
    error,
  } = state;

  let progressTimer: ReturnType<typeof setInterval> | null = null;
  let activeStopWriting: (() => void) | null = null;
  const chapterDebounceTimers: Record<number, ReturnType<typeof setTimeout>> = {};

  function clearWritingTimer() {
    if (progressTimer) {
      clearInterval(progressTimer);
      progressTimer = null;
    }
  }

  function deriveStatusesFromMap(map: Record<number, string>): Record<number, ChapterRunStatus> {
    const res: Record<number, ChapterRunStatus> = {};
    for (const [k, v] of Object.entries(map)) {
      const seq = Number(k);
      if (!isNaN(seq)) {
        res[seq] = v.trim().length > 0 ? "completed" : "idle";
      }
    }
    return res;
  }

  async function loadChapters(
    baseUrl?: string,
    projectName?: string,
  ): Promise<Record<number, string>> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = projectName || currentProject.value?.name;
    if (!targetName) {
      chapters.value = {};
      chapterStatuses.value = {};
      return {};
    }

    if (targetUrl) {
      try {
        const res = await engineApi.getProjectChapters(targetUrl, targetName);
        if (res && res.chapters) {
          const newChaps: Record<number, string> = {};
          for (const [k, v] of Object.entries(res.chapters)) {
            const seq = Number(k);
            if (!isNaN(seq)) newChaps[seq] = v;
          }
          chapters.value = newChaps;
          chapterStatuses.value = deriveStatusesFromMap(newChaps);
          saveChaptersToLocal(targetName, newChaps);
          return newChaps;
        }
      } catch {
        /* fallback to local */
      }
    }

    const local = loadChaptersFromLocal(targetName);
    if (local) {
      chapters.value = local;
      chapterStatuses.value = deriveStatusesFromMap(local);
      return local;
    }

    chapters.value = {};
    chapterStatuses.value = {};
    return {};
  }

  async function saveChapter(
    baseUrl?: string,
    seq?: number,
    text?: string,
    immediate = false,
  ): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = currentProject.value?.name;
    const targetSeq = seq !== undefined ? seq : selectedChapterSeq.value;
    const targetText = text !== undefined ? text : chapters.value[targetSeq] || "";

    chapters.value[targetSeq] = targetText;
    if (targetText.trim().length > 0) {
      chapterStatuses.value[targetSeq] = "completed";
    }

    if (targetName) {
      saveChaptersToLocal(targetName, chapters.value);
    }

    if (!targetUrl || !targetName) return;

    const doSave = async () => {
      try {
        await engineApi.saveProjectChapter(targetUrl, targetName, targetSeq, targetText);
      } catch {
        /* non-fatal */
      }
    };

    if (immediate) {
      await doSave();
    } else {
      if (chapterDebounceTimers[targetSeq]) {
        clearTimeout(chapterDebounceTimers[targetSeq]);
      }
      chapterDebounceTimers[targetSeq] = setTimeout(doSave, 300);
    }
  }

  async function deleteChapter(baseUrl?: string, seq?: number): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    const targetName = currentProject.value?.name;
    const targetSeq = seq !== undefined ? seq : selectedChapterSeq.value;

    delete chapters.value[targetSeq];
    chapterStatuses.value[targetSeq] = "idle";

    if (targetName) {
      saveChaptersToLocal(targetName, chapters.value);
      if (targetUrl) {
        try {
          await engineApi.deleteProjectChapter(targetUrl, targetName, targetSeq);
        } catch {
          /* ignore */
        }
      }
    }
  }

  function selectChapter(seq: number) {
    selectedChapterSeq.value = seq;
  }

  function stopWriting() {
    batchWriting.value = false;
    clearWritingTimer();
    writingProgress.value = null;
    if (activeStopWriting) {
      activeStopWriting();
      activeStopWriting = null;
    }
    currentWritingSeq.value = null;
  }

  async function writeSingleChapterStream(
    baseUrl: string,
    seq: number,
    llmConfig: LLMConfig,
    hint?: string,
  ): Promise<void> {
    if (baseUrl) lastBaseUrl.value = baseUrl;
    const targetName = currentProject.value?.name || "";
    if (!baseUrl) throw new Error("引擎未就绪");
    if (!outlineMd.value) throw new Error("请先生成或设置大纲内容");

    if (activeStopWriting) {
      activeStopWriting();
      activeStopWriting = null;
    }
    clearWritingTimer();

    selectedChapterSeq.value = seq;
    currentWritingSeq.value = seq;
    chapterStatuses.value[seq] = "writing";
    chapters.value[seq] = "";
    writingProgress.value = {
      seq,
      stage: "rag",
      message: "🔍 正在三源检索：工程底稿库 + 行业规程库 + 权威政务联网信息(.gov.cn)...",
      elapsedSeconds: 0,
      thoughtText: "",
    };

    progressTimer = setInterval(() => {
      if (writingProgress.value && writingProgress.value.seq === seq) {
        writingProgress.value.elapsedSeconds += 1;
      }
    }, 1000);

    if (targetName) {
      saveChaptersToLocal(targetName, chapters.value);
    }

    const predecessor_chapters: Record<string, string> = {};
    for (const [k, v] of Object.entries(chapters.value)) {
      const chSeq = Number(k);
      if (!isNaN(chSeq) && chSeq !== seq && v && v.trim().length > 0) {
        predecessor_chapters[String(chSeq)] = v;
      }
    }

    return new Promise<void>((resolve, reject) => {
      const stop = engineApi.streamChapterWriting(
        baseUrl,
        {
          project: targetName,
          report_type: reportType.value,
          outline_md: outlineMd.value,
          chapter_seq: seq,
          stream: true,
          llm_config: llmConfig,
          topic: targetName,
          predecessor_chapters,
          writing_hint: hint || "",
        },
        (chunk) => {
          const cur = chapters.value[seq] || "";
          chapters.value = { ...chapters.value, [seq]: cur + chunk };
          if (targetName) {
            saveChaptersToLocal(targetName, chapters.value);
          }
        },
        async () => {
          clearWritingTimer();
          writingProgress.value = null;
          chapterStatuses.value[seq] = "completed";
          currentWritingSeq.value = null;
          activeStopWriting = null;

          const rawText = chapters.value[seq] || "";
          const known = extractOutlineHeadings(outlineMd.value);
          const normalized = normalizeMarkdown(rawText, known);
          chapters.value = { ...chapters.value, [seq]: normalized };

          if (targetName) {
            saveChaptersToLocal(targetName, chapters.value);
            try {
              await engineApi.saveProjectChapter(baseUrl, targetName, seq, chapters.value[seq]);
            } catch {
              /* ignore */
            }
          }
          resolve();
        },
        (err) => {
          clearWritingTimer();
          writingProgress.value = null;
          chapterStatuses.value[seq] = "error";
          currentWritingSeq.value = null;
          activeStopWriting = null;
          error.value = err.message;
          reject(err);
        },
        (event) => {
          if (!writingProgress.value || writingProgress.value.seq !== seq) return;
          if (event.type === "stage") {
            if (event.stage) writingProgress.value.stage = event.stage;
            if (event.message) writingProgress.value.message = event.message;
          } else if (event.type === "thought") {
            writingProgress.value.stage = "reasoning";
            writingProgress.value.thoughtText += event.chunk || "";
          } else if (event.type === "chunk") {
            writingProgress.value.stage = "writing";
          }
        },
      );

      activeStopWriting = () => {
        stop();
        clearWritingTimer();
        writingProgress.value = null;
        if (chapterStatuses.value[seq] === "writing") {
          chapterStatuses.value[seq] = chapters.value[seq] ? "completed" : "idle";
        }
        currentWritingSeq.value = null;
        activeStopWriting = null;
        resolve();
      };
    });
  }

  async function writeAllChapters(
    baseUrl: string,
    llmConfig: LLMConfig,
    forceAll = false,
  ): Promise<void> {
    if (batchWriting.value) return;
    const targetChapters = outlineChapters.value;
    if (targetChapters.length === 0) {
      throw new Error("大纲中暂无章节");
    }

    const execOrder =
      writingOrder.value && writingOrder.value.length > 0
        ? writingOrder.value
        : targetChapters.map((c) => c.seq);

    const targetSeqs = execOrder.filter(
      (seq) => forceAll || !chapters.value[seq] || chapters.value[seq].trim().length === 0,
    );
    if (targetSeqs.length === 0) return;

    batchWriting.value = true;
    error.value = null;
    try {
      for (const seq of targetSeqs) {
        if (!batchWriting.value) break;
        selectedChapterSeq.value = seq;
        await writeSingleChapterStream(baseUrl, seq, llmConfig);
      }
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      batchWriting.value = false;
      currentWritingSeq.value = null;
    }
  }

  return {
    loadChapters,
    saveChapter,
    deleteChapter,
    selectChapter,
    stopWriting,
    writeSingleChapterStream,
    writeAllChapters,
  };
}
