import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import legacy from '@vitejs/plugin-legacy'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue(),
    // 老浏览器兼容：额外产出一套 ES2015 的 nomodule 包 + polyfill，供不支持 ES Module 的老浏览器加载
    legacy({
      targets: ['defaults', 'not IE 11'],
      additionalLegacyPolyfills: ['regenerator-runtime/runtime'],
      modernPolyfills: true,
    })
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) }
  },
  build: {
    // 单端口部署：前端产物直接进后端 spa/ 目录，由 Django 托管
    // 注意：当前构建沙箱禁止对 backend/spa/assets 执行 unlink，故关闭 emptyOutDir，
    // 让 vite 仅覆盖写新产物、保留未被引用的旧 chunk（无害），从而避免构建被拦截。
    outDir: '../backend/spa',
    emptyOutDir: false,
    // 拆包：把体积大的第三方库拆成独立 vendor chunk，降低首屏主包体积（公网加载更快）
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue', 'vue-router', 'pinia'],
          element: ['element-plus', '@element-plus/icons-vue'],
          echarts: ['echarts'],
          export: ['html2canvas', 'jspdf', 'qrcode']
        }
      }
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    // 沙盒反代会改写 host header，需要放行所有 host 否则 vite 拒绝请求
    allowedHosts: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/media': { target: 'http://127.0.0.1:8000', changeOrigin: true }
    }
  },
  // 生产构建版预览（跑 dist/ 目录）：npm run preview => http://127.0.0.1:4173
  preview: {
    host: '0.0.0.0',
    port: 4173,
    allowedHosts: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/media': { target: 'http://127.0.0.1:8000', changeOrigin: true }
    }
  }
})
