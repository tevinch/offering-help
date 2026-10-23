import { defineConfig } from 'vite';
import { resolve } from 'node:path';
export default defineConfig({
  build: { assetsInlineLimit: 0 },
  // A deliberately incomplete operation for the expected-failure test only.
  resolve: { alias: process.env.OMIT_DELETE === '1'
    ? [{ find: './operation.js', replacement: resolve('tests/passthrough.js') }] : [] },
});
