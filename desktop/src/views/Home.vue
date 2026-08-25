<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from "vue";
import { useAuthStore } from "../stores/auth";
import { useEngineStore } from "../stores/engine";
import { useProjectStore } from "../stores/project";
import Settings from "./Settings.vue";
import Step1Project from "../components/Step1Project.vue";
import Step2Outline from "../components/Step2Outline.vue";
import Step3Writing from "../components/Step3Writing.vue";

const auth = useAuthStore();
const engine = useEngineStore();
const projectStore = useProjectStore();

const view = ref<"wizard" | "settings">("wizard");
const mainContentRef = ref<HTMLElement | null>(null);

const steps = [
  { num: 1, label: "项目与资料" },
  { num: 2, label: "模板与大纲" },
  { num: 3, label: "章节写作" },
  { num: 4, label: "审阅修改" },
  { num: 5, label: "成果导出" },
];

function scrollToTop() {
  nextTick(() => {
    if (mainContentRef.value) {
      mainContentRef.value.scrollTop = 0;
    }
  });
}

onMounted(async () => {
  try {
    await engine.start();
    if (engine.baseUrl) {
      await Promise.all([
        projectStore.loadProjects(engine.baseUrl),
        projectStore.checkGenericStatus(engine.baseUrl),
      ]);
    }
  } catch {
    /* 引擎启动异常显示状态指示灯，不阻断 UI */
  }
});

watch(
  () => engine.status,
  async (newStatus) => {
    if (newStatus === "healthy" && engine.baseUrl) {
      await Promise.all([
        projectStore.loadProjects(engine.baseUrl),
        projectStore.checkGenericStatus(engine.baseUrl),
      ]);
    }
  },
);

watch(
  () => projectStore.currentStep,
  () => {
    scrollToTop();
  },
);

watch(
  () => view.value,
  () => {
    scrollToTop();
  },
);

function goToStep(stepNum: number) {
  if (stepNum > 1 && !projectStore.currentProject) {
    return;
  }
  if (view.value === "settings") {
    view.value = "wizard";
  }
  projectStore.setStep(stepNum);
  scrollToTop();
}

async function onLogout() {
  await engine.stop();
  await auth.logout();
}
</script>

<template>
  <div class="home-wrap">
    <!-- 顶部主导航条 -->
    <header class="topbar">
      <div class="brand-area">
        <span class="brand-logo">🪄</span>
        <span class="brand-title">FairyReport</span>
      </div>

      <!-- 5 步向导步骤条 -->
      <nav class="wizard-nav" v-if="view === 'wizard'">
        <div
          v-for="(s, index) in steps"
          :key="s.num"
          class="wizard-step"
          :class="{
            active: projectStore.currentStep === s.num,
            completed: projectStore.currentStep > s.num,
            disabled: !projectStore.currentProject && s.num > 1,
          }"
          @click="goToStep(s.num)"
        >
          <span class="step-num">{{ s.num }}</span>
          <span class="step-label">{{ s.label }}</span>
          <span v-if="index < steps.length - 1" class="step-arrow">&gt;</span>
        </div>
      </nav>
      <div v-else class="settings-title">
        <span>系统设置</span>
      </div>

      <!-- 右侧状态与操作 -->
      <div class="topbar-right">
        <button
          class="nav-tab-btn"
          :class="{ active: view === 'wizard' }"
          @click="view = 'wizard'"
        >
          主流程
        </button>
        <button
          class="nav-tab-btn"
          :class="{ active: view === 'settings' }"
          @click="view = 'settings'"
        >
          设置
        </button>

        <span class="engine-dot" :class="engine.status">
          {{
            engine.status === "healthy"
              ? "引擎就绪"
              : engine.status === "starting"
              ? "启动中…"
              : engine.status === "error"
              ? "引擎异常"
              : "未启动"
          }}
        </span>

        <span class="user-email" :title="auth.email">{{ auth.email }}</span>
        <button class="logout-btn" @click="onLogout">退出</button>
      </div>
    </header>

    <!-- 主视口内容 -->
    <main ref="mainContentRef" class="main-content">
      <div v-if="view === 'wizard'" class="wizard-content">
        <!-- 步骤 1：项目与资料管理 -->
        <Step1Project v-show="projectStore.currentStep === 1" />

        <!-- 步骤 2：模板与大纲 -->
        <Step2Outline v-show="projectStore.currentStep === 2" />

        <!-- 步骤 3：章节流式写作 -->
        <Step3Writing v-show="projectStore.currentStep === 3" />

        <!-- 步骤 4：审阅修改（占位） -->
        <div v-show="projectStore.currentStep === 4" class="step-placeholder">
          <div class="placeholder-card">
            <span class="placeholder-icon">🔍</span>
            <h3>Step 4：专家审阅与修改</h3>
            <p>对生成章节进行合规检查、数值校验及人工润色修改。</p>
            <div class="btn-group">
              <button class="btn btn-secondary" @click="projectStore.setStep(3)">&larr; 返回上一步</button>
              <button class="btn btn-primary" @click="projectStore.setStep(5)">下一步：成果导出 &rarr;</button>
            </div>
          </div>
        </div>

        <!-- 步骤 5：成果导出（占位） -->
        <div v-show="projectStore.currentStep === 5" class="step-placeholder">
          <div class="placeholder-card">
            <span class="placeholder-icon">📦</span>
            <h3>Step 5：成果格式化导出</h3>
            <p>一键导出标准化 Word 报告文档（.docx）及附表附图资料包。</p>
            <div class="btn-group">
              <button class="btn btn-secondary" @click="projectStore.setStep(4)">&larr; 返回上一步</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 设置视图 -->
      <Settings v-else />
    </main>
  </div>
