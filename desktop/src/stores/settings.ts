import { defineStore } from "pinia";
import { ref } from "vue";
import { readState, writeState } from "../lib/state";

export const DEFAULT_SERVER_URL = "http://101.42.9.223";

export const useSettingsStore = defineStore("settings", () => {
  const serverUrl = ref<string>(DEFAULT_SERVER_URL);
  const llmKey = ref<string>("");
  const llmBaseUrl = ref<string>("https://api.deepseek.com/v1");
  const llmModel = ref<string>("deepseek-v4-flash");

  async function load() {
    try {
      const s = await readState();
      serverUrl.value = s.serverUrl || DEFAULT_SERVER_URL;
      llmKey.value = s.llmKey || "";
      llmBaseUrl.value = s.llmBaseUrl || "https://api.deepseek.com/v1";
      llmModel.value = s.llmModel || "deepseek-v4-flash";
    } catch {
      /* 保持默认 */
    }
  }

  async function save() {
    await writeState({
      serverUrl: serverUrl.value,
      llmKey: llmKey.value,
      llmBaseUrl: llmBaseUrl.value,
      llmModel: llmModel.value,
    });
  }

  return { serverUrl, llmKey, llmBaseUrl, llmModel, load, save };
});
