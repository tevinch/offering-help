import { Decoration, EditorView, MatchDecorator, ViewPlugin } from '@codemirror/view';

const marker = Decoration.mark({ class: 'wa-marker' });
const bold = Decoration.mark({ class: 'wa-bold' });

// Bounded inline syntax only: isolated single asterisks, one line, no backslashes.
const matcher = new MatchDecorator({
  regexp: /(?<![\\*])\*([^*\\\n]+)\*(?!\*)/g,
  decorate(add, from, to) {
    add(from, from + 1, marker);
    add(from + 1, to - 1, bold);
    add(to - 1, to, marker);
  },
});

const marks = ViewPlugin.fromClass(class {
  constructor(view) {
    this.decorations = matcher.createDeco(view);
  }
  update(update) {
    this.decorations = matcher.updateDeco(update, this.decorations);
  }
}, { decorations: value => value.decorations });

export const inlineMarks = [marks, EditorView.baseTheme({
  '.wa-marker': { color: '#68778a' },
  '.wa-bold': { fontWeight: '700' },
})];
