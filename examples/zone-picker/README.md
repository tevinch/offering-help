# Report times

A runnable Ant Design example for querying UTC report data while the user chooses an IANA time zone. DatePicker, TimePicker and RangePicker share that zone, including typed input, calendar selection, today highlighting and clear/reselect.

For example, with a browser in Asia/Shanghai and the selected zone set to UTC, entering `2026-05-25 18:00:00` sends `2026-05-25T18:00:00.000Z`. It must not become `10:00Z` just because the browser is eight hours ahead.

## Run

Requires Node.js 22 or newer and a modern browser with `Intl.supportedValuesOf`.

```sh
npm ci --ignore-scripts
npm run dev
```

Open http://127.0.0.1:4173. The server listens only on your computer. It builds the application when it starts; restart it after editing source files.

1. Leave **Display time zone** set to **UTC**.
2. Enter `2026-05-25 18:00:00` in **Report date and time**, then press Enter or confirm with OK.
3. Click **Query reports**. The page shows **UTC evening report** and the JSON actually submitted to the local sample endpoint.
4. Clear the date, select it again, or load the saved UTC example. Switch zones and reload: committed instants remain unchanged, while their displayed wall times change.

For a range, enter both endpoints and confirm the selection. Finish the current picker edit before switching zones. **Clear date/time/range** also clears an unfinished or invalid edit for that control.

The endpoint contains three synthetic reports. Date and time filters match exact instants; a range includes both endpoints. Empty controls omit their filter. Replace `scripts/server.mjs`'s sample query with your own service contract when integrating.

## Why this works

The example uses Ant Design's [documented custom date-library integration](https://ant.design/docs/react/use-custom-date-library/) and the existing Luxon adapter:

```tsx
import { DatePicker } from 'antd';
import luxonGenerateConfig from '@rc-component/picker/generate/luxon';
import { DateTime, Settings } from 'luxon';

// One shared preference in this browser application.
Settings.defaultZone = 'UTC';
const Picker = DatePicker.generatePicker<DateTime>(luxonGenerateConfig);
```

The complete implementation is in `src/App.tsx`. It stores canonical UTC ISO strings and creates displayed values with `DateTime.fromISO(utcValue, { zone })`. A new wall-clock selection is interpreted in the selected zone, checked, and serialized with `toUTC().toISO()`. Changing the display zone does not reinterpret an existing instant.

With Day.js, [`tz.setDefault` affects `dayjs.tz`, not plain `dayjs(value)`](https://day.js.org/docs/en/plugin/timezone). Current picker releases already consult the default zone for `getNow()`; this example does not patch an old today-highlighting defect. It uses the official Luxon integration to keep typed parsing and newly created values in the same selected zone.

The pinned versions are Ant Design 6.6.7, `@rc-component/picker` 1.12.2, Luxon 3.7.2 and React 19.2.8. Switching a larger application from Day.js to Luxon changes its value types. Ant Design also documents Luxon's ISO-week and locale-formatting differences; check those before replacing existing controls.

## Dates, clock changes and persistence

- A time alone cannot identify an instant. **Report time** uses the visible **Time reference date** in the selected zone. Changing this reference date intentionally creates a new instant; changing only the display zone preserves an existing instant and updates its displayed reference date.
- A clock jump can skip a wall time. Such **typed input** is rejected and querying stays disabled. The error includes the original rejected text; the picker may display its normalized value, but that invalid draft is not saved or submitted. Retype a valid value or clear that control before making another selection. OK alone does not accept normalization.
- A calendar or clock-panel selection may already move a skipped time forward before the application receives it. For example, choosing hour `02` from `2026-03-08 01:30:00` in New York displays `03:30:00`; confirming sends `07:30Z`. Check the displayed value before OK. This example does not reject the original skipped panel choice; it commits the valid time shown by the picker.
- A backward clock change can repeat a wall time. **Repeated wall times** explicitly selects the earlier or later instant for new entries. The choice does not rewrite already committed values. Clear and re-enter a repeated time to choose its other occurrence.
- `src/time.ts` checks raw typed text and confirmed picker values by round-tripping their fields, and uses Luxon's possible offsets for repeated times. Valid typed edits can be followed by calendar, clock or Now selections; the latest confirmed selection is submitted. Zone rules come from the browser's time-zone database.
- Committed values, the zone and the reference date are stored in localStorage. Draft edits are not persisted. Invalid saved preferences are ignored; unavailable storage does not prevent current-session queries.

This is a browser SPA with one shared zone. `Settings.defaultZone` is process-global: **do not set it per user request in a multiuser SSR process**. It is not a new `ConfigProvider.timeZone` feature. No dependencies or date-library methods are patched.

## Verify

```sh
npm run typecheck
npm run build
npx playwright install chromium
npm test
```

To run against an already installed Google Chrome instead:

```sh
PLAYWRIGHT_CHANNEL=chrome npm test
```

The browser tests exercise actual picker input and selection, observe the outgoing HTTP JSON independently, and check visible query results. They cover browser/selected-zone differences, a day boundary, repeated clear/reselect, UTC reload, fractional offsets and daylight-saving transitions. Focused tests also check invalid dates and both occurrences of a repeated wall time.

MIT licensed; see `LICENSE`.

## Optional coffee

This example is free. If it saved you time and you would like to buy me a coffee, a contribution is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
