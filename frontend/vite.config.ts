import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/storage': {
        // Presigned S3 uploads go through nginx, not the API.
        target: 'http://localhost',
        changeOrigin: true,
      },
    },
  },
})
