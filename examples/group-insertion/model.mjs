export function initialState() {
  return { groups: [
    { id: 'group-a', title: 'Group A', items: [
      { id: 'alpha', label: 'Alpha', canStartGroup: true },
      { id: 'beta', label: 'Beta', canStartGroup: true },
      { id: 'note', label: 'Attached note', canStartGroup: false },
    ] },
    { id: 'group-b', title: 'Group B', items: [
      { id: 'gamma', label: 'Gamma', canStartGroup: true },
      { id: 'delta', label: 'Delta', canStartGroup: true },
    ] },
    { id: 'group-c', title: 'Group C', items: [
      { id: 'epsilon', label: 'Epsilon', canStartGroup: true },
    ] },
  ], nextGroup: 1 };
}

export function applyDrop(state, result) {
  const { source, destination, draggableId, reason } = result;
  if (reason !== 'DROP' || !destination) return state;
  const sourceGroup = state.groups.find((group) => group.id === source.droppableId);
  const item = sourceGroup?.items[source.index];
  if (!Number.isInteger(source.index) || item?.id !== draggableId) return state;

  const gap = /^gap:(\d+)$/.exec(destination.droppableId);
  if (gap) {
    const position = Number(gap[1]);
    if (position > state.groups.length || destination.index !== 0 || !item.canStartGroup) return state;
    const groups = state.groups.map((group) => group.id === sourceGroup.id
      ? { ...group, items: group.items.filter((entry) => entry.id !== item.id) }
      : group);
    groups.splice(position, 0, {
      id: `created-${state.nextGroup}`,
      title: `New group ${state.nextGroup}`,
      items: [item],
    });
    return { groups, nextGroup: state.nextGroup + 1 };
  }

  const target = state.groups.find((group) => group.id === destination.droppableId);
  const size = target?.items.length - (sourceGroup === target ? 1 : 0);
  if (!target || !Number.isInteger(destination.index) || destination.index < 0 || destination.index > size) return state;
  if (sourceGroup === target && source.index === destination.index) return state;
  const groups = state.groups.map((group) => ({ ...group, items: [...group.items] }));
  groups.find((group) => group.id === sourceGroup.id).items.splice(source.index, 1);
  groups.find((group) => group.id === target.id).items.splice(destination.index, 0, item);
  return { ...state, groups };
}
