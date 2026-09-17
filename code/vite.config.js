import { defineConfig } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';

// SPEC §6: single self-contained HTML file. Everything is inlined except
// CesiumJS, which is loaded from CDN at a pinned exact version in index.html
// and referenced as the global `Cesium` — it is deliberately not an npm
// dependency (see CLAUDE.md).
//
// The Vite root is this directory (code/). The zone data is imported from
// ../data/build/zones.json — a separately licensed tree (see ../LICENSE.md) —
// so the dev server is allowed to read from the repository root, and the
// bundle is written to ../dist/ as the aggregation of the two.
export default defineConfig({
  base: './',
  plugins: [viteSingleFile()],
  server: { fs: { allow: ['..'] } },
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    target: 'es2020',
    assetsInlineLimit: 100_000_000,
    cssCodeSplit: false,
    reportCompressedSize: true,
    rollupOptions: {
      external: ['cesium'],
      output: { globals: { cesium: 'Cesium' } },
    },
  },
});
