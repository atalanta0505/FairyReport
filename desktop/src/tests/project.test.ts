import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { fetch as pluginFetch } from "@tauri-apps/plugin-http";
import * as engineApi from "../lib/engineApi";
import { useProjectStore } from "../stores/project";

vi.mock("@tauri-apps/plugin-http", () => ({ fetch: vi.fn() }));

const BASE_URL = "http://127.0.0.1:8765";
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

describe("engineApi 基础接口", () => {
  it("listProjects: 正常获取项目列表", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse([
        { id: 1, name: "项目A", created_at: "2026-08-25T00:00:00Z" },
        { id: 2, name: "项目B", created_at: "2026-08-25T01:00:00Z" },
      ]),
    );
    const list = await engineApi.listProjects(BASE_URL);
    expect(list).toHaveLength(2);
    expect(list[0].name).toBe("项目A");
    expect(mockFetch).toHaveBeenCalledWith(
      `${BASE_URL}/projects`,
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("createProject: 创建项目成功", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ id: 3, name: "新建水库项目", created_at: "2026-08-25T02:00:00Z" }, 201),
    );
    const proj = await engineApi.createProject(BASE_URL, "新建水库项目");
    expect(proj.id).toBe(3);
    expect(proj.name).toBe("新建水库项目");
    expect(mockFetch).toHaveBeenCalledWith(
      `${BASE_URL}/projects`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "新建水库项目" }),
      }),
    );
  });

  it("deleteProject: 删除项目成功 (204)", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 204,
      json: () => Promise.resolve({}),
    } as unknown as Response);

    await expect(engineApi.deleteProject(BASE_URL, "项目A")).resolves.toBeUndefined();
    expect(mockFetch).toHaveBeenCalledWith(
      `${BASE_URL}/projects/%E9%A1%B9%E7%9B%AEA`,
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("listMaterials: 列出项目资料", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse([
        {
          id: 10,
          source_id: "report.docx",
          filename: "report.docx",
          ext: ".docx",
          chunk_count: 5,
          size_bytes: 10240,
          created_at: "2026-08-25T00:00:00Z",
        },
      ]),
    );
    const mats = await engineApi.listMaterials(BASE_URL, "项目A");
    expect(mats).toHaveLength(1);
    expect(mats[0].source_id).toBe("report.docx");
    expect(mats[0].chunk_count).toBe(5);
  });

  it("ingestMaterials: 摄取资料成功", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse([
        {
          source_id: "data.csv",
          filename: "data.csv",
          ext: ".csv",
          chunk_count: 3,
          size_bytes: 2048,
          status: "ok",
          error: null,
        },
      ]),
    );
    const res = await engineApi.ingestMaterials(BASE_URL, "项目A", ["D:\\data.csv"]);
    expect(res).toHaveLength(1);
    expect(res[0].status).toBe("ok");
    expect(res[0].chunk_count).toBe(3);
  });

  it("deleteMaterial: 删除资料", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 204,
      json: () => Promise.resolve({}),
    } as unknown as Response);

    await expect(
      engineApi.deleteMaterial(BASE_URL, "项目A", "data.csv"),
    ).resolves.toBeUndefined();
  });

  it("getGenericStatus: 查询通用包状态", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ installed: true, version: "v1.0", installed_at: "2026-08-25T00:00:00Z" }),
    );
    const status = await engineApi.getGenericStatus(BASE_URL);
    expect(status.installed).toBe(true);
    expect(status.version).toBe("v1.0");
  });

  it("updateGenericKnowledge: 更新通用知识包", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ status: "installed", version: "v1.1" }),
    );
    const r = await engineApi.updateGenericKnowledge(BASE_URL, "http://cloud.test", "tok-abc");
    expect(r.status).toBe("installed");
    expect(r.version).toBe("v1.1");
  });

  it("错误响应 → 抛出 EngineApiError 包含 detail", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ detail: "项目已存在：重复项目" }, 409),
    );
    await expect(engineApi.createProject(BASE_URL, "重复项目")).rejects.toMatchObject({
      name: "EngineApiError",
      status: 409,
      message: "项目已存在：重复项目",
    });
  });

  it("网络异常 → 抛出 EngineApiError status=0", async () => {
    mockFetch.mockRejectedValue(new Error("Connection refused"));
    await expect(engineApi.listProjects(BASE_URL)).rejects.toMatchObject({
      name: "EngineApiError",
      status: 0,
    });
  });
});

