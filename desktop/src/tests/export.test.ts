import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetch as pluginFetch } from "@tauri-apps/plugin-http";
import { exportDocx, exportMd, verifyContext } from "../lib/engineApi";

vi.mock("@tauri-apps/plugin-http", () => ({ fetch: vi.fn() }));

const BASE_URL = "http://127.0.0.1:8001";
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

describe("engineApi.verifyContext", () => {
  it("成功向 /export/verify-context 发送核验请求并返回诊断结构", async () => {
    const mockData = {
      is_consistent: true,
      score: 100,
      summary: "全书跨章节核心指标完全吻合",
      conflicts_count: 0,
      warnings_count: 0,
      passed_count: 3,
      items: [
        {
          id: "IND-PASS-1",
          type: "indicator",
          status: "pass",
          severity: "low",
          title: "核心指标「总投资」全篇数值高度自洽",
          description: "第 1 章与第 3 章均为 5000万元",
          affected_chapters: [1, 3],
          suggestion: "",
        },
      ],
    };

    mockFetch.mockResolvedValue(jsonResponse(mockData));

    const result = await verifyContext(BASE_URL, {
      project: "测试项目",
      report_type: "feasi",
      chapters: {
        "1": "第一章：总投资为5000万元",
        "3": "第三章：估算总投资为5000万元",
      },
    });

    expect(result.is_consistent).toBe(true);
    expect(result.score).toBe(100);
    expect(result.items.length).toBe(1);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe(`${BASE_URL}/export/verify-context`);
    expect(init?.method).toBe("POST");
    const body = JSON.parse(init?.body as string);
    expect(body.project).toBe("测试项目");
    expect(body.chapters["1"]).toContain("5000万元");
  });

  it("当存在矛盾时正确解析 conflict 状态与扣分结果", async () => {
    const mockData = {
      is_consistent: false,
      score: 75,
      summary: "检测到 1 处跨章节核心数据冲突",
      conflicts_count: 1,
      warnings_count: 0,
      passed_count: 1,
      items: [
        {
          id: "IND-CONFLICT-1",
          type: "indicator",
          status: "conflict",
          severity: "critical",
          title: "核心指标「总投资」在跨章节间存在数值矛盾",
          description: "第 1 章 5000万元 vs 第 3 章 6800万元",
          affected_chapters: [1, 3],
          suggestion: "建议统一为权威估算值",
        },
      ],
    };

    mockFetch.mockResolvedValue(jsonResponse(mockData));

    const result = await verifyContext(BASE_URL, {
      project: "冲突测试",
      chapters: {
        "1": "总投资为5000万元",
        "3": "总投资为6800万元",
      },
    });

    expect(result.is_consistent).toBe(false);
    expect(result.conflicts_count).toBe(1);
    expect(result.score).toBe(75);
    expect(result.items[0].status).toBe("conflict");
  });
});

describe("engineApi.exportDocx & exportMd", () => {
  it("exportDocx 发送完整合并参数并返回下载路径与大小", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({
        path: "/exports/report_2026.docx",
        size_bytes: 1048576,
        filename: "report_2026.docx",
      }),
    );

    const res = await exportDocx(BASE_URL, {
      project: "项目A",
      title: "可行性研究报告",
      chapters: { "1": "正文第一章" },
      include_refs: true,
    });

    expect(res.path).toBe("/exports/report_2026.docx");
    expect(res.size_bytes).toBe(1048576);
    expect(mockFetch.mock.calls[0][0]).toBe(`${BASE_URL}/export/docx`);
  });

  it("exportMd 发送请求并返回 md 内容与路径", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({
        path: "/exports/report_2026.md",
        size_bytes: 2048,
        content: "# 可研报告\n\n正文",
        filename: "report_2026.md",
      }),
    );

    const res = await exportMd(BASE_URL, {
      project: "项目B",
      title: "项目建议书",
      chapters: { "1": "# 第一章" },
    });

    expect(res.content).toContain("# 可研报告");
    expect(mockFetch.mock.calls[0][0]).toBe(`${BASE_URL}/export/md`);
  });
});
