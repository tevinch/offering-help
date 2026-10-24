# Insert an item as a new group

Drag an item between groups to create a new group, while keeping ordinary moves and keyboard dragging available. This example uses the public API of `@hello-pangea/dnd` 18.0.1 with React 19.3.1.

## Run

Use Node 20 or later:

```sh
npm ci --ignore-scripts
npm run build
npm start
```

Open `http://127.0.0.1:4173`. Drag Alpha into a dashed strip. The item becomes the only item in a new group at that position. Move another item into that new group to continue organizing.

For keyboard dragging, focus an item with Tab, press Space, move with the arrow keys, then press Space again. Up/Down moves within a group; Left/Right moves between the columns and insertion strips. Escape cancels.

## Keep the targets at the same level

The root is a normal container. Each group and each insertion strip is a sibling `Droppable` with the same `type="ITEM"`:

```text
plain container
  gap:0
  group-a
  gap:1
  group-b
  gap:2
```

The gap targets already exist when the drag starts. Their dimensions stay fixed during dragging. When a drop finishes on `gap:1`, `applyDrop` removes the item from its original list and inserts a new group at position 1 in one state update. It preserves the order of the other groups and items, including named groups that become empty.

This changes the target structure; it does not enable parent-to-child or child-to-parent drops. The library documents independent nested lists but excludes parent-to-child transfers. See the [supported interactions](https://github.com/hello-pangea/dnd#currently-supported-feature-set-).

## A condition becomes a boolean prop

`isDropDisabled` does not take a callback. Store the active item from `onDragStart`, then calculate the boolean for each target:

```jsx
const [state, setState] = useState(initialState);
const [draggingId, setDraggingId] = useState(null);
const activeItem = state.groups.flatMap(group => group.items)
  .find(item => item.id === draggingId);

<DragDropContext
  onDragStart={start => setDraggingId(start.draggableId)}
  onDragEnd={result => {
    setState(current => applyDrop(current, result));
    setDraggingId(null);
  }}
>
  {/* Each insertion strip: */}
  <Droppable
    droppableId="gap:1"
    type="ITEM"
    isDropDisabled={activeItem?.canStartGroup === false}
  >
    {/* render the target, ref, props and placeholder */}
  </Droppable>
</DragDropContext>
```

The complete wiring is in [app.jsx](./app.jsx). `canStartGroup` is just a demonstration rule: Attached note cannot start a group, but can move into an existing group. Replace it with your own policy. The state transition in [model.mjs](./model.mjs) also checks the rule before changing data.

Use `onDragStart` for this state update. The [responders guide](https://github.com/hello-pangea/dnd/blob/v18.0.1/docs/guides/responders.md) explains the lifecycle and synchronous `onDragEnd` update. Keep each draggable's ID stable, its index consistent with its list, and attach the supplied ref, handle props and placeholder.

## Verify

```sh
npx playwright install chromium
npm test
```

The tests cover insertion before, between and after existing groups; moves within and between groups; repeated operations after creation; cancellation; preservation of every item; and the example restriction. Browser checks use real pointer and keyboard input. Three isolated negative builds detect missing group creation, missing drag-start state, and a missing `isDropDisabled` prop even when the target still looks disabled. Results and a screenshot are written to `test-results/`.

This is a small local consumer example. It does not cover whole-group reordering, arbitrary nested transfers, touch input, remote persistence or another application's styling. Reloading resets the board. The original requester's application has not been tested, and their adoption has not been confirmed.

## Optional coffee

The example is free. If it saves you some time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
