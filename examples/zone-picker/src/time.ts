import { DateTime, IANAZone } from 'luxon';

export type RepeatPolicy = 'earlier' | 'later';
export const WALL_FORMAT = 'yyyy-MM-dd HH:mm:ss';

export function validZone(zone: string): boolean {
  return zone === 'UTC' || IANAZone.isValidZone(zone);
}

export function parseWall(text: string, zone: string, policy: RepeatPolicy): DateTime {
  if (!validZone(zone) || !/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(text)) {
    throw new Error('Enter a valid date and time as YYYY-MM-DD HH:mm:ss.');
  }
  const parsed = DateTime.fromFormat(text, WALL_FORMAT, { zone, locale: 'en' });
  if (!parsed.isValid) throw new Error('Invalid date or time.');
  if (parsed.toFormat(WALL_FORMAT) !== text) {
    throw new Error(`${text} does not exist in ${zone}. Choose a time outside the clock change.`);
  }
  const choices = parsed.getPossibleOffsets().sort((a, b) => a.toMillis() - b.toMillis());
  return policy === 'earlier' ? choices[0] : choices[choices.length - 1];
}
