import assert from 'node:assert/strict';
import {chromium, firefox} from 'playwright';

// Missing onmounted/scroll wiring must fail at the first offscreen target.
const kind = process.env.BROWSER ?? 'chromium';
const browser = await ({chromium, firefox}[kind]).launch({headless: true});
const page = await browser.newPage({viewport: {width: 1100, height: 900}});
const errors = [];
page.on('pageerror', error => errors.push(error.message));
const evidence = [];
async function until(check, label) {
  const deadline = Date.now() + 15000;
  do {
    if (await check()) return;
    await new Promise(resolve => setTimeout(resolve, 50));
  } while (Date.now() < deadline);
  assert.fail(label);
}
try {
  await page.goto(process.env.DEMO_URL ?? 'http://127.0.0.1:8187');
  const viewport = page.locator('.dx-virtual-list-container');
  await until(async () => await viewport.count() === 1, "the real virtual list must render");
  const initial = await viewport.elementHandle();
  assert(initial, 'real virtual-list container is mounted');
  assert.equal(await page.locator('[data-virtual-index="30000"]').count(), 0,
    'first destination must start outside the mounted window');
  await page.locator('#first-label').fill('Saved label');
  let navigations = 0;
  page.on('framenavigated', frame => { if (frame === page.mainFrame()) navigations++; });

  async function record(index) {
    await until(async () => page.evaluate(index => {
      const box = document.querySelector('.dx-virtual-list-container');
      const row = box?.querySelector(`[data-virtual-index="${index}"]`);
      if (!row) return false;
      const a = box.getBoundingClientRect(), b = row.getBoundingClientRect();
      return b.top >= a.top - 1 && b.bottom <= a.bottom + 1;
    }, index), `index ${index} must really enter the viewport`);
    const state = await page.evaluate(({index, initial}) => {
      const box = document.querySelector('.dx-virtual-list-container');
      const row = box.querySelector(`[data-virtual-index="${index}"]`);
      return {
        index, scrollTop: box.scrollTop, height: row.getBoundingClientRect().height,
        text: row.textContent, rendered: box.querySelectorAll('[data-virtual-index]').length,
        setsize: row.getAttribute('aria-setsize'), sameContainer: box === initial,
        count: document.querySelector('#row-count').textContent,
        savedLabel: document.querySelector('#first-label').value,
      };
    }, {index, initial});
    assert.equal(state.sameContainer, true, 'navigation must preserve the actual mounted container');
    assert.equal(state.setsize, '39999');
    assert.equal(state.count, '39999');
    assert.equal(state.savedLabel, 'Saved label');
    assert.equal(state.height, 48, 'real CSS height must match the estimate');
    assert(state.rendered > 0 && state.rendered < 300, 'list must stay virtualized');
    assert.equal(state.text.trim(), `${index} ${index === 0 ? 'Saved label' : `Test_${index + 1}`}`);
    if (index > 20) assert(state.scrollTop > 0, 'offscreen navigation must change native scrollTop');
    if (index === 0) assert.equal(state.scrollTop, 0);
    evidence.push(state);
  }
  async function go(index, click = false) {
    await page.locator('#target-index').fill(String(index));
    if (click) await page.getByRole('button', {name: 'Go to row', exact: true}).click();
    else await page.locator('#target-index').press('Enter');
    await record(index);
  }
  await go(30000);
  await go(12);
  await go(39998);
  await go(15000, true);
  await page.getByRole('button', {name: 'Go to top', exact: true}).click();
  await record(0);
  await viewport.hover();
  await page.mouse.wheel(0, 960);
  await until(async () => viewport.evaluate(el => el.scrollTop > 0), 'wheel must scroll the real list');
  await go(20000);
  const beforeInvalid = await viewport.evaluate(el => el.scrollTop);
  for (const invalid of ['-1', '39999', 'abc', '']) {
    await page.locator('#target-index').fill(invalid);
    await page.locator('#target-index').press('Enter');
    await until(async () => (await page.locator('#status').textContent()).includes('0 to 39998'),
      'invalid target must show an actionable range');
    assert.equal(await viewport.evaluate(el => el.scrollTop), beforeInvalid, 'invalid target must not move the list');
  }
  await go(30000);
  await go(0);
  assert.equal(navigations, 0, 'Enter must not reload/navigate the document');
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({browser: kind, passed: true, evidence}, null, 2));
} finally {
  await browser.close();
}
