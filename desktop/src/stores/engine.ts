import { defineStore } from "pinia";
import { ref } from "vue";
import { startEngine, pollHealth, type EngineHandle } from "../lib/engine";
import { useSettingsStore } from "./settings";

export type EngineStatus = "idle" | "starting" | "healthy" | "error";

export const useEngineStore = defineStore("engine", () => {
  const status = ref<EngineStatus>("idle");
  const baseUrl = ref<string>("");
  const isRemote = ref<boolean>(false);
  let handle: EngineHandle | null = null;

  async function start() {
    const settings = useSettingsStore();

    // 0. 浏览器环境自适应：若在纯 Web 环境（非 Tauri）中访问，优先探测当前同源后端地址
    if (
      typeof (globalThis as any).__TAURI_INTERNALS__ === "undefined" &&
      typeof window !== "undefined" &&
      window.location &&
      (window.location.protocol === "http:" || window.location.protocol === "https:")
    ) {
      const currentOrigin = window.location.origin;
      try {
        await pollHealth(currentOrigin, { maxAttempts: 2, sleep: () => Promise.resolve() });
        baseUrl.value = currentOrigin;
        status.value = "healthy";
        isRemote.value = true;
        return;
      } catch {
        // 同源地址未提供 /health（可能为独立的 vite dev 前端开发服务），继续向下探测
      }
    }

    // 1. 若已配置云端引擎地址，优先直连云端，跳过本地 Python 启动
    if (settings.engineUrl && settings.engineUrl.trim()) {
      status.value = "starting";
      const remote = settings.engineUrl.trim().replace(/\/+$/, "");
      try {
        await pollHealth(remote, { maxAttempts: 6 });
        baseUrl.value = remote;
        status.value = "healthy";
        isRemote.value = true;
        return;
      } catch {
        status.value = "error";
        baseUrl.value = remote;
        isRemote.value = true;
        return;
      }
    }

    // 2. 未配置云端引擎时，启动本地 Python 引擎
    if (handle) return;
    status.value = "starting";
    try {
      // 优先探测本地 8001 / 8000 是否已有开发服务在运行（支持 uvicorn --reload 外部启动）
      const devPorts = [8001, 8000];
      for (const p of devPorts) {
        const testUrl = `http://127.0.0.1:${p}`;
        try {
          await pollHealth(testUrl, { maxAttempts: 1, sleep: () => Promise.resolve() });
          baseUrl.value = testUrl;
          status.value = "healthy";
          isRemote.value = false;
          if (typeof (globalThis as any).__TAURI_INTERNALS__ !== "undefined") {
            const { invoke } = await import("@tauri-apps/api/core");
            await invoke("log_from_js", { msg: `[Engine] 检测到本地运行中的服务，已成功直连: ${testUrl}` });
          }
          return;
        } catch {
          // 当前端口未启动，继续检查下一个
        }
      }

      if (typeof (globalThis as any).__TAURI_INTERNALS__ === "undefined") {
        throw new Error("开发环境未在 8001/8000 端口检测到引擎服务，请先在终端启动 uvicorn。");
      }
      handle = await startEngine();
      baseUrl.value = handle.baseUrl;
      status.value = "healthy";
      isRemote.value = false;
    } catch (e) {
      status.value = "error";
      handle = null;
      throw e;
    }
  }

  async function connectRemote(url: string) {
    status.value = "starting";
    const cleanUrl = url.trim().replace(/\/+$/, "");
    try {
      await pollHealth(cleanUrl, { maxAttempts: 4 });
      baseUrl.value = cleanUrl;
      status.value = "healthy";
      isRemote.value = true;
      if (handle) {
        try {
          await handle.stop();
        } catch {
          /* 忽略旧子进程退出错误 */
        }
        handle = null;
      }
      const settings = useSettingsStore();
      settings.engineUrl = cleanUrl;
      await settings.save();
      return true;
    } catch (e) {
      status.value = "error";
      baseUrl.value = cleanUrl;
      throw e;
    }
  }

  async function stop() {
    if (handle) {
      try {
        await handle.stop();
      } catch {
        /* 退出清理忽略错误 */
      }
      handle = null;
    }
    status.value = "idle";
    baseUrl.value = "";
    isRemote.value = false;
  }

  return { status, baseUrl, isRemote, start, stop, connectRemote };
});
