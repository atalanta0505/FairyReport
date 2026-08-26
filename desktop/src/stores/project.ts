import { defineStore } from "pinia";
import { ref } from "vue";
import * as engineApi from "../lib/engineApi";
import type {
  ChapterInfo,
  GenericStatus,
  GenericUpdateResult,
  IngestResult,
  LLMConfig,
  MaterialOut,
  OutlineResult,
  ProjectOut,
  TemplateItem,
} from "../lib/engineApi";

export function parseChaptersFromOutline(outlineMd: string): ChapterInfo[] {
  if (!outlineMd) return [];
  const lines = outlineMd.split("\n");
  const chapters: ChapterInfo[] = [];
  let seq = 1;
  for (const line of lines) {
    const trimmed = line.trim();
    const match =
      trimmed.match(/^#{1,2}\s+(第[一二三四五六七八九十百零\d]+章[\s：:].+)/) ||
      trimmed.match(/^#{1,2}\s+(第[一二三四五六七八九十百零\d]+章.+)/) ||
      trimmed.match(/^(第[一二三四五六七八九十百零\d]+章[\s：:].+)/) ||
      trimmed.match(/^#\s+(.+)/);
    if (match) {
      chapters.push({ seq: seq++, title: match[1].trim() });
    }
  }
  return chapters;
}

function getStoredStep(): number {
  try {
    if (typeof localStorage !== "undefined") {
      const raw = localStorage.getItem("frl_current_step");
      if (raw) {
        const val = Number(raw);
        if (Number.isInteger(val) && val >= 1 && val <= 5) {
          return val;
        }
      }
    }
    if (typeof sessionStorage !== "undefined") {
      const raw = sessionStorage.getItem("frl_current_step");
      if (raw) {
        const val = Number(raw);
        if (Number.isInteger(val) && val >= 1 && val <= 5) {
          return val;
        }
      }
    }
  } catch {
    // ignore
  }
  return 1;
}

function getStoredProjectName(): string | null {
  try {
    if (typeof localStorage !== "undefined") {
      const val = localStorage.getItem("frl_current_project");
      if (val) return val;
    }
    if (typeof sessionStorage !== "undefined") {
      return sessionStorage.getItem("frl_current_project");
    }
  } catch {
    // ignore
  }
  return null;
}

function setStoredStep(step: number): void {
  try {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem("frl_current_step", String(step));
    }
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.setItem("frl_current_step", String(step));
    }
  } catch {
    // ignore
  }
}

function setStoredProjectName(name: string | null): void {
  try {
    if (typeof localStorage !== "undefined") {
      if (name) {
        localStorage.setItem("frl_current_project", name);
      } else {
        localStorage.removeItem("frl_current_project");
      }
    }
    if (typeof sessionStorage !== "undefined") {
      if (name) {
        sessionStorage.setItem("frl_current_project", name);
      } else {
        sessionStorage.removeItem("frl_current_project");
      }
    }
  } catch {
    // ignore
  }
}

export function getOutlineStorageKey(projectName: string): string {
  return `frl_outline_${projectName}`;
}

export function getChaptersStorageKey(projectName: string): string {
  return `frl_chapters_${projectName}`;
}

export function getReviewsStorageKey(projectName: string): string {
  return `frl_reviews_${projectName}`;
}

export function loadOutlineFromLocal(
  projectName: string,
): { report_type?: string; outline_md?: string; chapters?: ChapterInfo[]; updated_at?: string } | null {
  try {
    if (typeof localStorage !== "undefined") {
      const raw = localStorage.getItem(getOutlineStorageKey(projectName));
      if (raw) {
        return JSON.parse(raw);
      }
    }
  } catch {
    // ignore
  }
  return null;
}

export function saveOutlineToLocal(
  projectName: string,
  data: {
    report_type: string;
    outline_md: string;
    chapters: ChapterInfo[];
    updated_at?: string;
  },
): void {
  try {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(getOutlineStorageKey(projectName), JSON.stringify(data));
    }
  } catch {
    // ignore
  }
}

export function loadChaptersFromLocal(
  projectName: string,
): Record<number, string> | null {
  try {
    if (typeof localStorage !== "undefined") {
      const raw = localStorage.getItem(getChaptersStorageKey(projectName));
      if (raw) {
        const parsed = JSON.parse(raw);
        const result: Record<number, string> = {};
        for (const [k, v] of Object.entries(parsed)) {
          const num = Number(k);
          if (!isNaN(num) && typeof v === "string") {
            result[num] = v;
          }
        }
        return result;
      }
    }
  } catch {
    // ignore
  }
  return null;
}

export function saveChaptersToLocal(
  projectName: string,
  chapters: Record<number, string>,
): void {
  try {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(
        getChaptersStorageKey(projectName),
        JSON.stringify(chapters),
      );
    }
  } catch {
    // ignore
  }
}

