import { build } from 'esbuild';
import { mkdir, copyFile } from 'node:fs/promises';
await mkdir('dist', { recursive: true });
await build({ entryPoints: [process.env.ENTRY || 'main.js'], bundle: true, format: 'esm', outfile: 'dist/main.js', sourcemap: true });
await copyFile('index.html', 'dist/index.html');
