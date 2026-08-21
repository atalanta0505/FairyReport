import { defineStore } from "pinia";
import { ref } from "vue";
import { startEngine, type EngineHandle } from "../lib/engine";

export type EngineStatus = "idle" | "starting" | "healthy" | "error";

export const useEngineStore = defineStore("engine", () => {
  const status = ref<EngineStatus>("idle");
  const baseUrl = ref<string>("");
  let handle: EngineHandle | null = null;

  async function start() {
    if (handle) return;
    status.value = "starting";
    try {
      handle = await startEngine();
      baseUrl.value = handle.baseUrl;
      status.value = "healthy";
    } catch (e) {
      status.value = "error";
      handle = null;
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
  }

  return { status, baseUrl, start, stop };
});
