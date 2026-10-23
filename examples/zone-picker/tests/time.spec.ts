import { expect, test } from '@playwright/test';
import { parseWall } from '../src/time';

test('typed UTC report boundary denotes the selected wall time, not the host time', () => {
  expect(parseWall('2026-05-25 18:00:00', 'UTC', 'earlier').toUTC().toISO()).toBe('2026-05-25T18:00:00.000Z');
  expect(parseWall('2026-05-25 18:00:00', 'Asia/Kathmandu', 'earlier').toUTC().toISO()).toBe('2026-05-25T12:15:00.000Z');
});

test('nonexistent wall times and invalid dates are rejected without normalization', () => {
  expect(() => parseWall('2026-03-08 02:30:00', 'America/New_York', 'earlier')).toThrow();
  expect(() => parseWall('2026-02-30 18:00:00', 'UTC', 'earlier')).toThrow();
});

test('repeated time explicitly selects either instant', () => {
  expect(parseWall('2026-11-01 01:30:00', 'America/New_York', 'earlier').toUTC().toISO()).toBe('2026-11-01T05:30:00.000Z');
  expect(parseWall('2026-11-01 01:30:00', 'America/New_York', 'later').toUTC().toISO()).toBe('2026-11-01T06:30:00.000Z');
});
