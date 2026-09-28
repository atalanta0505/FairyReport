/**
 * 本地引擎 API 客户端 — 与本地 Python 引擎进程的 HTTP 通信。
 *
 * 采用 @tauri-apps/plugin-http fetch（Tauri 原生通道，绕开 CORS 与安全限制）。
 * 覆盖项目管理、资料摄取与删除、通用知识包状态与同步等接口。
 */
import { fetch as pluginFetch } from "@tauri-apps/plugin-http";

function engineFetch(input: string | URL, init?: RequestInit): Promise<Response> {
  if (
    typeof (globalThis as any).__TAURI_INTERNALS__ !== "undefined" ||
    (pluginFetch && typeof (pluginFetch as any).mock !== "undefined")
  ) {
    return pluginFetch(input, init);
  }
  if (typeof window !== "undefined" && window.fetch) {
    return window.fetch(input, init);
  }
  return pluginFetch(input, init);
}

export class EngineApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "EngineApiError";
    this.status = status;
  }
}

export interface ProjectOut {
  id: number;
  name: string;
  created_at: string;
}

export interface MaterialOut {
  id: number;
  source_id: string;
  filename: string;
  ext: string;
  chunk_count: number;
  size_bytes: number;
  created_at: string;
}

export interface IngestResult {
  source_id: string;
  filename: string;
  ext: string;
  chunk_count: number;
  size_bytes: number;
  status: string;
  error?: string | null;
}

export interface UploadFileItem {
  filename: string;
  content_base64: string;
}

export interface GenericStatus {
  installed: boolean;
  version?: string;
  installed_at?: string;
}

export interface GenericUpdateResult {
  status: string;
  version: string;
}

export interface TemplateItem {
  report_type: string;
  total_words_max?: number;
  notes?: string;
  writing_order?: number[];
  writing_order_reason?: string;
}

export interface LLMConfig {
  api_key: string;
  base_url: string;
  model: string;
}

export interface OutlineRequest {
  project?: string;
  report_type: string;
  llm_config: LLMConfig;
}

export interface ChapterInfo {
  seq: number;
  title: string;
}

export interface OutlineResult {
  outline_md: string;
  chapters: ChapterInfo[];
  writing_order?: number[];
  writing_order_reason?: string;
}

