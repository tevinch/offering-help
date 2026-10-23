import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { buildApp } from './build.mjs';

await buildApp();
const files = { '/': ['index.html', 'text/html'], '/app.js': ['app.js', 'text/javascript'], '/app.css': ['app.css', 'text/css'] };
const reports = [
  { id: 'before', name: 'Earlier report', at: '2026-05-25T16:00:00.000Z' },
  { id: 'evening', name: 'UTC evening report', at: '2026-05-25T18:00:00.000Z' },
  { id: 'after', name: 'Later report', at: '2026-05-25T20:00:00.000Z' },
];
const isInstant = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value) && Number.isFinite(Date.parse(value));
createServer(async (req, res) => {
  if (req.url === '/api/reports' && req.method === 'POST') {
    try {
      let text = '';
      for await (const chunk of req) {
        text += chunk;
        if (text.length > 16384) { res.writeHead(413).end(); return; }
      }
      const query = JSON.parse(text);
      if (!query || typeof query.zone !== 'string'
        || !(query.dateTime === null || isInstant(query.dateTime))
        || !(query.time === null || isInstant(query.time))
        || !(query.range === null || (Array.isArray(query.range) && query.range.length === 2 && query.range.every(isInstant) && query.range[0] <= query.range[1]))) {
        res.writeHead(400).end('Invalid UTC query'); return;
      }
      const matches = reports.filter(report => (!query.dateTime || report.at === query.dateTime)
        && (!query.time || report.at === query.time)
        && (!query.range || (report.at >= query.range[0] && report.at <= query.range[1])));
      res.setHeader('Content-Type', 'application/json');
      res.end(JSON.stringify({ reports: matches }));
    } catch { res.writeHead(400).end('Invalid JSON'); }
    return;
  }
  const file = files[req.url];
  if (!file || req.method !== 'GET') { res.writeHead(404).end(); return; }
  res.setHeader('Content-Type', file[1]);
  res.end(await readFile(`dist/${file[0]}`));
}).listen(4173, '127.0.0.1', () => console.log('Open http://127.0.0.1:4173'));
