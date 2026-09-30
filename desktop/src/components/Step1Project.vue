<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "../stores/auth";
import { useEngineStore } from "../stores/engine";
import { useSettingsStore } from "../stores/settings";
import { useProjectStore } from "../stores/project";

const auth = useAuthStore();
const engine = useEngineStore();
const settings = useSettingsStore();
const projectStore = useProjectStore();

const showNewProjectInput = ref(false);
const newProjectName = ref("");
const actionMessage = ref<{ type: "success" | "error" | "info"; text: string } | null>(null);
const isDragOver = ref(false);
const browserFileInputRef = ref<HTMLInputElement | null>(null);

function isTauriEnv(): boolean {
  return typeof (globalThis as any).__TAURI_INTERNALS__ !== "undefined";
}

interface IngestFailure {
  filename: string;
  error: string;
  isPdfScan: boolean;
}
const ingestFailures = ref<IngestFailure[]>([]);

function showMsg(text: string, type: "success" | "error" | "info" = "success") {
  actionMessage.value = { type, text };
  setTimeout(() => {
    if (actionMessage.value?.text === text) {
      actionMessage.value = null;
    }
  }, 4000);
}

onMounted(async () => {
  if (engine.status === "healthy") {
    await initData();
  }
});

async function initData() {
  if (!engine.baseUrl) return;
  try {
    await Promise.all([
      projectStore.loadProjects(engine.baseUrl),
      projectStore.checkGenericStatus(engine.baseUrl),
    ]);
  } catch (e) {
    showMsg(`初始化数据失败: ${(e as Error).message}`, "error");
  }
}

async function onSelectProject(e: Event) {
  const target = e.target as HTMLSelectElement;
  const name = target.value;
  if (!name) return;
  ingestFailures.value = [];
  try {
    await projectStore.selectProject(engine.baseUrl, name);
  } catch (err) {
    showMsg(`切换项目失败: ${(err as Error).message}`, "error");
  }
}

async function handleCreateProject() {
  const name = newProjectName.value.trim();
  if (!name) {
    showMsg("项目名称不能为空", "error");
    return;
  }
  try {
    await projectStore.createProject(engine.baseUrl, name);
    newProjectName.value = "";
    showNewProjectInput.value = false;
    ingestFailures.value = [];
    showMsg(`项目「${name}」创建成功`);
  } catch (err) {
    showMsg(`创建项目失败: ${(err as Error).message}`, "error");
  }
}

async function handleDeleteProject() {
  if (!projectStore.currentProject) return;
  const name = projectStore.currentProject.name;
  if (!confirm(`确认删除项目「${name}」及其全部资料与向量数据库？此操作不可恢复。`)) {
    return;
  }
  try {
    await projectStore.deleteProject(engine.baseUrl, name);
    ingestFailures.value = [];
    showMsg(`项目「${name}」已删除`);
  } catch (err) {
    showMsg(`删除项目失败: ${(err as Error).message}`, "error");
  }
}

async function handleOpenProjectDir() {
  if (!projectStore.currentProject) {
    showMsg("请先创建或选择项目", "error");
    return;
  }
  if (!engine.baseUrl) {
    showMsg("引擎未就绪", "error");
    return;
  }
  try {
    await projectStore.openProjectDir(engine.baseUrl);
  } catch (err) {
    showMsg(`打开资料目录失败: ${(err as Error).message}`, "error");
  }
}

async function handleScanMaterials() {
  if (!projectStore.currentProject) {
    showMsg("请先创建或选择项目", "error");
    return;
  }
  try {
    const results = await projectStore.scanMaterials(engine.baseUrl);
    const failed = results.filter((r) => r.status === "error");
    if (results.length === 0) {
      showMsg("资料目录中暂无可摄取的新文件");
    } else if (failed.length > 0) {
      ingestFailures.value = failed.map((f) => ({
        filename: f.filename,
        error: f.error || (f.ext === ".pdf" ? "未检测到可提取文字（纯图片扫描件，需先经 OCR 识别转文字）" : "解析失败或内容为空"),
        isPdfScan: f.ext === ".pdf" || (f.error?.includes("扫描件") ?? false),
      }));
      showMsg(`扫描完成，发现 ${failed.length} 份文件无法解析入库，请查看下方排查卡片`, "error");
    } else {
      ingestFailures.value = [];
      showMsg(`扫描完成，成功摄取 ${results.length} 份本地资料并建立索引！`);
    }
  } catch (err) {
    showMsg(`扫描本地资料失败: ${(err as Error).message}`, "error");
  }
}

