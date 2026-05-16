import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      '/ws': {
        target: 'http://localhost:8080',
        ws: true,
        rewriteWsOrigin: true,
      },
      '/ice-servers': 'http://localhost:8080',
    },
  },
});
