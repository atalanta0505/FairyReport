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

/** 获取项目本地 files 目录绝对路径（用于打开文件夹等） */
export async function getProjectFilesDir(projectName: string): Promise<string> {
  try {
    const { localDataDir, join } = await import("@tauri-apps/api/path");
    const local = await localDataDir();
    return await join(local, "FairyReport", "projects", projectName, "files");
  } catch {
    return `C:\\Users\\Default\\AppData\\Local\\FairyReport\\projects\\${projectName}\\files`;
  }
}

/** 在系统资源管理器中打开项目 files 目录 */
export async function openProjectDir(projectName: string): Promise<void> {
  const dir = await getProjectFilesDir(projectName);
  const { open } = await import("@tauri-apps/plugin-shell");
  await open(dir);
}
