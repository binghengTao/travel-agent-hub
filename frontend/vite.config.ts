/**
 * 本文件属于前端 TypeScript 逻辑层，注释说明状态、请求和路由等关键职责。
 * 注释只解释工程意图和边界，不修改任何输入输出结构。
 */
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    chunkSizeWarningLimit: 950,
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue', 'vue-router', 'pinia'],
          element: ['element-plus', '@element-plus/icons-vue'],
          charts: ['echarts', 'vue-echarts'],
          flow: ['@vue-flow/core', '@vue-flow/background', '@vue-flow/controls']
        }
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/outputs': 'http://localhost:8000'
    }
  }
})