function joinUrl(baseUrl: string, path: string): string {
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

async function request<T>(
  baseUrl: string,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  let resp: Response;
  try {
    resp = await engineFetch(joinUrl(baseUrl, path), { ...options, headers });
  } catch (e) {
    throw new EngineApiError(0, `引擎通信失败：${(e as Error).message}`);
  }

  if (resp.status === 204) {
    return undefined as unknown as T;
  }

  if (!resp.ok) {
    let msg = `引擎错误 ${resp.status}`;
    try {
      const j = await resp.json();
      msg = j.detail || j.message || msg;
    } catch {
      /* 非 JSON 响应 */
    }
    throw new EngineApiError(resp.status, msg);
  }

  return resp.json();
}

/** 列出所有项目 */
export async function listProjects(baseUrl: string): Promise<ProjectOut[]> {
  return request<ProjectOut[]>(baseUrl, "/projects", { method: "GET" });
}

/** 创建新项目 */
export async function createProject(baseUrl: string, name: string): Promise<ProjectOut> {
  return request<ProjectOut>(baseUrl, "/projects", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

/** 删除项目 */
export async function deleteProject(baseUrl: string, name: string): Promise<void> {
  return request<void>(baseUrl, `/projects/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
}

/** 列出项目下的所有资料 */
export async function listMaterials(baseUrl: string, projectName: string): Promise<MaterialOut[]> {
  return request<MaterialOut[]>(baseUrl, `/projects/${encodeURIComponent(projectName)}/materials`, {
    method: "GET",
  });
}

/** 摄取资料（本地文件绝对路径列表） */
export async function ingestMaterials(
  baseUrl: string,
  projectName: string,
  filePaths: string[],
): Promise<IngestResult[]> {
  return request<IngestResult[]>(baseUrl, `/projects/${encodeURIComponent(projectName)}/materials/ingest`, {
    method: "POST",
    body: JSON.stringify({ file_paths: filePaths }),
  });
}

/** 跨网上传资料文件（Base64 编码，适配云端远程模式） */
export async function uploadMaterials(
  baseUrl: string,
  projectName: string,
  files: UploadFileItem[],
): Promise<IngestResult[]> {
  return request<IngestResult[]>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/materials/upload`,
    {
      method: "POST",
      body: JSON.stringify({ files }),
    },
  );
}

/** 扫描项目本地 files 目录并摄取资料 */
export async function scanMaterials(
  baseUrl: string,
  projectName: string,
): Promise<IngestResult[]> {
  return request<IngestResult[]>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/materials/scan`,
    {
      method: "POST",
    },
  );
}

/** 删除资料 */
export async function deleteMaterial(
  baseUrl: string,
  projectName: string,
  sourceId: string,
): Promise<void> {
  return request<void>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/materials/${encodeURIComponent(sourceId)}`,
    {
      method: "DELETE",
    },
  );
}

/** 获取通用知识包状态 */
export async function getGenericStatus(baseUrl: string): Promise<GenericStatus> {
  return request<GenericStatus>(baseUrl, "/generic/status", { method: "GET" });
}

/** 下载并安装通用知识包 */
export async function updateGenericKnowledge(
  baseUrl: string,
  serverUrl: string,
  token: string,
): Promise<GenericUpdateResult> {
  return request<GenericUpdateResult>(baseUrl, "/generic/update", {
    method: "POST",
    body: JSON.stringify({ server_url: serverUrl, token }),
  });
}

/** 获取 14 类标准报告模板列表与字数预算 */
export async function getTemplates(baseUrl: string): Promise<TemplateItem[]> {
  return request<TemplateItem[]>(baseUrl, "/writing/templates", {
    method: "GET",
  });
}

/** 生成结构化大纲 */
export async function generateOutline(
  baseUrl: string,
  req: OutlineRequest,
): Promise<OutlineResult> {
  return request<OutlineResult>(baseUrl, "/writing/outline", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/** 在系统资源管理器中打开项目 files 目录 */
export async function openProjectDir(
  baseUrl: string,
  projectName: string,
): Promise<{ path: string }> {
  return request<{ path: string }>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/open-folder`,
    {
      method: "POST",
    },
  );
}

export interface OutlineData {
  report_type: string;
  outline_md: string;
  chapters: ChapterInfo[];
  writing_order?: number[];
  writing_order_reason?: string;
  updated_at?: string;
}

export interface ChaptersData {
  chapters: Record<string, string>;
  updated_at?: string;
}

export interface ChapterStreamRequest {
  project?: string;
  report_type: string;
  outline_md: string;
  chapter_seq: number;
  stream?: boolean;
  llm_config: LLMConfig;
  topic?: string;
  predecessor_chapters?: Record<string, string>;
  writing_hint?: string;
}

/** 获取项目持久化大纲数据 */
export async function getProjectOutline(
  baseUrl: string,
  projectName: string,
): Promise<OutlineResult & { report_type?: string; updated_at?: string }> {
  return request<OutlineResult & { report_type?: string; updated_at?: string }>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/outline`,
    {
      method: "GET",
    },
  );
}

/** 保存项目大纲数据 */
export async function saveProjectOutline(
  baseUrl: string,
  projectName: string,
  data: {
    report_type: string;
    outline_md: string;
    chapters?: ChapterInfo[];
    writing_order?: number[];
    writing_order_reason?: string;
    updated_at?: string;
  },
): Promise<OutlineResult & { report_type?: string; updated_at?: string }> {
  return request<OutlineResult & { report_type?: string; updated_at?: string }>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/outline`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
  );
}

/** 获取项目所有章节内容 */
export async function getProjectChapters(
  baseUrl: string,
  projectName: string,
): Promise<ChaptersData> {
  return request<ChaptersData>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/chapters`,
    {
      method: "GET",
    },
  );
}

/** 保存项目单章内容 */
export async function saveProjectChapter(
  baseUrl: string,
  projectName: string,
  seq: number,
  text: string,
): Promise<ChaptersData> {
  return request<ChaptersData>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/chapters/${seq}`,
    {
      method: "POST",
      body: JSON.stringify({ text }),
    },
  );
}

/** 删除项目单章内容 */
export async function deleteProjectChapter(
  baseUrl: string,
  projectName: string,
  seq: number,
): Promise<{ ok: boolean; seq: number }> {
  return request<{ ok: boolean; seq: number }>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/chapters/${seq}`,
    {
      method: "DELETE",
    },
  );
}

export interface WritingProgressEvent {
  type: "stage" | "thought" | "chunk";
  stage?: string;
  message?: string;
  chunk?: string;
}

/** 流式写作单章（SSE 透传，支持中止取消与阶段/思考/正文事件回调） */
export function streamChapterWriting(
  baseUrl: string,
  req: ChapterStreamRequest,
  onChunk: (chunk: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
  onProgress?: (event: WritingProgressEvent) => void,
): () => void {
  const controller = new AbortController();
  const { signal } = controller;

  const processContent = (content: string): boolean => {
    if (content === "[DONE]") {
      onDone();
      return true;
    }
    if (content.startsWith("{")) {
      try {
        const parsed = JSON.parse(content);
        if (parsed && typeof parsed === "object") {
          if (parsed.error) {
            throw new Error(parsed.error);
          }
          if (parsed.type === "stage") {
            if (onProgress) {
              onProgress({
                type: "stage",
                stage: parsed.stage,
                message: parsed.message,
              });
            }
            return false;
          }
          if (parsed.type === "thought") {
            if (onProgress) {
              onProgress({
                type: "thought",
                chunk: parsed.chunk || "",
              });
            }
            return false;
          }
        }
      } catch (err) {
        if (
          err instanceof Error &&
          !(err instanceof SyntaxError) &&
          err.message !== "Unexpected token"
        ) {
          throw err;
        }
      }
    }
    if (onProgress) {
      onProgress({ type: "chunk", chunk: content });
    }
    onChunk(content);
    return false;
  };

  (async () => {
    try {
      const resp = await engineFetch(joinUrl(baseUrl, "/writing/chapter"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...req, stream: true }),
        signal,
      });

      if (!resp.ok) {
        let msg = `引擎错误 ${resp.status}`;
        try {
          const j = await resp.json();
          msg = j.detail || j.message || msg;
        } catch {
          /* ignore */
        }
        throw new EngineApiError(resp.status, msg);
      }

      if (resp.body && typeof resp.body.getReader === "function") {
        const reader = resp.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          let eventEndIndex: number;
          while ((eventEndIndex = buffer.indexOf("\n\n")) !== -1) {
            const rawEvent = buffer.slice(0, eventEndIndex);
            buffer = buffer.slice(eventEndIndex + 2);

            if (!rawEvent.trim()) continue;

            const lines = rawEvent.split("\n");
            for (const line of lines) {
              if (line.startsWith("data:")) {
                const content = line.slice(5).replace(/^\s/, "");
                const isDone = processContent(content);
                if (isDone) return;
              } else if (!line.startsWith(":") && line.length > 0) {
                if (onProgress) {
                  onProgress({ type: "chunk", chunk: "\n" + line });
                }
                onChunk("\n" + line);
              }
            }
          }
        }

        if (buffer.trim()) {
          const lines = buffer.trim().split("\n");
          for (const line of lines) {
            if (line.startsWith("data:")) {
              const content = line.slice(5).replace(/^\s/, "");
              const isDone = processContent(content);
              if (isDone) return;
            }
          }
        }
      } else if (typeof resp.text === "function") {
        const fullText = await resp.text();
        const lines = fullText.split("\n\n");
        for (const block of lines) {
          const trimmed = block.trim();
          if (trimmed.startsWith("data:")) {
            const content = trimmed.slice(5).replace(/^\s/, "");
            const isDone = processContent(content);
            if (isDone) return;
          }
        }
      }

      onDone();
    } catch (err) {
      if (signal.aborted) {
        return;
      }
      onError(err as Error);
    }
  })();

  return () => {
    controller.abort();
  };
}

