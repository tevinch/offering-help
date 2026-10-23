import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { readFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
const fixtures = resolve('.work/fixtures');
const outputs = resolve('.work/downloads');
const python = process.env.PYTHON || 'python3';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const verify = (...args) => execFileSync(python, ['tests/verify.py', ...args], { encoding: 'utf8' });
test.beforeAll(() => {
  mkdirSync(outputs, { recursive: true });
  console.log(verify('generate', fixtures));
});
async function inputHash(page) {
  return page.locator('#file').evaluate(async input => {
    const bytes = await input.files[0].arrayBuffer();
    return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
      n => n.toString(16).padStart(2, '0')).join('');
  });
}
async function saveCopy(page, name, form, suffix) {
  const source = resolve(fixtures, name);
  const before = hash(readFileSync(source));
  await page.locator('#file').setInputFiles(source);
  expect(await inputHash(page)).toBe(before);
  await page.locator('#form').selectOption(form);
  await page.getByRole('button', { name: 'Prepare copy' }).click();
  await expect(page.locator('#status')).toContainText('Copy ready.', { timeout: 150000 });
  await expect(page.locator('#download')).toBeVisible();
  const downloadEvent = page.waitForEvent('download');
  await page.locator('#download').click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toBe(name.replace(/\.jpg$/, '-without-trailer.jpg'));
  const output = resolve(outputs, suffix + '.jpg');
  await download.saveAs(output);
  expect(await download.failure()).toBeNull();
  expect(hash(readFileSync(source))).toBe(before);
  expect(await inputHash(page)).toBe(before);
  console.log(verify('verify', source, output));
  return output;
}
for (const form of ['tags', 'args']) {
  test(`${form} removes trailers from actual saved copies and preserves input`, async ({ page }) => {
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto('/');
    const output = await saveCopy(page, 'trailer1.jpg', form, form + '-first');
    expect(hash(readFileSync(output))).not.toBe(hash(readFileSync(resolve(fixtures, 'trailer1.jpg'))));
    await saveCopy(page, 'trailer2.jpg', form, form + '-second');
    await saveCopy(page, 'plain1.jpg', form, form + '-plain');
    await page.screenshot({ path: resolve(outputs, form + '.png'), fullPage: true });
    expect(errors).toEqual([]);
  });
}
test('invalid input fails without download and next valid operation works', async ({ page }) => {
  await page.goto('/');
  const source = resolve(fixtures, 'invalid.jpg');
  const before = hash(readFileSync(source));
  const downloads = []; page.on('download', download => downloads.push(download));
  await page.locator('#file').setInputFiles(source);
  await page.getByRole('button', { name: 'Prepare copy' }).click();
  await expect(page.locator('#status')).toContainText('Could not prepare copy:', { timeout: 150000 });
  await expect(page.locator('#download')).toBeHidden();
  await expect(page.locator('#download')).not.toHaveAttribute('href');
  expect(hash(readFileSync(source))).toBe(before);
  expect(await inputHash(page)).toBe(before);
  expect(downloads).toEqual([]);
  await saveCopy(page, 'trailer2.jpg', 'tags', 'after-error');
});

test('valid PNG and renamed spoofed PNG are rejected without a download', async ({ page }) => {
  await page.goto('/');
  await saveCopy(page, 'trailer2.jpg', 'args', 'before-png');
  const source = resolve(fixtures, 'valid.png');
  const bytes = readFileSync(source);
  const before = hash(bytes);
  const downloads = []; page.on('download', download => downloads.push(download));
  for (const input of [source, { name: 'renamed.jpg', mimeType: 'image/jpeg', buffer: bytes }]) {
    await page.locator('#file').setInputFiles(input);
    await expect(page.locator('#download')).not.toHaveAttribute('href');
    expect(await inputHash(page)).toBe(before);
    await page.getByRole('button', { name: 'Prepare copy' }).click();
    await expect(page.locator('#status')).toContainText('Choose a JPEG file', { timeout: 5000 });
    await expect(page.locator('#download')).toBeHidden();
    await expect(page.locator('#download')).not.toHaveAttribute('href');
    expect(hash(readFileSync(source))).toBe(before);
    expect(await inputHash(page)).toBe(before);
    expect(downloads).toEqual([]);
  }
  await saveCopy(page, 'trailer1.jpg', 'tags', 'after-png');
});
