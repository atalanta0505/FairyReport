<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  compact?: boolean
}>()

const copiedKey = ref<string | null>(null)

const copyText = async (text: string, key: string) => {
  try {
    await navigator.clipboard.writeText(text)
    copiedKey.value = key
    setTimeout(() => {
      if (copiedKey.value === key) {
        copiedKey.value = null
      }
    }, 2200)
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = text
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    copiedKey.value = key
    setTimeout(() => {
      if (copiedKey.value === key) {
        copiedKey.value = null
      }
    }, 2200)
  }
}

const packageInfo = {
  version: 'v1.6.5',
  releaseDate: '2026-11-01',
  fileName: 'FairyReport-Local-v1.6.5-Windows-x64.zip',
  fileSize: '396 MB',
  os: 'Windows 10 / Windows 11 (64 位)',
  sha256: '97B214137B32D1A7A4CC191FE34629487CE1E9A95588565ADA372A6D22B52D09',
  githubUrl: 'https://github.com/atalanta0505/FairyReport',
}

const channels = [
  {
    id: 'baidu',
    name: '百度网盘',
    badge: '网盘分流一',
    desc: '绿色免安装便携压缩包，已打包本地 Python 引擎、离线向量模型与 15 类内置模板。',
    url: 'https://pan.baidu.com/s/1XG5DlAl6zpCWEoWfXmtvTg?pwd=i56v',
    code: 'i56v',
    theme: 'baidu',
    icon: '☁️',
  },
  {
    id: 'quark',
    name: '夸克网盘',
    badge: '网盘分流二',
    desc: '与百度网盘版本完全一致，可根据您平时的网盘使用习惯任选其一下载。',
    url: 'https://pan.quark.cn/s/893e062482e6?pwd=DymL',
    code: 'DymL',
    theme: 'quark',
    icon: '⚡',
  },
]
</script>

<template>
  <div class="fr-download-wrapper" :class="{ 'is-compact': compact }">
    <!-- 顶部软件包规格横幅 -->
    <div class="fr-pkg-banner">
      <div class="fr-pkg-Banner-left">
        <div class="fr-pkg-badges">
          <span class="fr-pill-gold">当前版本 {{ packageInfo.version }}</span>
          <span class="fr-pill-blue">开源免费 · 绿色免安装</span>
          <span class="fr-pill-outline">免注册开箱即用</span>
        </div>
        <h3 class="fr-pkg-title">{{ packageInfo.fileName }}</h3>
        <p class="fr-pkg-meta">
          <span>📦 包体大小：<b>{{ packageInfo.fileSize }}</b>（内含后端引擎、离线向量模型与 15 类内置模板）</span>
          <span class="fr-meta-sep">|</span>
          <span>💻 适用系统：<b>{{ packageInfo.os }}</b></span>
          <span class="fr-meta-sep">|</span>
          <span>📅 发布日期：{{ packageInfo.releaseDate }}</span>
        </p>
      </div>
    </div>

    <!-- 双网盘并列卡片 -->
    <div class="fr-netdisk-grid">
      <div
        v-for="ch in channels"
        :key="ch.id"
        class="fr-netdisk-card"
        :class="`theme-${ch.theme}`"
      >
        <div class="fr-netdisk-header">
          <div class="fr-netdisk-icon">{{ ch.icon }}</div>
          <div class="fr-netdisk-titles">
            <span class="fr-netdisk-tag">{{ ch.badge }}</span>
            <h4 class="fr-netdisk-name">{{ ch.name }}</h4>
          </div>
        </div>

        <p class="fr-netdisk-desc">{{ ch.desc }}</p>

        <!-- 提取码交互条 -->
        <div class="fr-code-box">
          <div class="fr-code-label">
            <span>提取码：</span>
            <code class="fr-code-val">{{ ch.code }}</code>
          </div>
          <button
            type="button"
            class="fr-btn-copy"
            @click="copyText(ch.code, ch.id)"
          >
            <span v-if="copiedKey === ch.id">✅ 已复制提取码</span>
            <span v-else>📋 复制提取码</span>
          </button>
        </div>

        <!-- 下载主按钮 -->
        <a
          :href="ch.url"
          target="_blank"
          rel="noopener noreferrer"
          class="fr-btn-download"
        >
          <span>下载</span>
          <span class="fr-btn-arrow">→</span>
        </a>
      </div>
    </div>

    <!-- SHA-256 校验条与 GitHub 开源仓库条 -->
    <div class="fr-sha-bar">
      <div class="fr-sha-info">
        <span class="fr-sha-badge">🔒 SHA-256 校验码</span>
        <code class="fr-sha-code">{{ packageInfo.sha256 }}</code>
      </div>
      <button
        type="button"
        class="fr-btn-sha-copy"
        @click="copyText(packageInfo.sha256, 'sha256')"
      >
        <span v-if="copiedKey === 'sha256'">✅ 已复制校验码</span>
        <span v-else>复制 SHA-256</span>
      </button>
    </div>

    <div class="fr-sha-bar" style="margin-top: 10px;">
      <div class="fr-sha-info">
        <span class="fr-sha-badge">⭐ GitHub 开源仓库</span>
        <span style="font-size: 0.85rem; color: var(--fr-text-secondary);">
          本项目完全开源免费，欢迎前往 GitHub 查看源码、提交 Issue 或点亮 Star：
        </span>
      </div>
      <a
        :href="packageInfo.githubUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="fr-btn-sha-copy"
        style="text-decoration: none; font-weight: 700; color: var(--fr-blue-600);"
      >
        github.com/atalanta0505/FairyReport ↗
      </a>
    </div>
  </div>
</template>