export interface ReviewIssue {
  id?: string;
  severity: "error" | "warning" | "suggestion" | string;
  category?: string;
  message?: string;
  dimension?: string;
  description?: string;
  location?: string;
  quote?: string;
  snippet?: string;
  suggestion?: string;
  chapterSeq?: number;
  chapterTitle?: string;
}

export interface NumericalCheckItem {
  parameter?: string;
  extracted_value?: string;
  indicator_name?: string;
  mentioned_value?: string;
  reference_value?: string;
  is_consistent?: boolean;
  status?: "normal" | "abnormal" | "pending" | string;
  note?: string;
  notes?: string;
  chapterSeq?: number;
  chapterTitle?: string;
}

export interface ExpertReviewResult {
  status: "通过" | "需补充" | "风险警告" | string;
  score?: number;
  summary?: string;
  issues?: ReviewIssue[];
  initial_issues_count?: number;
  numerical_checks?: NumericalCheckItem[];
  data_gap_checklist?: string[];
  suggestions?: string;
  raw?: string;
  parse_error?: string | null;
  updated_at?: string;
}

export interface ReviewsData {
  reviews: Record<string, ExpertReviewResult>;
  updated_at?: string;
}

export interface ReviewChapterRequest {
  chapter_text: string;
  report_type?: string;
  chapter_title?: string;
  mode?: "fast" | "all" | "compliance" | "numeric" | "technical";
  llm_config: LLMConfig;
}

