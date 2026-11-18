import type { ComputedRef, Ref } from "vue";
import type * as engineApi from "../../lib/engineApi";
import type {
  ChapterInfo,
  GenericStatus,
  MaterialOut,
  ProjectOut,
  TemplateItem,
} from "../../lib/engineApi";

export type ChapterRunStatus = "idle" | "writing" | "completed" | "error";
export type ReviewMode = "fast" | "all" | "compliance" | "numeric" | "technical";

export interface ChapterWritingProgress {
  seq: number;
  stage: "rag" | "skeleton" | "reasoning" | "writing" | string;
  message: string;
  elapsedSeconds: number;
  thoughtText: string;
}

export interface ReviewProgress {
  currentSeq: number;
  currentTitle: string;
  currentIndex: number;
  totalTarget: number;
  percent: number;
  elapsedSeconds: number;
  thoughtText: string;
  completedIssuesCount: number;
}

export interface ChapterRevisionProgress {
  seq: number;
  stage: string;
  message: string;
  elapsedSeconds: number;
  thoughtText: string;
}

export interface ActiveRevisionRecord {
  seq: number;
  originalText: string;
  revisedText: string;
  instruction: string;
  createdAt: string;
}

export interface ProjectStoreState {
  currentStep: Ref<number>;
  projects: Ref<ProjectOut[]>;
  currentProject: Ref<ProjectOut | null>;
  materials: Ref<MaterialOut[]>;
  genericStatus: Ref<GenericStatus | null>;

  reportType: Ref<string>;
  templates: Ref<TemplateItem[]>;
  loadingTemplates: Ref<boolean>;
  outlineMd: Ref<string>;
  outlineChapters: Ref<ChapterInfo[]>;
  writingOrder: Ref<number[]>;
  writingOrderReason: Ref<string>;
  generatingOutline: Ref<boolean>;

  chapters: Ref<Record<number, string>>;
  chapterStatuses: Ref<Record<number, ChapterRunStatus>>;
  selectedChapterSeq: Ref<number>;
  batchWriting: Ref<boolean>;
  currentWritingSeq: Ref<number | null>;
  writingProgress: Ref<ChapterWritingProgress | null>;

  chapterReviews: Ref<Record<number, engineApi.ExpertReviewResult>>;
  fullBookReview: Ref<engineApi.FullReviewData | null>;
  reviewingSeq: Ref<number | null>;
  reviewingMode: Ref<ReviewMode>;
  batchReviewing: Ref<boolean>;
  reviewProgress: Ref<ReviewProgress | null>;
  revisingSeq: Ref<number | null>;
  revisingIssueId: Ref<string | null>;
  revisionProgress: Ref<ChapterRevisionProgress | null>;
  chapterSnapshots: Ref<Record<number, string>>;
  activeRevision: Ref<ActiveRevisionRecord | null>;

  lastBaseUrl: Ref<string>;
  loadingProjects: Ref<boolean>;
  loadingMaterials: Ref<boolean>;
  ingesting: Ref<boolean>;
  updatingGeneric: Ref<boolean>;
  error: Ref<string | null>;
  isWritingAnyChapter: ComputedRef<boolean>;
}
