import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const uiBuildStamp = new Date().toISOString();

export default defineConfig({
  base: './',
  define: {
    __UI_BUILD_STAMP__: JSON.stringify(uiBuildStamp),
  },
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8765',
    },
  },
});
