import { build } from 'esbuild';
import { mkdir, readFile, copyFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export async function buildApp(outdir = 'dist', appSource, modelSource) {
  await mkdir(outdir, { recursive: true });
  await build({
    entryPoints: ['app.jsx'], bundle: true, format: 'esm', jsx: 'transform',
    outdir, sourcemap: false, minify: false, legalComments: 'eof',
    // Development build retains the library's setup checks during verification.
    define: { 'process.env.NODE_ENV': '"development"' },
    plugins: appSource === undefined ? [] : [{
      name: 'isolated-test-source',
      setup(builder) {
        builder.onLoad({ filter: /\/app\.jsx$/ }, () => ({ contents: appSource, loader: 'jsx', resolveDir: process.cwd() }));
        builder.onLoad({ filter: /\/model\.mjs$/ }, async () => ({
          contents: modelSource ?? await readFile('model.mjs', 'utf8'), loader: 'js',
        }));
      },
    }],
  });
  await copyFile('index.html', resolve(outdir, 'index.html'));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await buildApp();
}
