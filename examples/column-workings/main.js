'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const symbols = { add: '+', sub: '−', mul: '×', div: '÷' };
  let sheet;
  let selected = [3, 0];
  let dirty = false;

  const blankRow = () => ({ line: false, cells: Array.from({ length: sheet.columns }, () => ({ digit: '', note: '', given: false, crossed: false })) });
  const cellAt = (row, col) => sheet.rows[row].cells[col];
  const inputAt = (row, col, small = false) => $('grid').rows[row].cells[col].querySelector(small ? '.small-number' : '.digit');

  function select(row, col) {
    selected = [row, col];
    document.querySelector('td.selected')?.classList.remove('selected');
    const td = $('grid').rows[row].cells[col];
    td.classList.add('selected');
    $('selection').textContent = `Row ${row + 1}, column ${col + 1}`;
    $('cross').setAttribute('aria-pressed', String(cellAt(row, col).crossed));
    $('line').setAttribute('aria-pressed', String(sheet.rows[row].line));
  }

  function move(row, col) {
    const nextRow = Math.max(0, Math.min(sheet.rows.length - 1, row));
    const nextCol = Math.max(0, Math.min(sheet.columns - 1, col));
    inputAt(nextRow, nextCol).focus();
  }

  function renderRow(row, index) {
    const tr = document.createElement('tr');
    tr.classList.toggle('underlined', row.line);
    row.cells.forEach((cell, col) => {
      const td = document.createElement('td');
      td.classList.toggle('given', cell.given);
      td.classList.toggle('crossed', cell.crossed);
      if (sheet.operation === 'div' && index === 1 && col >= sheet.dividendStart) {
        td.classList.add('division-top');
        if (col === sheet.dividendStart) td.classList.add('division-start');
      }
      const main = document.createElement('input');
      main.type = 'text'; main.className = 'digit'; main.inputMode = 'numeric';
      main.autocomplete = 'off'; main.spellcheck = false; main.maxLength = 1;
      main.setAttribute('aria-label', `Digit, row ${index + 1}, column ${col + 1}`);
      main.value = cell.digit; main.readOnly = cell.given;
      const small = document.createElement('input');
      small.type = 'text'; small.className = 'small-number'; small.inputMode = 'numeric';
      small.autocomplete = 'off'; small.spellcheck = false; small.maxLength = 2; small.tabIndex = -1;
      small.setAttribute('aria-label', `Small number, row ${index + 1}, column ${col + 1}`);
      small.value = cell.note;
      const printDigit = document.createElement('span'); printDigit.className = 'print-digit'; printDigit.textContent = cell.digit; printDigit.setAttribute('aria-hidden', 'true');
      const printNote = document.createElement('span'); printNote.className = 'print-note'; printNote.textContent = cell.note; printNote.setAttribute('aria-hidden', 'true');
      main.addEventListener('focus', () => select(index, col));
      small.addEventListener('focus', () => select(index, col));
      main.addEventListener('input', () => {
        const value = main.value.replace(/\D/g, '').slice(-1);
        main.value = value; cell.digit = value; printDigit.textContent = value; dirty = true;
        if (value && col + 1 < sheet.columns) move(index, col + 1);
      });
      small.addEventListener('input', () => {
        const value = small.value.replace(/\D/g, '').slice(0, 2);
        small.value = value; cell.note = value; printNote.textContent = value; dirty = true;
      });
      main.addEventListener('keydown', event => {
        const arrows = { ArrowLeft: [index, col - 1], ArrowRight: [index, col + 1], ArrowUp: [index - 1, col], ArrowDown: [index + 1, col] };
        if (arrows[event.key]) { event.preventDefault(); move(...arrows[event.key]); }
        // Replacing an occupied square needs one keystroke, without selecting its text first.
        if (!main.readOnly && /^\d$/.test(event.key) && !event.ctrlKey && !event.metaKey && !event.altKey) {
          event.preventDefault(); main.value = event.key; main.dispatchEvent(new Event('input', { bubbles: true }));
        }
      });
      small.addEventListener('keydown', event => { if (event.key === 'Escape') { event.preventDefault(); main.focus(); } });
      td.append(main, small, printDigit, printNote);
      if (index === 2 && col === 0 && sheet.operation !== 'div') {
        const sign = document.createElement('span'); sign.className = 'operator'; sign.textContent = symbols[sheet.operation]; sign.setAttribute('aria-hidden', 'true'); td.append(sign);
      }
      tr.append(td);
    });
    return tr;
  }

  function makeSheet(operation, first, second) {
    const columns = operation === 'mul' || operation === 'div' ? first.length + second.length + (operation === 'mul' ? 2 : 1) : Math.max(first.length, second.length) + 2;
    sheet = { operation, columns, dividendStart: second.length + 1, rows: [] };
    const count = operation === 'mul' ? Math.max(8, second.length + 5) : operation === 'div' ? Math.max(8, first.length * 2 + 2) : 6;
    sheet.rows = Array.from({ length: count }, blankRow);
    const put = (value, row, start) => [...value].forEach((digit, offset) => Object.assign(cellAt(row, start + offset), { digit, given: true }));
    if (operation === 'div') { put(second, 1, 0); put(first, 1, sheet.dividendStart); }
    else { put(first, 1, columns - first.length); put(second, 2, columns - second.length); sheet.rows[2].line = true; }
    $('grid').replaceChildren(...sheet.rows.map(renderRow));
    document.querySelector('table').style.setProperty('--columns', columns);
    $('problem').textContent = `${first} ${symbols[operation]} ${second}`;
    dirty = false;
    move(operation === 'div' ? 0 : 3, columns - 1);
  }

  $('setup').addEventListener('submit', event => {
    event.preventDefault();
    const operation = $('operation').value;
    const first = $('first').value.trim(); const second = $('second').value.trim();
    let error = '';
    if (!/^\d{1,8}$/.test(first) || !/^\d{1,8}$/.test(second)) error = 'Use whole numbers from 0 to 99999999, with no signs or decimal points.';
    else if (operation === 'div' && BigInt(second) === 0n) error = 'Choose a second number greater than zero for division.';
    else if (operation === 'sub' && BigInt(first) < BigInt(second)) error = 'For this page, the first number must be at least as large as the second number.';
    $('error').textContent = error;
    if (error) return;
    if (dirty && !window.confirm('Make a new page? Your current working will be cleared. Print it first if you want to keep it.')) return;
    makeSheet(operation, first, second);
  });
  $('small').addEventListener('click', () => { const input = inputAt(...selected, true); input.focus(); input.select(); });
  $('cross').addEventListener('click', () => {
    const [row, col] = selected; const cell = cellAt(row, col); cell.crossed = !cell.crossed; dirty = true;
    $('grid').rows[row].cells[col].classList.toggle('crossed', cell.crossed); select(row, col); inputAt(row, col).focus();
  });
  $('line').addEventListener('click', () => {
    const [row, col] = selected; sheet.rows[row].line = !sheet.rows[row].line; dirty = true;
    $('grid').rows[row].classList.toggle('underlined', sheet.rows[row].line); select(row, col); inputAt(row, col).focus();
  });
  $('add-row').addEventListener('click', () => { const row = blankRow(); sheet.rows.push(row); $('grid').append(renderRow(row, sheet.rows.length - 1)); dirty = true; move(sheet.rows.length - 1, 0); });
  $('print').addEventListener('click', () => window.print());
  makeSheet('add', '58', '67');
})();
