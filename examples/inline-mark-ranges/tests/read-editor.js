import { EditorView } from '@codemirror/view';
export function readEditor(element) {
  const view = EditorView.findFromDOM(element);
  if (!view) throw new Error('No real CodeMirror view found');
  return { doc: view.state.doc.toString(), from: view.state.selection.main.from,
    to: view.state.selection.main.to };
}