async function handleSyncGeneric() {
  if (!engine.baseUrl) {
    showMsg("引擎未就绪", "error");
    return;
  }
  if (!auth.token) {
    showMsg("请先在左侧完成登录或使用演示模式，再同步云端知识库", "error");
    return;
  }
  try {
    const res = await projectStore.updateGeneric(engine.baseUrl, settings.serverUrl, auth.token);
    if (res && res.status === "already_installed") {
      showMsg(`通用知识包已是最新版本（${res.version}）`);
    } else {
      showMsg("通用知识包同步成功！");
    }
  } catch (err) {
    const errMsg = (err as Error).message || "";
    showMsg(`通用知识包同步失败: ${errMsg}`, "error");
  }
}

function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const res = reader.result as string;
      const base64 = res.includes(",") ? res.split(",")[1] : res;
      resolve(base64);
    };
    reader.onerror = (err) => reject(err);
    reader.readAsDataURL(file);
  });
}

function handleIngestResults(results: any[]) {
  const failed = results.filter((r) => r.status === "error");
  if (failed.length > 0) {
    ingestFailures.value = failed.map((f) => ({
      filename: f.filename,
      error: f.error || (f.ext === ".pdf" ? "未检测到可提取文字（纯图片扫描件，需先经 OCR 识别转文字）" : "解析失败或内容为空"),
      isPdfScan: f.ext === ".pdf" || (f.error?.includes("扫描件") ?? false),
    }));
    showMsg(`摄取完成，${failed.length} 份文件无法解析入库，请查看下方排查卡片`, "error");
  } else {
    ingestFailures.value = [];
    showMsg(`成功摄取 ${results.length} 份文件并完成向量化！`);
  }
}

async function doUploadBrowserFiles(fileList: FileList | File[]) {
  if (!projectStore.currentProject) return;
  const items: { filename: string; content_base64: string }[] = [];
  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i];
    try {
      const base64 = await readFileAsBase64(file);
      items.push({ filename: file.name, content_base64: base64 });
    } catch (e) {
      showMsg(`读取文件 ${file.name} 失败: ${(e as Error).message}`, "error");
    }
  }
  if (items.length === 0) return;

  try {
    const results = await projectStore.uploadFiles(engine.baseUrl, items);
    handleIngestResults(results);
  } catch (err) {
    showMsg(`上传解析资料失败: ${(err as Error).message}`, "error");
  }
}

async function handleBrowserFileInput(e: Event) {
  const target = e.target as HTMLInputElement;
  if (!target.files || target.files.length === 0) return;
  await doUploadBrowserFiles(target.files);
  target.value = "";
}

async function handlePickFiles() {
  if (!projectStore.currentProject) {
    showMsg("请先创建或选择项目", "error");
    return;
  }
  if (!isTauriEnv()) {
    browserFileInputRef.value?.click();
    return;
  }
  try {
    const { open } = await import("@tauri-apps/plugin-dialog");
    const selected = await open({
      multiple: true,
      filters: [
        {
          name: "支持的文件 (*.docx, *.xlsx, *.csv, *.md, *.txt, *.pdf)",
          extensions: ["docx", "xlsx", "csv", "md", "txt", "pdf"],
        },
      ],
    });

    if (!selected) return;

    const paths = Array.isArray(selected) ? selected : [selected];
    if (paths.length === 0) return;

    await doIngest(paths);
  } catch (err) {
    showMsg(`选取文件失败: ${(err as Error).message}`, "error");
  }
}

