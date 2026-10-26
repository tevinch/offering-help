# Calendar day markers

Show colored dots on chosen Cally dates without replacing its selection or navigation. This standalone example uses **Cally 0.9.2** and **daisyUI 5.7.50**, pinned in `index.html`. No build step is needed; the page loads those packages from jsDelivr.

Serve this directory with `python3 -m http.server 8000`, then open [the example](http://localhost:8000). Select a marked date, select another date, navigate between months, or switch between the light and dark themes.

## Add the parts on the parent

Assign `getDayParts` to `<calendar-date>`, after its custom element is defined. It returns space-separated part names for each day button:

```js
await customElements.whenDefined("calendar-date");
const calendar = document.querySelector("calendar-date");
const dates = new Map([
  ["2026-10-07", "event-primary"],
  ["2026-10-21", "event-warning"],
]);

calendar.getDayParts = (date) => {
  const colorPart = dates.get(date.toISOString().slice(0, 10));
  return colorPart ? `has-event ${colorPart}` : "";
};
```

Cally passes UTC dates to this callback. Use the full UTC date key so a marker cannot shift to the previous day in a negative UTC offset or repeat on the same day number in another month. Update the sample dates and the nearby event list together. To replace the map after rendering, assign a new callback so Cally renders the new parts.

## Style the parts on the month

Use ordinary CSS on `<calendar-month>` rather than applying the whole `indicator-item` rule, which includes selector structure that cannot be composed through `::part()`:

```css
calendar-month::part(day) {
  position: relative;
  height: 2.5rem;
  padding-bottom: .4rem;
}
calendar-month::part(event-primary) {
  --day-marker-color: var(--color-primary);
}
calendar-month::part(event-warning) {
  --day-marker-color: var(--color-warning);
}
calendar-month::part(has-event)::after {
  content: "";
  position: absolute;
  width: .4375rem;
  height: .4375rem;
  border-radius: 50%;
  inset-inline-start: 50%;
  bottom: .2rem;
  transform: translateX(-50%);
  background: var(--day-marker-color);
  pointer-events: none;
}
calendar-month::part(has-event today)::after {
  background: var(--color-primary-content);
}
/* Keep selected last, including when a date is both today and selected. */
calendar-month::part(has-event selected)::after {
  background: var(--color-base-100);
}
```

The primary and warning colors follow the active daisyUI theme. Native today uses `primary-content` against daisyUI's primary fill so a primary marker stays visible. The selected day uses a contrasting neutral dot against the `base-content` selection fill; keep that rule last so it also wins when today is selected. The empty pseudo-element remains decorative and lets clicks reach the original button. Keep a text event list or another accessible source of event details: the dot does not add an event description to Cally's date label. This technique adds visual marks, not arbitrary badge HTML.

The example leaves Cally's native date values, change events, labels and keyboard handling in place. Software-operated Chromium 156.0.8078.4 checks covered marked/unmarked/repeated selection, clicking a dot, arrow-key selection with Enter, next/previous month navigation, light/dark themes, a 360px viewport, and the America/Los_Angeles and Pacific/Kiritimati timezones. A primary event on native today was also checked unselected and selected in both themes. Other browser engines and assistive technologies have not been validated.

References: [Cally date API](https://wicky.nillia.ms/cally/components/calendar-date/), [Cally theming](https://wicky.nillia.ms/cally/guides/theming/), [daisyUI calendar](https://daisyui.com/components/calendar/).

## Optional coffee

This example is free to use. If it saved you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
