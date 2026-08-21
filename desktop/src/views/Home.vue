<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useAuthStore } from "../stores/auth";
import { useEngineStore } from "../stores/engine";
import Settings from "./Settings.vue";

const auth = useAuthStore();
const engine = useEngineStore();
const view = ref<"home" | "settings">("home");

onMounted(async () => {
  // 登录后自动拉起引擎
  try {
    await engine.start();
  } catch {
    /* 引擎启动失败仅置 error 态，不阻断 UI */
  }
});

async function onLogout() {
  await engine.stop();
  await auth.logout();
}
</script>

<template>
  <div class="home-wrap">
    <header class="topbar">
      <span class="brand">FairyReport</span>
      <nav>
        <button :class="{ active: view === 'home' }" @click="view = 'home'">首页</button>
        <button :class="{ active: view === 'settings' }" @click="view = 'settings'">设置</button>
      </nav>
      <span class="engine-dot" :class="engine.status">
        {{ engine.status === "healthy" ? "引擎就绪" : engine.status === "starting" ? "启动中…" : engine.status === "error" ? "引擎异常" : "未启动" }}
      </span>
      <button class="logout" @click="onLogout">退出</button>
    </header>

    <main>
      <div v-if="view === 'home'" class="placeholder">
        <h2>欢迎，{{ auth.email }}</h2>
        <p>5 步主流程 UI 将在 T9 填充。引擎地址：{{ engine.baseUrl || "（未启动）" }}</p>
        <button class="primary" v-if="engine.status !== 'healthy'" @click="engine.start()">启动引擎</button>
      </div>
      <Settings v-else />
    </main>
  </div>
</template>

<style scoped>
.home-wrap {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.topbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 20px;
  height: 52px;
  background: #fff;
  border-bottom: 1px solid #eee;
}
.brand {
  font-weight: 600;
  margin-right: auto;
}
.topbar nav button {
  border: none;
  background: none;
  cursor: pointer;
  padding: 6px 10px;
  color: #666;
  border-radius: 6px;
}
.topbar nav button.active {
  color: #2b6cff;
  background: #eef3ff;
}
.engine-dot {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 10px;
}
.engine-dot.healthy {
  background: #e3f6e8;
  color: #2a9;
}
.engine-dot.starting {
  background: #fff5e0;
  color: #c90;
}
.engine-dot.error {
  background: #fdeaea;
  color: #d33;
}
.engine-dot.idle {
  background: #eee;
  color: #999;
}
.logout {
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 6px;
  padding: 5px 12px;
  cursor: pointer;
}
main {
  flex: 1;
  overflow: auto;
  background: #f5f6f8;
}
.placeholder {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}
.placeholder h2 {
  color: #333;
}
.primary {
  margin-top: 16px;
  padding: 8px 20px;
  border: none;
  border-radius: 6px;
  background: #2b6cff;
  color: #fff;
  cursor: pointer;
}
</style>
