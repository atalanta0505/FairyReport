import { defineConfig } from 'vitepress'

const base = (process.env.VITEPRESS_BASE || '/') as `/${string}/`

export default defineConfig({
  base,
  title: 'FairyReport 🧚‍♂️',
  description: 'FairyReport 开源智能报告编制工具 | 免费免注册 · 纯本地数据存储 · 三源 RAG 检索 · 15 类报告模板与标准 Word 导出',
  lang: 'zh-CN',
  head: [
    ['link', { rel: 'icon', href: `${base}logo.svg` }],
    ['meta', { name: 'theme-color', content: '#0f2942' }],
    [
      'meta',
      {
        name: 'keywords',
        content:
          'FairyReport,开源报告生成,智能报告编制,可行性研究报告,初步可行性研究报告,项目建议书,资金申请报告,项目申请报告,特许经营方案,产业发展规划,智库专报,三源RAG',
      },
    ],
  ],
  themeConfig: {
    logo: '/logo.svg',
    siteTitle: 'FairyReport',

    nav: [
      { text: '首页', link: '/' },
      { text: '五步流程', link: '/#workbench' },
      { text: '15 类模板', link: '/#templates' },
      { text: '快速上手', link: '/guide/getting-started' },
      {
        text: '功能手册',
        items: [
          { text: '系统架构与本地存储', link: '/docs/architecture' },
          { text: '五步工作台解析', link: '/docs/pipeline' },
          { text: '绿色免安装版运行指南', link: '/docs/portable' },
          { text: '扫描件 PDF 离线 OCR 处理', link: '/docs/pdf-ocr' },
        ],
      },
      { text: '更新日志', link: '/changelog' },
      { text: '下载', link: '/download' },
      { text: '常见问题', link: '/guide/faq' },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/atalanta0505/FairyReport' },
    ],

    sidebar: {
      '/guide/': [
        {
          text: '操作指引',
          items: [
            { text: '快速上手操作指南', link: '/guide/getting-started' },
            { text: '常见问题解答 (FAQ)', link: '/guide/faq' },
          ],
        },
      ],
      '/docs/': [
        {
          text: '系统与安全',
          items: [
            { text: '系统架构与本地存储', link: '/docs/architecture' },
            { text: '绿色免安装版运行指南', link: '/docs/portable' },
          ],
        },
        {
          text: '深度工作流',
          items: [
            { text: '五步工作台深度解析', link: '/docs/pipeline' },
            { text: '扫描件 PDF 离线 OCR 处理', link: '/docs/pdf-ocr' },
          ],
        },
      ],
    },

    search: {
      provider: 'local',
      options: {
        locales: {
          root: {
            translations: {
              button: {
                buttonText: '搜索文档',
                buttonAriaLabel: '搜索文档',
              },
              modal: {
                noResultsText: '未找到相关结果',
                resetButtonTitle: '清除查询条件',
                footer: {
                  selectText: '选择',
                  navigateText: '切换',
                  closeText: '关闭',
                },
              },
            },
          },
        },
      },
    },

    footer: {
      message: 'FairyReport 开源智能报告编制工具 · 免费免注册 · 本地运行',
      copyright: '开源仓库：<a href="https://github.com/atalanta0505/FairyReport" target="_blank" rel="noopener noreferrer">github.com/atalanta0505/FairyReport</a> · 欢迎 Star 与交流反馈',
    },

    docFooter: {
      prev: '上一篇',
      next: '下一篇',
    },

    outline: {
      level: [2, 3],
      label: '本页导读',
    },
  },
})
