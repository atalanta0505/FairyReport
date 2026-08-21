<script setup lang="ts">
import { ref } from "vue";
import { useSettingsStore, DEFAULT_SERVER_URL } from "../stores/settings";

const settings = useSettingsStore();
const saved = ref(false);

async function onSave() {
  await settings.save();
  saved.value = true;
  setTimeout(() => (saved.value = false), 2000);
}

function onResetServer() {
  settings.serverUrl = DEFAULT_SERVER_URL;
}
</script>

<template>
  <div class="settings-wrap">
    <h2>设置</h2>

    <section class="group">
      <h3>服务器</h3>
      <div class="field">
        <label>服务器地址</label>
        <div class="row">
          <input v-model="settings.serverUrl" type="text" placeholder="http://..." />
          <button class="ghost" @click="onResetServer">默认</button>
        </div>
      </div>
    </section>

    <section class="group">
      <h3>LLM 配置（用户自带 Key，仅本地保存，不上传云端）</h3>
      <div class="field">
        <label>API Key</label>
        <input v-model="settings.llmKey" type="password" placeholder="sk-..." />
      </div>
      <div class="field">
        <label>Base URL</label>
        <input v-model="settings.llmBaseUrl" type="text" placeholder="https://api.deepseek.com/v1" />
      </div>
      <div class="field">
        <label>模型</label>
        <input v-model="settings.llmModel" type="text" placeholder="deepseek-v4-flash" />
      </div>
    </section>

    <div class="actions">
      <button class="primary" @click="onSave">保存</button>
      <span v-if="saved" class="saved">已保存</span>
    </div>
  </div>
</template>

<style scoped>
.settings-wrap {
  max-width: 560px;
  margin: 0 auto;
  padding: 24px;
}
h2 {
  margin: 0 0 20px;
}
.group {
  margin-bottom: 24px;
  padding: 16px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.05);
}
.group h3 {
  margin: 0 0 14px;
  font-size: 15px;
  color: #333;
}
.field {
  margin-bottom: 14px;
}
.field label {
  display: block;
  font-size: 13px;
  color: #555;
  margin-bottom: 4px;
}
.field input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-sizing: border-box;
  font-size: 14px;
}
.row {
  display: flex;
  gap: 8px;
}
.row input {
  flex: 1;
}
.ghost {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}
.actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.primary {
  padding: 10px 24px;
  border: none;
  border-radius: 6px;
  background: #2b6cff;
  color: #fff;
  cursor: pointer;
}
.saved {
  color: #2a9;
  font-size: 13px;
}
</style>
