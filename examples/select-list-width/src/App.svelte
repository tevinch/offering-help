<script>
  import Select from 'svelte-select';

  const items = [
    { value: 'maple', label: 'Maple — planning notes' },
    { value: 'cedar', label: 'Cedar — reference material' },
    { value: 'meadow', label: 'Meadow — a longer option label that can use the wider list' },
  ];
  let wideValue = $state(null);
  let normalValue = $state(null);
</script>

<main>
  <h1>Dropdown width per select</h1>
  <p>The first dropdown can grow to 60rem. The second keeps its input width.</p>

  <section class="control-wide">
    <label for="wide-select">Wider dropdown</label>
    <Select id="wide-select" class="wide-options" {items} bind:value={wideValue} name="wideChoice" />
    <p>Selected: <output id="wide-value">{wideValue?.value ?? 'None'}</output></p>
  </section>

  <section class="control-normal">
    <label for="normal-select">Default dropdown</label>
    <Select id="normal-select" {items} bind:value={normalValue} name="normalChoice" />
    <p>Selected: <output id="normal-value">{normalValue?.value ?? 'None'}</output></p>
  </section>
</main>

<style>
  :global(html) { font-family: system-ui, sans-serif; line-height: 1.5; color: #202d3c; background: #f6f8fa; }
  :global(body) { margin: 0; }
  main { padding: 2rem 1rem; }
  h1 { margin: 0 0 0.5rem; font-size: 1.5rem; }
  section { width: 18rem; max-width: 100%; margin-top: 2rem; }
  section + section { margin-top: 10rem; }
  label { display: block; margin-bottom: 0.5rem; font-weight: 600; }
  section p { margin: 0.5rem 0; font-size: 0.9rem; }

  :global(.wide-options .svelte-select-list) {
    width: min(60rem, calc(100vw - 2rem)) !important;
  }
</style>
