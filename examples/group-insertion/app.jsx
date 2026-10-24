import React, { Fragment, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { DragDropContext, Draggable, Droppable } from '@hello-pangea/dnd';
import { applyDrop, initialState } from './model.mjs';
import './style.css';

function App() {
  const [state, setState] = useState(initialState);
  const [draggingId, setDraggingId] = useState(null);
  const [message, setMessage] = useState('Ready.');
  const activeItem = state.groups.flatMap((group) => group.items).find((item) => item.id === draggingId);
  const newGroupDisabled = activeItem?.canStartGroup === false;

  function onDragStart(start) {
    setDraggingId(start.draggableId);
    const item = state.groups.flatMap((group) => group.items).find((entry) => entry.id === start.draggableId);
    setMessage(`Picked up ${item.label}. New groups ${item.canStartGroup ? 'allowed' : 'disabled'}.`);
  }

  function onDragEnd(result) {
    setState((current) => applyDrop(current, result));
    setDraggingId(null);
    setMessage(result.reason === 'CANCEL' || !result.destination
      ? 'No move made.'
      : 'Move finished.');
  }

  function gap(position) {
    return <Droppable droppableId={`gap:${position}`} type="ITEM" isDropDisabled={newGroupDisabled}>
      {(provided, snapshot) => <section
        ref={provided.innerRef}
        {...provided.droppableProps}
        className={`gap ${snapshot.isDraggingOver ? 'over' : ''}`}
        data-gap={position}
        aria-label={`New group at position ${position + 1}`}
        aria-disabled={newGroupDisabled}
      >
        <span>New<br />group</span>
        {provided.placeholder}
      </section>}
    </Droppable>;
  }

  return <main>
    <h1>Create groups by dropping between them</h1>
    <p>Drag an item into a “New group” strip, or into another group. With a handle focused,
      press Space to pick up, use arrow keys to move, and Space to drop. Escape cancels.</p>
    <p>Example rule: “Attached note” can move between existing groups, but cannot start a new group.</p>
    <p role="status" aria-live="polite">{message}</p>
    <DragDropContext onDragStart={onDragStart} onDragEnd={onDragEnd}>
      <div className="board" aria-label="Grouped items">
        {state.groups.map((group, groupIndex) => <Fragment key={group.id}>
          {gap(groupIndex)}
          <Droppable droppableId={group.id} type="ITEM">
            {(provided, snapshot) => <section
              ref={provided.innerRef}
              {...provided.droppableProps}
              className={`group ${snapshot.isDraggingOver ? 'over' : ''}`}
              data-group-id={group.id}
              aria-label={group.title}
            >
              <h2>{group.title}</h2>
              {group.items.map((item, index) => <Draggable key={item.id} draggableId={item.id} index={index}>
                {(dragProvided) => <div
                  ref={dragProvided.innerRef}
                  {...dragProvided.draggableProps}
                  {...dragProvided.dragHandleProps}
                  className="card"
                  style={dragProvided.draggableProps.style}
                  data-item-id={item.id}
                >{item.label}</div>}
              </Draggable>)}
              {provided.placeholder}
            </section>}
          </Droppable>
        </Fragment>)}
        {gap(state.groups.length)}
      </div>
    </DragDropContext>
    <p>Named groups stay in place when emptied. Changes last until this page is reloaded.</p>
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
