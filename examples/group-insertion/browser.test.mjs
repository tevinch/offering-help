import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { chromium } from 'playwright';
import { buildApp } from './build.mjs';
import { serve } from './server.mjs';

const directory = await mkdtemp(join(tmpdir(), 'group-insertion-'));
await mkdir('test-results', { recursive: true });
const browser = await chromium.launch({ headless: true });
const checks = [];
const faults = [];
const check = (name, value, expected) => {
  assert.deepEqual(value, expected, name);
  checks.push({ name, value });
};
const source = await readFile(new URL('./app.jsx', import.meta.url), 'utf8');
const modelSource = await readFile(new URL('./model.mjs', import.meta.url), 'utf8');
const collect = async (page) => page.locator('[data-group-id]').evaluateAll((groups) => groups.map((group) => ({
  id: group.dataset.groupId,
  items: [...group.querySelectorAll('[data-item-id]')].map((item) => item.dataset.itemId),
})));
const initial = [
  { id: 'group-a', items: ['alpha', 'beta', 'note'] },
  { id: 'group-b', items: ['gamma', 'delta'] },
  { id: 'group-c', items: ['epsilon'] },
];
const allItems = (state) => state.flatMap((g) => g.items).sort();
async function until(fn, message) {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (await fn()) return;
    await new Promise((resolve) => setTimeout(resolve, 25));
  }
  throw new Error(message);
}
async function atRest(page) {
  await until(async () => await page.locator('[data-rfd-drag-handle-draggable-id][aria-describedby]').count() === 6,
    'all drag handles must be present');
  await until(async () => !(await page.locator('[data-rfd-draggable-id][style*="position: fixed"]').count()),
    'drag animation must settle');
}
async function pointerLift(page, id) {
  const handle = page.locator(`[data-rfd-drag-handle-draggable-id="${id}"]`);
  await handle.scrollIntoViewIfNeeded();
  const box = await handle.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 8, box.y + box.height / 2, { steps: 3 });
  await until(async () => (await page.locator('[role="status"]').textContent()).startsWith('Picked up'),
    'onDragStart must run');
}
async function pointerOver(page, targetId, targetIndex = 0) {
  const target = page.locator(`[data-rfd-droppable-id="${targetId}"]`);
  await target.scrollIntoViewIfNeeded();
  const box = await target.boundingBox();
  const items = target.locator('[data-item-id]');
  const count = await items.count();
  let y = box.y + 35;
  if (count) {
    const itemBox = await items.nth(Math.min(targetIndex, count - 1)).boundingBox();
    y = targetIndex < count ? itemBox.y + 3 : itemBox.y + itemBox.height + 12;
  }
  await page.mouse.move(box.x + box.width / 2, y, { steps: 18 });
  await page.waitForTimeout(100);
}
async function pointerDrop(page, id, targetId, targetIndex) {
  await pointerLift(page, id);
  await pointerOver(page, targetId, targetIndex);
  await page.mouse.up();
  await atRest(page);
}
async function fresh(page, url) {
  await page.goto(url);
  await atRest(page);
  check('initial board', await collect(page), initial);
}
async function assertInserted(page, position, moved, sourceId) {
  await until(async () => await page.locator('[data-group-id]').count() === 4, 'gap drop must create a group');
  const expected = structuredClone(initial);
  expected.find((g) => g.id === sourceId).items = expected.find((g) => g.id === sourceId).items.filter((id) => id !== moved);
  expected.splice(position, 0, { id: 'created-1', items: [moved] });
  check(`group inserted at ${position}`, await collect(page), expected);
  check('all original items exactly once', allItems(await collect(page)), allItems(initial));
}

