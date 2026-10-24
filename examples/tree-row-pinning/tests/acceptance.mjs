import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import { chromium } from 'playwright';
import { createHash } from 'node:crypto';

const output = process.env.RESULT_DIR || 'test-results';
await mkdir(output, { recursive: true });
const dataBefore = await readFile('data.js');
const version = JSON.parse(await readFile('node_modules/ag-grid-community/package.json')).version;
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };
const server = createServer(async (request, response) => {
  try {
    const path = new URL(request.url, 'http://localhost').pathname;
    const file = resolve('dist', path === '/' ? 'index.html' : '.' + path);
    if (!file.startsWith(resolve('dist') + '/')) throw Error('Path outside dist');
    response.setHeader('Content-Type', mime[extname(file)] || 'application/octet-stream');
    response.end(await readFile(file));
  } catch { response.writeHead(404).end('Not found'); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1180, height: 1000 } });
const consoleMessages = [], errors = [], steps = [];
page.on('console', message => consoleMessages.push({ type: message.type(), text: message.text() }));
page.on('pageerror', error => errors.push(String(error)));
const bodyRow = id => page.locator(`.ag-row:not(.ag-row-pinned)[row-id="${id}"]`);
const topRow = () => page.locator('.ag-row-pinned[row-index="t-0"]');
async function count(locator, expected, label) {
  await locator.first().waitFor({ state: expected ? 'visible' : 'hidden', timeout: 4000 });
  assert.equal(await locator.count(), expected, label);
}
async function state() { return JSON.parse(await page.locator('#state').textContent()); }
async function waitState(predicate, label) {
  await page.waitForFunction(predicate, null, { timeout: 4000 });
  steps.push({ label, state: await state() });
}
async function clickGroup(row) {
  const control = row.locator('button[data-tree-toggle], .ag-group-contracted:not(.ag-hidden), .ag-group-expanded:not(.ag-hidden)');
  assert.equal(await control.count(), 1, 'a usable tree expansion control exists on target row');
  if (process.env.OMIT_EXPAND !== '1') await control.click();
}
async function settleRows() {
  await page.waitForFunction(() => document.getAnimations().every(animation =>
    animation.playState !== 'running' || !animation.effect?.target?.closest?.('.ag-row')),
  null, { timeout: 4000 });
}