export function loadReviewsFromLocal(
  projectName: string,
): Record<number, engineApi.ExpertReviewResult> | null {
  try {
    if (typeof localStorage !== "undefined") {
      const raw = localStorage.getItem(getReviewsStorageKey(projectName));
      if (raw) {
        const parsed = JSON.parse(raw);
        const result: Record<number, engineApi.ExpertReviewResult> = {};
        for (const [k, v] of Object.entries(parsed)) {
          const num = Number(k);
          if (!isNaN(num) && v && typeof v === "object") {
            result[num] = v as engineApi.ExpertReviewResult;
          }
        }
        return result;
      }
    }
  } catch {
    // ignore
  }
  return null;
}

export function saveReviewsToLocal(
  projectName: string,
  reviews: Record<number, engineApi.ExpertReviewResult>,
): void {
  try {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(
        getReviewsStorageKey(projectName),
        JSON.stringify(reviews),
      );
    }
  } catch {
    // ignore
  }
}

export function getFullReviewStorageKey(projectName: string): string {
  return `frl_full_review_${projectName}`;
}

export function loadFullReviewFromLocal(
  projectName: string,
): engineApi.FullReviewData | null {
  try {
    if (typeof localStorage !== "undefined") {
      const raw = localStorage.getItem(getFullReviewStorageKey(projectName));
      if (raw) {
        return JSON.parse(raw);
      }
    }
  } catch {
    // ignore
  }
  return null;
}

export function saveFullReviewToLocal(
  projectName: string,
  data: engineApi.FullReviewData,
): void {
  try {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(
        getFullReviewStorageKey(projectName),
        JSON.stringify(data),
      );
    }
  } catch {
    // ignore
  }
}

export interface ChapterWritingProgress {
  seq: number;
  stage: "rag" | "skeleton" | "reasoning" | "writing" | string;
  message: string;
  elapsedSeconds: number;
  thoughtText: string;
}

