/**
 * 本地引擎 API 客户端 — 与本地 Python 引擎进程的 HTTP 通信。
 *
 * 采用 @tauri-apps/plugin-http fetch（Tauri 原生通道，绕开 CORS 与安全限制）。
 * 覆盖项目管理、资料摄取与删除、通用知识包状态与同步等接口。
 */
import { fetch as pluginFetch } from "@tauri-apps/plugin-http";

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
  total_words_max: number;
  notes?: string;
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
    resp = await pluginFetch(joinUrl(baseUrl, path), { ...options, headers });
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

/** 流式写作单章（SSE 透传，支持中止取消） */
export function streamChapterWriting(
  baseUrl: string,
  req: ChapterStreamRequest,
  onChunk: (chunk: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): () => void {
  const controller = new AbortController();
  const { signal } = controller;

  (async () => {
    try {
      const resp = await pluginFetch(joinUrl(baseUrl, "/writing/chapter"), {
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
                if (content === "[DONE]") {
                  onDone();
                  return;
                }
                if (content.startsWith("{") && content.includes('"error"')) {
                  try {
                    const parsed = JSON.parse(content);
                    if (parsed.error) {
                      throw new Error(parsed.error);
                    }
                  } catch (err) {
                    if (err instanceof Error && err.message !== "Unexpected token") {
                      throw err;
                    }
                  }
                }
                onChunk(content);
              } else if (!line.startsWith(":") && line.length > 0) {
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
              if (content === "[DONE]") {
                onDone();
                return;
              }
              onChunk(content);
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
            if (content === "[DONE]") {
              onDone();
              return;
            }
            onChunk(content);
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