try {
  for (const variant of ['working', 'no-gap-move', 'no-drag-start', 'no-disabled-prop']) {
    const output = join(directory, variant);
    const appSource = variant === 'no-drag-start'
      ? source.replace('setDraggingId(start.draggableId);', '/* drag-start state omitted */')
      : variant === 'no-disabled-prop'
        ? source.replace('isDropDisabled={newGroupDisabled}', '')
        : source;
    if (variant === 'no-drag-start' || variant === 'no-disabled-prop') assert.notEqual(appSource, source);
    await buildApp(output, appSource,
    variant === 'no-gap-move'
      ? modelSource.replace('if (gap) {', 'if (gap) return state;\n  if (gap) {')
      : modelSource);
    const server = await serve(output, 0);
    const page = await browser.newPage({ viewport: { width: 1500, height: 900 } });
    page.on('pageerror', (error) => faults.push({ variant, type: 'pageerror', message: error.message }));
    page.on('console', (message) => {
      if (message.type() === 'error') faults.push({ variant, type: 'console', message: message.text() });
    });
    const url = `http://127.0.0.1:${server.address().port}`;
    try {
      await fresh(page, url);
      if (variant === 'no-gap-move') {
        await pointerDrop(page, 'alpha', 'gap:1');
        await assert.rejects(() => assertInserted(page, 1, 'alpha', 'group-a'), /gap drop must create a group/);
        check('negative: omitted gap mutation detected', await page.locator('[data-group-id]').count(), 3);
        check('negative preserves contents', await collect(page), initial);
        continue;
      }
      if (variant === 'no-drag-start') {
        await pointerLift(page, 'note');
        const disabled = await page.locator('[data-gap="1"]').getAttribute('aria-disabled');
        assert.throws(() => assert.equal(disabled, 'true'));
        check('negative: omitted hook state fails gap configuration acceptance', disabled, 'false');
        await pointerOver(page, 'gap:1');
        await page.mouse.up();
        await atRest(page);
        check('negative: drop responder reports accepted target without active-item condition',
          await page.locator('[role="status"]').textContent(), 'Move finished.');
        continue;
      }
      if (variant === 'no-disabled-prop') {
        await pointerLift(page, 'note');
        check('negative: presentation alone still says disabled', await page.locator('[data-gap="1"]').getAttribute('aria-disabled'), 'true');
        await pointerOver(page, 'gap:1');
        await page.mouse.up();
        await atRest(page);
        const message = await page.locator('[role="status"]').textContent();
        assert.throws(() => assert.equal(message, 'No move made.'));
        check('negative: missing actual isDropDisabled fails refused-drop acceptance', message, 'Move finished.');
        check('negative: model guard alone preserves data but cannot prove target configuration', await collect(page), initial);
        continue;
      }
      check('root is not a drop target', await page.locator('.board[data-rfd-droppable-id]').count(), 0);
      check('seven sibling targets', await page.locator('.board > [data-rfd-droppable-id]').count(), 7);
      for (const position of [0, 1, 3]) {
        await fresh(page, url);
        await pointerDrop(page, 'alpha', `gap:${position}`);
        await assertInserted(page, position, 'alpha', 'group-a');
      }
      await fresh(page, url);
      await pointerDrop(page, 'beta', 'gap:1');
      await assertInserted(page, 1, 'beta', 'group-a');
      await pointerDrop(page, 'gamma', 'created-1', 1);
      await until(async () => (await collect(page)).find((g) => g.id === 'created-1').items.includes('gamma'),
        'new group must accept another item');
      check('repeated operation after creation', await collect(page), [
        { id: 'group-a', items: ['alpha', 'note'] },
        { id: 'created-1', items: ['beta', 'gamma'] },
        { id: 'group-b', items: ['delta'] }, { id: 'group-c', items: ['epsilon'] },
      ]);
      await page.screenshot({ path: 'test-results/group-insertion.png', fullPage: true });

      await fresh(page, url);
      await pointerDrop(page, 'epsilon', 'group-b', 1);
      check('pointer group-to-group and empty group retained', await collect(page), [
        initial[0], { id: 'group-b', items: ['gamma', 'epsilon', 'delta'] }, { id: 'group-c', items: [] },
      ]);
      await fresh(page, url);
      const alpha = page.locator('[data-rfd-drag-handle-draggable-id="alpha"]');
      await alpha.focus();
      await page.keyboard.press('Space');
      await until(async () => (await page.locator('[role="status"]').textContent()).includes('Picked up Alpha'), 'keyboard lift');
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(100);
      await page.keyboard.press('Space');
      await atRest(page);
      check('keyboard within-group reorder', await collect(page), [
        { id: 'group-a', items: ['beta', 'alpha', 'note'] }, initial[1], initial[2],
      ]);
      await fresh(page, url);
      await alpha.focus();
      await page.keyboard.press('Space');
      await until(async () => (await page.locator('[role="status"]').textContent()).includes('Picked up Alpha'), 'keyboard lift');
      await page.keyboard.press('ArrowRight');
      await page.waitForTimeout(100);
      await page.keyboard.press('Space');
      await atRest(page);
      await assertInserted(page, 1, 'alpha', 'group-a');

      await fresh(page, url);
      await alpha.focus();
      await page.keyboard.press('Space');
      await until(async () => (await page.locator('[role="status"]').textContent()).includes('Picked up Alpha'), 'keyboard lift');
      await page.keyboard.press('ArrowRight');
      await page.waitForTimeout(100);
      await page.keyboard.press('ArrowRight');
      await page.waitForTimeout(100);
      await page.keyboard.press('Space');
      await atRest(page);
      check('keyboard group-to-group', await collect(page), [
        { id: 'group-a', items: ['beta', 'note'] },
        { id: 'group-b', items: ['alpha', 'gamma', 'delta'] }, initial[2],
      ]);

      for (const mode of ['pointer', 'keyboard']) {
        await fresh(page, url);
        if (mode === 'pointer') {
          await pointerLift(page, 'alpha');
          await pointerOver(page, 'gap:1');
        } else {
          await alpha.focus();
          await page.keyboard.press('Space');
          await page.keyboard.press('ArrowRight');
        }
        await page.keyboard.press('Escape');
        await page.mouse.up();
        await atRest(page);
        check(`${mode} cancellation`, await collect(page), initial);
      }

      await fresh(page, url);
      await pointerLift(page, 'note');
      check('drag-start reads actual restricted item', await page.locator('[role="status"]').textContent(),
        'Picked up Attached note. New groups disabled.');
      check('all gap targets disabled', await page.locator('[data-gap][aria-disabled="true"]').count(), 4);
      await pointerOver(page, 'gap:1');
      await page.mouse.up();
      await atRest(page);
      check('actual library rejected the disabled gap', await page.locator('[role="status"]').textContent(), 'No move made.');
      check('restricted gap drop preserves board', await collect(page), initial);
      await pointerDrop(page, 'note', 'group-b', 0);
      check('restricted item still moves to existing group', await collect(page), [
        { id: 'group-a', items: ['alpha', 'beta'] },
        { id: 'group-b', items: ['note', 'gamma', 'delta'] }, initial[2],
      ]);
    } finally {
      await page.close();
      await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
    }
  }
  check('no page or console errors', faults, []);
  await writeFile('test-results/result.json', JSON.stringify({ checks, faults, browser: browser.version() }, null, 2));
  console.log(`Browser acceptance passed: ${checks.length} observations; three negative controls detected.`);
} finally {
  await writeFile('test-results/latest-observations.json', JSON.stringify({ checks, faults }, null, 2));
  await browser.close();
  await rm(directory, { recursive: true, force: true });
}
