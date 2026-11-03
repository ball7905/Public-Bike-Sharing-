import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// /api/* được chuyển tiếp sang FastAPI (cổng 8000) khi chạy `npm run dev`
// Dùng 127.0.0.1 thay vì localhost: Node 17+ phân giải localhost thành ::1 (IPv6),
// trong khi uvicorn mặc định chỉ lắng nghe IPv4 -> ECONNREFUSED ::1:8000
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://127.0.0.1:8000' } },
})
