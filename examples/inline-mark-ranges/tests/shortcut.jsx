import React from 'react';
import { createRoot } from 'react-dom/client';
import { Decoration, MatchDecorator, ViewPlugin } from '@codemirror/view';
import { EditorDemo } from '../src/EditorDemo.jsx';

// Deliberately the single-decoration shortcut from the original question.
const matcher = new MatchDecorator({
  regexp: /(?<![\\*])\*([^*\\\n]+)\*(?!\*)/g,
  decoration: Decoration.mark({ class: 'wa-bold' }),
});
const shortcut = ViewPlugin.fromClass(class {
  constructor(view) { this.decorations = matcher.createDeco(view); }
  update(update) { this.decorations = matcher.updateDeco(update, this.decorations); }
}, { decorations: value => value.decorations });
createRoot(document.getElementById('root')).render(<EditorDemo markExtension={shortcut} />);