</template>

<style scoped>
.home-wrap {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  z-index: 10;
}

.brand-area {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 150px;
}
.brand-logo {
  font-size: 20px;
}
.brand-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.3px;
}

.wizard-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}

.wizard-step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s ease;
}
.wizard-step:hover:not(.disabled) {
  background: #f1f5f9;
  color: #1e293b;
}
.wizard-step.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}
.wizard-step.completed {
  color: #15803d;
}
.wizard-step.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.step-num {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #e2e8f0;
  color: #475569;
  font-size: 11px;
  font-weight: 600;
}
.wizard-step.active .step-num {
  background: #2563eb;
  color: #fff;
}
.wizard-step.completed .step-num {
  background: #dcfce7;
  color: #15803d;
}

.step-arrow {
  color: #cbd5e1;
  font-size: 12px;
  margin-left: 4px;
}

.settings-title {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.nav-tab-btn {
  border: none;
  background: none;
  cursor: pointer;
  padding: 6px 12px;
  font-size: 13px;
  color: #64748b;
  border-radius: 6px;
  font-weight: 500;
}
.nav-tab-btn.active {
  color: #2563eb;
  background: #eff6ff;
}

.engine-dot {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 10px;
  font-weight: 500;
}
.engine-dot.healthy {
  background: #dcfce7;
  color: #15803d;
}
.engine-dot.starting {
  background: #fef3c7;
  color: #b45309;
}
.engine-dot.error {
  background: #fee2e2;
  color: #dc2626;
}
.engine-dot.idle {
  background: #f1f5f9;
  color: #64748b;
}

.user-email {
  font-size: 12px;
  color: #64748b;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logout-btn {
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
  color: #475569;
}
.logout-btn:hover {
  background: #f1f5f9;
}

.main-content {
  flex: 1;
  overflow-y: auto;
}

.wizard-content {
  height: 100%;
}

.step-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}
.placeholder-card {
  max-width: 500px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 40px 30px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.placeholder-icon {
  font-size: 40px;
  display: block;
  margin-bottom: 12px;
}
.placeholder-card h3 {
  margin: 0 0 8px 0;
  color: #0f172a;
  font-size: 18px;
}
.placeholder-card p {
  color: #64748b;
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 24px;
}
.btn-group {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.btn {
  padding: 8px 18px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
}
.btn-primary:hover {
  background: #1d4ed8;
}
.btn-secondary {
  background: #f1f5f9;
  color: #334155;
  border-color: #cbd5e1;
}
.btn-secondary:hover {
  background: #e2e8f0;
}
</style>
