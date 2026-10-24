# Keep long integer input exact

For a value such as `12345678901234567890`, use Maska's **string mask**, keep the Vue value as a string, and send that string to your server. Maska 3.2.2 documents a numeric-mode limit around JavaScript's safe-integer range. Its numeric mode changes the seventeenth digit in the sequence from [issue 280](https://github.com/beholdr/maska/issues/280).

This example uses existing reversed and repeated string tokens. It does not patch Maska's numeric formatter. It accepts **ASCII unsigned integer digits and optional grouping commas**. Signs, decimal points, currencies and locale-specific formatting are unsupported. Do not use this recipe for amounts or decimal arithmetic.

## Run

Use Node.js 20 or later:

```sh
npm ci
npm run dev
```

Open <http://127.0.0.1:4179>. Type `12345678901234567890`, then click **Submit string**. The input displays `12,345,678,901,234,567,890`; the raw value and the server's reply remain `12345678901234567890`. Edit the middle, paste a grouped value, clear the input and enter another value to continue.

The dependencies are pinned to Maska **3.2.2** and Vue **3.5.44**. No version was specified in the original question. The original CodePen configuration was not verified; this example covers the integer sequence described in the question, rather than any additional options in that Pen.

## Configuration

[integer-options.js](integer-options.js) contains the complete mask:

```js
export const integerOptions = {
  mask: '9,99#',
  reversed: true,
  tokens: { 9: { pattern: /[0-9]/, repeated: true } },
};
```

`#` uses Maska's default digit token. `9` is a custom repeated digit token; reversed mode groups the string from the right. Repetition allows the input to continue beyond twenty digits without a fixed-width mask discarding earlier digits. Leading zeros also remain part of the string.

Remove **all** `data-maska-number` and `data-maska-number-*` attributes, and remove any `number` option. Data attributes override directive options, so adding a string mask while leaving a numeric-mode attribute still activates the numeric formatter.

[main.js](main.js) uses the ordinary Vue Options API with `masked` and `raw` declared as string data properties:

```html
<input
  type="text"
  inputmode="numeric"
  required
  v-model="masked"
  v-maska:raw.unmasked="options"
>
```

The complete input also has small `beforeinput` and `paste` handlers. They reject signs, decimal points and other unsupported characters, leave the existing digits intact, and block submission until the next valid edit. A string mask by itself filters nonmatching characters; these handlers prevent an attempted `-12` or `12.34` from silently becoming an accepted positive integer. This is deliberately a narrow input example.

If integrating with `<script setup>`, follow Maska's [Vue binding guidance](https://beholdr.github.io/maska/v3/#/vue?id=bind-value), including exposing the bound raw variable with `defineExpose`. The runnable example here uses the Options API.

Keep the raw string throughout the request:

```js
body: JSON.stringify({ value: this.raw })
```

Avoid `v-model.number`, `Number`, `parseFloat`, unary `+`, or numeric coercion on the server. A JSON number cannot preserve this digit sequence through JavaScript numeric conversion. [server.mjs](server.mjs) demonstrates a local endpoint that accepts only a quoted digit string and echoes it unchanged. Adapt that handoff to your own API and storage rules; this example does not establish how an existing backend stores values.

## Checks

```sh
npx playwright install chromium
npm test
```

The software-operated Chromium sequence checks every original keystroke, continuation to thirty digits, middle insertion and caret position, Backspace/Delete, real clipboard paste with and without commas, leading zeros, clearing and re-entry, and three actual HTTP submissions. It also checks required-empty behavior, rejected sign/decimal input and continued editing afterward. Results and the final page are written to `test-results/`. These checks cover this local consumer, not the questioner's application or mobile keyboards.

Official references: [options and number-mode limit](https://beholdr.github.io/maska/v3/#/options), [repeated tokens](https://beholdr.github.io/maska/v3/#/tokens), [Vue integration](https://beholdr.github.io/maska/v3/#/vue), and [supported input types](https://beholdr.github.io/maska/v3/#/issues).

## Optional coffee

If this example saved you some time, a coffee is welcome. It is entirely optional; the example stays free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
