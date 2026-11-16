// Responsable: Cristian Cruz · Configuración de Vite (servidor de desarrollo y compilación)
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // Puerto fijo: es el que la API tiene autorizado en CORS_ORIGENES.
  server: { port: 5173, strictPort: true },
})