async function handleDrop(e: DragEvent) {
  isDragOver.value = false;
  if (!projectStore.currentProject) {
    showMsg("请先选择或创建项目", "error");
    return;
  }

  const files = e.dataTransfer?.files;
  if (!files || files.length === 0) return;

  if (isTauriEnv()) {
    const paths: string[] = [];
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      const fullPath = (f as any).path;
      if (fullPath) {
        paths.push(fullPath);
      }
    }
    if (paths.length > 0) {
      await doIngest(paths);
      return;
    }
  }

  // 纯浏览器环境或无本地绝对路径时：直接以 File 流读取 Base64 上传至云端
  await doUploadBrowserFiles(files);
}

async function doIngest(paths: string[]) {
  try {
    const results = await projectStore.ingestFiles(engine.baseUrl, paths);
    handleIngestResults(results);
  } catch (err) {
    showMsg(`摄取资料失败: ${(err as Error).message}`, "error");
  }
}

async function handleDeleteMaterial(sourceId: string) {
  if (!confirm(`确认删除资料「${sourceId}」？`)) return;
  try {
    await projectStore.deleteMaterial(engine.baseUrl, sourceId);
    showMsg(`资料「${sourceId}」已删除`);
  } catch (err) {
    showMsg(`删除资料失败: ${(err as Error).message}`, "error");
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    return d.toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

function nextStep() {
  if (!projectStore.currentProject) {
    showMsg("请先选择或创建项目", "error");
    return;
  }
  projectStore.setStep(2);
}
</script>

<template>
  <div class="step1-container">
    <!-- 全局操作消息条 -->
    <transition name="fade">
      <div v-if="actionMessage" :class="['alert-banner', actionMessage.type]">
        {{ actionMessage.text }}
      </div>
    </transition>

    <!-- 1. 项目管理卡片 -->
    <div class="card project-card">
      <div class="card-header">
        <div class="title-with-badge">
          <h3>项目管理</h3>
          <span class="badge" v-if="projectStore.currentProject">
            当前活动：{{ projectStore.currentProject.name }}
          </span>
        </div>
        <div class="header-actions">
          <button
            v-if="!showNewProjectInput"
            class="btn btn-secondary"
            @click="showNewProjectInput = true"
          >
            + 新建项目
          </button>
        </div>
      </div>

      <div class="card-body">
        <div v-if="showNewProjectInput" class="new-project-row">
          <input
            v-model="newProjectName"
            type="text"
            placeholder="请输入项目名称（如：某水库安全鉴定报告）"
            class="input-text"
            @keyup.enter="handleCreateProject"
          />
          <button class="btn btn-primary" @click="handleCreateProject">创建</button>
          <button class="btn btn-text" @click="showNewProjectInput = false">取消</button>
        </div>

        <div class="project-selector-row">
          <label class="label">选择已有项目：</label>
          <select
            class="select-input"
            :value="projectStore.currentProject?.name || ''"
            :disabled="projectStore.projects.length === 0"
            @change="onSelectProject"
          >
            <option v-if="projectStore.projects.length === 0" value="">
              暂无项目，请先新建
            </option>
            <option
              v-for="p in projectStore.projects"
              :key="p.id"
              :value="p.name"
            >
              {{ p.name }} ({{ formatDate(p.created_at) }})
            </option>
          </select>

          <button
            v-if="projectStore.currentProject"
            class="btn btn-danger-outline"
            @click="handleDeleteProject"
          >
            删除项目
          </button>
        </div>
      </div>
    </div>

    <!-- 2. 通用知识包状态卡片 -->
    <div class="card generic-card">
      <div class="card-header">
        <h3>通用知识包状态</h3>
        <span
          class="status-tag"
          :class="projectStore.genericStatus?.installed ? 'ready' : 'missing'"
        >
          {{ projectStore.genericStatus?.installed ? "● 已就绪" : "○ 未就绪" }}
        </span>
      </div>
      <div class="card-body generic-body">
        <div v-if="projectStore.genericStatus?.installed" class="generic-info">
          <p>
            已安装知识包版本：
            <strong>{{ projectStore.genericStatus.version || "未知版本" }}</strong>
          </p>
          <p class="text-muted">
            安装时间：{{ formatDate(projectStore.genericStatus.installed_at || "") }}（含 15 类专业报告交付物标准模板与行业规范向量库）
          </p>
        </div>
        <div v-else class="generic-info">
          <p class="text-warning">
            本地尚未同步通用知识包（包含 15 类报告标准模板与行业规范向量库）。知识包由云端统一维护和更新，请点击右侧「从云端同步知识包」。
          </p>
        </div>

        <button
          class="btn btn-outline"
          :disabled="projectStore.updatingGeneric"
          @click="handleSyncGeneric"
        >
          <span v-if="projectStore.updatingGeneric">同步中...</span>
          <span v-else>
            {{ projectStore.genericStatus?.installed ? "检查云端更新" : "从云端同步知识包" }}
          </span>
        </button>
      </div>
    </div>

    <!-- 3. 资料导入与管理卡片 -->
    <div class="card materials-card">
      <div class="card-header">
        <div class="title-with-badge">
          <h3>项目资料管理</h3>
          <span class="count-badge" v-if="projectStore.currentProject">
            {{ projectStore.materials.length }} 份资料
          </span>
        </div>
        <div class="header-actions" v-if="projectStore.currentProject">
          <button
            class="btn btn-outline btn-sm"
            title="打开当前项目在本地磁盘中的资料目录"
            @click="handleOpenProjectDir"
          >
            📁 打开资料目录
          </button>
          <button
            class="btn btn-outline btn-sm"
            :disabled="projectStore.ingesting"
            title="扫描资料目录下新增或直接拷入的文件并自动入库"
            @click="handleScanMaterials"
          >
            🔄 扫描本地资料
          </button>
        </div>
      </div>

      <div class="card-body">
        <div v-if="!projectStore.currentProject" class="empty-hint">
          请先在上方创建或选择一个项目以管理资料。
        </div>

        <div v-else>
          <!-- 拖拽导入与按钮区 -->
          <div
            class="upload-dropzone"
            :class="{ dragover: isDragOver }"
            @dragover.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
            @drop.prevent="handleDrop"
          >
            <div class="dropzone-content">
              <svg class="upload-icon" viewBox="0 0 24 24" width="36" height="36">
                <path
                  fill="currentColor"
                  d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"
                />
              </svg>
              <div class="upload-texts">
                <p class="primary-text">
                  点击按钮选取文件，或将本地文件拖拽至此处
                </p>
                <p class="secondary-text">
                  支持格式：.docx, .xlsx, .csv, .md, .txt, .pdf。可点击「选择文件」选取，或点击上方「📁 打开资料目录」将文件直接拷入后点击「🔄 扫描本地资料」一键向量化入库。
                </p>
              </div>
              <button
                class="btn btn-primary btn-upload"
                :disabled="projectStore.ingesting"
                @click="handlePickFiles"
              >
                {{ projectStore.ingesting ? "正在向量化摄取..." : "选择文件" }}
              </button>
              <input
                ref="browserFileInputRef"
                type="file"
                multiple
                accept=".docx,.xlsx,.csv,.md,.txt,.pdf"
                style="display: none"
                @change="handleBrowserFileInput"
              />
            </div>
          </div>

          <!-- 摄取中指示 -->
          <div v-if="projectStore.ingesting" class="loading-bar">
            <div class="spinner"></div>
            <span>文件解析与分块向量化入库中，请稍候...</span>
          </div>

          <!-- 摄取失败醒目常驻排查卡片 -->
          <div v-if="ingestFailures.length > 0" class="ingest-failures-card">
            <div class="failures-header">
              <div class="failures-title">
                <span class="warning-badge-icon">⚠️</span>
                <span class="title-text">发现 {{ ingestFailures.length }} 份文件未能成功解析入库</span>
              </div>
              <button class="btn-dismiss-failures" type="button" @click="ingestFailures = []">
                ✕ 关闭提示
              </button>
            </div>
            <div class="failures-list">
              <div v-for="item in ingestFailures" :key="item.filename" class="failure-row">
                <span class="failure-fname">📄 {{ item.filename }}</span>
                <span class="failure-reason">{{ item.error }}</span>
              </div>
            </div>
            <div v-if="ingestFailures.some((f) => f.isPdfScan)" class="failures-guide-box">
              <div class="guide-title">💡 纯图片扫描件 PDF 处理建议</div>
              <div class="guide-body">
                检测到纯图片扫描版 PDF（由纸质原件拍照或扫描生成，<strong>内部无文字层</strong>），本地语义引擎无法直接提取纯文本。
                <br />
                <strong>操作指引</strong>：建议使用<strong>电脑微信（聊天框发送后右键点击“提取文字”）、WPS 或福昕阅读器</strong>自带的“OCR 文字识别”功能，将其另存为 <code>.docx</code>、<code>.txt</code> 或 <code>.md</code> 文档后重新拖入，即可秒级向量化入库。
              </div>
            </div>
          </div>

          <!-- 资料列表表格 -->
          <div class="materials-table-wrap">
            <table v-if="projectStore.materials.length > 0" class="table">
              <thead>
                <tr>
                  <th>文件名</th>
                  <th style="width: 80px;">类型</th>
                  <th style="width: 90px;">分块数</th>
                  <th style="width: 100px;">文件大小</th>
                  <th style="width: 160px;">摄取时间</th>
                  <th style="width: 80px; text-align: center;">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="m in projectStore.materials" :key="m.id">
                  <td class="filename-cell">
                    <span class="file-badge">{{ m.ext.replace(".", "").toUpperCase() }}</span>
                    <span class="filename-text" :title="m.filename">{{ m.filename }}</span>
                  </td>
                  <td>{{ m.ext }}</td>
                  <td>
                    <span class="chunk-badge">{{ m.chunk_count }} 块</span>
                  </td>
                  <td>{{ formatBytes(m.size_bytes) }}</td>
                  <td>{{ formatDate(m.created_at) }}</td>
                  <td style="text-align: center;">
                    <button
                      class="btn-icon-danger"
                      title="删除资料"
                      @click="handleDeleteMaterial(m.source_id)"
                    >
                      删除
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else-if="!projectStore.loadingMaterials" class="empty-list">
              当前项目暂无资料文件。（💡 提示：<strong>智库专报</strong>等宏观战略类报告支持资料留空，可直接点击下方「下一步：模板与大纲」，依托权威联网检索与知识规程库高质量起草）
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部流转按钮 -->
    <div class="bottom-nav">
      <button
        class="btn btn-primary btn-lg"
        :disabled="!projectStore.currentProject"
        @click="nextStep"
      >
        下一步：模板与大纲 &rarr;
      </button>
    </div>
  </div>
</template>

<style scoped>
.step1-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px 20px 48px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.alert-banner {
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.4;
  margin-bottom: 4px;
}
.alert-banner.success {
  background: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}
.alert-banner.error {
  background: #ffebee;
  color: #c62828;
  border: 1px solid #ffcdd2;
}
.alert-banner.info {
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #bae6fd;
}

.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 12px;
}

.badge {
  background: #e0e7ff;
  color: #4338ca;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
}

.count-badge {
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
}

.card-body {
  padding: 20px;
}

.new-project-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  background: #f8fafc;
  padding: 12px;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
}

