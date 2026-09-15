import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src')
    },
  },
  optimizeDeps: {
    // maplibre-gl ships its own worker bundle; Vite's dep optimizer cannot
    // process it and will throw a missing-file error if it tries.
    exclude: ['maplibre-gl'],
  },
})

