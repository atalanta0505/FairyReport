import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { fetch as pluginFetch } from "@tauri-apps/plugin-http";
import { useSettingsStore } from "../stores/settings";

vi.mock("@tauri-apps/plugin-http", () => ({ fetch: vi.fn() }));
const mockFetch = vi.mocked(pluginFetch);

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

beforeEach(() => {
  setActivePinia(createPinia());
  mockFetch.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Settings Store - DeepSeek API 配置与动态拉取", () => {
  it("初始化默认值严格对齐官方规范", () => {
    const store = useSettingsStore();
    expect(store.llmBaseUrl).toBe("https://api.deepseek.com");
    expect(store.llmModel).toBe("deepseek-flash");
    expect(store.availableModels).toContain("deepseek-flash");
    expect(store.availableModels).toContain("deepseek-v4-pro");
  });

  it("fetchRemoteModels 在未提供 API Key 时给出友好拦截", async () => {
    const store = useSettingsStore();
    store.llmKey = "";
    await expect(store.fetchRemoteModels()).rejects.toThrow(
      "请先输入 API Key，再拉取官方模型列表"
    );
  });

  it("fetchRemoteModels 成功向官方 /models 端点拉取并合并模型列表", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({
        object: "list",
        data: [
          { id: "deepseek-flash", object: "model" },
          { id: "deepseek-v4-pro", object: "model" },
          { id: "deepseek-custom-exp", object: "model" },
        ],
      })
    );

    const store = useSettingsStore();
    store.llmKey = "sk-test-mock-key";
    store.llmBaseUrl = "https://api.deepseek.com";

    const models = await store.fetchRemoteModels();
    expect(models).toEqual([
      "deepseek-flash",
      "deepseek-v4-pro",
      "deepseek-custom-exp",
    ]);
    expect(store.availableModels).toContain("deepseek-custom-exp");

    const call = mockFetch.mock.calls[0];
    expect(call[0]).toBe("https://api.deepseek.com/models");
    expect((call[1]?.headers as any)["Authorization"]).toBe(
      "Bearer sk-test-mock-key"
    );
  });
});
