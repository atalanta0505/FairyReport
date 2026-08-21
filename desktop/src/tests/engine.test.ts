import { describe, expect, it, vi } from "vitest";
import {
  ENGINE_HEALTH_MAX_ATTEMPTS,
  pollHealth,
  startEngine,
  type EngineChild,
} from "../lib/engine";

function okResponse(): Response {
  return { ok: true, status: 200 } as unknown as Response;
}
function failResponse(): Response {
  return { ok: false, status: 500 } as unknown as Response;
}

describe("pollHealth", () => {
  it("首次即 ok → 立即返回", async () => {
    const fetcher = vi.fn().mockResolvedValue(okResponse());
    await pollHealth("http://127.0.0.1:8001", { fetcher });
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher).toHaveBeenCalledWith("http://127.0.0.1:8001/health");
  });

  it("前几次失败后成功 → 在 MAX_ATTEMPTS 内重试", async () => {
    const fetcher = vi
      .fn()
      .mockRejectedValueOnce(new Error("conn refused"))
      .mockRejectedValueOnce(new Error("conn refused"))
      .mockResolvedValueOnce(okResponse());
    const sleep = vi.fn().mockResolvedValue(undefined);
    await pollHealth("http://127.0.0.1:8001", { fetcher, sleep });
    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(sleep).toHaveBeenCalledTimes(2);
  });

  it("持续失败 → 超时抛错", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("down"));
    const sleep = vi.fn().mockResolvedValue(undefined);
    await expect(
      pollHealth("http://127.0.0.1:8001", { fetcher, sleep }),
    ).rejects.toThrow("引擎健康检查超时");
    expect(fetcher).toHaveBeenCalledTimes(ENGINE_HEALTH_MAX_ATTEMPTS);
  });
});

describe("startEngine", () => {
  it("编排：选端口 → 取 cwd → spawn 正确参数 → 轮询健康 → 返回 handle", async () => {
    const killed = vi.fn();
    const child: EngineChild = { kill: killed };
    const pickFreePort = vi.fn().mockResolvedValue(8001);
    const cwdProvider = vi.fn().mockResolvedValue("/repo/root");
    const spawnProcess = vi.fn().mockResolvedValue(child);
    const fetcher = vi.fn().mockResolvedValue(okResponse());
    const sleep = vi.fn().mockResolvedValue(undefined);

    const handle = await startEngine({
      pickFreePort,
      cwdProvider,
      spawnProcess,
      fetcher,
      sleep,
    });

    expect(handle.port).toBe(8001);
    expect(handle.baseUrl).toBe("http://127.0.0.1:8001");
    // spawn 参数：python -m uvicorn engine.app.main:app --host 127.0.0.1 --port 8001
    const [args, cwd] = spawnProcess.mock.calls[0];
    expect(args).toEqual([
      "-m",
      "uvicorn",
      "engine.app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      "8001",
    ]);
    expect(cwd).toBe("/repo/root");
    // 健康轮询用注入 fetcher
    expect(fetcher).toHaveBeenCalledWith("http://127.0.0.1:8001/health");

    // stop 调用 kill
    await handle.stop();
    expect(killed).toHaveBeenCalled();
  });

  it("健康失败 → startEngine 抛错且不返回 handle", async () => {
    const pickFreePort = vi.fn().mockResolvedValue(9000);
    const cwdProvider = vi.fn().mockResolvedValue("/repo");
    const spawnProcess = vi.fn().mockResolvedValue({ kill: vi.fn() } as EngineChild);
    const fetcher = vi.fn().mockResolvedValue(failResponse());
    const sleep = vi.fn().mockResolvedValue(undefined);

    await expect(
      startEngine({ pickFreePort, cwdProvider, spawnProcess, fetcher, sleep }),
    ).rejects.toThrow("引擎健康检查超时");
  });
});
