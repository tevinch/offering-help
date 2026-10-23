import React from 'react';
import { createRoot } from 'react-dom/client';
import { EditorDemo } from './EditorDemo.jsx';
import { inlineMarks } from './inlineMarks.js';

createRoot(document.getElementById('root')).render(<EditorDemo markExtension={inlineMarks} />);
