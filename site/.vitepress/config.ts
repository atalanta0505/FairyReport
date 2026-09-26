import { defineConfig } from 'vitepress'

export default defineConfig({
  title: "FairyReport 🧚‍♂️",
  description: "FairyReport 智能报告编制应用 | 纯本地物理隔离 · 三源RAG · 15类标准模板 · 出版级Word导出",
  lang: "zh-CN",
  head: [
    ['link', { rel: 'icon', href: '/logo.svg' }],
    ['meta', { name: 'theme-color', content: '#3b82f6' }]
  ],
  themeConfig: {
    logo: '/logo.svg',
    siteTitle: 'FairyReport',
    
    nav: [
      { text: '首页', link: '/' },
      { text: '快速上手', link: '/guide/getting-started' },
      { 
        text: '功能手册',
        items: [
          { text: '系统架构与本地安全', link: '/docs/architecture' },
          { text: '五步端到端工作台解析', link: '/docs/pipeline' },
          { text: '绿色免安装运行指南', link: '/docs/portable' },
          { text: '扫描件 PDF 离线 OCR', link: '/docs/pdf-ocr' }
        ]
      },
      { text: '更新日志', link: '/changelog' },
      { text: '📥 下载客户端', link: '/download' },
      { text: '常见问题', link: '/guide/faq' }
    ],

    sidebar: {
      '/guide/': [
        {
          text: '操作指引',
          items: [
            { text: '快速上手指引', link: '/guide/getting-started' },
            { text: '常见问题解答 (FAQ)', link: '/guide/faq' }
          ]
        }
      ],
      '/docs/': [
        {
          text: '系统与安全',
          items: [
            { text: '系统架构与三源物理隔离', link: '/docs/architecture' },
            { text: '绿色免安装便携版运行指南', link: '/docs/portable' }
          ]
        },
        {
          text: '深度工作流',
          items: [
            { text: '五步端到端工作台深度解析', link: '/docs/pipeline' },
            { text: '扫描件 PDF 离线 OCR 处理', link: '/docs/pdf-ocr' }
          ]
        }
      ]
    },

    search: {
      provider: 'local',
      options: {
        locales: {
          root: {
            translations: {
              button: {
                buttonText: '搜索文档',
                buttonAriaLabel: '搜索文档'
              },
              modal: {
                noResultsText: '未找到相关结果',
                resetButtonTitle: '清除查询条件',
                footer: {
                  selectText: '选择',
                  navigateText: '切换',
                  closeText: '关闭'
                }
              }
            }
          }
        }
      }
    },


    footer: {
      message: 'FairyReport 智能报告编制应用 | 遵循行业通用编制指南与现行规程',
      copyright: 'Copyright © 2026 FairyReport Team. 保留所有权利。'
    },

    docFooter: {
      prev: '上一篇',
      next: '下一篇'
    },

    outline: {
      level: [2, 3],
      label: '本页导读'
    }
  }
})
