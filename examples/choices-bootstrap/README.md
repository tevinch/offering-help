# Keep Bootstrap form styles with Choices

Load Bootstrap and the Choices **core stylesheet**. Omit Choices' optional `base.css` / `base.min.css`: it styles the whole page, including `.form-control`, labels and headings. Moving it before Bootstrap can still leave declarations such as `margin-bottom` on ordinary fields.

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/choices.js@11.2.4/public/assets/styles/choices.min.css">
<!-- Put the script after your select markup. -->
<script src="https://cdn.jsdelivr.net/npm/choices.js@11.2.4/public/assets/scripts/choices.min.js"></script>
```

Keep Bootstrap's `form-control` on ordinary inputs and textareas, and `form-select` on native selects. Initialize Choices only on the selects you want to enhance. The [complete example](index.html) has both a searchable single select and a multiple select with remove buttons. It uses no CSS overrides or library patch.

## Run

From the repository root:

```sh
python3 -m http.server 8000
```

Open [the example](http://localhost:8000/examples/choices-bootstrap/). Its pinned CDN assets require an internet connection.

1. Open Country, search for Japan, select it, then change it to Canada.
2. Search for topics, add several, and remove one. The selection summary updates with the underlying selects.
3. Edit any ordinary field and click **Show form data**. The displayed result reads the native form's `FormData`; multiple topics use `getAll('topics')`. No data is sent to a server.

## Checked scope

Checked with Bootstrap **5.3.8** and Choices **11.2.4** in Chromium at desktop and narrow widths. Ordinary input, select and textarea styles were compared with a Bootstrap-only page. Adding the optional base stylesheet changed those styles, including with base loaded first; omitting it restored the comparison. Both real Choices instances were exercised through search, selection, changes, removal and form submission, while the ordinary field values remained intact.

These are scripted browser checks of this example. The original application's versions and styles are unknown; this does not establish compatibility with every Bootstrap theme or Choices version.

References: [Choices installation instructions](https://github.com/Choices-js/Choices/tree/v11.2.4#installation), [optional base stylesheet](https://github.com/Choices-js/Choices/blob/v11.2.4/public/assets/styles/base.css), [Bootstrap form controls](https://getbootstrap.com/docs/5.3/forms/form-control/), [original styling question](https://github.com/Choices-js/Choices/issues/1448).

## Optional coffee

The example is free. If it helps, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
