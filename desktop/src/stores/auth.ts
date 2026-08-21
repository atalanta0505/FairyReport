import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as api from "../lib/api";
import { readState, writeState } from "../lib/state";

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string>("");
  const email = ref<string>("");
  const isLoggedIn = computed(() => !!token.value);

  async function load() {
    try {
      const s = await readState();
      token.value = s.token || "";
      email.value = s.email || "";
    } catch {
      /* 无保存状态，保持未登录 */
    }
  }

  async function login(serverUrl: string, em: string, password: string) {
    const r = await api.login(serverUrl, em, password);
    token.value = r.access_token;
    email.value = em;
    await writeState({ token: token.value, email: email.value });
  }

  async function logout() {
    token.value = "";
    email.value = "";
    await writeState({ token: "", email: "" });
  }

  return { token, email, isLoggedIn, load, login, logout };
});
