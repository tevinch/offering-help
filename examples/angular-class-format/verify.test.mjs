import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { ESLint } from 'eslint';
import * as prettier from 'prettier';

// Catches loss of the narrow class ignore: a normal format would undo wrapping.
test('Angular class wrapping and other HTML formatting remain stable on repeated saves', async () => {
  const source = await readFile(new URL('./sample.component.html', import.meta.url), 'utf8');
  const eslint = new ESLint({ fix: true });
  const check = new ESLint({ fix: false });
  const format = text => prettier.format(text, { parser: 'angular', printWidth: 80 });
  const collapsed = source.replace(/class="[^\"]*"/, 'class="text-black underline focus:font-bold focus:text-red-700 hover:font-bold hover:text-blue-700"')
    .replace('(click)="select($event)"', '(click)="  select(  $event  ) "')
    .replace('{{ title }}', '{{title}}').replace('{{ description }}', '{{ description}}');
  assert.match(collapsed, /select\(  \$event  \)/);
  const [before] = await check.lintText(collapsed, { filePath: 'sample.component.html' });
  assert.ok(before.messages.some(m => m.ruleId === 'better-tailwindcss/enforce-consistent-line-wrapping'),
    'The wrapping rule must actually run against the collapsed class');
  const [first] = await eslint.lintText(await format(collapsed), { filePath: 'sample.component.html' });
  assert.equal(first.fatalErrorCount, 0, JSON.stringify(first.messages));
  assert.equal(first.errorCount, 0, JSON.stringify(first.messages));
  assert.ok(first.output, 'ESLint must actually fix the collapsed input');
  const wrapped = first.output;
  assert.match(wrapped, /class="[^\"]*\n[^\"]*focus:/);
  assert.match(wrapped, /\(click\)="select\(\$event\)"/);
  assert.match(wrapped, /{{ title }}/);
  assert.match(wrapped, /{{ description }}/);
  const tokens = html => html.match(/class="([^\"]*)"/)[1].trim().split(/\s+/).sort();
  assert.deepEqual(tokens(wrapped), [
    'text-black', 'underline', 'focus:font-bold', 'focus:text-red-700',
    'hover:font-bold', 'hover:text-blue-700',
  ].sort());
  let current = wrapped;
  for (let i = 0; i < 3; i++) {
    const formatted = await format(current);
    const [linted] = await check.lintText(formatted, { filePath: 'sample.component.html' });
    assert.equal(linted.errorCount, 0, `Save ${i + 1}: ${JSON.stringify(linted.messages)}`);
    assert.equal(formatted, current, `Save ${i + 1} changed the previous result`);
    const [fixed] = await eslint.lintText(formatted, { filePath: 'sample.component.html' });
    current = fixed.output ?? formatted;
    assert.equal(current, formatted);
    const [lintFirst] = await eslint.lintText(current, { filePath: 'sample.component.html' });
    const formatLast = await format(lintFirst.output ?? current);
    assert.equal(formatLast, current, `Reverse order at save ${i + 1} changed the result`);
  }

  const withoutIgnore = collapsed.replace(/\s*<!-- prettier-ignore-attribute class -->/, '');
  const [negativeFixed] = await eslint.lintText(await format(withoutIgnore), { filePath: 'sample.component.html' });
  assert.ok(negativeFixed.output, 'The negative control must actually apply an ESLint fix');
  const [negativeCheck] = await check.lintText(await format(negativeFixed.output), { filePath: 'sample.component.html' });
  assert.ok(negativeCheck.messages.some(m => m.ruleId === 'better-tailwindcss/enforce-consistent-line-wrapping'),
    'Without the narrow ignore, a later Prettier pass must reproduce the wrapping conflict');
});
