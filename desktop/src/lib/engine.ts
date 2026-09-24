/**
 * 引擎生命周期 — 选空闲端口 → 子进程启动 uvicorn → 轮询 /health → 退出时 kill。
 *
 * 默认实现走 Tauri（pickFreePort/engineCwd 用 @tauri-apps/api/core invoke；
 * spawn 用 @tauri-apps/plugin-shell Command，scope "python-uvicorn" → python；
 * 健康检查用 @tauri-apps/plugin-http fetch（原生通道，绕开 CORS/混合内容））。
 * 所有依赖可注入，测试打桩 spawn/fetch/端口，不联网、不依赖 Tauri 运行时。
 */

import { fetch as pluginFetch } from "@tauri-apps/plugin-http";

export interface EngineChild {
  kill: () => Promise<void> | void;
}

export interface EngineDeps {
  pickFreePort: () => Promise<number>;
  cwdProvider: () => Promise<string>;
  spawnProcess: (args: string[], cwd: string) => Promise<EngineChild>;
  fetcher: (url: string) => Promise<Response>;
  sleep: (ms: number) => Promise<void>;
  maxAttempts?: number;
}

export interface EngineHandle {
  port: number;
  baseUrl: string;
  stop: () => Promise<void>;
}

export const ENGINE_HEALTH_MAX_ATTEMPTS = 60;
export const ENGINE_HEALTH_INTERVAL_MS = 500;

/** 选空闲端口（默认：Rust 命令 pick_free_port，绑定 127.0.0.1:0 取系统分配端口）。 */
export async function pickFreePort(): Promise<number> {
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<number>("pick_free_port");
}

/** 引擎子进程工作目录（默认：Rust 命令 engine_cwd，MVP 开发形态=仓库根）。 */
export async function engineCwd(): Promise<string> {
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<string>("engine_cwd");
}

/** 默认 spawn：优先调用 Rust 原生命令启动独立引擎，失败时平滑回退至 python-uvicorn（开发环境）。 */
export async function defaultSpawn(args: string[], cwd: string): Promise<EngineChild> {
  const { invoke } = await import("@tauri-apps/api/core");

  // 提取 port 参数
  const portIdx = args.indexOf("--port");
  const port = portIdx !== -1 && portIdx + 1 < args.length ? parseInt(args[portIdx + 1], 10) : 8000;

  try {
    // 1. 优先调用 Rust 原生指令启动本地独立引擎（保留系统环境变量，Windows 下不弹黑框）
    await invoke<string>("start_local_engine", { port });
    return {
      kill: async () => {
        try {
          await invoke("stop_local_engine");
        } catch {
          /* 忽略停止错误 */
        }
      },
    };
  } catch (nativeErr) {
    console.warn("未能通过原生指令启动独立引擎，尝试回退到开发环境 python-uvicorn:", nativeErr);
    // 2. 平滑回退到开发环境的 python-uvicorn
    const { Command } = await import("@tauri-apps/plugin-shell");
    const cmd = Command.create("python-uvicorn", args, { cwd });
    const child = await cmd.spawn();
    return {
      kill: async () => {
        await child.kill();
      },
    };
  }
}

function defaultFetcher(input: string | URL | Request, init?: RequestInit): Promise<Response> {
  if (typeof (globalThis as any).__TAURI_INTERNALS__ !== "undefined") {
    return pluginFetch(input as any, init);
  }
  return window.fetch(input as any, init);
}

/** 轮询 /health 直到 ok 或超时（本地引擎走 Rust 原生 TCP 探针，云端走 plugin-http）。 */
export async function pollHealth(
  baseUrl: string,
  deps?: Partial<EngineDeps>,
): Promise<void> {
  const fetcher = deps?.fetcher ?? defaultFetcher;
  const sleep = deps?.sleep ?? ((ms: number) => new Promise<void>((r) => setTimeout(r, ms)));
  const maxAttempts = deps?.maxAttempts ?? ENGINE_HEALTH_MAX_ATTEMPTS;

  let port = 0;
  let isLocal = false;
  try {
    const u = new URL(baseUrl);
    isLocal = u.hostname === "127.0.0.1" || u.hostname === "localhost";
    port = parseInt(u.port, 10);
  } catch {
    /* 忽略非标准 URL 解析 */
  }

  for (let i = 0; i < maxAttempts; i++) {
    try {
      if (isLocal && port && !deps?.fetcher && typeof (globalThis as any).__TAURI_INTERNALS__ !== "undefined") {
        const { invoke } = await import("@tauri-apps/api/core");
        const ok = await invoke<boolean>("check_engine_health", { port });
        if (ok) return;
      } else {
        const resp = await fetcher(`${baseUrl}/health`);
        if (resp.ok) return;
      }
    } catch {
      /* 引擎尚未就绪，重试 */
    }
    await sleep(ENGINE_HEALTH_INTERVAL_MS);
  }
  throw new Error(`引擎健康检查超时：${baseUrl}/health`);
}

/** 启动引擎：选端口 → 取 cwd → spawn uvicorn → 轮询健康 → 返回 handle。 */
export async function startEngine(deps?: Partial<EngineDeps>): Promise<EngineHandle> {
  const pickPort = deps?.pickFreePort ?? pickFreePort;
  const cwdProvider = deps?.cwdProvider ?? engineCwd;
  const spawn = deps?.spawnProcess ?? defaultSpawn;

  const port = await pickPort();
  const cwd = await cwdProvider();
  const args = [
    "-m",
    "uvicorn",
    "engine.app.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    String(port),
  ];
  const child = await spawn(args, cwd);
  const baseUrl = `http://127.0.0.1:${port}`;
  await pollHealth(baseUrl, deps);
  return {
    port,
    baseUrl,
    stop: async () => {
      await child.kill();
    },
  };
}
