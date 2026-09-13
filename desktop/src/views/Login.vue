<script setup lang="ts">
import { computed, ref } from "vue";
import { useAuthStore } from "../stores/auth";
import { useSettingsStore } from "../stores/settings";
import * as api from "../lib/api";

const auth = useAuthStore();
const settings = useSettingsStore();

const tab = ref<"login" | "register">("login");

const email = ref("");
const password = ref("");
const code = ref("");
const errorMsg = ref("");
const loading = ref(false);

// 验证码发送按钮 60s 倒计时
const countdown = ref(0);
let timer: ReturnType<typeof setInterval> | null = null;

const canSendCode = computed(() => !!email.value && countdown.value === 0);

function startCountdown() {
  countdown.value = 60;
  timer = setInterval(() => {
    countdown.value -= 1;
    if (countdown.value <= 0 && timer) {
      clearInterval(timer);
      timer = null;
    }
  }, 1000);
}

async function onSendCode() {
  errorMsg.value = "";
  if (!email.value) {
    errorMsg.value = "请输入邮箱";
    return;
  }
  loading.value = true;
  try {
    await api.sendCode(settings.serverUrl, email.value);
    startCountdown();
  } catch (e: any) {
    errorMsg.value = e?.message || "验证码发送失败";
  } finally {
    loading.value = false;
  }
}

async function onRegister() {
  errorMsg.value = "";
  loading.value = true;
  try {
    await api.register(settings.serverUrl, email.value, code.value, password.value);
    // 注册成功后直接登录
    await auth.login(settings.serverUrl, email.value, password.value);
  } catch (e: any) {
    errorMsg.value = e?.message || "注册失败";
  } finally {
    loading.value = false;
  }
}

async function onLogin() {
  errorMsg.value = "";
  loading.value = true;
  try {
    await auth.login(settings.serverUrl, email.value, password.value);
  } catch (e: any) {
    errorMsg.value = e?.message || "登录失败";
  } finally {
    loading.value = false;
  }
}

async function onDemoLogin() {
  await auth.loginAsDemo();
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card">
      <h1 class="title">FairyReport</h1>
      <div class="tabs">
        <button :class="{ active: tab === 'login' }" @click="tab = 'login'">登录</button>
        <button :class="{ active: tab === 'register' }" @click="tab = 'register'">注册</button>
      </div>

      <div class="field">
        <label>邮箱</label>
        <input v-model="email" type="email" placeholder="user@example.com" />
      </div>

      <template v-if="tab === 'register'">
        <div class="field code-field">
          <div class="code-input">
            <label>验证码</label>
            <input v-model="code" type="text" placeholder="6 位验证码" />
          </div>
          <button class="send-btn" :disabled="!canSendCode || loading" @click="onSendCode">
            {{ countdown > 0 ? `${countdown}s 后重发` : "发送验证码" }}
          </button>
        </div>
      </template>

      <div class="field">
        <label>密码</label>
        <input v-model="password" type="password" placeholder="密码" />
      </div>

      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <button class="primary" :disabled="loading" @click="tab === 'login' ? onLogin() : onRegister()">
        {{ loading ? "处理中…" : tab === "login" ? "登录" : "注册并登录" }}
      </button>

      <div class="demo-divider">
        <span>或</span>
      </div>

      <button class="demo-btn" @click="onDemoLogin">
        🎯 快捷演示体验（免登录直接进入）
      </button>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: #f5f6f8;
}
.login-card {
  width: 360px;
  background: #fff;
  border-radius: 12px;
  padding: 32px 28px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}
.title {
  text-align: center;
  margin: 0 0 16px;
  font-size: 22px;
}
.tabs {
  display: flex;
  margin-bottom: 18px;
  border-bottom: 1px solid #eee;
}
.tabs button {
  flex: 1;
  padding: 8px;
  border: none;
  background: none;
  cursor: pointer;
  color: #888;
  border-bottom: 2px solid transparent;
}
.tabs button.active {
  color: #2b6cff;
  border-bottom-color: #2b6cff;
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
.code-field {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.code-input {
  flex: 1;
}
.send-btn {
  padding: 8px 10px;
  border: 1px solid #2b6cff;
  border-radius: 6px;
  background: #fff;
  color: #2b6cff;
  cursor: pointer;
  white-space: nowrap;
  font-size: 12px;
}
.send-btn:disabled {
  border-color: #ccc;
  color: #aaa;
  cursor: not-allowed;
}
.error {
  color: #d33;
  font-size: 13px;
  margin: 0 0 12px;
}
.primary {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 6px;
  background: #2b6cff;
  color: #fff;
  font-size: 15px;
  cursor: pointer;
}
.primary:disabled {
  background: #9db7ff;
}
.demo-divider {
  display: flex;
  align-items: center;
  margin: 16px 0 12px;
  color: #94a3b8;
  font-size: 12px;
}
.demo-divider::before,
.demo-divider::after {
  content: "";
  flex: 1;
  border-bottom: 1px dashed #cbd5e1;
}
.demo-divider span {
  padding: 0 10px;
}
.demo-btn {
  width: 100%;
  padding: 10px;
  border: 1px solid #10b981;
  border-radius: 6px;
  background: #ecfdf5;
  color: #047857;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}
.demo-btn:hover {
  background: #d1fae5;
  border-color: #059669;
}
</style>
