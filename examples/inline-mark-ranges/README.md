# Inline mark ranges

`MatchDecorator` can apply several marks to one match. Use its `decorate(add, from, to, match, view)` callback and call `add` for each range. The `decoration` option is the shortcut for one mark over the complete match.

For a document containing `testing *line*`, this example produces:

```html
<div class="cm-line">testing <span class="wa-marker">*</span><span class="wa-bold">line</span><span class="wa-marker">*</span></div>
```

The asterisks are already in the document. Marks decorate existing characters; they cannot prepend or append characters that are absent from the source. There are no widgets or replacement decorations here. The absence of `.cm-widgetBuffer` alone does not establish how another website was implemented.

## Run

Node.js 18 or later and npm are required. From this directory:

```sh
npm ci
npm run dev
```

Open the local URL printed by Vite. Type inside the marked text, remove or restore an asterisk, and use **Save text** to extract `editor.state.doc.toString()`. The visible current and saved values include the asterisks and every other document character.

```sh
npm run build
npm run preview
```

The build creates `dist/`. Development and preview servers bind to `127.0.0.1`.

## Use in an existing React editor

Copy [`src/inlineMarks.js`](src/inlineMarks.js) into your project and add it through the supported `extensions` prop:

```sh
npm install @uiw/react-codemirror@4.25.12 @codemirror/view@6.43.15 @codemirror/state@6.7.6
```

```jsx
import { useState } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { inlineMarks } from './inlineMarks.js';

const extensions = [inlineMarks];

export function Example() {
  const [value, setValue] = useState('testing *line*');
  return <CodeMirror value={value} extensions={extensions} onChange={setValue} />;
}
```

`inlineMarks` exports the plugin and its styles as an extension array. `createDeco(view)` initializes its decorations; `updateDeco(update, decorations)` keeps them aligned with edits and viewport changes. The callback adds the opening marker, inner text, and closing marker as three non-overlapping ranges inside each match.

The demo uses `basicSetup={false}` and installs history and editing keymaps explicitly so no overlapping selection/search/language highlights change the simple DOM above. The adoption snippet leaves your editor's existing setup enabled. Other extensions can split or nest marked DOM spans, so depend on document ranges and classes rather than an exact sibling structure in an editor with additional highlights.

## Syntax boundary

This is a small inline pattern, **not a Markdown parser**. It accepts nonempty text between isolated single `*` delimiters on the same line. Empty pairs, double-asterisk pairs, escaped opening delimiters and pairs spanning lines are excluded. Backslashes inside a pair are excluded. The source remains editable literal text when a pair no longer matches. Nested formatting, Markdown escapes, lists, code blocks, and complete emphasis rules need a language parser instead.

`MatchDecorator` operates on visible ranges with its documented bounded look-around for long or folded lines. This example tests normal lines and scrolling; it does not promise full highlighting of arbitrary very long, partially visible matches.

## Browser checks

```sh
npx playwright install chromium
npm test
```

The software-operated Chromium tests mount the actual React CodeMirror component. They check the three-span DOM and actual document; keyboard insertion, delimiter deletion/restoration, multiple matches/lines, selection across boundaries, undo/redo, scrolling, independent change-count observations, and exact saved text. They do not establish human testing or adoption by another application.

The single-decoration comparison is intentionally expected to fail the first assertion (one span instead of three):

```sh
npm run test:shortcut
```

Its nonzero exit is the expected negative-control result. It uses the same React consumer and actual editor, with only the mark extension changed. Test output stays in ignored `test-results/`.

## References

- [MatchDecorator reference](https://codemirror.net/docs/ref/#view.MatchDecorator)
- [CodeMirror decoration guide](https://codemirror.net/examples/decoration/)
- [React CodeMirror usage](https://github.com/uiwjs/react-codemirror#usage)
- [EditorView and state](https://codemirror.net/docs/ref/#view.EditorView)

Tested dependency versions are pinned in `package.json` and `package-lock.json`. MIT licensed; see [LICENSE](LICENSE).

## Optional coffee

The example is free. If it helps and you would like to buy me a coffee, contributions are entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
