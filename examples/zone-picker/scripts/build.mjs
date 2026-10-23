import { build } from 'esbuild';
import { mkdir, copyFile } from 'node:fs/promises';

export async function buildApp() {
  await mkdir('dist', { recursive: true });
  await build({
    entryPoints: ['src/main.tsx'],
    bundle: true,
    outfile: 'dist/app.js',
    sourcemap: true,
    target: 'es2022',
    define: { 'process.env.NODE_ENV': '"production"' },
  });
  await copyFile('index.html', 'dist/index.html');
}

if (process.argv[1]?.endsWith('build.mjs')) await buildApp();
