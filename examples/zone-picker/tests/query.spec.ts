import { expect, test, type Page } from '@playwright/test';

async function enter(page: Page, label: string, value: string) {
  const input = page.getByLabel(label, { exact: true });
  await input.fill(value);
  await expect(input).toHaveValue(value);
  await input.press('Enter');
  await input.press('Tab');
}

async function enterRange(page: Page, start: string, end: string) {
  const first = page.getByLabel('Range start', { exact: true });
  const last = page.getByLabel('Range end', { exact: true });
  await first.fill(start);
  await first.press('Enter');
  await last.fill(end);
  await last.press('Enter');
  await last.press('Tab');
}

async function eraseWithKeyboard(page: Page, label: string) {
  const input = page.getByLabel(label, { exact: true });
  await input.click();
  await input.press('ControlOrMeta+A');
  await input.press('Backspace');
  await expect(input).toHaveValue('');
}

async function submit(page: Page) {
  const request = page.waitForRequest(request => request.url().endsWith('/api/reports') && request.method() === 'POST');
  await page.getByRole('button', { name: 'Query reports' }).click();
  const payload = (await request).postDataJSON();
  await expect(page.getByRole('status')).toContainText('Query complete');
  return payload;
}

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-05-25T18:30:00Z'));
  await page.goto('/');
});

test('typed UTC query returns the matching report, including after clear and repeated edits', async ({ page }) => {
  await enter(page, 'Report date and time', '2026-05-25 18:00:00');
  expect((await submit(page)).dateTime).toBe('2026-05-25T18:00:00.000Z');
  await expect(page.getByTestId('results')).toContainText('UTC evening report');
  for (const value of ['2026-05-25 17:00:00', '2026-05-25 18:00:00']) {
    await page.getByRole('button', { name: 'Clear date', exact: true }).click();
    await expect(page.getByLabel('Report date and time', { exact: true })).toHaveValue('');
    await enter(page, 'Report date and time', value);
    expect((await submit(page)).dateTime).toBe(value.replace(' ', 'T') + '.000Z');
  }
});

test('time-only and range endpoints use the shared zone and final request', async ({ page }) => {
  await page.getByLabel('Time reference date').fill('2026-05-25');
  await enter(page, 'Report time', '18:00:00');
  await enterRange(page, '2026-05-25 17:00:00', '2026-05-25 19:00:00');
  const payload = await submit(page);
  expect(payload.time).toBe('2026-05-25T18:00:00.000Z');
  expect(payload.range).toEqual(['2026-05-25T17:00:00.000Z', '2026-05-25T19:00:00.000Z']);
  await expect(page.getByTestId('results')).toContainText('UTC evening report');
});

test('today uses selected zone across the browser day boundary', async ({ page }) => {
  await page.getByLabel('Report date and time', { exact: true }).click();
  await expect(page.locator('.ant-picker-cell-today')).toHaveAttribute('title', '2026-05-25');
  await page.locator('.ant-picker-dropdown').filter({ visible: true }).getByText('Now', { exact: true }).click();
  await page.getByRole('heading', { name: 'Report times' }).click();
  expect((await submit(page)).dateTime).toBe('2026-05-25T18:30:00.000Z');
});

test('a typed date followed by Now submits the new instant', async ({ page }) => {
  await page.getByLabel('Report date and time', { exact: true }).fill('2026-05-25 18:00:00');
  await page.locator('.ant-picker-dropdown').filter({ visible: true }).getByText('Now', { exact: true }).click();
  await page.getByRole('heading', { name: 'Report times' }).click();
  expect((await submit(page)).dateTime).toBe('2026-05-25T18:30:00.000Z');
  await expect(page.getByRole('status')).toContainText('0 matching reports');
});

test('a typed date followed by calendar and clock edits submits the confirmed selection', async ({ page }) => {
  await page.getByLabel('Report date and time', { exact: true }).fill('2026-05-24 17:00:00');
  const popup = page.locator('.ant-picker-dropdown').filter({ visible: true });
  await popup.locator('td[title="2026-05-25"]').click();
  await popup.locator('.ant-picker-time-panel-column').nth(0).getByText('18', { exact: true }).click();
  await popup.getByRole('button', { name: 'OK', exact: true }).click();
  expect((await submit(page)).dateTime).toBe('2026-05-25T18:00:00.000Z');
  await expect(page.getByTestId('results')).toContainText('UTC evening report');
});

