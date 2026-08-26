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
  let activeStopWriting: (() => void) | null = null;
  const chapterDebounceTimers: Record<number, ReturnType<typeof setTimeout>> = {};

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
        } else if (list.length > 0) {
          currentProject.value = list[0];
          setStoredProjectName(list[0].name);
          await loadMaterials(baseUrl, list[0].name);
          await loadOutline(baseUrl, list[0].name);
          await loadChapters(baseUrl, list[0].name);
        } else {
          currentProject.value = null;
          setStoredProjectName(null);
          materials.value = [];
          outlineMd.value = "";
          outlineChapters.value = [];
          chapters.value = {};
          chapterStatuses.value = {};
        }
      } else if (list.length > 0) {
        currentProject.value = list[0];
        setStoredProjectName(list[0].name);
        await loadMaterials(baseUrl, list[0].name);
        await loadOutline(baseUrl, list[0].name);
        await loadChapters(baseUrl, list[0].name);
      } else {
        currentProject.value = null;
        setStoredProjectName(null);
        materials.value = [];
        outlineMd.value = "";
        outlineChapters.value = [];
        chapters.value = {};
        chapterStatuses.value = {};
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
    }
  }

  async function createProject(baseUrl: string, name: string): Promise<ProjectOut> {
    if (!baseUrl) throw new Error("引擎未就绪");
    lastBaseUrl.value = baseUrl;
    error.value = null;
    try {
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

    selectedChapterSeq.value = seq;
    currentWritingSeq.value = seq;
    chapterStatuses.value[seq] = "writing";
    chapters.value[seq] = "";
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
          chapterStatuses.value[seq] = "error";
          currentWritingSeq.value = null;
          activeStopWriting = null;
          error.value = err.message;
          reject(err);
        },
      );

      activeStopWriting = () => {
        stop();
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
  };
});