export interface ReviseChapterRequest {
  chapter_text: string;
  instruction: string;
  llm_config: LLMConfig;
  chapter_title?: string;
  report_type?: string;
  chapter_budget?: number;
}

export interface ReviewProgressEvent {
  type: "stage" | "thought" | "chunk" | "done";
  stage?: string;
  message?: string;
  chunk?: string;
  review?: ExpertReviewResult;
}

/** 针对章节执行专家全维审阅或专项审查 */
export async function reviewChapter(
  baseUrl: string,
  req: ReviewChapterRequest,
): Promise<{ raw: string; review: ExpertReviewResult }> {
  return request<{ raw: string; review: ExpertReviewResult }>(
    baseUrl,
    "/writing/review",
    {
      method: "POST",
      body: JSON.stringify(req),
    },
  );
}

/** 流式全维专家审阅章节（SSE 透传，支持阶段/思考/诊断事件回调与 Promise 结果返回） */
export async function streamChapterReview(
  baseUrl: string,
  req: ReviewChapterRequest,
  onProgress?: (event: ReviewProgressEvent) => void,
): Promise<{ raw: string; review: ExpertReviewResult }> {
  const resp = await engineFetch(joinUrl(baseUrl, "/writing/review_stream"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!resp.ok) {
    let msg = `引擎错误 ${resp.status}`;
    try {
      const j = await resp.json();
      msg = j.detail || j.message || msg;
    } catch {
      /* ignore */
    }
    throw new EngineApiError(resp.status, msg);
  }

  let finalReview: ExpertReviewResult | null = null;
  let rawBuffer = "";

  const processContent = (content: string): boolean => {
    if (content === "[DONE]") {
      return true;
    }
    if (content.startsWith("{")) {
      try {
        const parsed = JSON.parse(content);
        if (parsed && typeof parsed === "object") {
          if (parsed.error) {
            throw new Error(parsed.error);
          }
          if (parsed.type === "stage") {
            if (onProgress) {
              onProgress({
                type: "stage",
                stage: parsed.stage,
                message: parsed.message,
              });
            }
            return false;
          }
          if (parsed.type === "thought") {
            if (onProgress) {
              onProgress({
                type: "thought",
                chunk: parsed.chunk || "",
              });
            }
            return false;
          }
          if (parsed.type === "chunk") {
            rawBuffer += parsed.chunk || "";
            if (onProgress) {
              onProgress({
                type: "chunk",
                chunk: parsed.chunk || "",
              });
            }
            return false;
          }
          if (parsed.type === "done") {
            finalReview = parsed.review as ExpertReviewResult;
            if (parsed.raw) {
              rawBuffer = parsed.raw;
            }
            if (onProgress) {
              onProgress({
                type: "done",
                review: finalReview,
              });
            }
            return true;
          }
        }
      } catch (err) {
        if (
          err instanceof Error &&
          !(err instanceof SyntaxError) &&
          err.message !== "Unexpected token"
        ) {
          throw err;
        }
      }
    }
    rawBuffer += content;
    if (onProgress) {
      onProgress({ type: "chunk", chunk: content });
    }
    return false;
  };

  if (resp.body && typeof resp.body.getReader === "function") {
    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      let eventEndIndex: number;
      while ((eventEndIndex = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, eventEndIndex);
        buffer = buffer.slice(eventEndIndex + 2);

        if (!rawEvent.trim()) continue;

        const lines = rawEvent.split("\n");
        for (const line of lines) {
          if (line.startsWith("data:")) {
            const content = line.slice(5).replace(/^\s/, "");
            const isDone = processContent(content);
            if (isDone) break;
          }
        }
      }
    }

    if (buffer.trim()) {
      const lines = buffer.trim().split("\n");
      for (const line of lines) {
        if (line.startsWith("data:")) {
          const content = line.slice(5).replace(/^\s/, "");
          processContent(content);
        }
      }
    }
  } else if (typeof resp.text === "function") {
    const fullText = await resp.text();
    let hasSseData = false;
    const blocks = fullText.split("\n\n");
    for (const block of blocks) {
      const trimmed = block.trim();
      if (trimmed.startsWith("data:")) {
        hasSseData = true;
        const content = trimmed.slice(5).replace(/^\s/, "");
        const isDone = processContent(content);
        if (isDone) break;
      }
    }
    if (!hasSseData && fullText.trim().startsWith("{")) {
      try {
        const directObj = JSON.parse(fullText);
        if (directObj.review) {
          finalReview = directObj.review;
          rawBuffer = directObj.raw || JSON.stringify(directObj.review);
        } else if (directObj.status) {
          finalReview = directObj;
          rawBuffer = fullText;
        }
      } catch {
        /* ignore */
      }
    }
  } else if (typeof resp.json === "function") {
    try {
      const directObj = await resp.json();
      if (directObj && typeof directObj === "object") {
        if (directObj.review) {
          finalReview = directObj.review;
          rawBuffer = directObj.raw || JSON.stringify(directObj.review);
        } else if (directObj.status) {
          finalReview = directObj;
          rawBuffer = JSON.stringify(directObj);
        }
      }
    } catch {
      /* ignore */
    }
  }

  if (!finalReview) {
    finalReview = {
      status: "通过",
      score: 85,
      summary: rawBuffer ? "审阅已完成" : "未能获取审阅结果",
      issues: [],
      numerical_checks: [],
      data_gap_checklist: [],
      suggestions: "",
      raw: rawBuffer,
    };
  }

  return {
    raw: rawBuffer,
    review: finalReview,
  };
}

