<script setup lang="ts">
import { ref } from "vue";
import { useSettingsStore, DEFAULT_SERVER_URL } from "../stores/settings";
import { useEngineStore } from "../stores/engine";

const settings = useSettingsStore();
const engine = useEngineStore();

const saved = ref(false);
const testingEngine = ref(false);
const engineTestResult = ref<string>("");

async function onSave() {
  await settings.save();
  saved.value = true;
  setTimeout(() => (saved.value = false), 2000);
}

function onResetServer() {
  settings.serverUrl = DEFAULT_SERVER_URL;
}

async function onTestEngine() {
  engineTestResult.value = "";
  if (!settings.engineUrl || !settings.engineUrl.trim()) {
    try {
      await engine.start();
      engineTestResult.value = "已切换为本地 Python 引擎并成功就绪！";
    } catch {
      engineTestResult.value = "本地未检测到 Python 引擎，请输入云服务器地址。";
    }
    return;
  }
  testingEngine.value = true;
  try {
    await engine.connectRemote(settings.engineUrl);
    engineTestResult.value = "✅ 云端引擎连接成功！服务正常就绪。";
  } catch {
    engineTestResult.value = "❌ 连接失败：请检查云服务器 IP、端口 8000 与防火墙放行状态。";
  } finally {
    testingEngine.value = false;
  }
}
</script>

<template>
  <div class="settings-wrap">
    <h2>系统设置</h2>

    <section class="group">
      <h3>核心引擎连接</h3>
      <div class="field">
        <label>云端引擎服务地址（合伙人云服务器）</label>
        <div class="row">
          <input
            v-model="settings.engineUrl"
            type="text"
            placeholder="留空为本地引擎，或填 http://<云服务器IP>:8000"
          />
          <button class="ghost" :disabled="testingEngine" @click="onTestEngine">
            {{ testingEngine ? "测试中…" : "测试并连接" }}
          </button>
        </div>
        <p
          v-if="engineTestResult"
          class="field-hint"
          :class="{
            ok: engineTestResult.includes('成功'),
            err: engineTestResult.includes('失败') || engineTestResult.includes('未检测'),
          }"
        >
          {{ engineTestResult }}
        </p>
        <p class="field-desc">
          💡 提示：在云服务器启动 Docker 容器后，填入例如 <code>http://123.57.xx.xx:8000</code>，客户端即可免安装 Python 直接使用！
        </p>
      </div>
    </section>

    <section class="group">
      <h3>认证与知识库服务</h3>
      <div class="field">
        <label>账号服务地址</label>
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
      <button class="primary" @click="onSave">保存设置</button>
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
.field-hint {
  margin: 6px 0 0;
  font-size: 12px;
  font-weight: 500;
}
.field-hint.ok {
  color: #16a34a;
}
.field-hint.err {
  color: #dc2626;
}
.field-desc {
  margin: 6px 0 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.4;
}
.field-desc code {
  background: #f1f5f9;
  padding: 2px 4px;
  border-radius: 4px;
  color: #0f172a;
}
</style>
