import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './styles/index.css'
import './styles/apple-theme.css'
import App from './App.vue'
import router from './router'
import { initBrand } from '@/store/brand'

// 主题初始化：跟随上次选择（localStorage），首次访问跟随系统深浅色
// 放在挂载前执行，避免暗色用户首屏闪白
(() => {
  const saved = localStorage.getItem('finops-theme')
  if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark')
  }
})()

const app = createApp(App)
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')

// 启动后拉取品牌配置（白标），失败时保持默认「财税企管云」
initBrand()
