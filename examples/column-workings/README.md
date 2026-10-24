# Column workings

A small keyboard writing pad for whole-number column addition, subtraction, multiplication and long division. Type your own steps, add small carry or borrowing numbers, and cross out a digit while keeping it visible. No TeX is needed.

## Open it

Download this folder and open `index.html` in a current browser. Keep `main.js` and `styles.css` beside it. No installation, account, server or internet connection is needed to use the page.

Choose an operation, enter two numbers and select **Make page**. The starting numbers are fixed in place; all working and answer squares start blank.

## Write the steps

- Click a square and type a digit. Typing moves right. Arrow keys move between squares, and Tab moves to the next square. Backspace clears the selected digit; typing another digit replaces it.
- To write a carry or replacement number, select the square beneath it and choose **Small number**. Type one or two digits, including `10`. Escape returns to the main square. Select the small number and press Backspace to clear it.
- **Cross out** toggles a line through the selected digit. It keeps the original digit visible. Use it together with a small replacement number for borrowing.
- **Underline row** toggles a rule below the selected row. **Add working row** appends a blank row without changing earlier work.
- **Print** prints the current page, including your notes, rules and crossed-out digits. Your browser may also offer Save as PDF.

For example, write `58 + 67` with a carried `1` and answer `125`; or `1000 − 387` with crossed-out original digits, replacement notes `0`, `9`, `9`, `10` and answer `613`.

For `23 × 14`, write the partial products `92` and `230`, add a rule, then write `322`. For `156 ÷ 12`, enter quotient `13` above the dividend, subtract `12` from `15`, bring down the `6` to write `36`, subtract `36`, then write remainder `0`. Place rules under the subtraction rows. The long-division bracket is already drawn.

## Bounds

Each starting number may have up to eight digits, including zero. Division needs a nonzero second number. Subtraction requires the first number to be at least as large as the second. Invalid new numbers leave the existing page intact.

The page provides aligned squares and a long-division bracket. It does not calculate answers, supply intermediate steps, check mathematics or enforce a teaching method. It accepts digits in working squares, with a separate small-number field; arbitrary signs, decimals, fractions and freehand annotations are outside its scope. Wide pages scroll horizontally on screen and shrink to the print width.

There is no autosave. Reloading or leaving the page loses the current work. Making a new page asks before clearing work you have entered. Print it first if you need a copy.

The sample has software-operated Chromium checks for complete written addition, borrowing across zeros, multiplication partial products, long division, keyboard correction, row growth and print output. It has not been tested with children or assessed for individual accessibility or teaching needs. It is an independent writing pad, not a KaTeX extension.

## Run the checks

Using Node.js 20 or later:

```sh
npm ci
npx playwright install chromium
npm test
```

The checks use real browser controls and include negative cases that omit a carry, borrowing annotation, partial product or division subtraction. Screenshots and recorded cell values go into `test-results/`.

To also generate five print PDFs:

```sh
WORKINGS_PRINT=1 npm test
```

## License

MIT; see [LICENSE](LICENSE).

## Optional coffee

The pad is free to use. If it helps and you would like to buy me a coffee, a contribution is entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
