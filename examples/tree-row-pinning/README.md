# Expand a tree from its pinned parent row

This example keeps a self-referential Tree Data parent pinned at the top and gives that pinned copy a button to expand or collapse the original tree. Children stay in the normal grid body. The original parent remains there too, as it normally does with manual row pinning.

AG Grid's built-in group renderer hides its expander on pinned rows in both 35.2.1 and 36.2.0. Switching to `enableRowPinning` alone does not change that. The button here is a custom cell renderer using public APIs; it does not change AG Grid's source or restore a built-in pinned-row expander.

Tree Data requires **AG Grid Enterprise**. The example sets no licence key and does not change the library's watermark or licence checks. AG Grid permits local evaluation without a key; its console notice is expected. The library may hide its watermark on localhost. Production use requires an appropriate AG Grid licence; this example does not provide one. The MIT licence here covers this example's code, not AG Grid Enterprise.

## Run

Use Node.js 20 or later:

```sh
npm ci
npm run dev
```

Open <http://127.0.0.1:4178>. Expand **Planning** in the top pinned row, then **Design** in the body. Sort **Effort**, select **Research**, collapse and reopen Planning, then change the selection to **Build**. The pinned button also follows expansion changes made through the ordinary body row. Enter and Space activate the focused button.

Dependencies are pinned to the question's 35.2.1 version. The same source was also checked against 36.2.0; an upgrade is not required for this approach.

## How it works

Keep the full self-referential data in `rowData` and provide stable IDs:

```js
treeData: true,
treeDataParentIdField: 'parentId',
getRowId: params => params.data.id,
enableRowPinning: true,
isRowPinned: node => node.id === 'planning' ? 'top' : null,
```

`isRowPinnable` controls whether a row may be pinned. `isRowPinned` chooses its initial pinned position. Do not also provide `pinnedTopRowData`: that supplies independent pinned rows, whose grouping, sorting and selection are not connected to the original tree.

Choose the custom renderer for the pinned copy and explicitly keep the built-in group renderer for body rows:

```js
cellRendererSelector: params => params.node.rowPinned
  ? {
      component: PinnedTreeToggle,
      params: { suppressMouseEventHandling: () => true },
    }
  : { component: 'agGroupCellRenderer' },
```

The button looks up the original row by its stable data ID, then changes that row's expansion:

```js
const node = params.api.getRowNode(params.data.id);
if (node) params.api.setRowNodeExpanded(node, !node.expanded);
```

Use the original node from `getRowNode`, rather than expanding `params.node`, which represents the pinned copy. `rowGroupOpened` and `modelUpdated` listeners keep the button's label and `aria-expanded` in sync. The renderer removes its listeners when destroyed. See [pinned-tree-toggle.js](pinned-tree-toggle.js) and [main.js](main.js) for the complete implementation.

The sample pins one known parent. Adapt its ID and the `name`/`id` field accesses to your data. Keep valid, unique string IDs and valid parent references. This is a client-side self-referential Tree Data example; it does not implement a subtree inside the pinned area or a server-side loading strategy. No source from the questioner's application was supplied, so that application has not been tested.

## Checks

```sh
npx playwright install chromium
npm test
```

The software-operated Chromium checks cover real pinned-button clicks, nested expansion, repeated collapse/reopen, ordinary-row changes updating the pinned button, sibling sorting, selection retained across collapse, continued selection, Enter/Space, unchanged data and parent relationships, and actual event execution. The full sequence passed with 35.2.1 and 36.2.0. Results and the final page are written to `test-results/`.

Official references: [row pinning](https://www.ag-grid.com/javascript-data-grid/row-pinning/), [self-referential Tree Data](https://www.ag-grid.com/javascript-data-grid/tree-data-self-referential/), [expansion API](https://www.ag-grid.com/javascript-data-grid/tree-data-opening-groups/), [custom cell renderers](https://www.ag-grid.com/javascript-data-grid/component-cell-renderer/), and [Enterprise evaluation and licensing](https://www.ag-grid.com/javascript-data-grid/community-vs-enterprise/).

## Optional coffee

If this example saved you some time, a coffee is welcome. It is entirely optional; the example stays free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
