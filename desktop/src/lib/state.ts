/**
 * 状态持久化 — token 与设置存到 %LOCALAPPDATA%/FairyReport/desktop-state.json。
 *
 * 文件 ACL 限当前用户：由 Rust 命令 write_state 在用户私有目录（LOCALAPPDATA，
 * 默认仅当前用户可访问）写入；密钥明文为 MVP 已知风险（发布前 keychain 加固）。
 * 浏览器开发形态（无 Tauri 运行时）降级到 localStorage，便于 UI 开发。
 */
import { invoke } from "@tauri-apps/api/core";

export interface PersistedState {
  engineUrl?: string;
  llmKey?: string;
  llmBaseUrl?: string;
  llmModel?: string;
}

const STORAGE_KEY = "frl-desktop-state";
const DEFAULT_STATE: PersistedState = {};

let _cache: PersistedState | null = null;
let _readPromise: Promise<PersistedState> | null = null;

function isTauri(): boolean {
  return typeof (globalThis as any).__TAURI_INTERNALS__ !== "undefined";
}

export async function readState(): Promise<PersistedState> {
  if (_cache) return { ..._cache };
  if (_readPromise) return _readPromise;

  _readPromise = (async () => {
    let raw = "";
    try {
      if (isTauri()) {
        raw = await invoke<string>("read_state");
      } else {
        raw = localStorage.getItem(STORAGE_KEY) || "";
      }
    } catch {
      raw = "";
    }

    const cleanRaw = (raw || "").replace(/^\uFEFF/, "").trim();
    try {
      _cache = cleanRaw ? { ...DEFAULT_STATE, ...(JSON.parse(cleanRaw) as PersistedState) } : { ...DEFAULT_STATE };
    } catch (e) {
      console.error("JSON.parse desktop-state failed:", e);
      _cache = { ...DEFAULT_STATE };
    } finally {
      _readPromise = null;
    }
    return { ..._cache };
  })();

  return _readPromise;
}

export async function writeState(patch: Partial<PersistedState>): Promise<void> {
  if (!_cache) await readState();
  _cache = { ..._cache, ...patch };
  const content = JSON.stringify(_cache);
  try {
    if (isTauri()) {
      await invoke("write_state", { content });
    } else {
      localStorage.setItem(STORAGE_KEY, content);
    }
  } catch {
    /* 持久化失败不阻断 UI */
  }
}
