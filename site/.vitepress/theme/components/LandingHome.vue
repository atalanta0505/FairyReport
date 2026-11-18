<script setup lang="ts">
import { ref, computed } from 'vue'
import { withBase } from 'vitepress'
import DownloadCards from './DownloadCards.vue'

// ── 五步工作台实景数据 ──
const activeStep = ref(0)
const lightboxImg = ref<{ src: string; title: string } | null>(null)

const steps = [
  {
    stepNo: 'STEP 01',
    shortTitle: '项目资料建库',
    title: '多格式底稿解析与本地向量建库',
    badge: '本地离线分块 · 支持资料留空',
    image: '/images/step1_materials.png',
    summary:
      '支持导入项目立项批复、地质勘察、技术方案、Excel 财务测算表等常见工程文档，在本地自动完成语义切片与向量化入库。针对「智库专报」等宏观课题，也支持不放任何资料、直接留空开始创作。',
    highlights: [
      '原生解析 Word (.docx)、Excel (.xlsx)、可搜索 PDF、Markdown 与 TXT',
      '使用本地离线嵌入模型与 ChromaDB 存储，项目底稿留在自己的电脑里',
      '智库专报等类型支持「资料留空」模式，依托内置规程与联网检索直接成文',
    ],
  },
  {
    stepNo: 'STEP 02',
    shortTitle: '规范大纲拟定',
    title: '15 类常见报告模板与多级大纲生成',
    badge: '内置标准模板 · 骨架锁定',
    image: '/images/step2_outline.png',
    summary:
      '内置 15 类常见投资建设与咨询报告的标准编制大纲。选中报告类型后即可一键生成多级目录，支持自由增删章节、拖拽排序以及补充各章节的写作侧重点。',
    highlights: [
      '内置 15 类报告模板 JSON，无需联网同步知识包即可开箱使用',
      '智库专报支持结合选题动态推演实质观点标题（5 章框架 + 中文短语小节）',
      '支持大纲结构骨架锁定，防止大模型在写长文时自行篡改章节层级',
    ],
  },
  {
    stepNo: 'STEP 03',
    shortTitle: '章节流式撰写',
    title: '三源 RAG 检索注入与三线表流式生成',
    badge: '实时思考流 · 标准三线表 · 来源角标',
    image: '/images/step3_writing.png',
    summary:
      '撰写过程实时展示大模型思考链与耗时统计。后台自动从「本地项目底稿 + 内置行业规程 + 公网搜索」三路检索相关参考片段，自动输出标准工程三线表与来源引用角标。',
    highlights: [
      '正文自动标注【源:...】【标:...】【网:...】三类引用角标，右侧台账抽屉支持点击定位高亮',
      '按工程排版习惯输出三线表格（主要技术经济指标、设备比选、投资估算、财务分析等）',
      '流式生成期间锁定步骤流转按钮，避免未写完的半截文字进入后续审阅环节',
    ],
  },
  {
    stepNo: 'STEP 04',
    shortTitle: '多维审阅修订',
    title: '多维问题诊断与段落级局部修订',
    badge: '单项销号 · 审改互斥锁',
    image: '/images/step4_review.png',
    summary:
      '提供常规快速体检、专项合规核验、数据自洽性复核、技术方案可行性及全维诊断五种审阅视角。针对查出的单一问题，支持只对该段落做原位替换并单项销号，不会把整章重写弄乱。',
    highlights: [
      '左侧目录清晰显示「待撰写 / 已撰写 / 已审阅共X个问题 / 已修改X/Y个问题」4 种状态',
      '设置「先审阅后修订」依赖与互斥锁，防止并发调用导致问题清单错乱',
      '局部修改只替换目标缺陷段落并单独销号，本章其余文字与未改问题完好保留',
    ],
  },
  {
    stepNo: 'STEP 05',
    shortTitle: '数据核对与导出',
    title: '跨章节指标核对与标准 Word 初稿导出',
    badge: '跨单位容差核对 · 15 套封面模板',
    image: '/images/step5_export.png',
    summary:
      '进入导出页会自动把全书各章节出现的关键数值（如总投资、占地面积、能耗 PUE 等）拉出来做交叉比对。确认无误后一键导出带封面、自动目录、仿宋正文、三线表与参考文献的 Word (.docx) 初稿。',
    highlights: [
      '支持跨单位换算容差比对（如万元/亿元、万㎡/㎡），给出跨章节上下文对照表',
      '15 类报告各自配有独立 Word 模板（pattern/），打开无弹窗，目录与页码直接可用',
      '全书引用按首次出现顺序自动编号为 [1], [2]... 并在文末汇总生成《参考文献》章',
    ],
  },
]