let result = 'FAIL', failure;
try {
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  await page.waitForFunction(() => document.querySelector('#state').textContent.includes('planning'));
  await count(topRow(), 1, 'root is really pinned');
  assert.match(await topRow().textContent(), /Planning/);
  assert.equal(await topRow().getByRole('button', { name: 'Expand Planning' }).getAttribute('aria-expanded'), 'false', 'custom pinned control starts collapsed');
  await count(bodyRow('support'), 1, 'unrelated original root remains visible');
  await count(bodyRow('design'), 0, 'tree starts collapsed');
  const initial = await state();
  assert.deepEqual(initial.rows.map(r => r.id).sort(), ['build','design','planning','research','support','support-a','support-b']);
  assert.equal(initial.rows.find(r => r.id === 'design').parent, 'planning');
  assert.equal(initial.rows.find(r => r.id === 'research').parent, 'design');
  assert.ok(initial.getRowIdCalls >= 7, 'required getRowId callback actually ran');
  steps.push({ label: 'pinned-original-tree', state: initial });

  await clickGroup(topRow());
  await count(bodyRow('design'), 1, 'pinned root reveals real child');
  await count(bodyRow('build'), 1, 'both children revealed');
  await waitState(() => JSON.parse(document.querySelector('#state').textContent).opened.some(e => e.id === 'planning' && e.expanded), 'root expansion event observed');
  await clickGroup(bodyRow('design'));
  await count(bodyRow('research'), 1, 'nested child reveals grandchild');
  await waitState(() => JSON.parse(document.querySelector('#state').textContent).opened.some(e => e.id === 'design' && e.expanded), 'nested expansion event observed');
  await clickGroup(topRow());
  await count(bodyRow('design'), 0, 'pinned collapse hides child');
  await count(bodyRow('research'), 0, 'pinned collapse hides grandchild');
  await clickGroup(topRow());
  await count(bodyRow('design'), 1, 'repeated root expand works');
  await count(bodyRow('research'), 1, 'nested expansion preserved');
  await clickGroup(bodyRow('planning'));
  await count(bodyRow('design'), 0, 'ordinary original node still collapses tree');
  assert.equal(await topRow().getByRole('button', { name: 'Expand Planning' }).getAttribute('aria-expanded'), 'false', 'pinned button follows body control');
  await clickGroup(bodyRow('planning'));
  await count(bodyRow('research'), 1, 'ordinary original node can reopen nested tree');
  assert.equal(await topRow().getByRole('button', { name: 'Collapse Planning' }).getAttribute('aria-expanded'), 'true', 'pinned button follows body expansion');

  await page.getByRole('columnheader', { name: /Effort/ }).click();
  await waitState(() => JSON.parse(document.querySelector('#state').textContent).sortEvents > 0, 'sort callback actually ran');
  await settleRows();
  const ordered = await page.locator('.ag-row:not(.ag-row-pinned)').evaluateAll(rows => rows.map(row => ({ id: row.getAttribute('row-id'), top: parseFloat(row.style.transform.match(/translateY\(([-\d.]+)/)?.[1] || row.style.top || '0') })).sort((a,b) => a.top-b.top).map(row => row.id));
  assert.ok(ordered.indexOf('build') < ordered.indexOf('design'), 'native numeric sort reorders sibling records');
  assert.ok(ordered.indexOf('research') > ordered.indexOf('design'), 'grandchild remains below its own parent after sort');
  await bodyRow('research').locator('input[type="checkbox"]').check();
  await waitState(() => JSON.parse(document.querySelector('#state').textContent).selected.includes('research'), 'leaf selection callback observed');
  await clickGroup(topRow());
  await count(bodyRow('research'), 0, 'selected descendant can be hidden normally');
  assert.ok((await state()).selected.includes('research'), 'collapse preserves selected record');
  await clickGroup(topRow());
  await count(bodyRow('research'), 1, 'selected descendant returns');
  assert.equal(await bodyRow('research').getAttribute('aria-selected'), 'true', 'rendered selection remains');
  await bodyRow('build').locator('input[type="checkbox"]').check();
  await bodyRow('research').locator('input[type="checkbox"]').uncheck();
  await waitState(() => JSON.stringify(JSON.parse(document.querySelector('#state').textContent).selected) === '["build"]', 'continued selection after pin/expand/sort succeeds');
  await clickGroup(topRow());
  await count(bodyRow('design'), 0, 'final pinned collapse');
  await clickGroup(topRow());
  await count(bodyRow('design'), 1, 'final pinned reopen');
  await topRow().getByRole('button', { name: 'Collapse Planning' }).focus();
  await page.keyboard.press('Enter');
  await count(bodyRow('design'), 0, 'pinned keyboard Enter collapses real tree');
  await page.keyboard.press('Space');
  await count(bodyRow('research'), 1, 'pinned keyboard Space reopens nested tree');
  await settleRows();
  const final = await state();
  assert.ok(final.opened.filter(e => e.id === 'planning').length >= 7, 'repeated native root operation events occurred');
  assert.ok(final.selectionEvents >= 3, 'selection hooks ran independently');
  assert.deepEqual(final.originalData, initial.originalData, 'every original record and field preserved');
  assert.deepEqual(final.rows.map(r => ({id:r.id,parent:r.parent})).sort((a,b)=>a.id.localeCompare(b.id)), initial.rows.map(r=>({id:r.id,parent:r.parent})).sort((a,b)=>a.id.localeCompare(b.id)), 'all original tree relationships preserved');
  assert.deepEqual(await readFile('data.js'), dataBefore, 'input source bytes unchanged');
  assert.deepEqual(errors, [], 'no page exceptions');
  assert.ok(consoleMessages.some(m => /License Key Not Found|license key|licen[cs]e/i.test(m.text)), 'Enterprise evaluation notice remains');
  steps.push({ label: 'final-reopened-tree-and-preserved-selection', state: final });
  await page.screenshot({ path: resolve(output, 'final.png'), fullPage: true });
  result = 'PASS';
} catch (error) { failure = String(error.stack || error); }
finally {
  await writeFile(resolve(output, 'dom.html'), await page.content());
  await writeFile(resolve(output, 'result.json'), JSON.stringify({ result, version, browser: browser.version(), steps, consoleMessages, errors, failure, inputSha256: createHash('sha256').update(dataBefore).digest('hex') }, null, 2));
  await browser.close(); await new Promise(resolve => server.close(resolve));
}
console.log(JSON.stringify({ result, version, steps: steps.length, output, failure }, null, 2));
if (result !== 'PASS') process.exitCode = 1;