test('a typed time followed by a clock edit submits the confirmed anchored time', async ({ page }) => {
  await page.getByLabel('Report time', { exact: true }).fill('17:00:00');
  const popup = page.locator('.ant-picker-dropdown').filter({ visible: true });
  await popup.locator('.ant-picker-time-panel-column').nth(0).getByText('18', { exact: true }).click();
  await popup.getByRole('button', { name: 'OK', exact: true }).click();
  expect((await submit(page)).time).toBe('2026-05-25T18:00:00.000Z');
  await expect(page.getByTestId('results')).toContainText('UTC evening report');
});

test('typed range endpoints followed by clock edits submit both confirmed bounds', async ({ page }) => {
  await page.getByLabel('Range start', { exact: true }).fill('2026-05-25 15:00:00');
  const popup = page.locator('.ant-picker-dropdown').filter({ visible: true });
  await popup.locator('.ant-picker-time-panel-column').nth(0).getByText('17', { exact: true }).click();
  await popup.getByRole('button', { name: 'OK', exact: true }).click();
  await page.getByLabel('Range end', { exact: true }).fill('2026-05-25 21:00:00');
  await popup.locator('.ant-picker-time-panel-column').nth(0).getByText('19', { exact: true }).click();
  await popup.getByRole('button', { name: 'OK', exact: true }).click();
  await page.getByRole('heading', { name: 'Report times' }).click();
  expect((await submit(page)).range).toEqual(['2026-05-25T17:00:00.000Z', '2026-05-25T19:00:00.000Z']);
  await expect(page.getByTestId('results')).toContainText('UTC evening report');
  await expect(page.getByRole('status')).toContainText('1 matching reports');
});

test('keyboard-cleared date followed by Now submits the new instant', async ({ page }) => {
  await enter(page, 'Report date and time', '2026-05-25 18:00:00');
  await eraseWithKeyboard(page, 'Report date and time');
  await page.locator('.ant-picker-dropdown').filter({ visible: true }).getByText('Now', { exact: true }).click();
  await page.getByLabel('Report date and time', { exact: true }).press('Tab');
  await expect(page.getByRole('button', { name: 'Query reports' })).toBeEnabled();
  expect((await submit(page)).dateTime).toBe('2026-05-25T18:30:00.000Z');
  await expect(page.getByRole('status')).toContainText('0 matching reports');
});

test('keyboard-cleared time followed by a clock choice submits the new anchored time', async ({ page }) => {
  await enter(page, 'Report time', '17:00:00');
  await eraseWithKeyboard(page, 'Report time');
  const popup = page.locator('.ant-picker-dropdown').filter({ visible: true });
  await popup.locator('.ant-picker-time-panel-column').nth(0).getByText('18', { exact: true }).click();
  await popup.getByRole('button', { name: 'OK', exact: true }).click();
  await page.getByLabel('Report time', { exact: true }).press('Tab');
  await expect(page.getByRole('button', { name: 'Query reports' })).toBeEnabled();
  expect((await submit(page)).time).toBe('2026-05-25T18:00:00.000Z');
  await expect(page.getByTestId('results')).toContainText('UTC evening report');
});

test('keyboard-cleared range endpoints accept new clock choices and query both bounds', async ({ page }) => {
  await enterRange(page, '2026-05-25 15:00:00', '2026-05-25 21:00:00');
  await eraseWithKeyboard(page, 'Range start');
  const popup = page.locator('.ant-picker-dropdown').filter({ visible: true });
  await popup.locator('.ant-picker-time-panel-column').nth(0).getByText('17', { exact: true }).click();
  await popup.getByRole('button', { name: 'OK', exact: true }).click();
  await eraseWithKeyboard(page, 'Range end');
  await popup.locator('.ant-picker-time-panel-column').nth(0).getByText('19', { exact: true }).click();
  await popup.getByRole('button', { name: 'OK', exact: true }).click();
  await page.getByLabel('Range end', { exact: true }).press('Tab');
  await expect(page.getByRole('button', { name: 'Query reports' })).toBeEnabled();
  expect((await submit(page)).range).toEqual(['2026-05-25T17:00:00.000Z', '2026-05-25T19:00:00.000Z']);
  await expect(page.getByRole('status')).toContainText('1 matching reports');
  await expect(page.getByTestId('results')).toContainText('UTC evening report');
});

test('loading UTC values and switching zones preserves instants through reload', async ({ page }) => {
  await page.getByRole('button', { name: 'Load saved UTC example' }).click();
  const before = await submit(page);
  await page.getByLabel('Display time zone').selectOption('Asia/Kathmandu');
  await expect(page.getByLabel('Report date and time', { exact: true })).toHaveValue('2026-05-25 23:45:00');
  const after = await submit(page);
  expect(after.dateTime).toBe(before.dateTime);
  expect(after.time).toBe(before.time);
  expect(after.range).toEqual(before.range);
  await page.reload();
  await expect(page.getByLabel('Display time zone')).toHaveValue('Asia/Kathmandu');
  expect((await submit(page)).dateTime).toBe(before.dateTime);
});

