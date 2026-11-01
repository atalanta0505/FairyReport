import { defineStore } from "pinia";
import { ref } from "vue";
import { readState, writeState } from "../lib/state";

export const DEFAULT_ENGINE_URL = "";
export const DEFAULT_LLM_BASE_URL = "https://api.deepseek.com";
export const DEFAULT_LLM_MODEL = "deepseek-flash";
/** 官方已下线的旧模型名：虽仍可调用，但会被新模型顶替，不应再出现在清单或默认值里。 */
export const DEPRECATED_MODELS = ["deepseek-v4-flash"];
/** 仅当拉取官方 /models 失败时使用的兜底清单；成功时一律以官方返回为准。 */
export const BUILTIN_MODELS = ["deepseek-flash", "deepseek-v4-pro"];

/** 去空、去重，并剔除官方已下线的旧模型名。 */
function sanitizeModels(ids: unknown[]): string[] {
  return Array.from(
    new Set(
      ids
        .filter((id): id is string => typeof id === "string" && id.trim().length > 0)
        .map((id) => id.trim())
        .filter((id) => !DEPRECATED_MODELS.includes(id))
    )
  );
}

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
  const engineUrl = ref<string>(DEFAULT_ENGINE_URL);
  const llmKey = ref<string>("");
  const llmBaseUrl = ref<string>(DEFAULT_LLM_BASE_URL);
  const llmModel = ref<string>(DEFAULT_LLM_MODEL);
  const availableModels = ref<string[]>([...BUILTIN_MODELS]);

  async function load() {
    try {
      const s = await readState();
      engineUrl.value = s.engineUrl !== undefined ? s.engineUrl : DEFAULT_ENGINE_URL;
      llmKey.value = s.llmKey || "";
      // 兼容旧配置自动平滑迁移
      if (!s.llmBaseUrl || s.llmBaseUrl === "https://api.deepseek.com/v1") {
        llmBaseUrl.value = DEFAULT_LLM_BASE_URL;
      } else {
        llmBaseUrl.value = s.llmBaseUrl;
      }
      if (!s.llmModel || DEPRECATED_MODELS.includes(s.llmModel)) {
        llmModel.value = DEFAULT_LLM_MODEL;
      } else {
        llmModel.value = s.llmModel;
      }
    } catch {
      /* 保持默认 */
    }
  }

  async function save() {
    await writeState({
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
      // 官方为唯一真源：不再把硬编码兜底清单并回来，只剔除已下线的旧名
      const official = sanitizeModels(data.data.map((m: any) => m?.id));
      if (official.length > 0) {
        // 保留用户手输的自定义 ID，避免拉取后从选择器里消失
        const custom =
          llmModel.value && !official.includes(llmModel.value) && !DEPRECATED_MODELS.includes(llmModel.value)
            ? [llmModel.value]
            : [];
        availableModels.value = sanitizeModels([...official, ...custom]);
        // 当前选中项已失效（下线或不在清单）时，回落到官方首选
        if (!availableModels.value.includes(llmModel.value)) {
          llmModel.value = official[0];
        }
        return official;
      }
    }
    throw new Error("官方返回的模型列表为空");
  }

  return {
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
