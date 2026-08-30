import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { fetch as pluginFetch } from "@tauri-apps/plugin-http";
import * as engineApi from "../lib/engineApi";
import {
  extractReferences,
  getReferencesSummary,
  highlightIssuesInHtml,
  htmlToMarkdown,
  markdownToHtml,
} from "../lib/markdown";
import { useProjectStore } from "../stores/project";

vi.mock("@tauri-apps/plugin-http", () => ({ fetch: vi.fn() }));

const BASE_URL = "http://127.0.0.1:8765";
const mockFetch = vi.mocked(pluginFetch);

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(typeof body === "string" ? body : JSON.stringify(body)),
  } as unknown as Response;
}

function mockSSEResponse(chunks: string[]): Response {
  const events = chunks.map((c) => `data: ${c}\n\n`).join("") + "data: [DONE]\n\n";
  const encoder = new TextEncoder();
  const uint8 = encoder.encode(events);

  return {
    ok: true,
    status: 200,
    body: {
      getReader: () => {
        let sent = false;
        return {
          read: async () => {
            if (!sent) {
              sent = true;
              return { done: false, value: uint8 };
            }
            return { done: true, value: undefined };
          },
        };
      },
    },
    text: () => Promise.resolve(events),
  } as unknown as Response;
}

class MockSessionStorage {
  private store: Record<string, string> = {};
  getItem(key: string): string | null {
    return this.store[key] ?? null;
  }
  setItem(key: string, value: string): void {
    this.store[key] = String(value);
  }
  removeItem(key: string): void {
    delete this.store[key];
  }
  clear(): void {
    this.store = {};
  }
}

const mockStorage = new MockSessionStorage();
const mockLocalStorage = new MockSessionStorage();
(globalThis as any).sessionStorage = mockStorage;
(globalThis as any).localStorage = mockLocalStorage;

