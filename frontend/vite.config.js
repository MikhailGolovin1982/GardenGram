import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Слушать на всех интерфейсах (0.0.0.0), иначе forwarded-порт 5173
    // в Codespaces не отвечает.
    host: true,
    // Принимать запросы с forwarded-домена Codespaces (xxx-5173.app.github.dev).
    allowedHosts: true,
  },
})