const currentStepData = computed(() => steps[activeStep.value])

const openLightbox = (src: string, title: string) => {
  lightboxImg.value = { src: withBase(src), title }
}

const closeLightbox = () => {
  lightboxImg.value = null
}

// ── 15 类专业报告分类矩阵 ──
const activeCategory = ref('all')

const categories = [
  { id: 'all', label: '全部模板 (15)' },
  { id: 'approval', label: '立项与核准 (4)' },
  { id: 'funding', label: '资金与投融资 (3)' },
  { id: 'evaluation', label: '评估与后评价 (3)' },
  { id: 'planning', label: '规划与智库专报 (5)' },
]

const reportTemplates = [
  {
    index: '01',
    category: 'approval',
    categoryName: '立项与审批',
    name: '可行性研究报告',
    tag: '通用标准大纲',
    desc: '参考现行投资项目可行性研究报告编写通用大纲，覆盖建设必要性、需求分析、建设方案、投资估算、财务评价与风险分析。',
    chapters: '概述 · 建设背景与需求 · 选址与要素保障 · 工程建设方案 · 投融资与财务评价',
  },
  {
    index: '02',
    category: 'approval',
    categoryName: '立项与审批',
    name: '初步可行性研究报告',
    tag: '预可研比选',
    desc: '用于项目立项前的多方案比选与初步技术经济论证，侧重功能定位、总体技术路线与投资匡算。',
    chapters: '项目背景 · 市场与需求预测 · 初步技术方案比选 · 投资匡算与效益初评',
  },
  {
    index: '03',
    category: 'approval',
    categoryName: '立项与审批',
    name: '项目建议书',
    tag: '立项申报',
    desc: '用于项目前期立项报批或内部立项研究，重点说明项目建设的政策契合度、必要性与初步建设设想。',
    chapters: '项目概况 · 建设的必要性与依据 · 建设地点与初步规模 · 投资匡算与资金筹措',
  },
  {
    index: '04',
    category: 'funding',
    categoryName: '资金与投融资',
    name: '资金申请报告',
    tag: '专项债 / 专项资金',
    desc: '适用于专项债券、投资补助及产业扶持资金申报，重点论证政策符合性与资金使用方案。',
    chapters: '项目单位与项目概况 · 申请资金的政策依据 · 资金使用方案 · 绩效目标与偿债保障',
  },
  {
    index: '05',
    category: 'approval',
    categoryName: '立项与审批',
    name: '项目申请书（报告）',
    tag: '企业投资核准',
    desc: '面向核准类企业投资项目，围绕公共安全、生态环保、资源开发利用与社会影响展开合规论证。',
    chapters: '申报单位及项目概况 · 发展规划与产业政策分析 · 资源利用与生态影响 · 社会稳定风险分析',
  },
  {
    index: '06',
    category: 'funding',
    categoryName: '资金与投融资',
    name: '政府和社会资本合作项目特许经营方案',
    tag: '特许经营方案',
    desc: '依据基础设施和公用事业特许经营相关规范，梳理特许经营模式、付费定价机制、风险分配与监管安排。',
    chapters: '项目可行性论证 · 特许经营模式与期限 · 投资回报与价格机制 · 风险分担与全周期监管',
  },
  {
    index: '07',
    category: 'evaluation',
    categoryName: '评估与评价',
    name: '项目评估报告',
    tag: '第三方评估复核',
    desc: '用于对可研报告、项目申请报告或特许经营方案进行第三方复核、审查与再论证。',
    chapters: '评估综述 · 建设规模与技术方案复核 · 投资估算核定 · 经济效益与风险评估结论',
  },
  {
    index: '08',
    category: 'funding',
    categoryName: '资金与投融资',
    name: '投资机会研究报告',
    tag: '前期机会鉴别',
    desc: '用于前期梳理特定区域、行业或潜在项目的投资价值，分析政策环境、市场空间与潜在回报。',
    chapters: '宏观与产业环境扫描 · 细分赛道机会鉴别 · 典型项目构想 · 收益潜力与进入策略',
  },
  {
    index: '09',
    category: 'evaluation',
    categoryName: '评估与评价',
    name: '后评价报告',
    tag: '全周期回顾总结',
    desc: '在项目竣工投产并运行一段时间后，对前期决策、实施过程、工程质量、财务效益及目标达成度进行复盘总结。',
    chapters: '项目全过程回顾 · 实施效果与技术水平评价 · 财务与经济效益重估 · 经验教训与改进建议',
  },
  {
    index: '10',
    category: 'evaluation',
    categoryName: '评估与评价',
    name: '社会评价报告',
    tag: '社会互适性评估',
    desc: '分析工程项目对所在地居民、社区及相关群体的社会影响，评估社会互适性并提出协调措施。',
    chapters: '社会影响范围界定 · 利益相关者诉求分析 · 社会互适性评估 · 社会管理与协同方案',
  },
  {
    index: '11',
    category: 'planning',
    categoryName: '规划与智库',
    name: '产业发展规划报告',
    tag: '区域产业规划',
    desc: '梳理区域产业基础、产业链环节、空间布局、重点工程与配套保障措施。',
    chapters: '发展基础与形势研判 · 总体思路与产业定位 · 现代产业体系构建 · 空间布局与重点工程',
  },
  {
    index: '12',
    category: 'planning',
    categoryName: '规划与智库',
    name: '企业发展规划报告',
    tag: '中长期发展规划',
    desc: '用于编制企业三年/五年发展规划，涵盖内外部环境分析、业务布局、研发投入与资源保障。',
    chapters: '内外部环境诊断 · 战略愿景与业务组合 · 核心竞争力锻造 · 财务预测与战略保障体系',
  },
  {
    index: '13',
    category: 'planning',
    categoryName: '规划与智库',
    name: '园区发展规划报告',
    tag: '产业园区规划',
    desc: '围绕高新区、经开区及专业园区，规划主导产业方向、空间功能分区、基础设施配套与运营机制。',
    chapters: '园区现状与对标分析 · 产业选择与集群培育 · 空间布局与载体建设 · 招商运营与体制机制',
  },
  {
    index: '14',
    category: 'planning',
    categoryName: '规划与智库',
    name: '专题研究报告',
    tag: '专项技术与课题',
    desc: '针对工程中的关键工艺比选、节能降碳专项、数字化改造方案或特定课题展开技术经济论证。',
    chapters: '课题研究背景与界定 · 现状剖析与机理研究 · 多方案深度比选论证 · 专项实施路径与结论',
  },
  {
    index: '15',
    category: 'planning',
    categoryName: '规划与智库',
    name: '智库专报',
    tag: '🌟 支持资料留空创作',
    isSpecial: true,
    desc: '用于决策参考与对策建言，采用 5 章框架与实质观点标题。即使手头还没有现成项目资料，也能结合内置规程与联网检索直接生成。',
    chapters: '战略背景与现状态势 · 核心痛点与深层症结 · 国内外标杆经验镜鉴 · 靶向对策与政策建议',
  },
]

