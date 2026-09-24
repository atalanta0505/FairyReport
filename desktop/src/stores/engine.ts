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
      if (typeof (globalThis as any).__TAURI_INTERNALS__ === "undefined") {
        const localBrowserUrl = "http://127.0.0.1:8001";
        await pollHealth(localBrowserUrl, { maxAttempts: 6 });
        baseUrl.value = localBrowserUrl;
        status.value = "healthy";
        isRemote.value = false;
        return;
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
