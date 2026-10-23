import React, { useCallback, useMemo, useRef, useState } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { history, historyKeymap, defaultKeymap } from '@codemirror/commands';
import { keymap } from '@codemirror/view';
import './style.css';

const editing = [history(), keymap.of([...defaultKeymap, ...historyKeymap])];

export function EditorDemo({ markExtension }) {
  const [value, setValue] = useState('testing *line*');
  const [changeCount, setChangeCount] = useState(0);
  const [saved, setSaved] = useState(null);
  const view = useRef(null);
  const extensions = useMemo(() => [...editing, markExtension], [markExtension]);
  const onChange = useCallback(next => {
    setValue(next);
    setChangeCount(count => count + 1);
  }, []);
  return <main>
    <h1>Inline mark ranges</h1>
    <p>Edit the asterisks and text. Each matched pair has two marker spans and one bold span.</p>
    <CodeMirror value={value} basicSetup={false} extensions={extensions}
      aria-label="Editable text" height="220px" onChange={onChange}
      onCreateEditor={editor => { view.current = editor; }} />
    <p>Changes: <output aria-label="Change count">{changeCount}</output></p>
    <button type="button" onClick={() => setSaved(view.current.state.doc.toString())}>Save text</button>
    <h2>Current text</h2><pre aria-label="Current text">{value}</pre>
    <h2>Saved text</h2><pre aria-label="Saved text">{saved === null ? 'Nothing saved yet.' : saved}</pre>
  </main>;
}
