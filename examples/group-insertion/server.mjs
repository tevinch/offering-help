import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export async function serve(directory = 'dist', port = 4173) {
  const files = { '/': ['index.html', 'text/html'], '/app.js': ['app.js', 'text/javascript'], '/app.css': ['app.css', 'text/css'] };
  const server = createServer(async (request, response) => {
    const entry = files[new URL(request.url, 'http://localhost').pathname];
    if (!entry) { response.writeHead(404).end(); return; }
    try {
      const content = await readFile(resolve(directory, entry[0]));
      response.writeHead(200, { 'Content-Type': `${entry[1]}; charset=utf-8`, 'Cache-Control': 'no-store' }).end(content);
    } catch {
      response.writeHead(500).end('Build the example first.');
    }
  });
  await new Promise((done, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', done);
  });
  return server;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const server = await serve();
  console.log(`Open http://127.0.0.1:${server.address().port}`);
}
