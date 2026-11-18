import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import LandingHome from './components/LandingHome.vue'
import DownloadCards from './components/DownloadCards.vue'
import './style.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('LandingHome', LandingHome)
    app.component('DownloadCards', DownloadCards)
  }
} satisfies Theme