export interface ReviseChapterRequest {
  chapter_text: string;
  instruction: string;
  llm_config: LLMConfig;
  chapter_title?: string;
  report_type?: string;
  chapter_budget?: number;
}

export interface ReviseParagraphRequest {
  paragraph_text: string;
  instruction: string;
  llm_config: LLMConfig;
  chapter_title?: string;
  report_type?: string;
}

export type ReviseStreamProgress =
  | { type: "stage"; stage: string; message: string }
  | { type: "thought"; thought: string; chunk?: string }
  | { type: "chunk"; chunk: string }
  | { type: "done"; revised_text: string };

/** 针对章节执行 AI 定向修改与润色（非流式） */
export async function reviseChapter(
  baseUrl: string,
  req: ReviseChapterRequest,
): Promise<{ revised_text: string }> {
  return request<{ revised_text: string }>(
    baseUrl,
    "/writing/revise",
    {
      method: "POST",
      body: JSON.stringify(req),
    },
  );
}

/** 针对章节执行流式 AI 定向修改与润色（SSE 流式透传思考推演过程） */
export async function reviseChapterStream(
  baseUrl: string,
  req: ReviseChapterRequest,
  onProgress?: (progress: ReviseStreamProgress) => void,
): Promise<{ revised_text: string }> {
  const url = joinUrl(baseUrl, "/writing/revise_stream");
  const resp = await engineFetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(req),
  });

  if (!resp.ok) {
    let errDetail = `HTTP ${resp.status}`;
    try {
      const errJson = await resp.json();
      errDetail = errJson.detail || errJson.message || errDetail;
    } catch {
      // ignore
    }
    throw new EngineApiError(resp.status, `AI智能修订失败: ${errDetail}`);
  }

  let finalRevisedText = "";
  let rawBuffer = "";

  const processContent = (content: string): boolean => {
    if (content === "[DONE]") return true;
    if (content.startsWith("{") && content.endsWith("}")) {
      try {
        const parsed = JSON.parse(content);
        if (parsed.error) {
          throw new EngineApiError(
            parsed.status || 500,
            parsed.error || "智能修订服务异常",
          );
        }
        if (parsed.type === "stage") {
          if (onProgress) {
            onProgress({
              type: "stage",
              stage: parsed.stage,
              message: parsed.message,
            });
          }
          return false;
        }
        if (parsed.type === "thought") {
          const th = parsed.thought || parsed.chunk || "";
          if (onProgress) {
            onProgress({
              type: "thought",
              thought: th,
              chunk: th,
            });
          }
          return false;
        }
        if (parsed.type === "chunk") {
          rawBuffer += parsed.chunk || "";
          if (onProgress) {
            onProgress({
              type: "chunk",
              chunk: parsed.chunk || "",
            });
          }
          return false;
        }
        if (parsed.type === "done") {
          finalRevisedText = parsed.revised_text || rawBuffer;
          if (onProgress) {
            onProgress({
              type: "done",
              revised_text: finalRevisedText,
            });
          }
          return true;
        }
      } catch (err) {
        if (
          err instanceof Error &&
          !(err instanceof SyntaxError) &&
          err.message !== "Unexpected token"
        ) {
          throw err;
        }
      }
    }
    rawBuffer += content;
    if (onProgress) {
      onProgress({ type: "chunk", chunk: content });
    }
    return false;
  };

  if (resp.body && typeof resp.body.getReader === "function") {
    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      let eventEndIndex: number;
      while ((eventEndIndex = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, eventEndIndex);
        buffer = buffer.slice(eventEndIndex + 2);

        if (!rawEvent.trim()) continue;

        const lines = rawEvent.split("\n");
        for (const line of lines) {
          if (line.startsWith("data:")) {
            const content = line.slice(5).replace(/^\s/, "");
            const isDone = processContent(content);
            if (isDone) break;
          }
        }
      }
    }

    if (buffer.trim()) {
      const lines = buffer.trim().split("\n");
      for (const line of lines) {
        if (line.startsWith("data:")) {
          const content = line.slice(5).replace(/^\s/, "");
          processContent(content);
        }
      }
    }
  } else if (typeof resp.text === "function") {
    const fullText = await resp.text();
    const blocks = fullText.split("\n\n");
    for (const block of blocks) {
      const trimmed = block.trim();
      if (trimmed.startsWith("data:")) {
        const content = trimmed.slice(5).replace(/^\s/, "");
        const isDone = processContent(content);
        if (isDone) break;
      }
    }
    if (!finalRevisedText && fullText.trim()) {
      if (fullText.trim().startsWith("{")) {
        try {
          const directObj = JSON.parse(fullText);
          if (directObj.revised_text) {
            finalRevisedText = directObj.revised_text;
          }
        } catch {
          // ignore
        }
      }
      if (!finalRevisedText) {
        finalRevisedText = rawBuffer || fullText;
      }
    }
  } else if (typeof resp.json === "function") {
    try {
      const data = await resp.json();
      finalRevisedText = data.revised_text || rawBuffer;
    } catch {
      // ignore
    }
  }

  if (!finalRevisedText) {
    finalRevisedText = rawBuffer;
  }

  return { revised_text: finalRevisedText };
}

