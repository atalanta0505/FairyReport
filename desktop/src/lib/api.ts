/**
 * 云端 API 客户端 — 对认证服务器（backend）的 HTTP 调用。
 *
 * 全部走 @tauri-apps/plugin-http fetch（Tauri 原生通道，绕开浏览器 CORS/混合内容限制）；
 * 测试通过 vi.mock 该模块覆盖成功/401/网络错误分支。
 * 不存储 Key；token 由调用方（auth store）管理。
 */

import { fetch } from "@tauri-apps/plugin-http";

export class CloudApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "CloudApiError";
    this.status = status;
  }
}

function joinUrl(server: string, path: string): string {
  return `${server.replace(/\/$/, "")}${path}`;
}

async function request(
  server: string,
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<any> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let resp: Response;
  try {
    resp = await fetch(joinUrl(server, path), { ...options, headers });
  } catch (e) {
    throw new CloudApiError(0, `网络错误：${(e as Error).message}`);
  }

  if (resp.status === 401) {
    throw new CloudApiError(401, "未授权或凭据无效");
  }
  if (!resp.ok) {
    let msg = `服务器错误 ${resp.status}`;
    try {
      const j = await resp.json();
      msg = j.detail || j.message || msg;
    } catch {
      /* 非 JSON 响应，保留默认 */
    }
    throw new CloudApiError(resp.status, msg);
  }
  return resp.json();
}

export async function sendCode(server: string, email: string): Promise<{ message: string }> {
  return request(server, "/api/auth/send-code", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function register(
  server: string,
  email: string,
  code: string,
  password: string,
): Promise<{ message: string }> {
  return request(server, "/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, code, password }),
  });
}

export interface LoginResponse {
  access_token: string;
}

export async function login(
  server: string,
  email: string,
  password: string,
): Promise<LoginResponse> {
  return request(server, "/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export interface UserInfo {
  id: number;
  email: string;
  created_at: string;
}

export async function me(server: string, token: string): Promise<UserInfo> {
  return request(server, "/api/users/me", { method: "GET" }, token);
}

export interface PackManifest {
  version: string;
  sha256: string;
  built_at: string;
  chunk_count: number;
  templates: string[];
}

export async function getPackManifest(server: string, token: string): Promise<PackManifest> {
  return request(server, "/api/pack/manifest", { method: "GET" }, token);
}
