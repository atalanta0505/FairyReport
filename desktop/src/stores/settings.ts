import { defineStore } from "pinia";
import { ref } from "vue";
import { readState, writeState } from "../lib/state";

export const DEFAULT_SERVER_URL = "http://101.42.9.223";
export const DEFAULT_ENGINE_URL = "";

export const useSettingsStore = defineStore("settings", () => {
  const serverUrl = ref<string>(DEFAULT_SERVER_URL);
  const engineUrl = ref<string>(DEFAULT_ENGINE_URL);
  const llmKey = ref<string>("");
  const llmBaseUrl = ref<string>("https://api.deepseek.com/v1");
  const llmModel = ref<string>("deepseek-v4-flash");

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
      llmBaseUrl.value = s.llmBaseUrl || "https://api.deepseek.com/v1";
      llmModel.value = s.llmModel || "deepseek-v4-flash";

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

  return { serverUrl, engineUrl, llmKey, llmBaseUrl, llmModel, load, save };
});
