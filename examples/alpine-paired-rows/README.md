# Paired table rows with Alpine

To repeat a heading row and a detail row with `x-for`, put both rows inside one `<tbody>` per record. Place the `<template>` directly inside the `<table>`, alongside the static header and footer. The repeated `<tbody>` is the single root that Alpine requires.

```html
<table x-data="{ records: [{ id: 'note-1', title: 'First record' }] }">
  <thead><tr><th>Record</th></tr></thead>
  <template x-for="record in records" :key="record.id">
    <tbody x-data="{ open: false }">
      <tr>
        <th scope="row">
          <button type="button"
            :id="`${record.id}-toggle`"
            :aria-controls="`${record.id}-detail`"
            :aria-expanded="open"
            @click="open = !open"
            x-text="record.title"></button>
        </th>
      </tr>
      <tr x-show="open"
        :id="`${record.id}-detail`"
        :aria-labelledby="`${record.id}-toggle`">
        <td>Details for this record</td>
      </tr>
    </tbody>
  </template>
  <tfoot><tr><td>Table end</td></tr></tfoot>
</table>
```

Remove the outer `<tbody>` from a structure such as `<table><tbody><template ...>` when making this change. Do not nest a `<tbody>` inside another `<tbody>`, wrap table rows in a `<div>`, or put both `<tr>` elements directly in the template.

Alpine's [x-for documentation](https://alpinejs.dev/directives/for) requires one root element and recommends stable keys for reordering. The [HTML table content model](https://html.spec.whatwg.org/multipage/tables.html#the-table-element) permits multiple sibling `<tbody>` elements. This creates one row group per record: adjust any CSS that assumes a single body, and do not use a `rowspan` across these groups.

## Run the complete example

From this directory, run:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Open [localhost:8000](http://localhost:8000). The page loads Alpine **3.17.4** from jsDelivr, so it needs an internet connection. It contains the complete markup, styles and data setup; no package installation or build step is needed.

Open a record with its button or the keyboard, edit the notes, reverse the order twice, then add and remove records. Both rows, the open state and edited text stay with the record. Removing every record leaves the header and footer in place; adding a new record lets you continue.

The example uses **Alpine to control expansion**. It replaces an external `data-accordion` controller rather than integrating with one. It does not initialize or validate Flowbite or another third-party accordion library. If your existing controller owns expansion, adapt and test its initialization and settings separately.

The sample data uses stable unique IDs for keys and related control/row IDs. Keep that uniqueness when replacing the data with your own list or `$store` data. Detail text uses `x-text` and note fields use `x-model`.

## Checked behavior

The original two-root template was checked with Alpine 3.17.4: only the first row rendered per record, with a single-root warning. The complete example was checked in a software-operated Chromium browser at desktop and narrow viewport widths, including keyboard toggles, repeated reordering, editing, addition, removal and empty-list recovery. These checks cover this standalone example; the original application, third-party accordion controller and screen-reader behavior were not tested.

## Optional coffee

If this saved you time, a coffee is welcome and entirely optional. The example is free to use.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
