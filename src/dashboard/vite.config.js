import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// /api/* được chuyển tiếp sang FastAPI (cổng 8000) khi chạy `npm run dev`
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
})
