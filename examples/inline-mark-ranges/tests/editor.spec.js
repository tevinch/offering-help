import { test, expect } from '@playwright/test';

const examplePath = process.env.EXAMPLE_PATH || '/';
test.afterEach(async ({ page }) => { expect(await page.pageErrors()).toEqual([]); });
async function state(page) {
  return page.locator('.cm-editor').evaluate(async element => {
    const { readEditor } = await import('/tests/read-editor.js');
    return readEditor(element);
  });
}
async function count(page) { return Number(await page.getByLabel('Change count').textContent()); }
async function assertDocument(page, expected) {
  expect((await state(page)).doc).toBe(expected);
  await expect(page.getByLabel('Current text', { exact: true })).toHaveText(expected);
}

test('three adjacent marks preserve the actual source text', async ({ page }) => {
  await page.goto(examplePath);
  const line = page.locator('.cm-line').first();
  await expect(line.locator('span')).toHaveCount(3);
  expect(await line.evaluate(element => [...element.childNodes].map(node => ({
    tag: node.nodeName, text: node.textContent,
    class: node.nodeType === Node.ELEMENT_NODE ? node.className : null,
  })))).toEqual([
    { tag: '#text', text: 'testing ', class: null },
    { tag: 'SPAN', text: '*', class: 'wa-marker' },
    { tag: 'SPAN', text: 'line', class: 'wa-bold' },
    { tag: 'SPAN', text: '*', class: 'wa-marker' },
  ]);
  await assertDocument(page, 'testing *line*');
  expect(await count(page)).toBe(0);
  await expect(page.locator('.cm-widgetBuffer')).toHaveCount(0);
  if (process.env.SCREENSHOT_DIR) await page.screenshot({ fullPage: true, path: `${process.env.SCREENSHOT_DIR}/initial.png` });
});

test('keyboard edits, delimiter repair, selection, history and save keep all text', async ({ page }) => {
  await page.goto(examplePath);
  const editor = page.locator('.cm-content');
  await editor.click();
  await page.keyboard.press('Home');
  for (let i = 0; i < 11; i++) await page.keyboard.press('ArrowRight');
  expect((await state(page)).from).toBe(11);
  await page.keyboard.type('X');
  await assertDocument(page, 'testing *liXne*');
  await expect(page.locator('.wa-bold')).toHaveText('liXne');
  expect(await count(page)).toBeGreaterThan(0);

  await page.keyboard.press('End');
  await page.keyboard.press('Backspace');
  await assertDocument(page, 'testing *liXne');
  await expect(page.locator('.wa-marker, .wa-bold')).toHaveCount(0);
  await page.keyboard.type('*');
  await assertDocument(page, 'testing *liXne*');
  await expect(page.locator('.wa-marker')).toHaveCount(2);
  await expect(page.locator('.wa-bold')).toHaveText('liXne');

  await page.keyboard.press('Enter');
  await page.keyboard.type('keep this content');
  await page.keyboard.press('Enter');
  await page.keyboard.type('*two* and *three*');
  const beforeSelection = 'testing *liXne*\nkeep this content\n*two* and *three*';
  await assertDocument(page, beforeSelection);
  await expect(page.locator('.wa-marker')).toHaveCount(6);
  expect(await page.locator('.wa-bold').allTextContents()).toEqual(['liXne', 'two', 'three']);

  await page.keyboard.press('ArrowUp');
  await page.keyboard.press('ArrowUp');
  await page.keyboard.press('Home');
  for (let i = 0; i < 8; i++) await page.keyboard.press('ArrowRight');
  for (let i = 0; i < 4; i++) await page.keyboard.press('Shift+ArrowRight');
  expect(await state(page)).toMatchObject({ from: 8, to: 12 });
  const previousCount = await count(page);
  // Separate the replacement from prior typing in history.
  await page.waitForTimeout(550);
  await page.keyboard.type('plain');
  const replaced = 'testing plainne*\nkeep this content\n*two* and *three*';
  await assertDocument(page, replaced);
  await expect(page.locator('.wa-marker')).toHaveCount(4);
  expect(await page.locator('.wa-bold').allTextContents()).toEqual(['two', 'three']);
  expect(await count(page)).toBeGreaterThan(previousCount);
  await page.keyboard.press('ControlOrMeta+z');
  await assertDocument(page, beforeSelection);
  await expect(page.locator('.wa-marker')).toHaveCount(6);
  await page.keyboard.press('ControlOrMeta+Shift+z');
  await assertDocument(page, replaced);
  await expect(page.locator('.wa-marker')).toHaveCount(4);
  await page.keyboard.press('ControlOrMeta+z');
  await assertDocument(page, beforeSelection);

  await page.keyboard.press('ControlOrMeta+End');
  expect(await state(page)).toMatchObject({ from: beforeSelection.length, to: beforeSelection.length });
  await page.keyboard.type('!');
  const finalText = 'testing *liXne*\nkeep this content\n*two* and *three*!';
  await assertDocument(page, finalText);
  await page.getByRole('button', { name: 'Save text' }).click();
  expect(await page.getByLabel('Saved text', { exact: true }).textContent()).toBe(finalText);
  expect((await state(page)).doc).toBe(finalText);
  await expect(page.locator('.wa-marker')).toHaveCount(6);
  expect(await page.locator('.wa-bold').allTextContents()).toEqual(['liXne', 'two', 'three']);
  await expect(page.locator('.cm-widgetBuffer')).toHaveCount(0);
  expect(await count(page)).toBeGreaterThan(10);
  if (process.env.SCREENSHOT_DIR) await page.screenshot({ fullPage: true, path: `${process.env.SCREENSHOT_DIR}/editing.png` });
});

test('viewport changes decorate distant lines and bounded syntax stays literal', async ({ page }) => {
  await page.goto(examplePath);
  const editor = page.locator('.cm-content');
  await editor.click();
  await page.keyboard.press('ControlOrMeta+a');
  const lines = ['unpaired *text', '**double**', 'empty **', '\\*escaped*', '*split', 'across*', '*valid*', ...Array.from({ length: 200 }, (_, i) => `plain ${i}`), '*distant*'];
  const text = lines.join('\n');
  await page.keyboard.insertText(text);
  await assertDocument(page, text);
  const editsBeforeScroll = await count(page);
  await page.locator('.cm-scroller').evaluate(element => { element.scrollTop = 0; });
  await expect(page.locator('.wa-bold')).toHaveText('valid');
  await page.locator('.cm-scroller').evaluate(element => { element.scrollTop = element.scrollHeight; });
  await expect(page.locator('.wa-bold')).toHaveText('distant');
  await expect(page.locator('.wa-marker')).toHaveCount(2);
  await assertDocument(page, text);
  expect(await count(page)).toBe(editsBeforeScroll);
  await page.getByRole('button', { name: 'Save text' }).click();
  expect(await page.getByLabel('Saved text', { exact: true }).textContent()).toBe(text);
  expect(await count(page)).toBeGreaterThan(0);
});