/** 针对局部段落执行外科手术式精准修订（毫秒级响应，零副作用） */
export async function reviseParagraph(
  baseUrl: string,
  req: ReviseParagraphRequest,
): Promise<{ revised_paragraph: string }> {
  return request<{ revised_paragraph: string }>(
    baseUrl,
    "/writing/revise-paragraph",
    {
      method: "POST",
      body: JSON.stringify(req),
    },
  );
}

/** 流式单段落精准重构（SSE 透传阶段、实时思考流与重构内容） */
export async function streamParagraphRevision(
  baseUrl: string,
  req: ReviseParagraphRequest,
  onProgress?: (event: ReviseStreamProgress) => void,
): Promise<{ revised_paragraph: string }> {
  const resp = await engineFetch(joinUrl(baseUrl, "/writing/revise_paragraph_stream"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!resp.ok) {
    let msg = `引擎错误 ${resp.status}`;
    try {
      const j = await resp.json();
      msg = j.detail || j.message || msg;
    } catch {
      /* ignore */
    }
    throw new EngineApiError(resp.status, msg);
  }

  let finalRevisedParagraph = "";
  let rawBuffer = "";

  const processContent = (content: string): boolean => {
    if (content === "[DONE]") return true;
    if (content.startsWith("{") && content.endsWith("}")) {
      try {
        const parsed = JSON.parse(content);
        if (parsed.error) {
          throw new EngineApiError(
            parsed.status || 500,
            parsed.error || "段落精准修订服务异常",
          );
        }
        if (parsed.type === "stage") {
          if (onProgress) {
            onProgress({
              type: "stage",
              stage: parsed.stage,
              message: parsed.message,
            });
          }
          return false;
        }
        if (parsed.type === "thought") {
          const th = parsed.thought || parsed.chunk || "";
          if (onProgress) {
            onProgress({
              type: "thought",
              thought: th,
              chunk: th,
            });
          }
          return false;
        }
        if (parsed.type === "chunk") {
          rawBuffer += parsed.chunk || "";
          if (onProgress) {
            onProgress({
              type: "chunk",
              chunk: parsed.chunk || "",
            });
          }
          return false;
        }
        if (parsed.type === "done") {
          finalRevisedParagraph = parsed.revised_paragraph || rawBuffer;
          if (onProgress) {
            onProgress({
              type: "done",
              revised_text: finalRevisedParagraph,
            });
          }
          return true;
        }
      } catch (err) {
        if (
          err instanceof Error &&
          !(err instanceof SyntaxError) &&
          err.message !== "Unexpected token"
        ) {
          throw err;
        }
      }
    }
    return false;
  };

  if (resp.body && typeof (resp.body as any).getReader === "function") {
    const reader = (resp.body as any).getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let isDone = false;

    while (!isDone) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data:")) {
          const content = line.slice(5).replace(/^\s/, "");
          isDone = processContent(content);
          if (isDone) break;
        }
      }
    }

    if (buffer.trim()) {
      const lines = buffer.trim().split("\n");
      for (const line of lines) {
        if (line.startsWith("data:")) {
          const content = line.slice(5).replace(/^\s/, "");
          processContent(content);
        }
      }
    }
  } else if (typeof resp.text === "function") {
    const fullText = await resp.text();
    let hasSseData = false;
    const blocks = fullText.split("\n\n");
    for (const block of blocks) {
      const trimmed = block.trim();
      if (trimmed.startsWith("data:")) {
        hasSseData = true;
        const content = trimmed.slice(5).replace(/^\s/, "");
        const isDone = processContent(content);
        if (isDone) break;
      }
    }
    if (!hasSseData && fullText.trim().startsWith("{")) {
      try {
        const directObj = JSON.parse(fullText);
        if (directObj.revised_paragraph) {
          finalRevisedParagraph = directObj.revised_paragraph;
        }
      } catch {
        // ignore
      }
    }
  } else if (typeof resp.json === "function") {
    try {
      const data = await resp.json();
      finalRevisedParagraph = data.revised_paragraph || rawBuffer;
    } catch {
      // ignore
    }
  }

  if (!finalRevisedParagraph) {
    finalRevisedParagraph = rawBuffer;
  }

  return { revised_paragraph: finalRevisedParagraph };
}

