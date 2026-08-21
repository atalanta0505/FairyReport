import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetch as pluginFetch } from "@tauri-apps/plugin-http";
import { getPackManifest, login, me, register, sendCode } from "../lib/api";

vi.mock("@tauri-apps/plugin-http", () => ({ fetch: vi.fn() }));

const SERVER = "http://cloud.test";
const mockFetch = vi.mocked(pluginFetch);

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

beforeEach(() => {
  mockFetch.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api.sendCode", () => {
  it("成功返回 message", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ message: "验证码已发送" }));
    const r = await sendCode(SERVER, "a@b.com");
    expect(r.message).toBe("验证码已发送");
    const call = mockFetch.mock.calls[0];
    expect(call[0]).toBe(`${SERVER}/api/auth/send-code`);
  });

  it("网络错误 → CloudApiError status=0", async () => {
    mockFetch.mockRejectedValue(new TypeError("fetch failed"));
    await expect(sendCode(SERVER, "a@b.com")).rejects.toMatchObject({
      name: "CloudApiError",
      status: 0,
    });
  });
});

describe("api.login", () => {
  it("成功返回 access_token", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ access_token: "tok-123" }));
    const r = await login(SERVER, "a@b.com", "pw");
    expect(r.access_token).toBe("tok-123");
  });

  it("401 → CloudApiError status=401", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "邮箱或密码错误" }, 401));
    await expect(login(SERVER, "a@b.com", "wrong")).rejects.toMatchObject({
      name: "CloudApiError",
      status: 401,
    });
  });
});

describe("api.register", () => {
  it("成功", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ message: "注册成功" }, 201));
    const r = await register(SERVER, "a@b.com", "123456", "pw");
    expect(r.message).toBe("注册成功");
  });
});

describe("api.me", () => {
  it("携带 Authorization 头", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ id: 1, email: "a@b.com", created_at: "2026-01-01" }),
    );
    const u = await me(SERVER, "tok-123");
    expect(u.email).toBe("a@b.com");
    const opts = mockFetch.mock.calls[0][1] as { headers: Record<string, string> };
    expect(opts.headers.Authorization).toBe("Bearer tok-123");
  });
});

describe("api.getPackManifest", () => {
  it("成功返回 manifest", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ version: "v1", sha256: "abc", built_at: "x", chunk_count: 3, templates: ["t.json"] }),
    );
    const m = await getPackManifest(SERVER, "tok");
    expect(m.version).toBe("v1");
    const opts = mockFetch.mock.calls[0][1] as { headers: Record<string, string> };
    expect(opts.headers.Authorization).toBe("Bearer tok");
  });
});