test('fractional offset input creates the intended UTC instant', async ({ page }) => {
  await page.getByLabel('Display time zone').selectOption('Asia/Kathmandu');
  await enter(page, 'Report date and time', '2026-05-25 18:00:00');
  expect((await submit(page)).dateTime).toBe('2026-05-25T12:15:00.000Z');
});

test('DST gap does not silently submit a different time; repeated times use visible policy', async ({ page }) => {
  await page.getByLabel('Display time zone').selectOption('America/New_York');
  const input = page.getByLabel('Report date and time', { exact: true });
  await input.fill('2026-03-08 02:30:00');
  await input.press('Enter');
  await page.getByRole('heading', { name: 'Report times' }).click();
  await expect(page.getByRole('alert')).toContainText('does not exist');
  await expect(page.getByRole('button', { name: 'Query reports' })).toBeDisabled();
  await enter(page, 'Report date and time', '2026-11-01 01:30:00');
  expect((await submit(page)).dateTime).toBe('2026-11-01T05:30:00.000Z');
  await page.getByLabel('Repeated wall times').selectOption('later');
  await page.getByRole('button', { name: 'Clear date', exact: true }).click();
  await enter(page, 'Report date and time', '2026-11-01 01:30:00');
  expect((await submit(page)).dateTime).toBe('2026-11-01T06:30:00.000Z');
});

test('OK cannot authorize a normalized invalid draft; correcting it restores the query', async ({ page }) => {
  await page.getByLabel('Display time zone').selectOption('America/New_York');
  const requests: object[] = [];
  page.on('request', request => {
    if (request.url().endsWith('/api/reports') && request.method() === 'POST') requests.push(request.postDataJSON());
  });
  await page.getByLabel('Report date and time', { exact: true }).fill('2026-03-08 02:30:00');
  await page.locator('.ant-picker-dropdown').filter({ visible: true }).getByRole('button', { name: 'OK', exact: true }).click();
  await page.getByRole('heading', { name: 'Report times' }).click();
  await expect(page.getByRole('alert')).toContainText('02:30:00 does not exist');
  await expect(page.getByRole('button', { name: 'Query reports' })).toBeDisabled();
  expect(requests).toHaveLength(0);
  await enter(page, 'Report date and time', '2026-03-08 03:30:00');
  expect((await submit(page)).dateTime).toBe('2026-03-08T07:30:00.000Z');
  expect(requests).toHaveLength(1);
});

test('calendar and clock selection produces the same complete UTC report query', async ({ page }) => {
  await page.getByLabel('Report date and time', { exact: true }).click();
  const popup = page.locator('.ant-picker-dropdown').filter({ visible: true });
  await popup.locator('td[title="2026-05-25"]').click();
  await popup.locator('.ant-picker-time-panel-column').nth(0).getByText('18', { exact: true }).click();
  await popup.getByRole('button', { name: 'OK', exact: true }).click();
  expect((await submit(page)).dateTime).toBe('2026-05-25T18:00:00.000Z');
  await expect(page.getByTestId('results')).toContainText('UTC evening report');
});

test('time and range clear and reselect repeatedly without retaining stale query bounds', async ({ page }) => {
  await page.getByRole('button', { name: 'Load saved UTC example' }).click();
  await page.getByRole('button', { name: 'Clear date', exact: true }).click();
  for (let cycle = 0; cycle < 2; cycle++) {
    await page.getByRole('button', { name: 'Clear time', exact: true }).click();
    await page.getByRole('button', { name: 'Clear range', exact: true }).click();
    const cleared = await submit(page);
    expect(cleared.time).toBeNull();
    expect(cleared.range).toBeNull();
    await expect(page.getByRole('status')).toContainText('3 matching reports');
    await enter(page, 'Report time', '18:00:00');
    await enterRange(page, '2026-05-25 17:00:00', '2026-05-25 19:00:00');
    const filled = await submit(page);
    expect(filled.time).toBe('2026-05-25T18:00:00.000Z');
    expect(filled.range).toEqual(['2026-05-25T17:00:00.000Z', '2026-05-25T19:00:00.000Z']);
    await expect(page.getByTestId('results')).toContainText('UTC evening report');
  }
});