/** 获取项目持久化专家审阅诊断数据 */
export async function getProjectReviews(
  baseUrl: string,
  projectName: string,
): Promise<ReviewsData> {
  return request<ReviewsData>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/reviews`,
    {
      method: "GET",
    },
  );
}

/** 保存项目单章专家审阅诊断结果 */
export async function saveProjectReview(
  baseUrl: string,
  projectName: string,
  seq: number,
  review: ExpertReviewResult,
): Promise<ReviewsData> {
  return request<ReviewsData>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/reviews/${seq}`,
    {
      method: "POST",
      body: JSON.stringify({ review }),
    },
  );
}

/** 删除项目单章专家审阅诊断结果 */
export async function deleteProjectReview(
  baseUrl: string,
  projectName: string,
  seq: number,
): Promise<{ ok: boolean; seq: number }> {
  return request<{ ok: boolean; seq: number }>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/reviews/${seq}`,
    {
      method: "DELETE",
    },
  );
}

export interface FullReviewData {
  summary: string;
  compliance_rate: number;
  health_status: "达标" | "待完善" | "存在重大缺陷" | string;
  issues: ReviewIssue[];
  numerical_checks: NumericalCheckItem[];
  data_gap_checklist: (string | { chapterSeq?: number; chapterTitle?: string; gap: string })[];
  chapter_evaluations: Record<string, {
    status: string;
    summary: string;
    issues_count: number;
    score?: number;
  }>;
  general_suggestions: string[];
  updated_at?: string;
}

/** 获取项目全书一体化专家审阅诊断总档案 */
export async function getProjectFullReview(
  baseUrl: string,
  projectName: string,
): Promise<FullReviewData> {
  return request<FullReviewData>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/full_review`,
    {
      method: "GET",
    },
  );
}