const filteredTemplates = computed(() => {
  if (activeCategory.value === 'all') return reportTemplates
  return reportTemplates.filter((t) => t.category === activeCategory.value)
})
</script>

<template>
  <div class="fr-landing">
    <!-- ==================== 1. HERO 首屏 ==================== -->
    <section class="fr-hero">
      <div class="fr-hero-bg-grid"></div>
      <div class="fr-container">
        <div class="fr-hero-top">
          <div class="fr-hero-badge">
            <span class="fr-badge-dot"></span>
            <span class="fr-badge-version">v1.6.5 开源免费版</span>
            <span class="fr-badge-divider">|</span>
            <span>免注册登录 · 内置 15 类模板 · 纯本地运行</span>
          </div>

          <h1 class="fr-hero-title">
            开源、本地优先的<br />
            <span class="fr-hero-highlight">智能报告编制工具</span>
          </h1>

          <p class="fr-hero-subtitle">
            面向可行性研究、项目建议书、资金申请、产业规划与智库专报等长文写作场景。<br class="fr-hide-sm" />
            基于<b>本地数据存储</b>、<b>三源 RAG 检索</b>、<b>多维审阅</b>与<b>标准 Word 排版导出</b>，帮你快速写出结构合规、有据可查的报告初稿。
          </p>

          <div class="fr-hero-actions">
            <a href="#download-section" class="fr-btn fr-btn-primary">
              <span>下载</span>
              <span class="fr-btn-sub">Windows 绿色免安装版 v1.6.5 · 396 MB</span>
            </a>
            <a :href="withBase('/guide/getting-started')" class="fr-btn fr-btn-secondary">
              <span>🚀 快速上手指南</span>
            </a>
            <a
              href="https://github.com/atalanta0505/FairyReport"
              target="_blank"
              rel="noopener noreferrer"
              class="fr-btn fr-btn-secondary"
            >
              <span>⭐ GitHub 开源仓库</span>
            </a>
          </div>

          <!-- 4 项核心特性栏 -->
          <div class="fr-trust-bar">
            <div class="fr-trust-item">
              <div class="fr-trust-num">15<span>类</span></div>
              <div class="fr-trust-label">内置常见报告大纲模板</div>
            </div>
            <div class="fr-trust-divider"></div>
            <div class="fr-trust-item">
              <div class="fr-trust-num">3<span>源</span></div>
              <div class="fr-trust-label">本地底稿 + 内置规程 + 联网检索</div>
            </div>
            <div class="fr-trust-divider"></div>
            <div class="fr-trust-item">
              <div class="fr-trust-num">100<span>%</span></div>
              <div class="fr-trust-label">项目底稿保存在本地电脑</div>
            </div>
            <div class="fr-trust-divider"></div>
            <div class="fr-trust-item">
              <div class="fr-trust-num">开源<span>免费</span></div>
              <div class="fr-trust-label">免注册免配环境 · 解压即用</div>
            </div>
          </div>
        </div>

        <!-- 首屏桌面工作台预览窗体 -->
        <div class="fr-hero-showcase">
          <div class="fr-window-frame">
            <div class="fr-window-topbar">
              <div class="fr-window-dots">
                <span class="dot-red"></span>
                <span class="dot-amber"></span>
                <span class="dot-green"></span>
              </div>
              <div class="fr-window-title">
                <span>FairyReport 智能报告编制应用 (v1.6.5)</span>
              </div>
              <div class="fr-window-status">
                <span class="status-indicator"></span>
                <span>本地引擎运行中 · 数据留在本地</span>
              </div>
            </div>
            <div
              class="fr-window-body"
              @click="openLightbox('/images/step3_writing.png', '步骤 3 · 三源 RAG 流式撰写与标准工程三线表')"
            >
              <img
                :src="withBase('/images/step3_writing.png')"
                alt="FairyReport 工作台实景预览"
              />
              <div class="fr-window-zoom-hint">🔍 点击放大查看截图细节</div>
            </div>
          </div>

          <!-- 悬浮特性小卡片 -->
          <div class="fr-float-card fr-float-left">
            <div class="fr-float-icon">🔒</div>
            <div>
              <div class="fr-float-title">纯本地数据存储</div>
              <div class="fr-float-desc">ChromaDB 本地向量库，底稿留在自己电脑</div>
            </div>
          </div>
          <div class="fr-float-card fr-float-right">
            <div class="fr-float-icon">📐</div>
            <div>
              <div class="fr-float-title">标准三线表 &amp; 来源角标</div>
              <div class="fr-float-desc">自动输出工程三线表与【源/标/网】引用标记</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== 2. 交互式五步工作流 ==================== -->
    <section id="workbench" class="fr-section fr-section-alt">
      <div class="fr-container">
        <div class="fr-section-header">
          <span class="fr-eyebrow">WORKFLOW</span>
          <h2 class="fr-section-title">五步完成一份规范报告初稿</h2>
          <p class="fr-section-desc">
            把「资料整理 ➔ 拟定目录 ➔ 分章撰写 ➔ 检查修改 ➔ 排版导出」串联成清晰的五步向导。点击下方步骤标签即可切换查看软件真实运行界面：
          </p>
        </div>

        <!-- 5 步横向导航 Tab -->
        <div class="fr-step-tabs">
          <button
            v-for="(step, idx) in steps"
            :key="step.stepNo"
            type="button"
            class="fr-step-tab"
            :class="{ active: activeStep === idx }"
            @click="activeStep = idx"
          >
            <span class="fr-step-tab-no">{{ step.stepNo }}</span>
            <span class="fr-step-tab-name">{{ step.shortTitle }}</span>
          </button>
        </div>

        <!-- 当前步骤详情与实机截图联动面板 -->
        <div class="fr-workbench-panel">
          <div class="fr-workbench-info">
            <div class="fr-workbench-meta">
              <span class="fr-step-pill">{{ currentStepData.stepNo }}</span>
              <span class="fr-step-badge-gold">{{ currentStepData.badge }}</span>
            </div>
            <h3 class="fr-workbench-title">{{ currentStepData.title }}</h3>
            <p class="fr-workbench-summary">{{ currentStepData.summary }}</p>

            <ul class="fr-workbench-list">
              <li v-for="(item, i) in currentStepData.highlights" :key="i">
                <span class="fr-check-icon">✓</span>
                <span>{{ item }}</span>
              </li>
            </ul>

            <div class="fr-workbench-nav-btns">
              <button
                type="button"
                class="fr-step-switch-btn"
                :disabled="activeStep === 0"
                @click="activeStep = Math.max(0, activeStep - 1)"
              >
                ← 上一步
              </button>
              <button
                type="button"
                class="fr-step-switch-btn primary"
                :disabled="activeStep === steps.length - 1"
                @click="activeStep = Math.min(steps.length - 1, activeStep + 1)"
              >
                下一步：{{ steps[Math.min(steps.length - 1, activeStep + 1)].shortTitle }} →
              </button>
            </div>
          </div>

          <div class="fr-workbench-screen">
            <div
              class="fr-screen-frame"
              @click="openLightbox(currentStepData.image, `${currentStepData.stepNo} · ${currentStepData.title}`)"
            >
              <div class="fr-screen-bar">
                <div class="fr-window-dots">
                  <span class="dot-red"></span>
                  <span class="dot-amber"></span>
                  <span class="dot-green"></span>
                </div>
                <span class="fr-screen-bar-title">{{ currentStepData.stepNo }} — {{ currentStepData.shortTitle }}</span>
                <span class="fr-screen-bar-action">🔍 点击放大</span>
              </div>
              <img :src="withBase(currentStepData.image)" :alt="currentStepData.title" />
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== 3. 15 类常见报告模板 ==================== -->
    <section id="templates" class="fr-section">
      <div class="fr-container">
        <div class="fr-section-header">
          <span class="fr-eyebrow">BUILT-IN TEMPLATES</span>
          <h2 class="fr-section-title">内置 15 类常见报告大纲与排版模板</h2>
          <p class="fr-section-desc">
            软件本地已内置 15 类常见报告的标准章节结构、写作提示词及对应的 Word 封面模板（<code>pattern/</code>），打开软件即可直接选用：
          </p>
        </div>

        <!-- 分类筛选栏 -->
        <div class="fr-cat-tabs">
          <button
            v-for="cat in categories"
            :key="cat.id"
            type="button"
            class="fr-cat-btn"
            :class="{ active: activeCategory === cat.id }"
            @click="activeCategory = cat.id"
          >
            {{ cat.label }}
          </button>
        </div>

        <!-- 15 类报告网格卡片 -->
        <div class="fr-template-grid">
          <div
            v-for="tpl in filteredTemplates"
            :key="tpl.index"
            class="fr-tpl-card"
            :class="{ 'is-special': tpl.isSpecial }"
          >
            <div class="fr-tpl-top">
              <span class="fr-tpl-num">NO.{{ tpl.index }}</span>
              <span class="fr-tpl-tag" :class="{ gold: tpl.isSpecial }">{{ tpl.tag }}</span>
            </div>
            <h3 class="fr-tpl-name">{{ tpl.name }}</h3>
            <p class="fr-tpl-desc">{{ tpl.desc }}</p>
            <div class="fr-tpl-chapters">
              <span class="fr-tpl-chapters-label">主要章节：</span>
              <span>{{ tpl.chapters }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== 4. 三源 RAG 检索与本地数据存储 ==================== -->
    <section id="security" class="fr-section fr-section-navy">
      <div class="fr-container">
        <div class="fr-section-header light">
          <span class="fr-eyebrow gold">LOCAL-FIRST &amp; THREE-SOURCE RAG</span>
          <h2 class="fr-section-title">三源 RAG 检索 · 数据保存在你自己的电脑上</h2>
          <p class="fr-section-desc">
            作为一款开源的本地桌面工具，FairyReport 没有中心化云端账号体系。文档切片、向量计算和项目数据库都运行在本地磁盘上。
          </p>
        </div>

        <!-- 三源融合卡片 -->
        <div class="fr-rag-grid">
          <div class="fr-rag-card">
            <div class="fr-rag-header">
              <span class="fr-rag-source">源 A · 本地项目底稿库</span>
              <span class="fr-rag-mark">标记：【源:...】</span>
            </div>
            <h4>你导入的项目文档与表格</h4>
            <p>
              解析本地导入的立项批复、地勘报告、技术方案与财务 Excel 表，用本地离线模型完成向量化检索，提取项目自身的建设规模、工艺参数与投资数据。
            </p>
            <div class="fr-rag-foot">🔒 存于本地磁盘 ChromaDB</div>
          </div>

          <div class="fr-rag-card featured">
            <div class="fr-rag-header">
              <span class="fr-rag-source">源 B · 内置行业规程库</span>
              <span class="fr-rag-mark">标记：【标:...】</span>
            </div>
            <h4>内置国标规范与编制指南</h4>
            <p>
              内置常见通用技术标准（GB/GB-T）、行业规范、节能降碳要求及 15 类报告编制指南，辅助约束各章节结构与专业表述。
            </p>
            <div class="fr-rag-foot">📚 客户端内置只读库（离线可用）</div>
          </div>

          <div class="fr-rag-card">
            <div class="fr-rag-header">
              <span class="fr-rag-source">源 C · 免 Key 联网检索</span>
              <span class="fr-rag-mark">标记：【网:...】</span>
            </div>
            <h4>实时公开政策与行业资讯</h4>
            <p>
              内置免 Key 联网搜索（优先百度检索，并过滤常见自媒体内容），用于补充宏观政策背景与公开对标数据，点击引用标题可打开原网页核实。
            </p>
            <div class="fr-rag-foot">🌐 断网或超时自动跳过，不卡主流程</div>
          </div>
        </div>

        <!-- 本地与开源说明条 -->
        <div class="fr-security-pledge">
          <div class="fr-pledge-item">
            <span class="fr-pledge-icon">💻</span>
            <div>
              <h5>代码完全开源透明</h5>
              <p>前后端源码均在 GitHub 公开，无任何隐藏后门或暗箱上传逻辑</p>
            </div>
          </div>
          <div class="fr-pledge-item">
            <span class="fr-pledge-icon">🔑</span>
            <div>
              <h5>自带 API Key 直连</h5>
              <p>在设置中填入你自己的 DeepSeek API Key 直接调用官方接口，无中间商抽成</p>
            </div>
          </div>
          <div class="fr-pledge-item">
            <span class="fr-pledge-icon">📂</span>
            <div>
              <h5>原始文档留在本地</h5>
              <p>撰写时仅向模型发送当前章节所需的检索摘要片段，原始底稿文件不上传云端</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== 5. 实用的排版与核对细节 ==================== -->
    <section class="fr-section">
      <div class="fr-container">
        <div class="fr-section-header">
          <span class="fr-eyebrow">PRACTICAL DETAILS</span>
          <h2 class="fr-section-title">针对长篇报告打磨的实用排版与核对细节</h2>
          <p class="fr-section-desc">
            写长篇报告最烦人的往往不是生成文字，而是后续调格式、画表格、核对前后数字。FairyReport 重点解决了这几个实际痛点：
          </p>
        </div>

        <div class="fr-feature-bento">
          <div class="fr-bento-card">
            <div class="fr-bento-badge">实用细节 01</div>
            <h4>📐 自动构建标准工程三线表</h4>
            <p>
              导出 Word 时自动把表格设为标准工程三线表样式（顶底线 <code>1.5 磅</code>、栏目线 <code>0.75 磅</code>、表头加粗居中），在 Word 和 WPS 里直接好看可用，省去手工重画表格的功夫。
            </p>
          </div>

          <div class="fr-bento-card">
            <div class="fr-bento-badge">实用细节 02</div>
            <h4>🔍 跨章节、跨单位数值自洽核对</h4>
            <p>
              自动提取全书各章出现的关键指标（总投资、占地面积、能耗 PUE、建设周期等），支持万元/亿元、万㎡/㎡ 等跨单位换算容差比对，帮你快速揪出前后不一致的数字。
            </p>
          </div>

          <div class="fr-bento-card">
            <div class="fr-bento-badge">实用细节 03</div>
            <h4>📑 15 套独立封面与自动目录</h4>
            <p>
              通过 <code>pattern/</code> 模板目录为 15 类报告匹配各自的封面名称与公文样式（小四仿宋 + 1.5 倍行距），自动生成带页码的目录（TOC），打开 Word 不会弹出烦人的域更新提示框。
            </p>
          </div>

          <div class="fr-bento-card">
            <div class="fr-bento-badge">实用细节 04</div>
            <h4>🧬 防标题粘连与参考文献自动排序</h4>
            <p>
              内置标题与正文语义切分规则，防止大模型漏换行导致整段正文变成粗体标题；全书引用按首次出现顺序自动编号为 <code>[1], [2]...</code> 并在文末汇总生成《参考文献》。
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== 6. 为什么是 FairyReport？ ==================== -->
    <section class="fr-section fr-section-alt">
      <div class="fr-container">
        <div class="fr-section-header">
          <span class="fr-eyebrow">WHY FAIRYREPORT</span>
          <h2 class="fr-section-title">为什么是 FairyReport？</h2>
          <p class="fr-section-desc">
            相比直接在网页聊天框里让 AI 一段段写、再手动复制粘贴到 Word 排版，FairyReport 针对长篇报告做了完整的流程整合：
          </p>
        </div>

        <div class="fr-table-wrap">
          <table class="fr-compare-table">
            <thead>
              <tr>
                <th style="width: 18%">对比维度</th>
                <th style="width: 38%">普通网页聊天 AI（对话框问答模式）</th>
                <th style="width: 44%" class="is-highlight">FairyReport 开源桌面工作台 (v1.6.5)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><b>底稿与数据存放</b></td>
                <td>需要把项目文档整份上传到网页端服务器</td>
                <td class="is-highlight"><b>纯本地存储</b>：底稿与 Chroma 向量库均保存在本机磁盘，代码开源可查</td>
              </tr>
              <tr>
                <td><b>目录结构与模板</b></td>
                <td>每次都要自己写长串提示词交代目录结构，容易漏章节</td>
                <td class="is-highlight"><b>内置 15 类报告模板</b>：开箱即用，且支持大纲骨架锁定，防止模型乱改标题</td>
              </tr>
              <tr>
                <td><b>表格与 Word 排版</b></td>
                <td>输出零碎 Markdown，复制到 Word 后需要花大量时间重调格式和表格</td>
                <td class="is-highlight"><b>一键导出标准 Word</b>：自带封面、目录、小四仿宋行距与 1.5pt/0.75pt 工程三线表</td>
              </tr>
              <tr>
                <td><b>数据来源与核实</b></td>
                <td>容易编造文号与数据，很难逐条核对出处</td>
                <td class="is-highlight"><b>三源 RAG + 角标溯源</b>：正文标注【源】【标】【网】角标，文末自动汇总顺序参考文献</td>
              </tr>
              <tr>
                <td><b>前后章节数字核对</b></td>
                <td>受限于对话长度，前面写的总投资和后面章节的估算表经常对不上</td>
                <td class="is-highlight"><b>跨章节自洽核对 + 局部修订</b>：自动列出全书关键指标对照表，支持按段落局部修改销号</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- ==================== 7. 底部下载与开源仓库 ==================== -->
    <section id="download-section" class="fr-section fr-download-section">
      <div class="fr-container">
        <div class="fr-section-header">
          <span class="fr-eyebrow">DOWNLOAD &amp; OPEN SOURCE</span>
          <h2 class="fr-section-title">下载</h2>
          <p class="fr-section-desc">
            FairyReport 完全开源免费，无需安装 Python 环境、无需注册登录。通过下方 <b>百度网盘</b> 或 <b>夸克网盘</b> 下载绿色便携包，解压后双击 <code>FairyReport.exe</code> 即可使用：
          </p>
        </div>

        <DownloadCards />

        <!-- 3 步启动提示卡 -->
        <div class="fr-quick-steps">
          <div class="fr-qstep">
            <span class="fr-qstep-num">1</span>
            <div>
              <h5>解压便携包</h5>
              <p>从百度网盘（提取码 <code>i56v</code>）或夸克网盘（提取码 <code>DymL</code>）下载 <code>.zip</code> 并解压到本地文件夹。</p>
            </div>
          </div>
          <div class="fr-qstep">
            <span class="fr-qstep-num">2</span>
            <div>
              <h5>双击启动程序</h5>
              <p>双击运行文件夹里的 <code>FairyReport.exe</code>，软件会自动启动本地引擎，直接进入工作台。</p>
            </div>
          </div>
          <div class="fr-qstep">
            <span class="fr-qstep-num">3</span>
            <div>
              <h5>填入 API Key 开始使用</h5>
              <p>点击右上角「设置」填入你自己的 DeepSeek API Key，即可导入资料或直接留空生成报告。</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 全屏高清截图灯箱 (Lightbox) -->
    <Teleport to="body">
      <div v-if="lightboxImg" class="fr-lightbox" @click="closeLightbox">
        <div class="fr-lightbox-content" @click.stop>
          <div class="fr-lightbox-bar">
            <span>{{ lightboxImg.title }}</span>
            <button type="button" class="fr-lightbox-close" @click="closeLightbox">✕ 关闭预览</button>
          </div>
          <img :src="lightboxImg.src" :alt="lightboxImg.title" />
        </div>
      </div>
    </Teleport>
  </div>
</template>
