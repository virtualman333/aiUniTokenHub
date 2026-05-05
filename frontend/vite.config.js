import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'

// 获取环境变量
const env = process.NODE_ENV || 'development'
const isProduction = env === 'production'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts',
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts',
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  
  // 生产环境专用配置
  base: isProduction ? '/' : '/',
  
  build: {
    // 输出目录
    outDir: 'dist',
    
    // 生产环境是否生成 source map
    sourcemap: !isProduction,
    
    // 构建目标
    target: 'es2015',
    
    // 代码分割策略
    rollupOptions: {
      output: {
        // 手动分包配置
        manualChunks: {
          'element-plus': ['element-plus'],
          'vendor': ['vue', 'vue-router', 'pinia'],
        },
        // 静态资源命名
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name.split('.')
          const ext = info[info.length - 1]
          if (/\.(png|jpe?g|gif|svg|webp|ico)$/.test(assetInfo.name)) {
            return `assets/images/[name]-[hash][extname]`
          }
          if (/\.(woff2?|eot|ttf|otf)$/.test(assetInfo.name)) {
            return `assets/fonts/[name]-[hash][extname]`
          }
          return `assets/[name]-[hash][extname]`
        },
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
      },
    },
    
    // 压缩配置
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: isProduction,
        drop_debugger: isProduction,
      },
    },
    
    // 启用报告
    // reportCompressedSize: true,
    
    // 分块大小警告阈值
    chunkSizeWarningLimit: 1500,
  },
  
  // 开发服务器配置
  server: {
    port: 3000,
    host: '0.0.0.0',
    open: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/admin': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
    historyApiFallback: true,
  },
  
  // 生产环境优化
  optimizeDeps: {
    include: ['vue', 'vue-router', 'pinia', 'element-plus', 'axios'],
  },
  
  // 预览配置
  preview: {
    port: 4173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