describe("Pinia useProjectStore", () => {
  it("setStep: 切换向导步骤（限 1~5）", () => {
    const store = useProjectStore();
    expect(store.currentStep).toBe(1);
    store.setStep(2);
    expect(store.currentStep).toBe(2);
    store.setStep(6);
    expect(store.currentStep).toBe(2); // 越界不改变
    store.setStep(0);
    expect(store.currentStep).toBe(2); // 越界不改变
  });

  it("loadProjects: 载入项目并自动选中首个项目与资料", async () => {
    const store = useProjectStore();

    // 第一次 mock 为 listProjects
    mockFetch.mockImplementation(async (url) => {
      const u = String(url);
      if (u.endsWith("/projects")) {
        return jsonResponse([
          { id: 1, name: "水库A", created_at: "2026-08-25T00:00:00Z" },
          { id: 2, name: "水库B", created_at: "2026-08-25T01:00:00Z" },
        ]);
      }
      if (u.includes("/projects/%E6%B0%B4%E5%BA%93A/materials")) {
        return jsonResponse([
          {
            id: 1,
            source_id: "doc.docx",
            filename: "doc.docx",
            ext: ".docx",
            chunk_count: 8,
            size_bytes: 4096,
            created_at: "2026-08-25T00:00:00Z",
          },
        ]);
      }
      return jsonResponse({});
    });

    await store.loadProjects(BASE_URL);
    expect(store.projects).toHaveLength(2);
    expect(store.currentProject?.name).toBe("水库A");
    expect(store.materials).toHaveLength(1);
    expect(store.materials[0].filename).toBe("doc.docx");
  });

  it("createProject: 创建项目并自动选中", async () => {
    const store = useProjectStore();

    mockFetch.mockImplementation(async (url, opts) => {
      const u = String(url);
      const method = opts?.method || "GET";
      if (u.endsWith("/projects") && method === "POST") {
        return jsonResponse({ id: 10, name: "新工程", created_at: "2026-08-25T00:00:00Z" }, 201);
      }
      if (u.endsWith("/projects") && method === "GET") {
        return jsonResponse([{ id: 10, name: "新工程", created_at: "2026-08-25T00:00:00Z" }]);
      }
      if (u.includes("/materials")) {
        return jsonResponse([]);
      }
      return jsonResponse({});
    });

    const p = await store.createProject(BASE_URL, "新工程");
    expect(p.name).toBe("新工程");
    expect(store.currentProject?.name).toBe("新工程");
  });

  it("deleteProject: 删除项目后清空当前选中并刷新", async () => {
    const store = useProjectStore();
    store.projects = [{ id: 1, name: "待删除", created_at: "2026-08-25T00:00:00Z" }];
    store.currentProject = store.projects[0];

    mockFetch.mockImplementation(async (url, opts) => {
      const u = String(url);
      const method = opts?.method || "GET";
      if (method === "DELETE") {
        return { ok: true, status: 204, json: () => Promise.resolve({}) } as unknown as Response;
      }
      if (u.endsWith("/projects") && method === "GET") {
        return jsonResponse([]);
      }
      return jsonResponse({});
    });

    await store.deleteProject(BASE_URL, "待删除");
    expect(store.currentProject).toBeNull();
    expect(store.projects).toHaveLength(0);
  });

  it("ingestFiles & deleteMaterial: 资料摄取与删除", async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: "项目1", created_at: "2026-08-25T00:00:00Z" };

    mockFetch.mockImplementation(async (url, opts) => {
      const u = String(url);
      const method = opts?.method || "GET";
      if (u.endsWith("/materials/ingest") && method === "POST") {
        return jsonResponse([
          {
            source_id: "test.docx",
            filename: "test.docx",
            ext: ".docx",
            chunk_count: 12,
            size_bytes: 8192,
            status: "ok",
            error: null,
          },
        ]);
      }
      if (u.includes("/materials") && method === "GET") {
        return jsonResponse([
          {
            id: 1,
            source_id: "test.docx",
            filename: "test.docx",
            ext: ".docx",
            chunk_count: 12,
            size_bytes: 8192,
            created_at: "2026-08-25T00:00:00Z",
          },
        ]);
      }
      if (method === "DELETE") {
        return { ok: true, status: 204, json: () => Promise.resolve({}) } as unknown as Response;
      }
      return jsonResponse({});
    });

    const results = await store.ingestFiles(BASE_URL, ["D:\\test.docx"]);
    expect(results).toHaveLength(1);
    expect(store.materials).toHaveLength(1);
    expect(store.materials[0].chunk_count).toBe(12);

    await store.deleteMaterial(BASE_URL, "test.docx");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/materials/test.docx"),
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("checkGenericStatus & updateGeneric: 通用知识包检测与更新", async () => {
    const store = useProjectStore();

    mockFetch.mockImplementation(async (url, opts) => {
      const u = String(url);
      const method = opts?.method || "GET";
      if (u.endsWith("/generic/status") && method === "GET") {
        return jsonResponse({ installed: false });
      }
      if (u.endsWith("/generic/update") && method === "POST") {
        return jsonResponse({ status: "installed", version: "v2.0" });
      }
      return jsonResponse({});
    });

    const status1 = await store.checkGenericStatus(BASE_URL);
    expect(status1.installed).toBe(false);
    expect(store.genericStatus?.installed).toBe(false);

    // 更新 generic 状态 mock 为 installed
    mockFetch.mockImplementation(async (url, opts) => {
      const u = String(url);
      const method = opts?.method || "GET";
      if (u.endsWith("/generic/status") && method === "GET") {
        return jsonResponse({ installed: true, version: "v2.0" });
      }
      if (u.endsWith("/generic/update") && method === "POST") {
        return jsonResponse({ status: "installed", version: "v2.0" });
      }
      return jsonResponse({});
    });

    const updateRes = await store.updateGeneric(BASE_URL, "http://server.test", "tok-xyz");
    expect(updateRes.version).toBe("v2.0");
    expect(store.genericStatus?.installed).toBe(true);
  });
});
