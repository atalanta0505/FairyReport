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
});

