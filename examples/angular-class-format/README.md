# Keep Prettier and ESLint class wrapping in Angular

For a static HTML `class` attribute, let ESLint own its whitespace and class order. Put Prettier’s attribute-specific ignore comment immediately before that element:

```html
<!-- prettier-ignore-attribute class -->
<div
  class="
    text-black underline
    hover:font-bold hover:text-blue-700
    focus:font-bold focus:text-red-700
  "
  (click)="select($event)"
>
  <span>{{ title }}</span>
</div>
```

Prettier still formats the other attributes, Angular expressions and child markup. The comment applies to the following element’s `class` attribute; it does not exclude the file or disable the ESLint rule. Use it on the class-heavy elements where the two tools otherwise disagree.

## Run the example

Use Node.js 24 or later, then from this directory:

```sh
npm ci --ignore-scripts
npm test
npm run format
npm run fix
npm run format
npm run lint
```

`sample.component.html` is the finished template. `eslint.config.mjs` uses the actual Angular template parser and enables both `enforce-consistent-line-wrapping` and `enforce-consistent-class-order`. `styles.css` supplies the Tailwind entry point. Copy those rule settings into your existing Angular ESLint configuration rather than replacing your other rules. Keep Prettier enabled for Angular HTML in your editor.

The first formatting pass normalizes the surrounding markup; ESLint then wraps and orders the class string. Further Prettier passes preserve that class layout. This avoids depending on an editor’s choice of which fixer runs last. If you substantially reindent an element, run both tools again to establish its new indentation.

## Checked scope

Pinned versions: Prettier 3.9.10, ESLint 10.13.0, better-tailwindcss 4.9.1, Angular template parser 22.6.0 and Tailwind CSS 4.3.3. The supplied check first proves that the wrapping rule detects a collapsed class string, then exercises real formatting/fixing and three more format/lint cycles. It verifies the class tokens, Angular binding/click expression and child text. Removing the ignore comment reproduces the formatting conflict.

These are command-line checks of an external Angular template, not a human editor-save or original-project verification. No Prettier plugins are installed here. Bound `[class]`, `ngClass`, inline TypeScript templates and additional formatter plugins need their own checks.

See [Prettier’s HTML attribute ignore syntax](https://prettier.io/docs/ignore#html), the plugin’s [Angular setup](https://github.com/schoero/eslint-plugin-better-tailwindcss/blob/v4.9.1/docs/parsers/angular.md) and [wrapping options](https://github.com/schoero/eslint-plugin-better-tailwindcss/blob/v4.9.1/docs/rules/enforce-consistent-line-wrapping.md). The official `strictness: "loose"` option can help width-related edge cases; it does not give the static class attribute a single formatter owner.

## Optional coffee

The example is free. If it helps, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
