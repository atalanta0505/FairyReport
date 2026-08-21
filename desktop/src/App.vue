<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useAuthStore } from "./stores/auth";
import { useSettingsStore } from "./stores/settings";
import Login from "./views/Login.vue";
import Home from "./views/Home.vue";

const auth = useAuthStore();
const settings = useSettingsStore();
const ready = ref(false);

onMounted(async () => {
  await Promise.all([auth.load(), settings.load()]);
  ready.value = true;
});
</script>

<template>
  <div v-if="!ready" class="boot">加载中…</div>
  <Login v-else-if="!auth.isLoggedIn" />
  <Home v-else />
</template>

<style>
:root {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Microsoft YaHei", sans-serif;
  color: #222;
}
body {
  margin: 0;
}
.boot {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  color: #888;
}
</style>