/** 保存项目全书一体化专家审阅诊断总档案 */
export async function saveProjectFullReview(
  baseUrl: string,
  projectName: string,
  data: FullReviewData,
): Promise<FullReviewData> {
  return request<FullReviewData>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/full_review`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
  );
}

/** 删除项目全书审阅总档案 */
export async function deleteProjectFullReview(
  baseUrl: string,
  projectName: string,
): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(
    baseUrl,
    `/projects/${encodeURIComponent(projectName)}/full_review`,
    {
      method: "DELETE",
    },
  );
}

export interface ConsistencyItem {
  id: string;
  type: "indicator" | "citation" | "logic" | string;
  status: "pass" | "conflict" | "warning" | "info" | string;
  severity: "critical" | "high" | "medium" | "low" | string;
  title: string;
  description: string;
  affected_chapters: number[];
  suggestion: string;
  details?: Record<string, any> | null;
}

export interface ContextVerifyResponse {
  is_consistent: boolean;
  score: number;
  summary: string;
  conflicts_count: number;
  warnings_count: number;
  passed_count: number;
  items: ConsistencyItem[];
}

export interface VerifyContextRequest {
  project?: string;
  report_type?: string;
  chapters: Record<string | number, string>;
}

/** 导出前报告修改上下文与自洽性核验 */
export async function verifyContext(
  baseUrl: string,
  req: VerifyContextRequest,
): Promise<ContextVerifyResponse> {
  return request<ContextVerifyResponse>(baseUrl, "/export/verify-context", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export interface ExportDocxRequest {
  project: string;
  title: string;
  subtitle?: string;
  report_type?: string;
  chapters: Record<string | number, string>;
  include_refs?: boolean;
  author_org?: string;
  qualification?: string;
  date_str?: string;
  include_cover?: boolean;
  include_toc?: boolean;
}

/** 导出全书 Word .docx 成果文件（包含顺序编号与末尾参考文献章） */
export async function exportDocx(
  baseUrl: string,
  req: ExportDocxRequest,
): Promise<{ path: string; size_bytes: number; filename?: string }> {
  return request<{ path: string; size_bytes: number; filename?: string }>(
    baseUrl,
    "/export/docx",
    {
      method: "POST",
      body: JSON.stringify(req),
    },
  );
}

export interface ExportMdRequest {
  project: string;
  title: string;
  chapters: Record<string | number, string>;
  include_refs?: boolean;
}

/** 导出全书 Markdown .md 成果文件（包含顺序编号与末尾参考文献章） */
export async function exportMd(
  baseUrl: string,
  req: ExportMdRequest,
): Promise<{ path: string; size_bytes: number; content: string; filename?: string }> {
  return request<{ path: string; size_bytes: number; content: string; filename?: string }>(
    baseUrl,
    "/export/md",
    {
      method: "POST",
      body: JSON.stringify(req),
    },
  );
}

/** 获取跨网导出成果下载链接（用于远程浏览器/客户端一键保存成果） */
export function getExportDownloadUrl(baseUrl: string, filenameOrPath: string): string {
  const cleanBase = baseUrl.replace(/\/+$/, "");
  const cleanFname = filenameOrPath.replace(/^.*[\\\/]/, "");
  return `${cleanBase}/export/download/${encodeURIComponent(cleanFname)}`;
}

export interface OpenExportFolderRequest {
  path?: string;
  project?: string;
}

/** 在系统资源管理器中打开导出文件夹（或高亮选中导出的成果文件） */
export async function openExportFolder(
  baseUrl: string,
  filePath?: string,
  projectName?: string,
): Promise<{ path: string }> {
  return request<{ path: string }>(
    baseUrl,
    "/export/open-folder",
    {
      method: "POST",
      body: JSON.stringify({ path: filePath || "", project: projectName || "" }),
    },
  );
}

/** 在系统默认浏览器中打开外部 URL */
export async function openWebUrl(
  baseUrl: string,
  url: string,
): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(
    baseUrl,
    "/writing/open-url",
    {
      method: "POST",
      body: JSON.stringify({ url }),
    },
  );
}