.project-selector-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.label {
  font-size: 14px;
  color: #475569;
  white-space: nowrap;
}

.input-text {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}
.input-text:focus {
  border-color: #2b6cff;
  box-shadow: 0 0 0 2px rgba(43, 108, 255, 0.15);
}

.select-input {
  flex: 1;
  max-width: 420px;
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 14px;
  background-color: #fff;
  outline: none;
}
.select-input:focus {
  border-color: #2b6cff;
}

.generic-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}
.generic-info p {
  margin: 4px 0;
  font-size: 14px;
  color: #334155;
}
.status-tag {
  font-size: 13px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 12px;
}
.status-tag.ready {
  background: #dcfce7;
  color: #15803d;
}
.status-tag.missing {
  background: #fef3c7;
  color: #b45309;
}
.text-muted {
  color: #64748b;
  font-size: 13px;
}
.text-warning {
  color: #b45309;
}

.upload-dropzone {
  border: 2px dashed #cbd5e1;
  border-radius: 8px;
  padding: 24px;
  text-align: center;
  background: #f8fafc;
  transition: all 0.2s ease;
  margin-bottom: 20px;
}
.upload-dropzone.dragover {
  border-color: #2b6cff;
  background: #eff6ff;
}
.dropzone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.upload-icon {
  color: #94a3b8;
}
.primary-text {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
}
.secondary-text {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}
.btn-upload {
  margin-top: 8px;
}

