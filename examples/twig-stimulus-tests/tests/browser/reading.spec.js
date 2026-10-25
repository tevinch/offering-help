import { test, expect } from '@playwright/test';

test('Twig loads the controller and repeated form operations reach the real server', async ({ page }) => {
  const errors = [];
  const controllers = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => {
    if (/title_count_controller[^/]*\.js/.test(response.url())) controllers.push(response.status());
  });
  await page.goto('/');
  await expect(page.locator('output')).toHaveText('0 characters');
  await expect.poll(() => controllers.length).toBeGreaterThan(0);
  expect(controllers.every(status => status === 200)).toBe(true);
  await page.getByLabel('Reading title').fill('ab');
  await expect(page.locator('output')).toHaveText('2 characters');
  const invalidResponse = page.waitForResponse(response =>
    response.request().method() === 'POST' && new URL(response.url()).pathname === '/');
  await page.getByRole('button', { name: 'Check title' }).click();
  expect((await invalidResponse).status()).toBe(422);
  await expect(page.locator('#result')).toHaveText('Use 3 to 40 characters.');
  await expect(page.locator('output')).toHaveText('2 characters');
  await page.getByLabel('Reading title').fill('  Read a chapter  ');
  await expect(page.locator('output')).toHaveText('18 characters');
  const acceptedResponse = page.waitForResponse(response =>
    response.request().method() === 'POST' && new URL(response.url()).pathname === '/');
  await page.getByRole('button', { name: 'Check title' }).click();
  expect((await acceptedResponse).status()).toBe(200);
  await expect(page.locator('#result')).toHaveText('Accepted: Read a chapter');
  await expect(page.getByLabel('Reading title')).toHaveValue('Read a chapter');
  await expect(page.locator('output')).toHaveText('14 characters');
  await page.getByLabel('Reading title').fill('Another book');
  await expect(page.locator('output')).toHaveText('12 characters');
  const repeatedResponse = page.waitForResponse(response =>
    response.request().method() === 'POST' && new URL(response.url()).pathname === '/');
  await page.getByRole('button', { name: 'Check title' }).click();
  expect((await repeatedResponse).status()).toBe(200);
  await expect(page.locator('#result')).toHaveText('Accepted: Another book');
  expect(errors).toEqual([]);
});
