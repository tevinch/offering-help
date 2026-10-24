import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { resolve, dirname, extname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { chromium } from 'playwright';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const output = resolve(process.env.WORKINGS_OUTPUT_DIR || resolve(root, 'test-results'));
const digit = (page, row, col) => page.getByRole('textbox', { name: `Digit, row ${row + 1}, column ${col + 1}`, exact: true });
const note = (page, row, col) => page.getByRole('textbox', { name: `Small number, row ${row + 1}, column ${col + 1}`, exact: true });

async function makePage(page, operation, first, second) {
  await page.getByLabel('Operation', { exact: true }).selectOption(operation);
  await page.getByLabel('First number', { exact: true }).fill(first);
  await page.getByLabel('Second number', { exact: true }).fill(second);
  await page.getByRole('button', { name: 'Make page', exact: true }).click();
  await assert.doesNotReject(() => page.getByRole('table', { name: 'Your working', exact: true }).waitFor({ timeout: 2000 }));
}

async function typeNumber(page, row, col, value) {
  await digit(page, row, col).focus();
  await page.keyboard.type(value);
}

async function smallNumber(page, row, col, value) {
  await digit(page, row, col).focus();
  await page.getByRole('button', { name: 'Small number', exact: true }).click();
  await page.keyboard.type(value);
  await page.keyboard.press('Escape');
  assert.equal(await digit(page, row, col).evaluate(e => e === document.activeElement), true, 'Escape returns to the main square');
}

async function crossOut(page, row, col) {
  await digit(page, row, col).focus();
  await page.getByRole('button', { name: 'Cross out', exact: true }).click();
}

async function underline(page, row, col) {
  await digit(page, row, col).focus();
  await page.getByRole('button', { name: 'Underline row', exact: true }).click();
}

async function expectValues(page, entries) {
  for (const [row, col, value] of entries) assert.equal(await digit(page, row, col).inputValue(), value, `digit at ${row},${col}`);
}

async function expectAddition(page) {
  await expectValues(page, [[1, 2, '5'], [1, 3, '8'], [2, 2, '6'], [2, 3, '7'], [3, 1, '1'], [3, 2, '2'], [3, 3, '5']]);
  assert.equal(await note(page, 1, 2).inputValue(), '1', 'the carried one is part of the completed working');
}

async function completeAddition(page, omitCarry = false) {
  await makePage(page, 'add', '58', '67');
  assert.equal(await digit(page, 3, 3).inputValue(), '', 'the page must not supply an answer');
  if (!omitCarry) await smallNumber(page, 1, 2, '1');
  await typeNumber(page, 3, 3, '5');
  await page.keyboard.press('ArrowLeft');
  assert.equal(await digit(page, 3, 2).evaluate(e => e === document.activeElement), true, 'left arrow moves one column');
  await page.keyboard.type('9'); // A deliberately wrong tens digit, then a normal correction.
  await digit(page, 3, 2).focus();
  await page.keyboard.press('Backspace');
  await page.keyboard.type('2');
  await typeNumber(page, 3, 1, '1');
}

async function expectSubtraction(page) {
  await expectValues(page, [[1, 2, '1'], [1, 3, '0'], [1, 4, '0'], [1, 5, '0'], [3, 3, '6'], [3, 4, '1'], [3, 5, '3']]);
  for (const [col, value] of [[2, '0'], [3, '9'], [4, '9'], [5, '10']]) {
    assert.equal(await note(page, 1, col).inputValue(), value);
    assert.equal(await digit(page, 1, col).evaluate(e => e.closest('td').classList.contains('crossed')), true);
    assert.match(await digit(page, 1, col).evaluate(e => getComputedStyle(e).textDecorationLine), /line-through/);
  }
}

async function completeSubtraction(page, omitBorrow = false) {
  await makePage(page, 'sub', '1000', '387');
  for (const [col, value] of [[2, '0'], [3, '9'], [4, '9'], [5, '10']]) {
    if (!(omitBorrow && col === 5)) {
      await crossOut(page, 1, col);
      await smallNumber(page, 1, col, value);
    }
  }
  await typeNumber(page, 3, 3, '613');
}

async function expectMultiplication(page) {
  await expectValues(page, [[1, 4, '2'], [1, 5, '3'], [2, 4, '1'], [2, 5, '4'], [3, 4, '9'], [3, 5, '2'], [4, 3, '2'], [4, 4, '3'], [4, 5, '0'], [5, 3, '3'], [5, 4, '2'], [5, 5, '2']]);
  assert.equal(await note(page, 1, 4).inputValue(), '1');
  assert.equal(await digit(page, 4, 3).evaluate(e => e.closest('tr').classList.contains('underlined')), true);
}

async function completeMultiplication(page, omitPartial = false) {
  await makePage(page, 'mul', '23', '14');
  await smallNumber(page, 1, 4, '1');
  await typeNumber(page, 3, 4, '92');
  if (!omitPartial) await typeNumber(page, 4, 3, '230');
  await underline(page, 4, 3);
  await typeNumber(page, 5, 3, '322');
}

async function expectDivision(page) {
  await expectValues(page, [[0, 4, '1'], [0, 5, '3'], [1, 0, '1'], [1, 1, '2'], [1, 3, '1'], [1, 4, '5'], [1, 5, '6'], [2, 3, '1'], [2, 4, '2'], [3, 4, '3'], [3, 5, '6'], [4, 4, '3'], [4, 5, '6'], [5, 5, '0']]);
  for (const row of [2, 4]) assert.equal(await digit(page, row, 4).evaluate(e => e.closest('tr').classList.contains('underlined')), true);
  const border = await digit(page, 1, 3).evaluate(e => ({ top: getComputedStyle(e.closest('td')).borderTopWidth, left: getComputedStyle(e.closest('td')).borderLeftWidth }));
  assert.ok(parseFloat(border.top) >= 2 && parseFloat(border.left) >= 2, 'long division must have a real bracket');
  const q = await digit(page, 0, 4).boundingBox();
  const a = await digit(page, 1, 4).boundingBox();
  assert.ok(Math.abs(q.x - a.x) < 1 && q.y < a.y, 'quotient must align above the dividend');
}

async function completeDivision(page, omitSubtract = false) {
  await makePage(page, 'div', '156', '12');
  await typeNumber(page, 0, 4, '13');
  await typeNumber(page, 2, 3, '12');
  await underline(page, 2, 3);
  await typeNumber(page, 3, 4, '36');
  if (!omitSubtract) await typeNumber(page, 4, 4, '36');
  await underline(page, 4, 4);
  await typeNumber(page, 5, 5, '0');
}

async function snapshot(page) {
  return page.getByRole('table', { name: 'Your working', exact: true }).evaluate(table => [...table.rows].map(row => ({
    line: row.classList.contains('underlined'),
    cells: [...row.cells].map(cell => ({ digit: cell.querySelector('.digit')?.value, note: cell.querySelector('.small-number')?.value, crossed: cell.classList.contains('crossed') }))
  })));
}

test('complete handwritten-style working through real browser controls', async t => {
  await mkdir(output, { recursive: true });
  const server = createServer(async (req, res) => {
    try {
      const pathname = new URL(req.url, 'http://localhost').pathname;
      const path = resolve(root, `.${pathname === '/' ? '/index.html' : pathname}`);
      if (!path.startsWith(`${root}/`)) { res.writeHead(404); res.end(); return; }
      const data = await readFile(path);
      res.setHeader('Content-Type', ({ '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' })[extname(path)] || 'application/octet-stream');
      res.end(data);
    } catch { res.writeHead(404); res.end('No page here.'); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  context.setDefaultTimeout(5000);
  const errors = [];
  const operations = [];
  const open = async (file = false) => {
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    page.on('dialog', dialog => dialog.accept());
    await page.goto(file ? pathToFileURL(resolve(root, 'index.html')).href : `http://127.0.0.1:${server.address().port}/`);
    await page.getByRole('heading', { name: 'Column workings', exact: true }).waitFor({ timeout: 2000 });
    return page;
  };
  const capture = async (page, name) => {
    await page.getByRole('table', { name: 'Your working', exact: true }).screenshot({ path: resolve(output, `${name}.png`) });
    if (process.env.WORKINGS_PRINT === '1') {
      await page.pdf({ path: resolve(output, `${name}.pdf`), format: 'A4', printBackground: true, preferCSSPageSize: true });
    }
    operations.push({ name, state: await snapshot(page) });
  };
  try {
    await t.test('addition retains a carry and correction when working rows grow', async () => {
      const page = await open();
      await completeAddition(page);
      await expectAddition(page);
      const before = await snapshot(page);
      await page.getByRole('button', { name: 'Add working row', exact: true }).click();
      const after = await snapshot(page);
      assert.deepEqual(after.slice(0, before.length), before);
      assert.equal(after.length, before.length + 1);
      await typeNumber(page, after.length - 1, 1, '7');
      assert.equal(await digit(page, after.length - 1, 1).inputValue(), '7');
      await digit(page, after.length - 1, 1).focus();
      await page.keyboard.press('Backspace');
      await expectAddition(page);
      await capture(page, 'addition');
      await page.close();
    });
    await t.test('subtraction preserves crossed originals and multi-digit replacement notes', async () => {
      const page = await open();
      await completeSubtraction(page);
      await expectSubtraction(page);
      await capture(page, 'subtraction');
      await page.close();
    });
    await t.test('multiplication includes both partial products and its own total', async () => {
      const page = await open(); await completeMultiplication(page); await expectMultiplication(page);
      await capture(page, 'multiplication'); await page.close();
    });
    await t.test('long division includes quotient, both subtractions and remainder', async () => {
      const page = await open(); await completeDivision(page); await expectDivision(page);
      await capture(page, 'division'); await page.close();
    });
    await t.test('eight-digit factors retain sixteen written result digits', async () => {
      const page = await open(); await makePage(page, 'mul', '99999999', '99999999');
      await typeNumber(page, 11, 2, '9999999800000001');
      const state = await snapshot(page);
      assert.equal(state[11].cells.slice(2).map(cell => cell.digit).join(''), '9999999800000001');
      assert.equal(state[1].cells.slice(10).map(cell => cell.digit).join(''), '99999999');
      assert.equal(state[2].cells.slice(10).map(cell => cell.digit).join(''), '99999999');
      await capture(page, 'maximum-width'); await page.close();
    });
    await t.test('invalid new setup keeps all existing working', async () => {
      const page = await open(); await completeAddition(page); const before = await snapshot(page);
      for (const [op, first, second] of [['div', '156', '0'], ['sub', '3', '8'], ['add', '123456789', '1'], ['add', '-1', '2'], ['add', '1.5', '2']]) {
        await page.getByLabel('Operation', { exact: true }).selectOption(op);
        await page.getByLabel('First number', { exact: true }).fill(first);
        await page.getByLabel('Second number', { exact: true }).fill(second);
        await page.getByRole('button', { name: 'Make page', exact: true }).click();
        assert.ok((await page.getByRole('alert').innerText()).length > 0);
        assert.deepEqual(await snapshot(page), before);
      }
      await makePage(page, 'add', '0', '0');
      await expectValues(page, [[1, 2, '0'], [2, 2, '0']]);
      await page.close();
    });
    await t.test('acceptance rejects a missing carry, borrowing, multiplication partial or division subtraction', async () => {
      for (const [run, check] of [[completeAddition, expectAddition], [completeSubtraction, expectSubtraction], [completeMultiplication, expectMultiplication], [completeDivision, expectDivision]]) {
        const page = await open(); await run(page, true); await assert.rejects(() => check(page), assert.AssertionError); await page.close();
      }
    });
    await t.test('keyboard arrows and Tab move between squares; Print opens the print operation', async () => {
      const page = await open(); await makePage(page, 'add', '58', '67');
      await digit(page, 3, 1).focus();
      for (const [key, row, col] of [['ArrowRight', 3, 2], ['ArrowUp', 2, 2], ['ArrowDown', 3, 2], ['ArrowLeft', 3, 1], ['Tab', 3, 2]]) {
        await page.keyboard.press(key);
        assert.equal(await digit(page, row, col).evaluate(e => e === document.activeElement), true, `${key} reaches row ${row + 1}, column ${col + 1}`);
      }
      const before = await snapshot(page);
      await page.evaluate(() => { window.printEvents = 0; window.addEventListener('beforeprint', () => { window.printEvents++; }); });
      await page.getByRole('button', { name: 'Print', exact: true }).click();
      assert.equal(await page.evaluate(() => window.printEvents), 1, 'the visible Print control starts native printing');
      assert.deepEqual(await snapshot(page), before);
      await page.close();
    });
    await t.test('the same page works as a local file without network requests', async () => {
      const page = await context.newPage(); const requests = [];
      page.on('request', req => { if (/^https?:/.test(req.url())) requests.push(req.url()); });
      await page.goto(pathToFileURL(resolve(root, 'index.html')).href);
      await completeDivision(page); await expectDivision(page); assert.deepEqual(requests, []);
      await page.close();
    });
    assert.deepEqual(errors, []);
    await writeFile(resolve(output, 'verification.json'), JSON.stringify({ operations, pageErrors: errors, print: process.env.WORKINGS_PRINT === '1' }, null, 2));
  } finally {
    await context.close(); await browser.close(); await new Promise(resolve => server.close(resolve));
  }
});