.loading-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 6px;
  color: #0369a1;
  font-size: 13px;
  margin-bottom: 16px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #bae6fd;
  border-top-color: #0284c7;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.materials-table-wrap {
  overflow-x: auto;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  text-align: left;
}
.table th {
  padding: 10px 12px;
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  border-bottom: 1px solid #e2e8f0;
}
.table td {
  padding: 12px;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
}
.table tr:hover td {
  background: #f8fafc;
}
.filename-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
.file-badge {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #475569;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 4px;
  border-radius: 4px;
}
.filename-text {
  font-weight: 500;
  color: #0f172a;
}
.chunk-badge {
  background: #e0f2fe;
  color: #0369a1;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.btn {
  padding: 7px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary {
  background: #2b6cff;
  color: #fff;
}
.btn-primary:hover:not(:disabled) {
  background: #1d57e0;
}
.btn-secondary {
  background: #f1f5f9;
  color: #334155;
  border-color: #cbd5e1;
}
.btn-secondary:hover:not(:disabled) {
  background: #e2e8f0;
}
.btn-outline {
  background: #fff;
  border-color: #cbd5e1;
  color: #334155;
}
.btn-outline:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #94a3b8;
}
.btn-danger-outline {
  background: #fff;
  border-color: #fecaca;
  color: #dc2626;
}
.btn-danger-outline:hover:not(:disabled) {
  background: #fef2f2;
}
.btn-text {
  background: transparent;
  color: #64748b;
}
.btn-text:hover {
  color: #334155;
}
.btn-lg {
  padding: 10px 24px;
  font-size: 15px;
}
.btn-sm {
  padding: 5px 12px;
  font-size: 12px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn-icon-danger {
  padding: 4px 8px;
  border: 1px solid #fecaca;
  background: #fff;
  color: #dc2626;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.btn-icon-danger:hover {
  background: #fee2e2;
}

.empty-hint, .empty-list {
  text-align: center;
  color: #94a3b8;
  padding: 32px 16px;
  font-size: 14px;
}

.bottom-nav {
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 摄取失败排查卡片样式 */
.ingest-failures-card {
  margin: 16px 0;
  padding: 16px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-left: 4px solid #f59e0b;
  border-radius: 6px;
}

.failures-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.failures-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #92400e;
  font-size: 14px;
}

.btn-dismiss-failures {
  background: #fff;
  border: 1px solid #fde68a;
  color: #b45309;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-dismiss-failures:hover {
  background: #fef3c7;
  color: #78350f;
}

.failures-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.failure-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  font-size: 13px;
  background: #fff;
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid #fef08a;
}

.failure-fname {
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 450px;
}

.failure-reason {
  color: #dc2626;
  font-size: 12px;
}

.failures-guide-box {
  background: #fefce8;
  border: 1px dashed #fcd34d;
  border-radius: 4px;
  padding: 10px 14px;
  font-size: 12px;
  color: #78350f;
  line-height: 1.6;
}

.guide-title {
  font-weight: 600;
  margin-bottom: 4px;
  color: #b45309;
}

.failures-guide-box code {
  background: #fef08a;
  padding: 1px 4px;
  border-radius: 3px;
  font-family: Consolas, monospace;
}
</style>
