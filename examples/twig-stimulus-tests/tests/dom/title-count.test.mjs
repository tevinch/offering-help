import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { JSDOM } from 'jsdom';
import { Application } from '@hotwired/stimulus';
import TitleCount from '../../assets/controllers/title_count_controller.js';

const fixture = JSON.parse(readFileSync(new URL('../../var/fixtures/title-form.json', import.meta.url)));
assert.ok(process.env.FIXTURE_RUN_ID, 'Run npm run test:dom to generate a fresh fixture');
assert.equal(fixture.run, process.env.FIXTURE_RUN_ID, 'Fixture must come from this test run');

async function until(check, message) {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (check()) return;
    await new Promise(resolve => setTimeout(resolve, 5));
  }
  assert.fail(message);
}

async function withController(operation) {
  const dom = new JSDOM(`<!doctype html><html><body>${fixture.html}</body></html>`);
  const names = ['window', 'document', 'MutationObserver', 'Node', 'Element', 'HTMLElement',
    'KeyboardEvent', 'MouseEvent', 'Event', 'CustomEvent'];
  for (const name of names) globalThis[name] = name === 'window' ? dom.window : dom.window[name];
  const errors = [];
  const app = Application.start(document.documentElement);
  app.handleError = error => errors.push(error);
  app.register('title-count', TitleCount);
  const form = document.querySelector('form');
  const controller = () => app.getControllerForElementAndIdentifier(form, 'title-count');
  try {
    await until(() => controller(), 'Real Stimulus controller never connected');
    await operation({ form, controller, app, dom });
    assert.deepEqual(errors, [], 'Stimulus must not report lifecycle or action errors');
  } finally {
    form.remove();
    await until(() => !controller(), 'Controller did not disconnect during teardown');
    app.stop();
    dom.window.close();
    for (const name of names) delete globalThis[name];
  }
}

function type(input, value, dom) {
  input.value = value;
  input.dispatchEvent(new dom.window.Event('input', { bubbles: true }));
}

test('real Twig actions, targets, disconnection and reconnection keep working', async () => {
  await withController(async ({ form, controller, dom }) => {
    const input = form.querySelector('[name="title"]');
    const count = form.querySelector('output');
    const connected = controller();
    assert.equal(count.textContent, '0 characters');
    type(input, 'Read', dom);
    assert.equal(count.textContent, '4 characters');
    type(input, '猫の本', dom);
    assert.equal(count.textContent, '3 characters');
    form.remove();
    await until(() => !controller(), 'Removal must disconnect the actual controller');
    type(input, 'Detached', dom);
    assert.equal(count.textContent, '3 characters', 'Detached actions must be unbound');
    document.body.append(form);
    await until(() => controller(), 'Reinsertion must reconnect the actual controller');
    assert.equal(controller(), connected, 'Stimulus reconnects the existing instance');
    assert.equal(count.textContent, '8 characters');
    type(input, 'A new chapter', dom);
    assert.equal(count.textContent, '13 characters');
  });
});

test('a fresh document and application receive no state from the previous test', async () => {
  await withController(async ({ form, dom }) => {
    assert.equal(form.querySelector('output').textContent, '0 characters');
    type(form.querySelector('[name="title"]'), 'Next', dom);
    assert.equal(form.querySelector('output').textContent, '4 characters');
  });
});