export const useProjectStore = defineStore("project", () => {
  const currentStep = ref<number>(getStoredStep());
  const projects = ref<ProjectOut[]>([]);
  const currentProject = ref<ProjectOut | null>(null);
  const materials = ref<MaterialOut[]>([]);
  const genericStatus = ref<GenericStatus | null>(null);

  // Step 2 大纲与模板状态
  const reportType = ref<string>("可行性研究报告");
  const templates = ref<TemplateItem[]>([]);
  const loadingTemplates = ref<boolean>(false);
  const outlineMd = ref<string>("");
  const outlineChapters = ref<ChapterInfo[]>([]);
  const generatingOutline = ref<boolean>(false);

  // Step 3 章节流式写作状态
  const chapters = ref<Record<number, string>>({});
  const chapterStatuses = ref<Record<number, "idle" | "writing" | "completed" | "error">>({});
  const selectedChapterSeq = ref<number>(1);
  const batchWriting = ref<boolean>(false);
  const currentWritingSeq = ref<number | null>(null);
  const writingProgress = ref<ChapterWritingProgress | null>(null);
  let progressTimer: ReturnType<typeof setInterval> | null = null;
  let activeStopWriting: (() => void) | null = null;
  const chapterDebounceTimers: Record<number, ReturnType<typeof setTimeout>> = {};

  // Step 4 专家审阅与修改状态
  const chapterReviews = ref<Record<number, engineApi.ExpertReviewResult>>({});
  const fullBookReview = ref<engineApi.FullReviewData | null>(null);
  const reviewingSeq = ref<number | null>(null);
  const reviewingMode = ref<"all" | "compliance" | "numeric" | "technical">("all");
  const revisingSeq = ref<number | null>(null);
  const activeRevision = ref<{
    seq: number;
    originalText: string;
    revisedText: string;
    instruction: string;
    createdAt: string;
  } | null>(null);

  const lastBaseUrl = ref<string>("");
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  const loadingProjects = ref<boolean>(false);
  const loadingMaterials = ref<boolean>(false);
  const ingesting = ref<boolean>(false);
  const updatingGeneric = ref<boolean>(false);
  const error = ref<string | null>(null);

  function setStep(step: number) {
    if (step >= 1 && step <= 5) {
      currentStep.value = step;
      setStoredStep(step);
    }
  }

  async function loadProjects(baseUrl: string) {
    if (!baseUrl) return;
    lastBaseUrl.value = baseUrl;
    loadingProjects.value = true;
    error.value = null;
    try {
      const list = await engineApi.listProjects(baseUrl);
      projects.value = list;

      const savedName = getStoredProjectName();
      const targetName = currentProject.value?.name || savedName;

      if (targetName) {
        const found = list.find((p) => p.name === targetName);
        if (found) {
          currentProject.value = found;
          setStoredProjectName(found.name);
          await loadMaterials(baseUrl, found.name);
          await loadOutline(baseUrl, found.name);
          await loadChapters(baseUrl, found.name);
          await loadReviews(baseUrl, found.name);
          await loadFullBookReview(baseUrl, found.name);
        } else if (list.length > 0) {
          currentProject.value = list[0];
          setStoredProjectName(list[0].name);
          await loadMaterials(baseUrl, list[0].name);
          await loadOutline(baseUrl, list[0].name);
          await loadChapters(baseUrl, list[0].name);
          await loadReviews(baseUrl, list[0].name);
          await loadFullBookReview(baseUrl, list[0].name);
        } else {
          currentProject.value = null;
          setStoredProjectName(null);
          materials.value = [];
          outlineMd.value = "";
          outlineChapters.value = [];
          chapters.value = {};
          chapterStatuses.value = {};
          chapterReviews.value = {};
          fullBookReview.value = null;
          activeRevision.value = null;
        }
      } else if (list.length > 0) {
        currentProject.value = list[0];
        setStoredProjectName(list[0].name);
        await loadMaterials(baseUrl, list[0].name);
        await loadOutline(baseUrl, list[0].name);
        await loadChapters(baseUrl, list[0].name);
        await loadReviews(baseUrl, list[0].name);
        await loadFullBookReview(baseUrl, list[0].name);
      } else {
        currentProject.value = null;
        setStoredProjectName(null);
        materials.value = [];
        outlineMd.value = "";
        outlineChapters.value = [];
        chapters.value = {};
        chapterStatuses.value = {};
        chapterReviews.value = {};
        fullBookReview.value = null;
        activeRevision.value = null;
      }
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      loadingProjects.value = false;
    }
  }

  async function selectProject(baseUrl: string, projectName: string) {
    if (baseUrl) lastBaseUrl.value = baseUrl;
    const p = projects.value.find((item) => item.name === projectName);
    if (p) {
      currentProject.value = p;
      setStoredProjectName(projectName);
      await loadMaterials(baseUrl, projectName);
      await loadOutline(baseUrl, projectName);
      await loadChapters(baseUrl, projectName);
      await loadReviews(baseUrl, projectName);
      await loadFullBookReview(baseUrl, projectName);
    }
  }

  async function createProject(baseUrl: string, name: string): Promise<ProjectOut> {
    if (!baseUrl) throw new Error("引擎未就绪");
    lastBaseUrl.value = baseUrl;
    error.value = null;
    try {
      if (typeof localStorage !== "undefined") {
        try {
          localStorage.removeItem(getOutlineStorageKey(name));
          localStorage.removeItem(getChaptersStorageKey(name));
          localStorage.removeItem(getReviewsStorageKey(name));
          localStorage.removeItem(getFullReviewStorageKey(name));
        } catch {
          // ignore
        }
      }
      materials.value = [];
      outlineMd.value = "";
      outlineChapters.value = [];
      chapters.value = {};
      chapterStatuses.value = {};
      chapterReviews.value = {};
      fullBookReview.value = null;
      activeRevision.value = null;

      const created = await engineApi.createProject(baseUrl, name);
      await loadProjects(baseUrl);
      await selectProject(baseUrl, created.name);
      return created;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    }
  }

  async function deleteProject(baseUrl: string, name: string): Promise<void> {
    if (!baseUrl) throw new Error("引擎未就绪");
    lastBaseUrl.value = baseUrl;
    error.value = null;
    try {
      await engineApi.deleteProject(baseUrl, name);
      if (typeof localStorage !== "undefined") {
        try {
          localStorage.removeItem(getOutlineStorageKey(name));
          localStorage.removeItem(getChaptersStorageKey(name));
          localStorage.removeItem(getReviewsStorageKey(name));
          localStorage.removeItem(getFullReviewStorageKey(name));
        } catch {
          // ignore
        }
      }
      if (currentProject.value?.name === name) {
        currentProject.value = null;
        setStoredProjectName(null);
        materials.value = [];
        outlineMd.value = "";
        outlineChapters.value = [];
        chapters.value = {};
        chapterStatuses.value = {};
        chapterReviews.value = {};
        fullBookReview.value = null;
        activeRevision.value = null;
      }
      await loadProjects(baseUrl);
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    }
  }

  async function loadMaterials(baseUrl: string, projectName?: string): Promise<MaterialOut[]> {
    const targetName = projectName || currentProject.value?.name;
    if (!baseUrl || !targetName) {
      materials.value = [];
      return [];
    }
    loadingMaterials.value = true;
    error.value = null;
    try {
      const list = await engineApi.listMaterials(baseUrl, targetName);
      materials.value = list;
      return list;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      loadingMaterials.value = false;
    }
  }

  async function ingestFiles(
    baseUrl: string,
    filePaths: string[],
    projectName?: string,
  ): Promise<IngestResult[]> {
    const targetName = projectName || currentProject.value?.name;
    if (!baseUrl || !targetName) {
      throw new Error("请先选择项目");
    }
    if (!filePaths || filePaths.length === 0) {
      return [];
    }
    ingesting.value = true;
    error.value = null;
    try {
      const results = await engineApi.ingestMaterials(baseUrl, targetName, filePaths);
      await loadMaterials(baseUrl, targetName);
      return results;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      ingesting.value = false;
    }
  }

  async function deleteMaterial(
    baseUrl: string,
    sourceId: string,
    projectName?: string,
  ): Promise<void> {
    const targetName = projectName || currentProject.value?.name;
    if (!baseUrl || !targetName) {
      throw new Error("请先选择项目");
    }
    error.value = null;
    try {
      await engineApi.deleteMaterial(baseUrl, targetName, sourceId);
      await loadMaterials(baseUrl, targetName);
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    }
  }

  async function scanMaterials(
    baseUrl: string,
    projectName?: string,
  ): Promise<IngestResult[]> {
    const targetName = projectName || currentProject.value?.name;
    if (!baseUrl || !targetName) {
      throw new Error("请先选择项目");
    }
    ingesting.value = true;
    error.value = null;
    try {
      const results = await engineApi.scanMaterials(baseUrl, targetName);
      await loadMaterials(baseUrl, targetName);
      return results;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      ingesting.value = false;
    }
  }

  async function checkGenericStatus(baseUrl: string): Promise<GenericStatus> {
    if (!baseUrl) {
      genericStatus.value = null;
      return { installed: false };
    }
    try {
      const status = await engineApi.getGenericStatus(baseUrl);
      genericStatus.value = status;
      return status;
    } catch (e) {
      genericStatus.value = { installed: false };
      return { installed: false };
    }
  }

  async function updateGeneric(
    baseUrl: string,
    serverUrl: string,
    token: string,
  ): Promise<GenericUpdateResult> {
    if (!baseUrl) throw new Error("引擎未就绪");
    updatingGeneric.value = true;
    error.value = null;
    try {
      const res = await engineApi.updateGenericKnowledge(baseUrl, serverUrl, token);
      await checkGenericStatus(baseUrl);
      return res;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      updatingGeneric.value = false;
    }
  }

  async function loadTemplates(baseUrl: string): Promise<TemplateItem[]> {
    if (!baseUrl) return [];
    loadingTemplates.value = true;
    error.value = null;
    try {
      const list = await engineApi.getTemplates(baseUrl);
      templates.value = list;
      if (list.length > 0 && !list.find((t) => t.report_type === reportType.value)) {
        reportType.value = list[0].report_type;
      }
      return list;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      loadingTemplates.value = false;
    }
  }

  async function generateOutline(
    baseUrl: string,
    llmConfig: LLMConfig,
    reportTypeOverride?: string,
    projectNameOverride?: string,
  ): Promise<OutlineResult> {
    if (baseUrl) lastBaseUrl.value = baseUrl;
    const targetProject =
      projectNameOverride !== undefined
        ? projectNameOverride
        : currentProject.value?.name || "";
    const targetType = reportTypeOverride || reportType.value;
    if (!baseUrl) throw new Error("引擎未就绪");
    if (!targetType) throw new Error("请先选择报告类型");

    generatingOutline.value = true;
    error.value = null;
    try {
      const res = await engineApi.generateOutline(baseUrl, {
        project: targetProject,
        report_type: targetType,
        llm_config: llmConfig,
      });
      outlineMd.value = res.outline_md;
      outlineChapters.value = res.chapters;
      if (targetProject) {
        await saveOutline(baseUrl, targetProject);
      }
      return res;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      generatingOutline.value = false;
    }
  }

  async function loadOutline(
    baseUrl?: string,
    projectName?: string,
  ): Promise<OutlineResult | null> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = projectName || currentProject.value?.name;
    if (!targetName) {
      outlineMd.value = "";
      outlineChapters.value = [];
      return null;
    }

    let loaded = false;
    if (targetUrl) {
      try {
        const res = await engineApi.getProjectOutline(targetUrl, targetName);
        if (
          res &&
          (res.outline_md || res.report_type || (res.chapters && res.chapters.length > 0))
        ) {
          outlineMd.value = res.outline_md || "";
          outlineChapters.value =
            res.chapters && res.chapters.length > 0
              ? res.chapters
              : parseChaptersFromOutline(res.outline_md || "");
          if (res.report_type) {
            reportType.value = res.report_type;
          }
          saveOutlineToLocal(targetName, {
            report_type: reportType.value,
            outline_md: outlineMd.value,
            chapters: outlineChapters.value,
            updated_at: res.updated_at,
          });
          loaded = true;
          return {
            outline_md: outlineMd.value,
            chapters: outlineChapters.value,
          };
        }
      } catch (e) {
        // engine call failed, fallback to local storage
      }
    }

    if (!loaded) {
      const local = loadOutlineFromLocal(targetName);
      if (local) {
        if (local.report_type) {
          reportType.value = local.report_type;
        }
        outlineMd.value = local.outline_md || "";
        outlineChapters.value =
          local.chapters && local.chapters.length > 0
            ? local.chapters
            : parseChaptersFromOutline(local.outline_md || "");
        return {
          outline_md: outlineMd.value,
          chapters: outlineChapters.value,
        };
      } else {
        outlineMd.value = "";
        outlineChapters.value = [];
      }
    }
    return null;
  }

  async function saveOutline(baseUrl?: string, projectName?: string): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = projectName || currentProject.value?.name;
    if (!targetName) return;

    const payload = {
      report_type: reportType.value,
      outline_md: outlineMd.value,
      chapters: outlineChapters.value,
      updated_at: new Date().toISOString(),
    };

    saveOutlineToLocal(targetName, payload);

    if (targetUrl) {
      try {
        await engineApi.saveProjectOutline(targetUrl, targetName, payload);
      } catch (e) {
        // non-fatal error
      }
    }
  }

  function triggerAutoSaveOutline(baseUrl?: string, projectName?: string, delayMs = 300) {
    const targetName = projectName || currentProject.value?.name;
    if (!targetName) return;

    saveOutlineToLocal(targetName, {
      report_type: reportType.value,
      outline_md: outlineMd.value,
      chapters: outlineChapters.value,
      updated_at: new Date().toISOString(),
    });

    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    debounceTimer = setTimeout(() => {
      saveOutline(baseUrl, targetName).catch(() => {});
    }, delayMs);
  }

  function setOutlineMd(md: string, baseUrl?: string) {
    outlineMd.value = md;
    outlineChapters.value = parseChaptersFromOutline(md);
    triggerAutoSaveOutline(baseUrl);
  }

  function setReportType(type: string, baseUrl?: string) {
    reportType.value = type;
    triggerAutoSaveOutline(baseUrl);
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

    let loaded = false;
    if (targetUrl) {
      try {
        const res = await engineApi.getProjectChapters(targetUrl, targetName);
        if (res && res.chapters) {
          const newChaps: Record<number, string> = {};
          const newStatuses: Record<number, "idle" | "writing" | "completed" | "error"> = {};
          for (const [k, v] of Object.entries(res.chapters)) {
            const seq = Number(k);
            if (!isNaN(seq)) {
              newChaps[seq] = v;
              newStatuses[seq] = v.trim().length > 0 ? "completed" : "idle";
            }
          }
          chapters.value = newChaps;
          chapterStatuses.value = newStatuses;
          saveChaptersToLocal(targetName, newChaps);
          loaded = true;
          return newChaps;
        }
      } catch {
        // fallback to local
      }
    }

    if (!loaded) {
      const local = loadChaptersFromLocal(targetName);
      if (local) {
        chapters.value = local;
        const newStatuses: Record<number, "idle" | "writing" | "completed" | "error"> = {};
        for (const [seqStr, v] of Object.entries(local)) {
          const seq = Number(seqStr);
          newStatuses[seq] = v.trim().length > 0 ? "completed" : "idle";
        }
        chapterStatuses.value = newStatuses;
        return local;
      } else {
        chapters.value = {};
        chapterStatuses.value = {};
      }
    }
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
        // non-fatal
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
          // ignore
        }
      }
    }
  }

  function selectChapter(seq: number) {
    selectedChapterSeq.value = seq;
  }

  function stopWriting() {
    batchWriting.value = false;
    if (progressTimer) {
      clearInterval(progressTimer);
      progressTimer = null;
    }
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
    if (progressTimer) {
      clearInterval(progressTimer);
      progressTimer = null;
    }

    selectedChapterSeq.value = seq;
    currentWritingSeq.value = seq;
    chapterStatuses.value[seq] = "writing";
    chapters.value[seq] = "";
    writingProgress.value = {
      seq,
      stage: "rag",
      message: "🔍 正在双源检索工程底稿与标准规程库...",
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

    // 汇总前序章节
    const predecessor_chapters: Record<string, string> = {};
    for (let i = 1; i < seq; i++) {
      if (chapters.value[i]) {
        predecessor_chapters[String(i)] = chapters.value[i];
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
          chapters.value[seq] = (chapters.value[seq] || "") + chunk;
          if (targetName) {
            saveChaptersToLocal(targetName, chapters.value);
          }
        },
        async () => {
          if (progressTimer) {
            clearInterval(progressTimer);
            progressTimer = null;
          }
          writingProgress.value = null;
          chapterStatuses.value[seq] = "completed";
          currentWritingSeq.value = null;
          activeStopWriting = null;
          if (targetName) {
            saveChaptersToLocal(targetName, chapters.value);
            try {
              await engineApi.saveProjectChapter(baseUrl, targetName, seq, chapters.value[seq]);
            } catch {
              // ignore
            }
          }
          resolve();
        },
        (err) => {
          if (progressTimer) {
            clearInterval(progressTimer);
            progressTimer = null;
          }
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
        if (progressTimer) {
          clearInterval(progressTimer);
          progressTimer = null;
        }
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
  ): Promise<void> {
    if (batchWriting.value) return;
    const targetChapters = outlineChapters.value;
    if (targetChapters.length === 0) {
      throw new Error("大纲中暂无章节");
    }

    batchWriting.value = true;
    error.value = null;

    try {
      for (const ch of targetChapters) {
        if (!batchWriting.value) break;
        selectedChapterSeq.value = ch.seq;
        await writeSingleChapterStream(baseUrl, ch.seq, llmConfig);
      }
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      batchWriting.value = false;
      currentWritingSeq.value = null;
    }
  }

  async function openProjectDir(
    baseUrl: string,
    projectName?: string,
  ): Promise<{ path: string }> {
    const targetName = projectName || currentProject.value?.name;
    if (!baseUrl || !targetName) {
      throw new Error("请先选择项目");
    }
    error.value = null;
    try {
      return await engineApi.openProjectDir(baseUrl, targetName);
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    }
  }

  // ── Step 4 专家审阅与修改方法 ──

  async function loadReviews(
    baseUrl?: string,
    projectName?: string,
  ): Promise<Record<number, engineApi.ExpertReviewResult>> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = projectName || currentProject.value?.name;
    if (!targetName) {
      chapterReviews.value = {};
      return {};
    }

    let loaded = false;
    if (targetUrl) {
      try {
        const res = await engineApi.getProjectReviews(targetUrl, targetName);
        if (res && res.reviews) {
          const newReviews: Record<number, engineApi.ExpertReviewResult> = {};
          for (const [k, v] of Object.entries(res.reviews)) {
            const seq = Number(k);
            if (!isNaN(seq) && v) {
              newReviews[seq] = v;
            }
          }
          chapterReviews.value = newReviews;
          saveReviewsToLocal(targetName, newReviews);
          loaded = true;
          return newReviews;
        }
      } catch {
        // fallback
      }
    }

    if (!loaded) {
      const local = loadReviewsFromLocal(targetName);
      if (local) {
        chapterReviews.value = local;
        return local;
      } else {
        chapterReviews.value = {};
      }
    }
    return {};
  }

  async function saveReview(
    baseUrl?: string,
    seq?: number,
    reviewResult?: engineApi.ExpertReviewResult,
  ): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = currentProject.value?.name;
    const targetSeq = seq !== undefined ? seq : selectedChapterSeq.value;
    if (!targetSeq) return;

    if (reviewResult) {
      chapterReviews.value[targetSeq] = reviewResult;
    }

    const currentResult = chapterReviews.value[targetSeq];
    if (!currentResult) return;

    if (targetName) {
      saveReviewsToLocal(targetName, chapterReviews.value);
    }

    if (targetUrl && targetName) {
      try {
        await engineApi.saveProjectReview(targetUrl, targetName, targetSeq, currentResult);
      } catch {
        // non-fatal
      }
    }
  }

  async function deleteReview(baseUrl?: string, seq?: number): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = currentProject.value?.name;
    const targetSeq = seq !== undefined ? seq : selectedChapterSeq.value;

    delete chapterReviews.value[targetSeq];
    if (targetName) {
      saveReviewsToLocal(targetName, chapterReviews.value);
      if (targetUrl) {
        try {
          await engineApi.deleteProjectReview(targetUrl, targetName, targetSeq);
        } catch {
          // ignore
        }
      }
    }
  }

  async function runChapterReview(
    baseUrl: string,
    seq: number,
    mode: "all" | "compliance" | "numeric" | "technical" = "all",
    llmConfig: engineApi.LLMConfig,
  ): Promise<engineApi.ExpertReviewResult> {
    if (baseUrl) lastBaseUrl.value = baseUrl;
    const targetText = chapters.value[seq] || "";
    if (!targetText.trim()) {
      throw new Error(`第 ${seq} 章尚无正文内容，请先在步骤 3 写作该章节`);
    }

    reviewingSeq.value = seq;
    reviewingMode.value = mode;
    error.value = null;

    const titles = outlineChapters.value.find((c) => c.seq === seq);
    const chapterTitle = titles?.title || `第 ${seq} 章`;

    try {
      const res = await engineApi.reviewChapter(baseUrl, {
        chapter_text: targetText,
        report_type: reportType.value,
        chapter_title: chapterTitle,
        mode,
        llm_config: llmConfig,
      });

      const reviewRes = {
        ...res.review,
        updated_at: new Date().toISOString(),
      };

      chapterReviews.value[seq] = reviewRes;
      await saveReview(baseUrl, seq, reviewRes);
      return reviewRes;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      reviewingSeq.value = null;
    }
  }

  async function runChapterRevision(
    baseUrl: string,
    seq: number,
    instruction: string,
    llmConfig: engineApi.LLMConfig,
  ): Promise<string> {
    if (baseUrl) lastBaseUrl.value = baseUrl;
    const originalText = chapters.value[seq] || "";
    if (!originalText.trim()) {
      throw new Error(`第 ${seq} 章尚无正文内容，无法修订`);
    }
    if (!instruction.trim()) {
      throw new Error("请输入修改指令或点击专家建议填入指令");
    }

    revisingSeq.value = seq;
    error.value = null;

    const titles = outlineChapters.value.find((c) => c.seq === seq);
    const chapterTitle = titles?.title || `第 ${seq} 章`;

    try {
      const res = await engineApi.reviseChapter(baseUrl, {
        chapter_text: originalText,
        instruction,
        llm_config: llmConfig,
        chapter_title: chapterTitle,
        report_type: reportType.value,
      });

      activeRevision.value = {
        seq,
        originalText,
        revisedText: res.revised_text,
        instruction,
        createdAt: new Date().toISOString(),
      };

      return res.revised_text;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      revisingSeq.value = null;
    }
  }

  async function applyRevision(baseUrl?: string, seq?: number): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (!activeRevision.value) return;
    const targetSeq = seq !== undefined ? seq : activeRevision.value.seq;
    if (activeRevision.value.seq !== targetSeq) return;

    const newText = activeRevision.value.revisedText;
    chapters.value[targetSeq] = newText;
    await saveChapter(targetUrl, targetSeq, newText, true);

    activeRevision.value = null;
  }

  const batchReviewing = ref<boolean>(false);

  async function runAllChaptersReview(
    baseUrl: string,
    llmConfig: engineApi.LLMConfig,
    forceAll = false,
  ): Promise<void> {
    if (baseUrl) lastBaseUrl.value = baseUrl;
    if (!baseUrl) throw new Error("引擎未就绪");

    const targetChapters = outlineChapters.value.filter((ch) => {
      const text = chapters.value[ch.seq];
      const hasContent = text && text.trim().length > 0;
      if (!hasContent) return false;
      if (forceAll) return true;
      return !chapterReviews.value[ch.seq];
    });

    if (targetChapters.length === 0) {
      const completed = outlineChapters.value.filter((ch) => chapters.value[ch.seq]?.trim());
      if (completed.length === 0) {
        throw new Error("暂无可审阅的章节（需先在步骤 3 写作并生成正文）");
      }
      return;
    }

    batchReviewing.value = true;
    error.value = null;

    try {
      for (const ch of targetChapters) {
        if (!batchReviewing.value) break;
        try {
          await runChapterReview(baseUrl, ch.seq, "all", llmConfig);
        } catch {
          // 章节审阅异常不中断批量任务
        }
      }
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      batchReviewing.value = false;
    }
  }

  function stopBatchReview(): void {
    batchReviewing.value = false;
  }

  function discardRevision(): void {
    activeRevision.value = null;
  }

  // ── 全书一体化审阅总档案持久化与审阅 ──

  async function loadFullBookReview(
    baseUrl?: string,
    projectName?: string,
  ): Promise<engineApi.FullReviewData | null> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = projectName || currentProject.value?.name;
    if (!targetName) {
      fullBookReview.value = null;
      return null;
    }

    let loaded = false;
    if (targetUrl) {
      try {
        const res = await engineApi.getProjectFullReview(targetUrl, targetName);
        if (
          res &&
          (res.summary ||
            (res.issues && res.issues.length > 0) ||
            (res.numerical_checks && res.numerical_checks.length > 0) ||
            (res.chapter_evaluations && Object.keys(res.chapter_evaluations).length > 0))
        ) {
          fullBookReview.value = res;
          saveFullReviewToLocal(targetName, res);
          loaded = true;
          return res;
        }
      } catch {
        // fallback
      }
    }

    if (!loaded) {
      const local = loadFullReviewFromLocal(targetName);
      if (local) {
        fullBookReview.value = local;
        return local;
      } else {
        fullBookReview.value = null;
      }
    }
    return fullBookReview.value;
  }

  async function saveFullBookReview(
    baseUrl?: string,
    data?: engineApi.FullReviewData,
  ): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = currentProject.value?.name;
    if (!targetName) return;

    if (data) {
      fullBookReview.value = data;
    }

    const currentData = fullBookReview.value;
    if (!currentData) return;

    saveFullReviewToLocal(targetName, currentData);

    if (targetUrl) {
      try {
        await engineApi.saveProjectFullReview(targetUrl, targetName, currentData);
      } catch {
        // non-fatal
      }
    }
  }

  async function deleteFullBookReview(baseUrl?: string): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = currentProject.value?.name;
    if (!targetName) return;

    fullBookReview.value = null;
    try {
      if (typeof localStorage !== "undefined") {
        localStorage.removeItem(getFullReviewStorageKey(targetName));
      }
    } catch {
      // ignore
    }

    if (targetUrl) {
      try {
        await engineApi.deleteProjectFullReview(targetUrl, targetName);
      } catch {
        // ignore
      }
    }
  }

  async function runFullBookReview(
    baseUrl: string,
    llmConfig: engineApi.LLMConfig,
    forceAll = false,
  ): Promise<engineApi.FullReviewData> {
    if (baseUrl) lastBaseUrl.value = baseUrl;
    if (!baseUrl) throw new Error("引擎未就绪");

    const targetChapters = outlineChapters.value.filter((ch) => {
      const text = chapters.value[ch.seq];
      return text && text.trim().length > 0;
    });

    if (targetChapters.length === 0) {
      throw new Error("暂无可审阅的章节（需先在步骤 3 写作并生成正文）");
    }

    batchReviewing.value = true;
    error.value = null;

    try {
      for (const ch of targetChapters) {
        if (!batchReviewing.value) break;
        if (forceAll || !chapterReviews.value[ch.seq]) {
          try {
            await runChapterReview(baseUrl, ch.seq, "all", llmConfig);
          } catch {
            // 章节审阅异常不中断
          }
        }
      }

      const allIssues: engineApi.ReviewIssue[] = [];
      const allNumerical: engineApi.NumericalCheckItem[] = [];
      const allGaps: (string | { chapterSeq?: number; chapterTitle?: string; gap: string })[] = [];
      const chapterEvals: Record<
        string,
        {
          status: string;
          summary: string;
          issues_count: number;
          score?: number;
        }
      > = {};

      let passedCount = 0;
      let warningCount = 0;

      for (const ch of outlineChapters.value) {
        const rev = chapterReviews.value[ch.seq];
        if (rev) {
          if (rev.status === "通过") passedCount++;
          if (rev.status === "需补充" || rev.status === "风险警告") warningCount++;

          if (rev.issues && rev.issues.length > 0) {
            for (const iss of rev.issues) {
              allIssues.push({
                ...iss,
                location: iss.location || `第 ${ch.seq} 章 ${ch.title}`,
              });
            }
          }
          if (rev.numerical_checks && rev.numerical_checks.length > 0) {
            for (const nc of rev.numerical_checks) {
              allNumerical.push({
                ...nc,
                note: nc.note ? `${nc.note} (第 ${ch.seq} 章)` : `来自第 ${ch.seq} 章`,
              });
            }
          }
          if (rev.data_gap_checklist && rev.data_gap_checklist.length > 0) {
            for (const g of rev.data_gap_checklist) {
              allGaps.push({
                chapterSeq: ch.seq,
                chapterTitle: ch.title,
                gap: g,
              });
            }
          }
          chapterEvals[String(ch.seq)] = {
            status: rev.status || "通过",
            summary: rev.summary || "",
            issues_count: rev.issues?.length || 0,
            score: rev.score,
          };
        } else {
          chapterEvals[String(ch.seq)] = {
            status: "未生成",
            summary: "该章节尚无正文或未执行审阅",
            issues_count: 0,
          };
        }
      }

      const totalTarget = targetChapters.length;
      const complianceRate =
        totalTarget > 0
          ? Math.max(0, Math.min(100, Math.round((passedCount / totalTarget) * 100)))
          : 100;
      const healthStatus =
        warningCount === 0 && allIssues.length === 0
          ? "达标"
          : warningCount > 2 ||
            allIssues.some(
              (i) =>
                i.severity === "error" ||
                (i.severity as string) === "danger" ||
                (i.severity as string) === "high",
            )
          ? "存在重大缺陷"
          : "待完善";

      const summary = `全书共 ${outlineChapters.value.length} 章（已审阅 ${totalTarget} 章），发现 ${allIssues.length} 处待优化问题与 ${allGaps.length} 处资料缺口。整体合规与数据自洽达标度为 ${complianceRate}%，健康评估状态为「${healthStatus}」。`;

      const generalSuggestions = [
        "1. 严格对照发改委与行业工程编制规程，核对前后章节投资估算与建设规模数据自洽性；",
        "2. 补充完善缺失的附表、附图与前置审批支撑性底稿；",
        "3. 针对高亮批注与数据疑点小节进行专项润色与 AI 修订。",
      ];

      const fullData: engineApi.FullReviewData = {
        summary,
        compliance_rate: complianceRate,
        health_status: healthStatus,
        issues: allIssues,
        numerical_checks: allNumerical,
        data_gap_checklist: allGaps,
        chapter_evaluations: chapterEvals,
        general_suggestions: generalSuggestions,
        updated_at: new Date().toISOString(),
      };

      fullBookReview.value = fullData;
      await saveFullBookReview(baseUrl, fullData);
      return fullData;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      batchReviewing.value = false;
    }
  }

  return {
    currentStep,
    projects,
    currentProject,
    materials,
    genericStatus,
    reportType,
    templates,
    loadingTemplates,
    outlineMd,
    outlineChapters,
    generatingOutline,
    chapters,
    chapterStatuses,
    selectedChapterSeq,
    batchWriting,
    currentWritingSeq,
    writingProgress,
    chapterReviews,
    fullBookReview,
    reviewingSeq,
    reviewingMode,
    batchReviewing,
    revisingSeq,
    activeRevision,
    lastBaseUrl,
    loadingProjects,
    loadingMaterials,
    ingesting,
    updatingGeneric,
    error,
    setStep,
    loadProjects,
    selectProject,
    createProject,
    deleteProject,
    loadMaterials,
    ingestFiles,
    scanMaterials,
    openProjectDir,
    deleteMaterial,
    checkGenericStatus,
    updateGeneric,
    loadTemplates,
    generateOutline,
    loadOutline,
    saveOutline,
    setOutlineMd,
    setReportType,
    loadChapters,
    saveChapter,
    deleteChapter,
    selectChapter,
    writeSingleChapterStream,
    writeAllChapters,
    stopWriting,
    loadReviews,
    saveReview,
    deleteReview,
    runChapterReview,
    runAllChaptersReview,
    stopBatchReview,
    runChapterRevision,
    applyRevision,
    discardRevision,
    loadFullBookReview,
    saveFullBookReview,
    deleteFullBookReview,
    runFullBookReview,
  };
});


