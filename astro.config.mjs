import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  vite: {
    // Keep production builds from replacing a running dev server's optimizer cache.
    cacheDir: process.argv.includes('dev') ? 'node_modules/.vite-dev' : 'node_modules/.vite-build',
    optimizeDeps: {
      // Astro component scripts are discovered after Vite's initial dependency scan.
      include: ['animejs'],
    },
    plugins: [tailwindcss()],
  },
  site: 'https://haikelfazzani.github.io'
});
