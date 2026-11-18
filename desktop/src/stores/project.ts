import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as engineApi from "../lib/engineApi";
import type {
  ChapterInfo,
  GenericStatus,
  MaterialOut,
  ProjectOut,
  TemplateItem,
} from "../lib/engineApi";
import {
  clearProjectLocalStorage,
  deriveDefaultWritingOrder,
  getChaptersStorageKey,
  getFullReviewStorageKey,
  getOutlineStorageKey,
  getReviewsStorageKey,
  getStoredProjectName,
  getStoredStep,
  getWritingOrderStorageKey,
  loadChaptersFromLocal,
  loadFullReviewFromLocal,
  loadOutlineFromLocal,
  loadReviewsFromLocal,
  loadWritingOrderFromLocal,
  parseChaptersFromOutline,
  saveChaptersToLocal,
  saveFullReviewToLocal,
  saveOutlineToLocal,
  saveReviewsToLocal,
  saveWritingOrderToLocal,
  setStoredProjectName,
  setStoredStep,
} from "./projectStorage";
import { createMaterialsSlice } from "./slices/materialsSlice";
import { createOutlineSlice } from "./slices/outlineSlice";
import { createReviewSlice } from "./slices/reviewSlice";
import { createWritingSlice } from "./slices/writingSlice";
import type {
  ActiveRevisionRecord,
  ChapterRevisionProgress,
  ChapterRunStatus,
  ChapterWritingProgress,
  ProjectStoreState,
  ReviewMode,
  ReviewProgress,
} from "./slices/types";

export {
  deriveDefaultWritingOrder,
  getChaptersStorageKey,
  getFullReviewStorageKey,
  getOutlineStorageKey,
  getReviewsStorageKey,
  getWritingOrderStorageKey,
  loadChaptersFromLocal,
  loadFullReviewFromLocal,
  loadOutlineFromLocal,
  loadReviewsFromLocal,
  loadWritingOrderFromLocal,
  parseChaptersFromOutline,
  saveChaptersToLocal,
  saveFullReviewToLocal,
  saveOutlineToLocal,
  saveReviewsToLocal,
  saveWritingOrderToLocal,
};

export type { ChapterRevisionProgress, ChapterWritingProgress, ReviewProgress };

export const useProjectStore = defineStore("project", () => {
  const currentStep = ref<number>(getStoredStep());
  const projects = ref<ProjectOut[]>([]);
  const currentProject = ref<ProjectOut | null>(null);
  const materials = ref<MaterialOut[]>([]);
  const genericStatus = ref<GenericStatus | null>(null);

  const reportType = ref<string>("可行性研究报告");
  const templates = ref<TemplateItem[]>([]);
  const loadingTemplates = ref<boolean>(false);
  const outlineMd = ref<string>("");
  const outlineChapters = ref<ChapterInfo[]>([]);
  const writingOrder = ref<number[]>([]);
  const writingOrderReason = ref<string>("");
  const generatingOutline = ref<boolean>(false);

  const chapters = ref<Record<number, string>>({});
  const chapterStatuses = ref<Record<number, ChapterRunStatus>>({});
  const selectedChapterSeq = ref<number>(1);
  const batchWriting = ref<boolean>(false);
  const currentWritingSeq = ref<number | null>(null);
  const writingProgress = ref<ChapterWritingProgress | null>(null);

  const chapterReviews = ref<Record<number, engineApi.ExpertReviewResult>>({});
  const fullBookReview = ref<engineApi.FullReviewData | null>(null);
  const reviewingSeq = ref<number | null>(null);
  const reviewingMode = ref<ReviewMode>("fast");
  const batchReviewing = ref<boolean>(false);
  const reviewProgress = ref<ReviewProgress | null>(null);
  const revisingSeq = ref<number | null>(null);
  const revisingIssueId = ref<string | null>(null);
  const revisionProgress = ref<ChapterRevisionProgress | null>(null);
  const chapterSnapshots = ref<Record<number, string>>({});
  const activeRevision = ref<ActiveRevisionRecord | null>(null);

  const lastBaseUrl = ref<string>("");
  const loadingProjects = ref<boolean>(false);
  const loadingMaterials = ref<boolean>(false);
  const ingesting = ref<boolean>(false);
  const updatingGeneric = ref<boolean>(false);
  const error = ref<string | null>(null);

  const isWritingAnyChapter = computed(() => {
    return (
      currentWritingSeq.value !== null ||
      batchWriting.value ||
      writingProgress.value !== null ||
      Object.values(chapterStatuses.value).some((s) => s === "writing")
    );
  });

  const state: ProjectStoreState = {
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
    writingOrder,
    writingOrderReason,
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
    reviewProgress,
    revisingSeq,
    revisingIssueId,
    revisionProgress,
    chapterSnapshots,
    activeRevision,
    lastBaseUrl,
    loadingProjects,
    loadingMaterials,
    ingesting,
    updatingGeneric,
    error,
    isWritingAnyChapter,
  };

  const materialsSlice = createMaterialsSlice(state);
  const outlineSlice = createOutlineSlice(state);
  const writingSlice = createWritingSlice(state);
  const reviewSlice = createReviewSlice(state, writingSlice.saveChapter);

  function resetActiveProjectData() {
    materials.value = [];
    outlineMd.value = "";
    outlineChapters.value = [];
    writingOrder.value = [];
    writingOrderReason.value = "";
    chapters.value = {};
    chapterStatuses.value = {};
    chapterReviews.value = {};
    fullBookReview.value = null;
    activeRevision.value = null;
  }

  async function hydrateActiveProject(baseUrl: string, project: ProjectOut) {
    currentProject.value = project;
    setStoredProjectName(project.name);
    await materialsSlice.loadMaterials(baseUrl, project.name);
    await outlineSlice.loadOutline(baseUrl, project.name);
    await writingSlice.loadChapters(baseUrl, project.name);
    await reviewSlice.loadReviews(baseUrl, project.name);
    await reviewSlice.loadFullBookReview(baseUrl, project.name);
  }

  function setStep(step: number) {
    if (step >= 1 && step <= 5) {
      if (isWritingAnyChapter.value && step !== 3) {
        return;
      }
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

      const targetName = currentProject.value?.name || getStoredProjectName();
      const targetProj =
        (targetName ? list.find((p) => p.name === targetName) : undefined) || list[0];

      if (targetProj) {
        await hydrateActiveProject(baseUrl, targetProj);
      } else {
        currentProject.value = null;
        setStoredProjectName(null);
        resetActiveProjectData();
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
      await hydrateActiveProject(baseUrl, p);
    }
  }

  async function createProject(baseUrl: string, name: string): Promise<ProjectOut> {
    if (!baseUrl) throw new Error("引擎未就绪");
    lastBaseUrl.value = baseUrl;
    error.value = null;
    try {
      clearProjectLocalStorage(name);
      resetActiveProjectData();
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
      clearProjectLocalStorage(name);
      if (currentProject.value?.name === name) {
        currentProject.value = null;
        setStoredProjectName(null);
        resetActiveProjectData();
      }
      await loadProjects(baseUrl);
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    }
  }

  return {
    ...state,
    deriveDefaultWritingOrder,
    setStep,
    loadProjects,
    selectProject,
    createProject,
    deleteProject,
    ...materialsSlice,
    ...outlineSlice,
    ...writingSlice,
    ...reviewSlice,
  };
});