test('repeated direct edits and changing the zone after clearing retain usable controls', async ({ page }) => {
  for (const hour of ['17', '18', '19']) {
    await enter(page, 'Report date and time', `2026-05-25 ${hour}:00:00`);
    expect((await submit(page)).dateTime).toBe(`2026-05-25T${hour}:00:00.000Z`);
  }
  await page.getByRole('button', { name: 'Clear date', exact: true }).click();
  await page.getByLabel('Display time zone').selectOption('America/Cuiaba');
  await enter(page, 'Report date and time', '2026-05-25 18:00:00');
  expect((await submit(page)).dateTime).toBe('2026-05-25T22:00:00.000Z');
  // Retyping an unchanged value must not leave the form waiting for a callback that will not fire.
  await enter(page, 'Report date and time', '2026-05-25 18:00:00');
  await expect(page.getByLabel('Display time zone')).toBeEnabled();
});

test('DST offsets change across the spring boundary while an invalid draft cannot overwrite saved data', async ({ page }) => {
  await page.getByLabel('Display time zone').selectOption('America/New_York');
  await enter(page, 'Report date and time', '2026-03-08 01:30:00');
  expect((await submit(page)).dateTime).toBe('2026-03-08T06:30:00.000Z');
  await enter(page, 'Report date and time', '2026-03-08 03:30:00');
  expect((await submit(page)).dateTime).toBe('2026-03-08T07:30:00.000Z');
  await page.getByLabel('Report date and time', { exact: true }).fill('2026-03-08 02:30:00');
  await page.getByLabel('Report date and time', { exact: true }).press('Enter');
  await expect(page.getByRole('alert')).toContainText('02:30:00 does not exist');
  await expect(page.getByRole('button', { name: 'Query reports' })).toBeDisabled();
  await page.reload();
  await expect(page.getByLabel('Report date and time', { exact: true })).toHaveValue('2026-03-08 03:30:00');
  expect((await submit(page)).dateTime).toBe('2026-03-08T07:30:00.000Z');
});

test('time reference date follows the displayed instant across midnight and can be deliberately changed', async ({ page }) => {
  await page.getByRole('button', { name: 'Load saved UTC example' }).click();
  await page.getByLabel('Display time zone').selectOption('Pacific/Kiritimati');
  await expect(page.getByLabel('Report time', { exact: true })).toHaveValue('08:00:00');
  await expect(page.getByLabel('Time reference date')).toHaveValue('2026-05-26');
  expect((await submit(page)).time).toBe('2026-05-25T18:00:00.000Z');
  await page.getByRole('button', { name: 'Clear time', exact: true }).click();
  await expect(page.getByLabel('Time reference date')).toHaveValue('2026-05-26');
  await enter(page, 'Report time', '08:00:00');
  expect((await submit(page)).time).toBe('2026-05-25T18:00:00.000Z');
  await page.getByLabel('Time reference date').fill('2026-05-27');
  expect((await submit(page)).time).toBe('2026-05-26T18:00:00.000Z');
});

test('ordinary character typing keeps the draft until a valid value is committed', async ({ page }) => {
  const input = page.getByLabel('Report date and time', { exact: true });
  await input.click();
  await input.pressSequentially('2026-05-25 18:00:00');
  await expect(input).toHaveValue('2026-05-25 18:00:00');
  await input.press('Enter');
  expect((await submit(page)).dateTime).toBe('2026-05-25T18:00:00.000Z');
});

test('the built-in clear buttons remove all bounds and allow a fresh selection', async ({ page }) => {
  await page.getByRole('button', { name: 'Load saved UTC example' }).click();
  for (const label of ['Report date and time', 'Report time', 'Range start']) {
    const field = page.locator('.field').filter({ has: page.getByLabel(label, { exact: true }) });
    await field.locator('.ant-picker').hover();
    await field.getByRole('button', { name: 'Clear', exact: true }).click();
  }
  expect(await submit(page)).toEqual({ zone: 'UTC', dateTime: null, time: null, range: null });
  await expect(page.getByRole('status')).toContainText('3 matching reports');
  await enter(page, 'Report date and time', '2026-05-25 18:00:00');
  expect((await submit(page)).dateTime).toBe('2026-05-25T18:00:00.000Z');
  await expect(page.getByTestId('results')).toContainText('UTC evening report');
});

test.describe('UTC browser', () => {
  test.use({ timezoneId: 'UTC' });
  test('selected zone controls all three picker types independently of browser zone', async ({ page }) => {
    await page.getByLabel('Display time zone').selectOption('Asia/Kathmandu');
    await enter(page, 'Report date and time', '2026-05-25 18:00:00');
    await enter(page, 'Report time', '18:00:00');
    await enterRange(page, '2026-05-25 17:00:00', '2026-05-25 19:00:00');
    const payload = await submit(page);
    expect(payload.dateTime).toBe('2026-05-25T12:15:00.000Z');
    expect(payload.time).toBe('2026-05-25T12:15:00.000Z');
    expect(payload.range).toEqual(['2026-05-25T11:15:00.000Z', '2026-05-25T13:15:00.000Z']);
  });
});