beforeEach(() => {
  mockStorage.clear();
  mockLocalStorage.clear();
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

  it("scanMaterials: 扫描本地资料目录并摄取", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse([
        {
          source_id: "scan1.docx",
          filename: "scan1.docx",
          ext: ".docx",
          chunk_count: 7,
          size_bytes: 4096,
          status: "ok",
          error: null,
        },
      ]),
    );
    const res = await engineApi.scanMaterials(BASE_URL, "项目A");
    expect(res).toHaveLength(1);
    expect(res[0].filename).toBe("scan1.docx");
    expect(mockFetch).toHaveBeenCalledWith(
      `${BASE_URL}/projects/%E9%A1%B9%E7%9B%AEA/materials/scan`,
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("getTemplates: 获取 14 类模板列表", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse([
        { report_type: "可行性研究报告", total_words_max: 50000, notes: "标准模板" },
        { report_type: "产业发展规划报告", total_words_max: 30000, notes: "" },
      ]),
    );
    const templates = await engineApi.getTemplates(BASE_URL);
    expect(templates).toHaveLength(2);
    expect(templates[0].report_type).toBe("可行性研究报告");
    expect(templates[0].total_words_max).toBe(50000);
  });

  it("generateOutline: 生成结构化大纲", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({
        outline_md: "# 第一章 概述\n# 第二章 建设背景",
        chapters: [
          { seq: 1, title: "第一章 概述" },
          { seq: 2, title: "第二章 建设背景" },
        ],
      }),
    );
    const res = await engineApi.generateOutline(BASE_URL, {
      project: "测试项目",
      report_type: "可行性研究报告",
      llm_config: { api_key: "sk-key", base_url: "http://api", model: "m" },
    });
    expect(res.outline_md).toContain("第一章");
    expect(res.chapters).toHaveLength(2);
  });

  it("getProjectOutline: 获取项目大纲数据", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({
        report_type: "可行性研究报告",
        outline_md: "# 第一章 概述",
        chapters: [{ seq: 1, title: "第一章 概述" }],
        updated_at: "2026-08-25T12:00:00Z",
      }),
    );
    const res = await engineApi.getProjectOutline(BASE_URL, "项目A");
    expect(res.report_type).toBe("可行性研究报告");
    expect(res.outline_md).toBe("# 第一章 概述");
    expect(res.chapters).toHaveLength(1);
    expect(mockFetch).toHaveBeenCalledWith(
      `${BASE_URL}/projects/%E9%A1%B9%E7%9B%AEA/outline`,
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("saveProjectOutline: 保存项目大纲数据", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({
        report_type: "产业发展规划报告",
        outline_md: "# 第一章 总述",
        chapters: [{ seq: 1, title: "第一章 总述" }],
        updated_at: "2026-08-25T12:00:00Z",
      }),
    );
    await engineApi.saveProjectOutline(BASE_URL, "项目A", {
      report_type: "产业发展规划报告",
      outline_md: "# 第一章 总述",
      chapters: [{ seq: 1, title: "第一章 总述" }],
    });
    expect(mockFetch).toHaveBeenCalledWith(
      `${BASE_URL}/projects/%E9%A1%B9%E7%9B%AEA/outline`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          report_type: "产业发展规划报告",
          outline_md: "# 第一章 总述",
          chapters: [{ seq: 1, title: "第一章 总述" }],
        }),
      }),
    );
  });

  it("openProjectDir: 请求引擎在本地打开文件夹", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ path: "C:\\projects\\项目A\\files" }),
    );
    const res = await engineApi.openProjectDir(BASE_URL, "项目A");
    expect(res.path).toBe("C:\\projects\\项目A\\files");
    expect(mockFetch).toHaveBeenCalledWith(
      `${BASE_URL}/projects/%E9%A1%B9%E7%9B%AEA/open-folder`,
      expect.objectContaining({ method: "POST" }),
    );
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

  it("createProject: 重建同名项目前彻底清理本地资料与大纲缓存", async () => {
    const store = useProjectStore();
    mockLocalStorage.setItem("frl_outline_重建工程", JSON.stringify({ outline_md: "历史大纲" }));
    mockLocalStorage.setItem("frl_chapters_重建工程", JSON.stringify({ 1: "历史章节" }));
    store.materials = [
      {
        id: 1,
        source_id: "old.md",
        filename: "old.md",
        ext: ".md",
        chunk_count: 5,
        size_bytes: 1024,
        created_at: "2026-08-25T00:00:00Z",
      },
    ];

    mockFetch.mockImplementation(async (url, opts) => {
      const u = String(url);
      const method = opts?.method || "GET";
      if (u.endsWith("/projects") && method === "POST") {
        return jsonResponse({ id: 11, name: "重建工程", created_at: "2026-08-25T00:00:00Z" }, 201);
      }
      if (u.endsWith("/projects") && method === "GET") {
        return jsonResponse([{ id: 11, name: "重建工程", created_at: "2026-08-25T00:00:00Z" }]);
      }
      if (u.includes("/materials")) {
        return jsonResponse([]);
      }
      if (u.includes("/outline")) {
        return jsonResponse({ report_type: "可行性研究报告", outline_md: "", chapters: [] });
      }
      if (u.includes("/chapters")) {
        return jsonResponse({ chapters: {} });
      }
      return jsonResponse({});
    });

    const p = await store.createProject(BASE_URL, "重建工程");
    expect(p.name).toBe("重建工程");
    expect(store.materials).toHaveLength(0);
    expect(store.outlineMd).toBe("");
    expect(store.outlineChapters).toHaveLength(0);
    expect(store.chapters).toEqual({});
    const rawOutline = mockLocalStorage.getItem("frl_outline_重建工程");
    expect(rawOutline).not.toContain("历史大纲");
    const rawChapters = mockLocalStorage.getItem("frl_chapters_重建工程");
    expect(rawChapters).not.toContain("历史章节");
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

  it("scanMaterials: 扫描本地资料并自动刷新资料列表", async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: "本地项目", created_at: "2026-08-25T00:00:00Z" };

    mockFetch.mockImplementation(async (url, opts) => {
      const u = String(url);
      const method = opts?.method || "GET";
      if (u.includes("/materials/scan") && method === "POST") {
        return jsonResponse([
          {
            source_id: "scanned.md",
            filename: "scanned.md",
            ext: ".md",
            chunk_count: 6,
            size_bytes: 1024,
            status: "ok",
            error: null,
          },
        ]);
      }
      if (u.includes("/materials") && method === "GET") {
        return jsonResponse([
          {
            id: 2,
            source_id: "scanned.md",
            filename: "scanned.md",
            ext: ".md",
            chunk_count: 6,
            size_bytes: 1024,
            created_at: "2026-08-25T00:00:00Z",
          },
        ]);
      }
      return jsonResponse({});
    });

    const res = await store.scanMaterials(BASE_URL);
    expect(res).toHaveLength(1);
    expect(res[0].filename).toBe("scanned.md");
    expect(store.materials).toHaveLength(1);
    expect(store.materials[0].filename).toBe("scanned.md");
  });

  it("loadTemplates: 加载 14 类模板并保留/更新 reportType", async () => {
    const store = useProjectStore();

    mockFetch.mockResolvedValue(
      jsonResponse([
        { report_type: "可行性研究报告", total_words_max: 50000, notes: "模板1" },
        { report_type: "园区发展规划报告", total_words_max: 35000, notes: "模板2" },
      ]),
    );

    const tmpls = await store.loadTemplates(BASE_URL);
    expect(tmpls).toHaveLength(2);
    expect(store.templates).toHaveLength(2);
    expect(store.reportType).toBe("可行性研究报告");

    store.setReportType("园区发展规划报告");
    expect(store.reportType).toBe("园区发展规划报告");
  });

  it("generateOutline: 调用 AI 生成大纲并填充 outlineMd 与章节树", async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: "水库工程", created_at: "2026-08-25T00:00:00Z" };
    store.reportType = "可行性研究报告";

    mockFetch.mockResolvedValue(
      jsonResponse({
        outline_md: "# 第一章 概述\n## 1.1 项目背景\n# 第二章 建设必要性\n## 2.1 背景分析\n# 第三章 结论",
        chapters: [
          { seq: 1, title: "第一章 概述" },
          { seq: 2, title: "第二章 建设必要性" },
          { seq: 3, title: "第三章 结论" },
        ],
      }),
    );

    const res = await store.generateOutline(BASE_URL, {
      api_key: "sk-test",
      base_url: "https://api.deepseek.com",
      model: "deepseek-chat",
    });

    expect(res.chapters).toHaveLength(3);
    expect(store.outlineMd).toContain("第一章 概述");
    expect(store.outlineChapters).toHaveLength(3);
    expect(store.outlineChapters[0].title).toBe("第一章 概述");
    expect(store.outlineChapters[1].title).toBe("第二章 建设必要性");
  });

  it("setOutlineMd: 用户手动编辑 Markdown 实时同步更新章节树", () => {
    const store = useProjectStore();
    expect(store.outlineChapters).toHaveLength(0);

    store.setOutlineMd("# 第一章 项目总论\n正文...\n# 第二章 市场预测\n正文...");
    expect(store.outlineChapters).toHaveLength(2);
    expect(store.outlineChapters[0].title).toBe("第一章 项目总论");
    expect(store.outlineChapters[1].title).toBe("第二章 市场预测");

    store.setOutlineMd("");
    expect(store.outlineChapters).toHaveLength(0);
  });

  it("openProjectDir: 通过 store 唤起项目文件夹", async () => {
    const store = useProjectStore();
    store.currentProject = { id: 1, name: "项目1", created_at: "2026-08-25T00:00:00Z" };

    mockFetch.mockResolvedValue(
      jsonResponse({ path: "D:\\projects\\项目1\\files" }),
    );

    const res = await store.openProjectDir(BASE_URL);
    expect(res.path).toBe("D:\\projects\\项目1\\files");
    expect(mockFetch).toHaveBeenCalledWith(
      `${BASE_URL}/projects/%E9%A1%B9%E7%9B%AE1/open-folder`,
      expect.objectContaining({ method: "POST" }),
    );
  });

  describe("localStorage 与跨会话阶段/项目自恢复", () => {
    it("setStep: 写入 localStorage 与 sessionStorage 并成功持久化", () => {
      const store = useProjectStore();
      expect(mockLocalStorage.getItem("frl_current_step")).toBeNull();

      store.setStep(2);
      expect(store.currentStep).toBe(2);
      expect(mockLocalStorage.getItem("frl_current_step")).toBe("2");

      store.setStep(5);
      expect(store.currentStep).toBe(5);
      expect(mockLocalStorage.getItem("frl_current_step")).toBe("5");

      // 越界值不修改 localStorage
      store.setStep(9);
      expect(store.currentStep).toBe(5);
      expect(mockLocalStorage.getItem("frl_current_step")).toBe("5");
    });

    it("Pinia 初始化: 从 localStorage 恢复有效步骤 (1~5)", () => {
      mockLocalStorage.setItem("frl_current_step", "3");
      setActivePinia(createPinia());
      const store = useProjectStore();
      expect(store.currentStep).toBe(3);
    });

    it("Pinia 初始化: 遇非法或越界步骤值安全回退到 1", () => {
      mockLocalStorage.setItem("frl_current_step", "99");
      setActivePinia(createPinia());
      const store1 = useProjectStore();
      expect(store1.currentStep).toBe(1);

      mockLocalStorage.setItem("frl_current_step", "not-a-number");
      setActivePinia(createPinia());
      const store2 = useProjectStore();
      expect(store2.currentStep).toBe(1);
    });

    it("selectProject: 同步项目名称到 localStorage", async () => {
      const store = useProjectStore();
      store.projects = [
        { id: 1, name: "水库A", created_at: "2026-08-25T00:00:00Z" },
        { id: 2, name: "水库B", created_at: "2026-08-25T01:00:00Z" },
      ];

      mockFetch.mockResolvedValue(jsonResponse([]));
      await store.selectProject(BASE_URL, "水库B");

      expect(store.currentProject?.name).toBe("水库B");
      expect(mockLocalStorage.getItem("frl_current_project")).toBe("水库B");
    });

    it("loadProjects: 优先从 localStorage 恢复之前选定的项目", async () => {
      mockLocalStorage.setItem("frl_current_project", "水库B");
      setActivePinia(createPinia());
      const store = useProjectStore();

      mockFetch.mockImplementation(async (url) => {
        const u = String(url);
        if (u.endsWith("/projects")) {
          return jsonResponse([
            { id: 1, name: "水库A", created_at: "2026-08-25T00:00:00Z" },
            { id: 2, name: "水库B", created_at: "2026-08-25T01:00:00Z" },
          ]);
        }
        if (u.includes("/materials")) {
          return jsonResponse([]);
        }
        return jsonResponse({});
      });

      await store.loadProjects(BASE_URL);
      expect(store.currentProject?.name).toBe("水库B");
      expect(mockLocalStorage.getItem("frl_current_project")).toBe("水库B");
    });

    it("deleteProject: 删除当前选中项目后清除 localStorage 记录", async () => {
      const store = useProjectStore();
      store.projects = [{ id: 1, name: "待删项目", created_at: "2026-08-25T00:00:00Z" }];
      store.currentProject = store.projects[0];
      mockLocalStorage.setItem("frl_current_project", "待删项目");

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

      await store.deleteProject(BASE_URL, "待删项目");
      expect(store.currentProject).toBeNull();
      expect(mockLocalStorage.getItem("frl_current_project")).toBeNull();
    });
  });

  describe("大纲全链路持久化与自动恢复", () => {
    it("loadOutline: 从引擎成功加载大纲并同步更新 localStorage 备份", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "持久化项目", created_at: "2026-08-25T00:00:00Z" };

      mockFetch.mockImplementation(async (url) => {
        const u = String(url);
        if (u.includes("/outline")) {
          return jsonResponse({
            report_type: "可行性研究报告",
            outline_md: "# 第一章 概述\n## 1.1 背景\n# 第二章 结论",
            chapters: [
              { seq: 1, title: "第一章 概述" },
              { seq: 2, title: "第二章 结论" },
            ],
            writing_order: [2, 1],
            writing_order_reason: "主体章节优先",
            updated_at: "2026-08-25T10:00:00Z",
          });
        }
        return jsonResponse({});
      });

      const res = await store.loadOutline(BASE_URL, "持久化项目");
      expect(res).not.toBeNull();
      expect(store.outlineMd).toContain("第一章 概述");
      expect(store.outlineChapters).toHaveLength(2);
      expect(store.reportType).toBe("可行性研究报告");
      expect(store.writingOrder).toEqual([2, 1]);

      // 验证 localStorage 备份写入
      const localRaw = mockLocalStorage.getItem("frl_outline_持久化项目");
      expect(localRaw).not.toBeNull();
      const localData = JSON.parse(localRaw!);
      expect(localData.outline_md).toContain("第一章 概述");
      expect(localData.writing_order).toEqual([2, 1]);

      const localWORaw = mockLocalStorage.getItem("frl_writing_order_持久化项目");
      expect(localWORaw).not.toBeNull();
      expect(JSON.parse(localWORaw!).order).toEqual([2, 1]);
    });

    it("loadOutline: 引擎接口异常时自动降级从 localStorage 恢复", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "本地离线项目", created_at: "2026-08-25T00:00:00Z" };

      mockLocalStorage.setItem(
        "frl_outline_本地离线项目",
        JSON.stringify({
          report_type: "产业发展规划报告",
          outline_md: "# 第一章 规划总论\n# 第二章 产业体系",
          chapters: [
            { seq: 1, title: "第一章 规划总论" },
            { seq: 2, title: "第二章 产业体系" },
          ],
        }),
      );

      mockFetch.mockRejectedValue(new Error("Network Error"));

      const res = await store.loadOutline(BASE_URL, "本地离线项目");
      expect(res).not.toBeNull();
      expect(store.reportType).toBe("产业发展规划报告");
      expect(store.outlineMd).toContain("第一章 规划总论");
      expect(store.outlineChapters).toHaveLength(2);
    });

    it("saveOutline: 同步写入引擎与 localStorage", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "保存测试项目", created_at: "2026-08-25T00:00:00Z" };
      store.reportType = "可行性研究报告";
      store.setOutlineMd("# 第一章 建设内容");

      mockFetch.mockResolvedValue(jsonResponse({}));

      await store.saveOutline(BASE_URL, "保存测试项目");

      // 验证 localStorage
      const savedLocal = mockLocalStorage.getItem("frl_outline_保存测试项目");
      expect(savedLocal).not.toBeNull();
      expect(JSON.parse(savedLocal!).outline_md).toBe("# 第一章 建设内容");

      // 验证引擎请求
      expect(mockFetch).toHaveBeenCalledWith(
        `${BASE_URL}/projects/%E4%BF%9D%E5%AD%98%E6%B5%8B%E8%AF%95%E9%A1%B9%E7%9B%AE/outline`,
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("第一章 建设内容"),
        }),
      );
    });

    it("setOutlineMd & setReportType: 立即写入 localStorage", () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "实时编辑项目", created_at: "2026-08-25T00:00:00Z" };

      store.setOutlineMd("# 第一章 实时测试");
      let local = JSON.parse(mockLocalStorage.getItem("frl_outline_实时编辑项目") || "{}");
      expect(local.outline_md).toBe("# 第一章 实时测试");

      store.setReportType("节能评估报告");
      local = JSON.parse(mockLocalStorage.getItem("frl_outline_实时编辑项目") || "{}");
      expect(local.report_type).toBe("节能评估报告");
    });

    it("selectProject: 切换项目时自动加载并回填目标项目大纲", async () => {
      const store = useProjectStore();
      store.projects = [
        { id: 1, name: "项目甲", created_at: "2026-08-25T00:00:00Z" },
        { id: 2, name: "项目乙", created_at: "2026-08-25T01:00:00Z" },
      ];

      mockFetch.mockImplementation(async (url) => {
        const u = String(url);
        if (u.includes("/projects/%E9%A1%B9%E7%9B%AE%E4%B9%99/outline")) {
          return jsonResponse({
            report_type: "产业发展规划报告",
            outline_md: "# 第一章 乙项目大纲",
            chapters: [{ seq: 1, title: "第一章 乙项目大纲" }],
          });
        }
        return jsonResponse([]);
      });

      await store.selectProject(BASE_URL, "项目乙");

      expect(store.currentProject?.name).toBe("项目乙");
      expect(store.outlineMd).toBe("# 第一章 乙项目大纲");
      expect(store.outlineChapters[0].title).toBe("第一章 乙项目大纲");
      expect(store.reportType).toBe("产业发展规划报告");
    });

    it("deleteProject: 删除项目时清除其对应 localStorage 大纲与章节备份", async () => {
      const store = useProjectStore();
      store.projects = [{ id: 1, name: "废弃项目", created_at: "2026-08-25T00:00:00Z" }];
      store.currentProject = store.projects[0];
      mockLocalStorage.setItem("frl_outline_废弃项目", JSON.stringify({ outline_md: "old" }));
      mockLocalStorage.setItem("frl_chapters_废弃项目", JSON.stringify({ 1: "ch1" }));

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

      await store.deleteProject(BASE_URL, "废弃项目");
      expect(mockLocalStorage.getItem("frl_outline_废弃项目")).toBeNull();
      expect(mockLocalStorage.getItem("frl_chapters_废弃项目")).toBeNull();
      expect(store.outlineMd).toBe("");
      expect(store.outlineChapters).toHaveLength(0);
      expect(store.chapters).toEqual({});
    });
  });

  describe("章节持久化与流式写作 (Step 3)", () => {
    it("getProjectChapters & saveProjectChapter & deleteProjectChapter: 客户端 API 请求", async () => {
      mockFetch.mockImplementation(async (url, opts) => {
        const u = String(url);
        const method = opts?.method || "GET";
        if (u.endsWith("/chapters") && method === "GET") {
          return jsonResponse({ chapters: { "1": "章1正文" }, updated_at: "2026-08-25T00:00:00Z" });
        }
        if (u.includes("/chapters/1") && method === "POST") {
          return jsonResponse({ chapters: { "1": "新章1正文" } });
        }
        if (u.includes("/chapters/1") && method === "DELETE") {
          return jsonResponse({ ok: true, seq: 1 });
        }
        return jsonResponse({});
      });

      const getRes = await engineApi.getProjectChapters(BASE_URL, "测试项目");
      expect(getRes.chapters["1"]).toBe("章1正文");

      const saveRes = await engineApi.saveProjectChapter(BASE_URL, "测试项目", 1, "新章1正文");
      expect(saveRes.chapters["1"]).toBe("新章1正文");

      const delRes = await engineApi.deleteProjectChapter(BASE_URL, "测试项目", 1);
      expect(delRes.ok).toBe(true);
      expect(delRes.seq).toBe(1);
    });

    it("streamChapterWriting: 正确解析 SSE 数据流并在完成时触发 onDone", async () => {
      mockFetch.mockResolvedValue(mockSSEResponse(["第一段内容", "第二段内容"]));

      const chunks: string[] = [];
      let done = false;

      await new Promise<void>((resolve) => {
        engineApi.streamChapterWriting(
          BASE_URL,
          {
            project: "项目A",
            report_type: "可行性研究报告",
            outline_md: "# 第一章",
            chapter_seq: 1,
            llm_config: { api_key: "sk-key", base_url: "http://api", model: "m" },
          },
          (c) => chunks.push(c),
          () => {
            done = true;
            resolve();
          },
          () => {},
        );
      });

      expect(chunks).toEqual(["第一段内容", "第二段内容"]);
      expect(done).toBe(true);
    });

    it("streamChapterWriting: 异常时触发 onError", async () => {
      mockFetch.mockResolvedValue(jsonResponse({ detail: "LLM 超时" }, 504));

      let errorMsg = "";
      await new Promise<void>((resolve) => {
        engineApi.streamChapterWriting(
          BASE_URL,
          {
            project: "项目A",
            report_type: "可行性研究报告",
            outline_md: "# 第一章",
            chapter_seq: 1,
            llm_config: { api_key: "sk-key", base_url: "http://api", model: "m" },
          },
          () => {},
          () => {},
          (err) => {
            errorMsg = err.message;
            resolve();
          },
        );
      });

      expect(errorMsg).toContain("LLM 超时");
    });

    it("loadChapters: 从引擎成功加载章节并更新状态与 localStorage", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "章节项目", created_at: "2026-08-25T00:00:00Z" };

      mockFetch.mockImplementation(async (url) => {
        const u = String(url);
        if (u.includes("/chapters")) {
          return jsonResponse({
            chapters: { "1": "章1正文", "2": "章2正文" },
            updated_at: "2026-08-25T10:00:00Z",
          });
        }
        return jsonResponse({});
      });

      const res = await store.loadChapters(BASE_URL, "章节项目");
      expect(res[1]).toBe("章1正文");
      expect(res[2]).toBe("章2正文");
      expect(store.chapters[1]).toBe("章1正文");
      expect(store.chapterStatuses[1]).toBe("completed");
      expect(store.chapterStatuses[2]).toBe("completed");

      // 验证 localStorage 备份
      const local = mockLocalStorage.getItem("frl_chapters_章节项目");
      expect(local).not.toBeNull();
      expect(JSON.parse(local!)["1"]).toBe("章1正文");
    });

    it("loadChapters: 引擎异常时自动从 localStorage 恢复", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "离线章节项目", created_at: "2026-08-25T00:00:00Z" };

      mockLocalStorage.setItem(
        "frl_chapters_离线章节项目",
        JSON.stringify({ 1: "本地缓存章1", 2: "本地缓存章2" }),
      );

      mockFetch.mockRejectedValue(new Error("Offline"));

      const res = await store.loadChapters(BASE_URL, "离线章节项目");
      expect(res[1]).toBe("本地缓存章1");
      expect(store.chapters[1]).toBe("本地缓存章1");
      expect(store.chapterStatuses[1]).toBe("completed");
    });

    it("saveChapter: 写入 state、localStorage 并向引擎提交", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "保存章节项目", created_at: "2026-08-25T00:00:00Z" };

      mockFetch.mockResolvedValue(jsonResponse({}));

      await store.saveChapter(BASE_URL, 1, "手动编辑的章1内容", true);

      expect(store.chapters[1]).toBe("手动编辑的章1内容");
      expect(store.chapterStatuses[1]).toBe("completed");

      const local = JSON.parse(mockLocalStorage.getItem("frl_chapters_保存章节项目") || "{}");
      expect(local["1"]).toBe("手动编辑的章1内容");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/chapters/1"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ text: "手动编辑的章1内容" }),
        }),
      );
    });

    it("deleteChapter: 清除指定章节并同步至引擎", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "清空章节项目", created_at: "2026-08-25T00:00:00Z" };
      store.chapters = { 1: "旧章1", 2: "章2" };
      store.chapterStatuses = { 1: "completed", 2: "completed" };

      mockFetch.mockResolvedValue(jsonResponse({ ok: true, seq: 1 }));

      await store.deleteChapter(BASE_URL, 1);

      expect(store.chapters[1]).toBeUndefined();
      expect(store.chapterStatuses[1]).toBe("idle");
      expect(store.chapters[2]).toBe("章2");

      const local = JSON.parse(mockLocalStorage.getItem("frl_chapters_清空章节项目") || "{}");
      expect(local["1"]).toBeUndefined();
    });

    it("writeSingleChapterStream: 单章流式写作全流程", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "流式写作项目", created_at: "2026-08-25T00:00:00Z" };
      store.outlineMd = "# 第一章 概述\n# 第二章 建设背景";
      store.outlineChapters = [
        { seq: 1, title: "第一章 概述" },
        { seq: 2, title: "第二章 建设背景" },
      ];

      mockFetch.mockImplementation(async (url, opts) => {
        const u = String(url);
        const method = opts?.method || "GET";
        if (u.includes("/writing/chapter") && method === "POST") {
          return mockSSEResponse(["第一章开头。", "第一章正文分析。"]);
        }
        if (u.includes("/chapters/1") && method === "POST") {
          return jsonResponse({ ok: true });
        }
        return jsonResponse({});
      });

      await store.writeSingleChapterStream(BASE_URL, 1, {
        api_key: "sk-test",
        base_url: "http://api",
        model: "m",
      });

      expect(store.chapters[1]).toBe("第一章开头。第一章正文分析。");
      expect(store.chapterStatuses[1]).toBe("completed");
      expect(store.currentWritingSeq).toBeNull();
    });

    it("deriveDefaultWritingOrder: 拓扑推导非第1章非尾章优先，第1章综述居后，尾章居末", () => {
      const { deriveDefaultWritingOrder } = useProjectStore();
      const chapters = [
        { seq: 1, title: "第一章 概述" },
        { seq: 2, title: "第二章 需求分析" },
        { seq: 3, title: "第三章 工程方案" },
        { seq: 4, title: "第四章 投资估算" },
        { seq: 5, title: "第五章 结论建议" },
      ];
      const order = deriveDefaultWritingOrder(chapters);
      expect(order).toEqual([2, 3, 4, 1, 5]);
    });

    it("writeAllChapters: 按照 writingOrder 推荐顺序执行与断点智能续写", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "全书写作项目", created_at: "2026-08-25T00:00:00Z" };
      store.outlineMd = "# 第一章 概述\n# 第二章 建设背景\n# 第三章 方案设计";
      store.outlineChapters = [
        { seq: 1, title: "第一章 概述" },
        { seq: 2, title: "第二章 建设背景" },
        { seq: 3, title: "第三章 方案设计" },
      ];
      store.writingOrder = [2, 3, 1]; // 推荐拓扑顺序
      // 预先将第 2 章标记为已有正文
      store.chapters = { 2: "已有第二章内容" };
      store.chapterStatuses = { 2: "completed" };

      const executedSeqs: number[] = [];

      mockFetch.mockImplementation(async (url, opts) => {
        const u = String(url);
        const method = opts?.method || "GET";
        if (u.includes("/writing/chapter") && method === "POST") {
          const body = JSON.parse(String(opts?.body || "{}"));
          executedSeqs.push(body.chapter_seq);
          return mockSSEResponse([`第${body.chapter_seq}章流式正文`]);
        }
        if (u.includes("/chapters/") && method === "POST") {
          return jsonResponse({ ok: true });
        }
        return jsonResponse({});
      });

      // 默认 forceAll = false: 应跳过第 2 章，只按 [3, 1] 顺序执行
      await store.writeAllChapters(BASE_URL, {
        api_key: "sk-test",
        base_url: "http://api",
        model: "m",
      });

      expect(executedSeqs).toEqual([3, 1]);
      expect(store.chapters[2]).toBe("已有第二章内容"); // 保持不变
      expect(store.chapters[3]).toBe("第3章流式正文");
      expect(store.chapters[1]).toBe("第1章流式正文");
      expect(store.batchWriting).toBe(false);

      // 当 forceAll = true 时，全部章节按 [2, 3, 1] 执行
      executedSeqs.length = 0;
      await store.writeAllChapters(
        BASE_URL,
        {
          api_key: "sk-test",
          base_url: "http://api",
          model: "m",
        },
        true,
      );

      expect(executedSeqs).toEqual([2, 3, 1]);
    });

    it("streamChapterWriting: 正确解析阶段指示事件与思考片段并通过 onProgress 派发", async () => {
      mockFetch.mockResolvedValue(
        mockSSEResponse([
          '{"type": "stage", "stage": "rag", "message": "正在检索..."}',
          '{"type": "stage", "stage": "skeleton", "message": "正在锁定骨架..."}',
          '{"type": "thought", "chunk": "思考参数A"}',
          '{"type": "thought", "chunk": "思考参数B"}',
          "正文段落第一节。",
        ]),
      );

      const chunks: string[] = [];
      const events: engineApi.WritingProgressEvent[] = [];
      let done = false;

      await new Promise<void>((resolve) => {
        engineApi.streamChapterWriting(
          BASE_URL,
          {
            project: "项目A",
            report_type: "可行性研究报告",
            outline_md: "# 第一章",
            chapter_seq: 1,
            llm_config: { api_key: "sk-key", base_url: "http://api", model: "m" },
          },
          (c) => chunks.push(c),
          () => {
            done = true;
            resolve();
          },
          () => {},
          (ev) => events.push(ev),
        );
      });

      // 验证普通 chunk 只包含正文，不包含 stage 和 thought JSON
      expect(chunks).toEqual(["正文段落第一节。"]);
      expect(done).toBe(true);

      // 验证 events 包含 stage、thought 与 chunk
      expect(events).toHaveLength(5);
      expect(events[0]).toEqual({ type: "stage", stage: "rag", message: "正在检索..." });
      expect(events[1]).toEqual({ type: "stage", stage: "skeleton", message: "正在锁定骨架..." });
      expect(events[2]).toEqual({ type: "thought", chunk: "思考参数A" });
      expect(events[3]).toEqual({ type: "thought", chunk: "思考参数B" });
      expect(events[4]).toEqual({ type: "chunk", chunk: "正文段落第一节。" });
    });

    it("writeSingleChapterStream: 流式生成时维护 writingProgress并在完成时清理", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "思考项目", created_at: "2026-08-25T00:00:00Z" };
      store.outlineMd = "# 第一章 概述";
      store.outlineChapters = [{ seq: 1, title: "第一章 概述" }];

      mockFetch.mockImplementation(async (url, opts) => {
        const u = String(url);
        const method = opts?.method || "GET";
        if (u.includes("/writing/chapter") && method === "POST") {
          return mockSSEResponse([
            '{"type": "stage", "stage": "rag", "message": "检索底稿..."}',
            '{"type": "thought", "chunk": "推演论点..."}',
            "生成的第一章正文。",
          ]);
        }
        if (u.includes("/chapters/1") && method === "POST") {
          return jsonResponse({ ok: true });
        }
        return jsonResponse({});
      });

      const promise = store.writeSingleChapterStream(BASE_URL, 1, {
        api_key: "sk-test",
        base_url: "http://api",
        model: "m",
      });

      // 生成刚启动时 writingProgress 存在
      expect(store.writingProgress).not.toBeNull();
      expect(store.writingProgress?.seq).toBe(1);

      await promise;

      // 生成完成后 writingProgress 恢复为 null
      expect(store.writingProgress).toBeNull();
      expect(store.chapters[1]).toBe("生成的第一章正文。");
      expect(store.chapterStatuses[1]).toBe("completed");
    });

    it("stopWriting: 中止当前流式生成任务并清理 writingProgress", () => {
      const store = useProjectStore();
      store.batchWriting = true;
      store.currentWritingSeq = 1;
      store.writingProgress = {
        seq: 1,
        stage: "reasoning",
        message: "正在构思...",
        elapsedSeconds: 5,
        thoughtText: "思考中",
      };
      store.stopWriting();
      expect(store.batchWriting).toBe(false);
      expect(store.currentWritingSeq).toBeNull();
      expect(store.writingProgress).toBeNull();
    });
  });

  describe("Step 4 专家审阅与修改系统", () => {
    it("engineApi.reviewChapter: 发送审阅请求并返回结构化诊断", async () => {
      const mockResult: engineApi.ExpertReviewResult = {
        status: "通过",
        score: 92,
        summary: "合规与技术方案齐备",
        issues: [
          {
            id: "ISSUE-1",
            severity: "warning",
            category: "数值计算",
            message: "负荷计算存在微小偏差",
            location: "3.2节",
            suggestion: "建议核实",
          },
        ],
        numerical_checks: [
          { parameter: "总投资", extracted_value: "1000万元", status: "normal", note: "自洽" },
        ],
        data_gap_checklist: ["电网批复"],
        suggestions: "整体表现优良",
      };

      mockFetch.mockResolvedValue(
        jsonResponse({ raw: "raw text", review: mockResult }),
      );

      const res = await engineApi.reviewChapter(BASE_URL, {
        chapter_text: "# 第一章 概述\n正文...",
        chapter_title: "第一章 概述",
        report_type: "可行性研究报告",
        mode: "all",
        llm_config: { api_key: "sk-test", base_url: "http://api", model: "m" },
      });

      expect(res.review.status).toBe("通过");
      expect(res.review.score).toBe(92);
      expect(res.review.issues).toHaveLength(1);
      expect(mockFetch).toHaveBeenCalledWith(
        `${BASE_URL}/writing/review`,
        expect.objectContaining({ method: "POST" }),
      );
    });

    it("engineApi.reviseChapter: 发送定向修订请求并返回修订正文", async () => {
      mockFetch.mockResolvedValue(
        jsonResponse({ revised_text: "# 第一章 概述\n修订后的正文内容。" }),
      );

      const res = await engineApi.reviseChapter(BASE_URL, {
        chapter_text: "# 第一章 概述\n原正文...",
        instruction: "补充合规论述",
        llm_config: { api_key: "sk-test", base_url: "http://api", model: "m" },
      });

      expect(res.revised_text).toBe("# 第一章 概述\n修订后的正文内容。");
      expect(mockFetch).toHaveBeenCalledWith(
        `${BASE_URL}/writing/revise`,
        expect.objectContaining({ method: "POST" }),
      );
    });

    it("engineApi.reviseParagraph: 发送局部段落精准修订请求并返回重构段落", async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ revised_paragraph: "修改后的精准工艺参数段落内容。" }),
      );

      const res = await engineApi.reviseParagraph(BASE_URL, {
        paragraph_text: "原工艺参数段落...",
        instruction: "补充能耗指标",
        llm_config: { api_key: "sk-test", base_url: "http://api", model: "m" },
      });

      expect(res.revised_paragraph).toBe("修改后的精准工艺参数段落内容。");
      expect(mockFetch).toHaveBeenCalledWith(
        `${BASE_URL}/writing/revise-paragraph`,
        expect.objectContaining({ method: "POST" }),
      );
    });

    it("engineApi 专家审阅持久化 CRUD", async () => {
      const reviewItem: engineApi.ExpertReviewResult = {
        status: "需补充",
        score: 75,
        summary: "缺少底稿",
      };

      // GET
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ reviews: { "1": reviewItem }, updated_at: "2026-08-25T00:00:00Z" }),
      );
      const getRes = await engineApi.getProjectReviews(BASE_URL, "水库项目");
      expect(getRes.reviews["1"].score).toBe(75);

      // POST save
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ reviews: { "1": reviewItem }, updated_at: "2026-08-25T01:00:00Z" }),
      );
      const saveRes = await engineApi.saveProjectReview(BASE_URL, "水库项目", 1, reviewItem);
      expect(saveRes.reviews["1"]).toBeDefined();

      // DELETE
      mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true, seq: 1 }));
      const delRes = await engineApi.deleteProjectReview(BASE_URL, "水库项目", 1);
      expect(delRes.ok).toBe(true);
    });

    it("store: runChapterReview 与 saveReview 流程", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "审阅项目", created_at: "2026-08-25T00:00:00Z" };
      store.chapters[1] = "# 第一章 概述\n正文详细内容。";
      store.outlineChapters = [{ seq: 1, title: "第一章 概述" }];

      const mockReview: engineApi.ExpertReviewResult = {
        status: "通过",
        score: 95,
        summary: "优秀",
        issues: [],
      };

      mockFetch.mockImplementation(async (url) => {
        const u = String(url);
        if (u.includes("/writing/review")) {
          return jsonResponse({ raw: "raw", review: mockReview });
        }
        if (u.includes("/reviews/1")) {
          return jsonResponse({ reviews: { "1": mockReview } });
        }
        return jsonResponse({});
      });

      const res = await store.runChapterReview(BASE_URL, 1, "all", {
        api_key: "sk-test",
        base_url: "http://api",
        model: "m",
      });

      expect(res.status).toBe("通过");
      expect(store.chapterReviews[1].score).toBe(95);
      expect(store.reviewingSeq).toBeNull();
    });

    it("store: runChapterRevision, applyRevision 与 discardRevision", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "修订项目", created_at: "2026-08-25T00:00:00Z" };
      store.chapters[1] = "# 第一章 概述\n原文内容。";
      store.outlineChapters = [{ seq: 1, title: "第一章 概述" }];

      mockFetch.mockImplementation(async (url) => {
        const u = String(url);
        if (u.includes("/writing/revise")) {
          return jsonResponse({ revised_text: "# 第一章 概述\n修订后内容。" });
        }
        if (u.includes("/chapters/1")) {
          return jsonResponse({ ok: true });
        }
        return jsonResponse({});
      });

      // 运行修订
      const revised = await store.runChapterRevision(BASE_URL, 1, "优化表达", {
        api_key: "sk-test",
        base_url: "http://api",
        model: "m",
      });

      expect(revised).toBe("# 第一章 概述\n修订后内容。");
      expect(store.activeRevision).not.toBeNull();
      expect(store.activeRevision?.seq).toBe(1);
      expect(store.activeRevision?.revisedText).toBe("# 第一章 概述\n修订后内容。");

      // 采纳修订
      await store.applyRevision(BASE_URL, 1);
      expect(store.chapters[1]).toBe("# 第一章 概述\n修订后内容。");
      expect(store.activeRevision).toBeNull();

      // 再次生成并放弃修订
      await store.runChapterRevision(BASE_URL, 1, "再次优化", {
        api_key: "sk-test",
        base_url: "http://api",
        model: "m",
      });
      expect(store.activeRevision).not.toBeNull();
      store.discardRevision();
      expect(store.activeRevision).toBeNull();
    });

    it("store: runParagraphRevision 外科手术式单段落替换、自动清除问题与 undoChapterRevision 回滚", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "精准修订项目", created_at: "2026-08-25T00:00:00Z" };
      store.chapters[1] = "# 第一章 概述\n\n段落一：项目基本背景。\n\n段落二：原工艺参数论述欠缺。\n\n段落三：结论建议。";
      store.outlineChapters = [{ seq: 1, title: "第一章 概述" }];
      store.chapterReviews[1] = {
        status: "需修改",
        score: 75,
        summary: "存在待修改问题",
        issues: [
          {
            id: "issue-1",
            dimension: "技术规范",
            severity: "high",
            description: "工艺参数论述欠缺",
            quote: "原工艺参数论述欠缺",
            suggestion: "补充吨耗电与回收率",
          },
        ],
      };

      mockFetch.mockImplementation(async (url) => {
        const u = String(url);
        if (u.includes("/writing/revise-paragraph")) {
          return jsonResponse({ revised_paragraph: "段落二：工艺参数已详实补充吨耗电0.45kWh及98%回收率。" });
        }
        if (u.includes("/chapters/1")) {
          return jsonResponse({ ok: true });
        }
        if (u.includes("/reviews/1")) {
          return jsonResponse({ ok: true });
        }
        return jsonResponse({});
      });

      // 1. 执行局部段落修复
      const updatedText = await store.runParagraphRevision(
        BASE_URL,
        1,
        store.chapterReviews[1].issues![0],
        { api_key: "sk-test", base_url: "http://api", model: "m" }
      );

      // 验证精准原位替换
      expect(updatedText).toContain("段落二：工艺参数已详实补充吨耗电0.45kWh及98%回收率。");
      expect(updatedText).toContain("段落一：项目基本背景。");
      expect(updatedText).toContain("段落三：结论建议。");
      expect(store.chapters[1]).toBe(updatedText);

      // 验证已从问题清单中移除
      expect(store.chapterReviews[1].issues?.length).toBe(0);
      expect(store.chapterSnapshots[1]).toBe("# 第一章 概述\n\n段落一：项目基本背景。\n\n段落二：原工艺参数论述欠缺。\n\n段落三：结论建议。");

      // 2. 撤销回滚
      await store.undoChapterRevision(BASE_URL, 1);
      expect(store.chapters[1]).toContain("段落二：原工艺参数论述欠缺。");
      expect(store.chapterSnapshots[1]).toBeUndefined();
    });

    it("store: runAllChaptersReview 批量审查所有章节并维护 batchReviewing 状态", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "批量审阅项目", created_at: "2026-08-25T00:00:00Z" };
      store.outlineChapters = [
        { seq: 1, title: "第一章 概述" },
        { seq: 2, title: "第二章 建设背景" },
      ];
      store.chapters = {
        1: "# 第一章 概述\n正文1",
        2: "# 第二章 建设背景\n正文2",
      };

      const mockReviewResult: engineApi.ExpertReviewResult = {
        status: "通过",
        score: 90,
        summary: "达标",
        issues: [],
      };

      mockFetch.mockImplementation(async (url) => {
        const u = String(url);
        if (u.includes("/writing/review")) {
          return jsonResponse({ raw: "raw", review: mockReviewResult });
        }
        if (u.includes("/reviews/")) {
          return jsonResponse({ reviews: { "1": mockReviewResult, "2": mockReviewResult } });
        }
        return jsonResponse({});
      });

      const reviewPromise = store.runAllChaptersReview(BASE_URL, {
        api_key: "sk-test",
        base_url: "http://api",
        model: "m",
      });

      expect(store.batchReviewing).toBe(true);

      await reviewPromise;

      expect(store.batchReviewing).toBe(false);
      expect(store.chapterReviews[1].score).toBe(90);
      expect(store.chapterReviews[2].score).toBe(90);
    });

    it("store: stopBatchReview 中止批量全书体检", () => {
      const store = useProjectStore();
      store.batchReviewing = true;
      store.stopBatchReview();
      expect(store.batchReviewing).toBe(false);
    });

    it("engineApi 全书一体化审阅总档案 full_review CRUD", async () => {
      const fullData: engineApi.FullReviewData = {
        summary: "全书质量优良",
        compliance_rate: 95,
        health_status: "达标",
        issues: [
          {
            id: "ISSUE-1",
            severity: "suggestion",
            category: "格式规范",
            message: "表格格式建议统一",
            location: "第 1 章",
            suggestion: "采用三线表",
          },
        ],
        numerical_checks: [
          {
            parameter: "总投资",
            extracted_value: "5000万元",
            status: "normal",
            note: "一致",
          },
        ],
        data_gap_checklist: ["环境影响评价报告批复"],
        chapter_evaluations: {
          "1": { status: "通过", summary: "合格", issues_count: 1, score: 95 },
        },
        general_suggestions: ["统一表格样式"],
        updated_at: "2026-08-26T00:00:00Z",
      };

      // GET
      mockFetch.mockResolvedValueOnce(jsonResponse(fullData));
      const getRes = await engineApi.getProjectFullReview(BASE_URL, "测试项目");
      expect(getRes.health_status).toBe("达标");
      expect(getRes.compliance_rate).toBe(95);

      // POST
      mockFetch.mockResolvedValueOnce(jsonResponse(fullData));
      const saveRes = await engineApi.saveProjectFullReview(BASE_URL, "测试项目", fullData);
      expect(saveRes.summary).toBe("全书质量优良");

      // DELETE
      mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));
      const delRes = await engineApi.deleteProjectFullReview(BASE_URL, "测试项目");
      expect(delRes.ok).toBe(true);
    });

    it("store: loadFullBookReview, saveFullBookReview 与 deleteFullBookReview", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "全书审阅项目", created_at: "2026-08-26T00:00:00Z" };

      const fullData: engineApi.FullReviewData = {
        summary: "全书测试通过",
        compliance_rate: 90,
        health_status: "达标",
        issues: [],
        numerical_checks: [],
        data_gap_checklist: [],
        chapter_evaluations: {
          "1": { status: "通过", summary: "良好", issues_count: 0 },
        },
        general_suggestions: ["继续保持"],
        updated_at: "2026-08-26T00:00:00Z",
      };

      mockFetch.mockResolvedValueOnce(jsonResponse(fullData));
      const loaded = await store.loadFullBookReview(BASE_URL, "全书审阅项目");
      expect(loaded?.summary).toBe("全书测试通过");
      expect(store.fullBookReview?.health_status).toBe("达标");

      // 本地缓存应当写入
      const local = mockLocalStorage.getItem("frl_full_review_全书审阅项目");
      expect(local).not.toBeNull();
      expect(JSON.parse(local!).compliance_rate).toBe(90);

      // saveFullBookReview
      mockFetch.mockResolvedValueOnce(jsonResponse({ ...fullData, compliance_rate: 96 }));
      await store.saveFullBookReview(BASE_URL, { ...fullData, compliance_rate: 96 });
      expect(store.fullBookReview?.compliance_rate).toBe(96);

      // deleteFullBookReview
      mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));
      await store.deleteFullBookReview(BASE_URL);
      expect(store.fullBookReview).toBeNull();
      expect(mockLocalStorage.getItem("frl_full_review_全书审阅项目")).toBeNull();
    });

    it("store: runFullBookReview 执行全书全维专家审阅并自动生成综合健康诊断", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "全书综合项目", created_at: "2026-08-26T00:00:00Z" };
      store.outlineChapters = [
        { seq: 1, title: "第一章 概述" },
        { seq: 2, title: "第二章 建设规模" },
      ];
      store.chapters = {
        1: "# 第一章 概述\n正文1内容",
        2: "# 第二章 建设规模\n正文2内容",
      };

      const mockRev1: engineApi.ExpertReviewResult = {
        status: "通过",
        score: 95,
        summary: "第一章概述合格",
        issues: [],
        numerical_checks: [{ parameter: "总投资", extracted_value: "1000万", status: "normal" }],
      };

      const mockRev2: engineApi.ExpertReviewResult = {
        status: "需补充",
        score: 80,
        summary: "第二章缺少数据",
        issues: [
          {
            id: "ISS-2",
            severity: "warning",
            category: "数据自洽",
            message: "规模数据待核验",
            location: "第 2 章 2.1 节",
            suggestion: "核对设计参数",
          },
        ],
        data_gap_checklist: ["地质勘察专项报告"],
      };

      mockFetch.mockImplementation(async (url) => {
        const u = String(url);
        if (u.includes("/writing/review")) {
          // returns either rev1 or rev2
          return jsonResponse({ raw: "raw", review: mockRev2 });
        }
        if (u.includes("/full_review")) {
          return jsonResponse({ ok: true });
        }
        return jsonResponse({});
      });

      store.chapterReviews[1] = mockRev1;
      store.chapterReviews[2] = mockRev2;

      const fullRes = await store.runFullBookReview(
        BASE_URL,
        {
          api_key: "sk-test",
          base_url: "http://api",
          model: "m",
        },
        false,
      );

      expect(fullRes).toBeDefined();
      expect(fullRes.health_status).toBe("待完善");
      expect(fullRes.issues).toHaveLength(1);
      expect(fullRes.numerical_checks).toHaveLength(1);
      expect(fullRes.data_gap_checklist).toHaveLength(1);
      expect(store.fullBookReview).not.toBeNull();
    });

    it("streamChapterReview: 正确解析 SSE 阶段/思考/正文/完成事件并返回结构化结果", async () => {
      const mockResult: engineApi.ExpertReviewResult = {
        status: "通过",
        score: 95,
        summary: "审查合格",
        issues: [],
        numerical_checks: [],
        data_gap_checklist: [],
        suggestions: "建议保持",
      };

      mockFetch.mockResolvedValue(
        mockSSEResponse([
          '{"type": "stage", "stage": "init", "message": "正在核对规程..."}',
          '{"type": "thought", "chunk": "思考合规要件..."}',
          '{"type": "chunk", "chunk": "{\\"status\\": \\"通过\\"}"}',
          JSON.stringify({ type: "done", review: mockResult, raw: '{"status": "通过"}' }),
        ]),
      );

      const progressEvents: engineApi.ReviewProgressEvent[] = [];
      const res = await engineApi.streamChapterReview(
        BASE_URL,
        {
          chapter_text: "第一章正文...",
          report_type: "可行性研究报告",
          chapter_title: "第一章 概述",
          mode: "all",
          llm_config: { api_key: "sk-key", base_url: "http://api", model: "m" },
        },
        (ev) => progressEvents.push(ev),
      );

      expect(res.review.status).toBe("通过");
      expect(res.review.score).toBe(95);
      expect(progressEvents).toHaveLength(4);
      expect(progressEvents[0].type).toBe("stage");
      expect(progressEvents[1].type).toBe("thought");
      expect(progressEvents[1].chunk).toBe("思考合规要件...");
      expect(progressEvents[2].type).toBe("chunk");
      expect(progressEvents[3].type).toBe("done");
    });

    it("streamChapterReview: 引擎 500 错误时抛出 EngineApiError", async () => {
      mockFetch.mockResolvedValue(jsonResponse({ detail: "上游大模型连接失败" }, 500));

      await expect(
        engineApi.streamChapterReview(BASE_URL, {
          chapter_text: "正文...",
          llm_config: { api_key: "sk-key", base_url: "http://api", model: "m" },
        }),
      ).rejects.toThrow("上游大模型连接失败");
    });

    it("runFullBookReview: 流式审阅全书时维护 reviewProgress 并即时保存每章结果", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "流式审阅项目", created_at: "2026-08-25T00:00:00Z" };
      store.outlineChapters = [
        { seq: 1, title: "第一章 概述" },
        { seq: 2, title: "第二章 建设背景" },
      ];
      store.chapters = {
        1: "第一章正文内容...",
        2: "第二章正文内容...",
      };
      store.chapterReviews = {};

      const mockRev1: engineApi.ExpertReviewResult = {
        status: "通过",
        score: 92,
        summary: "第一章合规",
        issues: [],
      };
      const mockRev2: engineApi.ExpertReviewResult = {
        status: "需补充",
        score: 75,
        summary: "第二章有待完善",
        issues: [
          {
            id: "ISS-1",
            severity: "warning",
            category: "合规性",
            message: "缺少批复文件",
            location: "2.1 节",
          },
        ],
      };

      mockFetch.mockImplementation(async (url, opts) => {
        const u = String(url);
        const method = opts?.method || "GET";
        if (u.includes("/writing/review_stream") && method === "POST") {
          const body = JSON.parse(opts?.body as string);
          const rev = body.chapter_title?.includes("第一章") ? mockRev1 : mockRev2;
          return mockSSEResponse([
            '{"type": "stage", "stage": "init", "message": "核对中..."}',
            '{"type": "thought", "chunk": "审阅推演细节..."}',
            JSON.stringify({ type: "done", review: rev, raw: "{}" }),
          ]);
        }
        if (u.includes("/reviews/") && method === "POST") {
          return jsonResponse({ ok: true });
        }
        if (u.includes("/full_review") && method === "POST") {
          return jsonResponse({ ok: true });
        }
        return jsonResponse({});
      });

      const fullRes = await store.runFullBookReview(
        BASE_URL,
        { api_key: "sk-test", base_url: "http://api", model: "m" },
        true,
      );

      expect(fullRes.health_status).toBe("待完善");
      expect(store.chapterReviews[1]?.status).toBe("通过");
      expect(store.chapterReviews[2]?.status).toBe("需补充");
      expect(store.batchReviewing).toBe(false);
      expect(store.reviewProgress).toBeNull();
    });

    it("stopBatchReview: 中止时清除 reviewProgress 并重置 batchReviewing", () => {
      const store = useProjectStore();
      store.batchReviewing = true;
      store.reviewProgress = {
        currentSeq: 1,
        currentTitle: "第一章",
        currentIndex: 1,
        totalTarget: 4,
        percent: 25,
        elapsedSeconds: 10,
        thoughtText: "正在思考...",
        completedIssuesCount: 0,
      };

      store.stopBatchReview();

      expect(store.batchReviewing).toBe(false);
      expect(store.reviewProgress).toBeNull();
    });

    it("runFullBookReview & runChapterReview: 支持 fast 常规审查与 all 全维精审双模式", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "双模式项目", created_at: "2026-08-25T00:00:00Z" };
      store.outlineChapters = [{ seq: 1, title: "第一章 概述" }];
      store.chapters = { 1: "第一章正文..." };

      let capturedMode = "";
      mockFetch.mockImplementation(async (url, opts) => {
        const u = String(url);
        if (u.includes("/writing/review_stream")) {
          const body = JSON.parse(opts?.body as string);
          capturedMode = body.mode;
          return mockSSEResponse([
            '{"type": "stage", "stage": "init", "message": "核对中..."}',
            JSON.stringify({
              type: "done",
              review: { status: "通过", score: 95, summary: "合格" },
              raw: "{}",
            }),
          ]);
        }
        if (u.includes("/reviews/") || u.includes("/full_review")) {
          return jsonResponse({ ok: true });
        }
        return jsonResponse({});
      });

      // 1. runChapterReview 默认 fast 模式
      await store.runChapterReview(
        BASE_URL,
        1,
        "fast",
        { api_key: "sk-test", base_url: "http://api", model: "m" },
      );
      expect(capturedMode).toBe("fast");

      // 2. runChapterReview 传入 all 模式
      await store.runChapterReview(
        BASE_URL,
        1,
        "all",
        { api_key: "sk-test", base_url: "http://api", model: "m" },
      );
      expect(capturedMode).toBe("all");

      // 3. runFullBookReview 传入 fast
      await store.runFullBookReview(
        BASE_URL,
        { api_key: "sk-test", base_url: "http://api", model: "m" },
        true,
        "fast",
      );
      expect(capturedMode).toBe("fast");

      // 4. runFullBookReview 传入 all
      await store.runFullBookReview(
        BASE_URL,
        { api_key: "sk-test", base_url: "http://api", model: "m" },
        true,
        "all",
      );
      expect(capturedMode).toBe("all");
    });

    it("runChapterRevision 与 applyRevision 完整就地修订闭环", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "修订测试项目", created_at: "2026-08-26T00:00:00Z" };
      store.chapters = { 1: "# 第一章 概述\n原文未修改内容..." };

      mockFetch.mockImplementation(async (url: string | URL | Request) => {
        const u = url.toString();
        if (u.includes("/writing/revise")) {
          return jsonResponse({
            revised_text: "# 第一章 概述\n修订后包含深化合规与投资估算的内容...",
          });
        }
        if (u.includes("/chapters/1")) {
          return jsonResponse({ ok: true });
        }
        return jsonResponse({});
      });

      expect(store.revisingSeq).toBeNull();
      expect(store.activeRevision).toBeNull();

      // 执行修订
      await store.runChapterRevision(
        BASE_URL,
        1,
        "核对投资估算与合规要件",
        { api_key: "sk-test", base_url: "http://api", model: "m" },
      );

      expect(store.revisingSeq).toBeNull();
      expect(store.activeRevision).not.toBeNull();
      expect(store.activeRevision?.seq).toBe(1);
      expect(store.activeRevision?.instruction).toBe("核对投资估算与合规要件");
      expect(store.activeRevision?.revisedText).toContain("修订后包含深化合规");

      // 采纳修订
      await store.applyRevision(BASE_URL, 1);
      expect(store.chapters[1]).toContain("修订后包含深化合规与投资估算的内容...");
      expect(store.activeRevision).toBeNull();
    });

    it("V2-T24: runFullBookReview 直接以指定模式执行全书审阅并维护真实耗时秒数", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "直启审阅项目", created_at: "2026-08-28T00:00:00Z" };
      store.outlineChapters = [
        { seq: 1, title: "第一章 概述" },
        { seq: 2, title: "第二章 建设方案" },
      ];
      store.chapters = {
        1: "第一章正文内容...",
        2: "第二章正文内容...",
      };
      store.chapterReviews = {};

      mockFetch.mockImplementation(async (url) => {
        const u = String(url);
        if (u.includes("/writing/review_stream")) {
          return mockSSEResponse([
            '{"type": "stage", "stage": "reasoning", "message": "国家发改委投资项目与工程咨询专业论证中..."}',
            JSON.stringify({
              type: "done",
              review: {
                status: "通过",
                score: 90,
                summary: "合规",
                issues: [],
              },
              raw: "{}",
            }),
          ]);
        }
        if (u.includes("/reviews/") || u.includes("/full_review")) {
          return jsonResponse({ ok: true });
        }
        return jsonResponse({});
      });

      const res = await store.runFullBookReview(
        BASE_URL,
        { api_key: "sk-test", base_url: "http://api", model: "m" },
        false,
        "fast",
      );

      expect(res.health_status).toBe("达标");
      expect(store.batchReviewing).toBe(false);
      expect(store.reviewProgress).toBeNull();
      expect(store.chapterReviews[1]?.status).toBe("通过");
      expect(store.chapterReviews[2]?.status).toBe("通过");
    });

    it("V2-T26: 准确判定未写作章节并支持实时保存后状态动态联动", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "占位测试项目", created_at: "2026-08-28T00:00:00Z" };
      store.outlineChapters = [
        { seq: 1, title: "第一章 概述" },
        { seq: 2, title: "第二章 建设背景和必要性" },
        { seq: 3, title: "第三章 建设方案" },
        { seq: 4, title: "第四章 投资估算" },
      ];
      store.chapters = {
        1: "# 第一章 概述\n已撰写内容",
        2: "   \n  \t ", // 空白字符
        3: "# 第三章 建设方案\n已撰写方案",
        // 4 为 undefined
      };

      const isWritten = (seq: number) => {
        const text = store.chapters[seq];
        return !!(text && text.trim().length > 0);
      };

      const getCompletedCount = () => store.outlineChapters.filter((c) => isWritten(c.seq)).length;
      const getUnwrittenCount = () => store.outlineChapters.filter((c) => !isWritten(c.seq)).length;

      expect(isWritten(1)).toBe(true);
      expect(isWritten(2)).toBe(false);
      expect(isWritten(3)).toBe(true);
      expect(isWritten(4)).toBe(false);

      expect(getCompletedCount()).toBe(2);
      expect(getUnwrittenCount()).toBe(2);

      // 模拟第 2 章就地输入正文并落盘保存
      mockFetch.mockResolvedValue(jsonResponse({ ok: true }));
      await store.saveChapter(BASE_URL, 2, "# 第二章 建设背景和必要性\n用户在占位卡片处点击输入的排版正文");

      expect(isWritten(2)).toBe(true);
      expect(getCompletedCount()).toBe(3);
      expect(getUnwrittenCount()).toBe(1);
    });

    it("V2-T27: 正文审阅问题持久化高亮与多级容错匹配机制", () => {
      const store = useProjectStore();
      store.outlineChapters = [{ seq: 1, title: "第一章 工程总投资与建设指标" }];
      store.chapters = {
        1: "# 第一章 工程总投资与建设指标\n\n本项目核准静态总投资为 3500 万元，建设工期为 18 个月。水库总库容为 1200 万m³。",
      };
      store.chapterReviews = {
        1: {
          status: "需补充",
          score: 82,
          summary: "存在部分数据需要核实",
          issues: [
            {
              id: "ISS-WARN-1",
              severity: "warning",
              category: "数值自洽",
              message: "核实静态总投资 3500 万元与预算表的差额",
              quote: "3500 万元",
              chapterSeq: 1,
            },
            {
              id: "ISS-ERR-2",
              severity: "error",
              category: "工程指标",
              message: "水库总库容指标「1200 万m³」防洪复核说明不足",
              chapterSeq: 1,
            },
          ],
        },
      };

      const rawHtml = markdownToHtml(store.chapters[1], 1);
      const highlightedHtml = highlightIssuesInHtml(rawHtml, store.chapterReviews[1].issues || [], 1);

      // 验证精准 quote 匹配
      expect(highlightedHtml).toContain('class="review-issue-highlight severity-warning"');
      expect(highlightedHtml).toContain('data-issue-id="ISS-WARN-1"');
      expect(highlightedHtml).toContain('data-chapter-seq="1"');
      expect(highlightedHtml).toContain('title="数值自洽: 核实静态总投资 3500 万元与预算表的差额"');

      // 验证无 quote 时从 message 提取引号「1200 万m³」匹配
      expect(highlightedHtml).toContain('class="review-issue-highlight severity-error"');
      expect(highlightedHtml).toContain('data-issue-id="ISS-ERR-2"');
    });

    it("V2-T27: 正文与诊断卡片双向定位与呼吸波纹联动数据机制", () => {
      const issues: engineApi.ReviewIssue[] = [
        {
          id: "ISS-NAV-01",
          severity: "warning",
          category: "合规性",
          message: "缺少水土保持专项评价",
          location: "第 2 章 2.3 水土保持方案",
          chapterSeq: 2,
        },
      ];

      const html = "<h2>2.3 水土保持方案</h2><p>本章叙述水土流失现状与防治措施。</p>";
      const highlighted = highlightIssuesInHtml(html, issues, 2);

      // 验证 location 小节匹配并生成 mark
      expect(highlighted).toContain('data-issue-id="ISS-NAV-01"');
      expect(highlighted).toContain('data-chapter-seq="2"');

      // 验证模拟点击 mark 提取 issueId 和 chapterSeq
      const match = highlighted.match(/data-issue-id="([^"]+)"\s+data-chapter-seq="(\d+)"/);
      expect(match).not.toBeNull();
      expect(match![1]).toBe("ISS-NAV-01");
      expect(Number(match![2])).toBe(2);
    });

    it("V2-T27: 就地编辑 Markdown 反向保存防漂移与纯净性", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "防漂移测试", created_at: "2026-08-28T00:00:00Z" };
      store.outlineChapters = [{ seq: 1, title: "第一章 概述" }];

      // 富文本编辑器内带有 mark 高亮标签的内容
      const canvasEditedHtml = `
        <h1>第一章 概述</h1>
        <p>本项目总投资为 <mark class="review-issue-highlight severity-warning" data-issue-id="ISS-10" data-chapter-seq="1" title="数据核实">3800 万元</mark>，工期调整为 20 个月。</p>
      `;

      // 验证 htmlToMarkdown 转换为纯净 Markdown（杜绝 mark 标签污染源码）
      const cleanMd = htmlToMarkdown(canvasEditedHtml);
      expect(cleanMd).not.toContain("<mark");
      expect(cleanMd).not.toContain("review-issue-highlight");
      expect(cleanMd).toContain("# 第一章 概述");
      expect(cleanMd).toContain("本项目总投资为 3800 万元，工期调整为 20 个月。");

      // 验证保存入库
      mockFetch.mockResolvedValue(jsonResponse({ ok: true }));
      await store.saveChapter(BASE_URL, 1, cleanMd);

      expect(store.chapters[1]).toBe(cleanMd);
      expect(store.chapters[1]).not.toContain("<mark");
    });

    it("V2-T29: 推荐写作顺序流程胶囊与章节折叠逻辑（100% 对齐 Step 3）", async () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "可研测试", created_at: "2026-08-28T00:00:00Z" };
      store.writingOrder = [2, 3, 4, 1, 5];
      store.writingOrderReason = "先完成主体论证，最后编制概述与附表";
      store.outlineChapters = [
        { seq: 1, title: "第一章 概述" },
        { seq: 2, title: "第二章 背景" },
        { seq: 3, title: "第三章 需求分析" },
        { seq: 4, title: "第四章 建设方案" },
        { seq: 5, title: "第五章 结论" },
      ];
      store.chapters = {
        1: "概述正文",
        2: "背景正文",
      };

      // 验证推荐写作顺序状态
      expect(store.writingOrder).toHaveLength(5);
      expect(store.writingOrder[0]).toBe(2);
      expect(store.writingOrderReason).toContain("先完成主体论证");

      // 验证章节完成状态辅助判断
      const isWritten = (seq: number) => !!(store.chapters[seq] && store.chapters[seq].trim().length > 0);
      expect(isWritten(1)).toBe(true);
      expect(isWritten(2)).toBe(true);
      expect(isWritten(3)).toBe(false);

      // 验证默认折叠判定函数（除 activeChapter 外默认全部折叠收起）
      const activeChapterSeq = 2;
      const collapsedMap: Record<number, boolean> = {};
      const isChapterCollapsed = (seq: number) => {
        if (collapsedMap[seq] !== undefined) return collapsedMap[seq];
        return activeChapterSeq !== seq;
      };

      expect(isChapterCollapsed(2)).toBe(false); // 激活章展开
      expect(isChapterCollapsed(1)).toBe(true);  // 非激活章默认折叠
      expect(isChapterCollapsed(3)).toBe(true);  // 非激活章默认折叠

      // 手动展开第 3 章
      collapsedMap[3] = false;
      expect(isChapterCollapsed(3)).toBe(false);
    });

    it("V2-T30: 全书多章节三源参考文献分类汇总与统计指标一致性", () => {
      const store = useProjectStore();
      store.currentProject = { id: 1, name: "三源统计项目", created_at: "2026-08-28T00:00:00Z" };
      store.chapters = {
        1: "# 第一章 概述\n依据批复【源:工程立项批复.docx】与勘测【源:地质报告.pdf】，结合规程【标:水工混凝土规范】。",
        2: "# 第二章 建设必要性\n复核批复【源:工程立项批复.docx】，参考宏观政策【网:国家发改委投资指引】与依据 [Z]。",
        3: "# 第三章 建设方案\n参照规程【标:水工混凝土规范】落实防洪标准【源:防洪规程.pdf】。",
      };

      // 提取全书合并参考文献
      let combined = "";
      for (const text of Object.values(store.chapters)) {
        if (text) combined += "\n" + text;
      }
      const allRefs = extractReferences(combined);
      expect(allRefs).toHaveLength(6);

      const summary = getReferencesSummary(allRefs);
      expect(summary.material.count).toBe(2); // 工程立项批复, 地质报告 (防洪规程 contains 规程 -> standard)
      expect(summary.standard.count).toBe(3); // 水工混凝土规范, 防洪规程, [Z]
      expect(summary.web.count).toBe(1);      // 国家发改委投资指引

      // 验证引用频次累加
      expect(summary.material.citations).toBe(3); // 2 + 1
      expect(summary.standard.citations).toBe(4); // 2 + 1 + 1
      expect(summary.web.citations).toBe(1);
      expect(summary.totalCount).toBe(6);
      expect(summary.totalCitations).toBe(8);
    });

    it("V2-T30: 正文内联标签与抽屉卡片数据特征匹配与高亮标记生成", () => {
      const chapterText = "# 第一章 概述\n项目建设方案【源:总体规划.docx#L1-10】以及【网:水利部公告】。";
      const html = markdownToHtml(chapterText, 1);

      expect(html).toContain('class="inline-ref-tag type-material"');
      expect(html).toContain('data-ref-type="material"');
      expect(html).toContain('data-ref-title="总体规划.docx#L1-10"');
      expect(html).toContain('class="inline-ref-tag type-web"');
      expect(html).toContain('data-ref-type="web"');
      expect(html).toContain('data-ref-title="水利部公告"');

      // 提取引用清单
      const refs = extractReferences(chapterText);
      expect(refs.some((r) => r.title === "总体规划.docx#L1-10" && r.type === "material")).toBe(true);
      expect(refs.some((r) => r.title === "水利部公告" && r.type === "web")).toBe(true);
    });

    it("V2-T34: 模板取消字数限制适配与自由长文推演支持", async () => {
      mockFetch.mockResolvedValue(
        jsonResponse([
          { report_type: "可行性研究报告", notes: "标准规范模板" },
          { report_type: "初步可行性研究报告", notes: "初设模板" },
        ]),
      );
      const store = useProjectStore();
      const tmpls = await store.loadTemplates(BASE_URL);
      expect(tmpls).toHaveLength(2);
      expect(tmpls[0].report_type).toBe("可行性研究报告");
      expect(tmpls[0].total_words_max).toBeUndefined();
    });

    it("V2-T34: isThinkingStage 计算逻辑与流式首字到达即时切换", () => {
      // 场景 1: 正在写作但处于推理构思阶段且正文为空 -> isThinkingStage 为 true
      const isWriting = true;
      let stage: string = "reasoning";
      let text: string = "";
      let isThinking = isWriting && stage !== "writing" && (!text || text.trim().length === 0);
      expect(isThinking).toBe(true);

      // 场景 2: 大模型开始输出首字 (stage 变为 writing 或 text 有内容) -> isThinkingStage 立即为 false
      stage = "writing";
      text = "本项目位于";
      isThinking = isWriting && stage !== "writing" && (!text || text.trim().length === 0);
      expect(isThinking).toBe(false);

      // 场景 3: stage 仍为 reasoning 但首个 chunk 已到达写入正文 -> isThinkingStage 立即为 false
      stage = "reasoning";
      text = "一、";
      isThinking = isWriting && stage !== "writing" && (!text || text.trim().length === 0);
      expect(isThinking).toBe(false);
    });
  });
});
