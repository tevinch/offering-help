import assert from 'node:assert/strict';
import { test } from 'node:test';
import { applyDrop, initialState } from './model.mjs';

const result = (id, from, index, to, targetIndex = 0) => ({
  draggableId: id,
  source: { droppableId: from, index },
  destination: to === null ? null : { droppableId: to, index: targetIndex },
  reason: 'DROP',
});
const ids = (state) => state.groups.map((g) => [g.id, g.items.map((i) => i.id)]);
const all = (state) => state.groups.flatMap((g) => g.items.map((i) => i.id)).sort();

for (const gap of [0, 1, 3]) {
  test(`an item dropped at gap ${gap} creates a group at that exact position`, () => {
    const before = initialState();
    const snapshot = structuredClone(before);
    const after = applyDrop(before, result('alpha', 'group-a', 0, `gap:${gap}`));
    assert.equal(after.groups.length, 4);
    assert.equal(after.groups[gap].id, 'created-1');
    assert.deepEqual(after.groups[gap].items.map((i) => i.id), ['alpha']);
    assert.deepEqual(after.groups.filter((g) => g.id !== 'created-1').map((g) => g.id),
      ['group-a', 'group-b', 'group-c']);
    assert.deepEqual(after.groups.find((g) => g.id === 'group-a').items.map((i) => i.id), ['beta', 'note']);
    assert.deepEqual(all(after), all(before));
    assert.deepEqual(before, snapshot);
  });
}

test('same-group reorder uses the final insertion index', () => {
  const before = initialState();
  const after = applyDrop(before, result('alpha', 'group-a', 0, 'group-a', 2));
  assert.deepEqual(ids(after), [
    ['group-a', ['beta', 'note', 'alpha']],
    ['group-b', ['gamma', 'delta']], ['group-c', ['epsilon']],
  ]);
});

test('moving between groups preserves unrelated order and an emptied named group', () => {
  const before = initialState();
  const after = applyDrop(before, result('epsilon', 'group-c', 0, 'group-b', 1));
  assert.deepEqual(ids(after), [
    ['group-a', ['alpha', 'beta', 'note']],
    ['group-b', ['gamma', 'epsilon', 'delta']], ['group-c', []],
  ]);
  assert.deepEqual(all(after), all(before));
});

test('the new group remains usable for the next operation', () => {
  const first = applyDrop(initialState(), result('beta', 'group-a', 1, 'gap:1'));
  const second = applyDrop(first, result('gamma', 'group-b', 0, 'created-1', 1));
  const third = applyDrop(second, result('beta', 'created-1', 0, 'gap:4'));
  assert.deepEqual(ids(third), [
    ['group-a', ['alpha', 'note']], ['created-1', ['gamma']],
    ['group-b', ['delta']], ['group-c', ['epsilon']], ['created-2', ['beta']],
  ]);
  assert.deepEqual(all(third), all(initialState()));
});

test('a cancelled or outside drop preserves the exact state', () => {
  const before = initialState();
  assert.equal(applyDrop(before, result('alpha', 'group-a', 0, null)), before);
  assert.equal(applyDrop(before, { ...result('alpha', 'group-a', 0, 'gap:1'), reason: 'CANCEL' }), before);
});

test('the demonstration rule refuses new groups for note but permits existing-group moves', () => {
  const before = initialState();
  assert.equal(applyDrop(before, result('note', 'group-a', 2, 'gap:1')), before);
  const after = applyDrop(before, result('note', 'group-a', 2, 'group-b', 0));
  assert.deepEqual(after.groups[1].items.map((i) => i.id), ['note', 'gamma', 'delta']);
  assert.deepEqual(all(after), all(before));
});

test('invalid destinations or stale item indices do not discard content', () => {
  const before = initialState();
  for (const r of [
    result('alpha', 'group-a', 1, 'gap:1'),
    result('alpha', 'group-a', 0, 'missing'),
    result('alpha', 'group-a', 0, 'gap:-1'),
    result('alpha', 'group-a', 0, 'gap:4'),
    result('alpha', 'group-a', 0, 'gap:1', 1),
    result('alpha', 'group-a', 0, 'group-b', 4),
  ]) assert.equal(applyDrop(before, r), before);
});
