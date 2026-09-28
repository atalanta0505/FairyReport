import { defineStore } from "pinia";
import { ref } from "vue";
import { readState, writeState } from "../lib/state";

export const DEFAULT_SERVER_URL = "http://101.42.9.223";
export const DEFAULT_ENGINE_URL = "";
export const DEFAULT_LLM_BASE_URL = "https://api.deepseek.com";
export const DEFAULT_LLM_MODEL = "deepseek-flash";
export const BUILTIN_MODELS = ["deepseek-flash", "deepseek-v4-pro", "deepseek-v4-flash"];

async function getHttpFetch() {
  try {
    const http = await import("@tauri-apps/plugin-http");
    if (http && typeof http.fetch === "function") {
      return http.fetch;
    }
  } catch {
    // 回退到全局 fetch（如测试环境或纯 Web 调试）
  }
  return globalThis.fetch;
}

export const useSettingsStore = defineStore("settings", () => {
  const serverUrl = ref<string>(DEFAULT_SERVER_URL);
  const engineUrl = ref<string>(DEFAULT_ENGINE_URL);
  const llmKey = ref<string>("");
  const llmBaseUrl = ref<string>(DEFAULT_LLM_BASE_URL);
  const llmModel = ref<string>(DEFAULT_LLM_MODEL);
  const availableModels = ref<string[]>([...BUILTIN_MODELS]);

  async function load() {
    try {
      const s = await readState();
      if (!s.serverUrl || s.serverUrl.includes("43.138.8.213")) {
        serverUrl.value = DEFAULT_SERVER_URL;
      } else {
        serverUrl.value = s.serverUrl;
      }
      engineUrl.value = s.engineUrl !== undefined ? s.engineUrl : DEFAULT_ENGINE_URL;
      llmKey.value = s.llmKey || "";
      // 兼容旧配置自动平滑迁移
      if (!s.llmBaseUrl || s.llmBaseUrl === "https://api.deepseek.com/v1") {
        llmBaseUrl.value = DEFAULT_LLM_BASE_URL;
      } else {
        llmBaseUrl.value = s.llmBaseUrl;
      }
      if (!s.llmModel || s.llmModel === "deepseek-v4-flash") {
        llmModel.value = DEFAULT_LLM_MODEL;
      } else {
        llmModel.value = s.llmModel;
      }

      // 若本地存储了旧的 43 服务器地址，自动清洗并写回
      if (s.serverUrl && s.serverUrl.includes("43.138.8.213")) {
        await save();
      }
    } catch {
      /* 保持默认 */
    }
  }

  async function save() {
    await writeState({
      serverUrl: serverUrl.value,
      engineUrl: engineUrl.value,
      llmKey: llmKey.value,
      llmBaseUrl: llmBaseUrl.value,
      llmModel: llmModel.value,
    });
  }

  async function fetchRemoteModels(): Promise<string[]> {
    const key = llmKey.value.trim();
    if (!key) {
      throw new Error("请先输入 API Key，再拉取官方模型列表");
    }
    const base = (llmBaseUrl.value || DEFAULT_LLM_BASE_URL).replace(/\/+$/, "");
    const url = `${base}/models`;
    const doFetch = await getHttpFetch();

    const resp = await doFetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${key}`,
        "Content-Type": "application/json",
      },
    });

    if (!resp.ok) {
      let errText = `获取失败 (${resp.status})`;
      try {
        const errJson = await resp.json();
        errText = errJson.error?.message || errJson.message || errText;
      } catch {
        /* ignore */
      }
      throw new Error(errText);
    }

    const data = await resp.json();
    if (data && Array.isArray(data.data)) {
      const remoteIds: string[] = data.data
        .map((m: any) => m.id)
        .filter((id: any) => typeof id === "string" && id.trim().length > 0);
      if (remoteIds.length > 0) {
        // 合并去重并优先保留拉取到的模型
        const merged = Array.from(new Set([...remoteIds, ...BUILTIN_MODELS]));
        availableModels.value = merged;
        // 如果当前选中的模型不在列表中，自动选中第一个
        if (!merged.includes(llmModel.value)) {
          llmModel.value = remoteIds[0];
        }
        return remoteIds;
      }
    }
    throw new Error("官方返回的模型列表为空");
  }

  return {
    serverUrl,
    engineUrl,
    llmKey,
    llmBaseUrl,
    llmModel,
    availableModels,
    load,
    save,
    fetchRemoteModels,
  };
});
