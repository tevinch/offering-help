export const rowData = [
  { id: 'planning', name: 'Planning', kind: 'Department', effort: 10 },
  { id: 'design', parentId: 'planning', name: 'Design', kind: 'Team', effort: 4 },
  { id: 'research', parentId: 'design', name: 'Research', kind: 'Task', effort: 1 },
  { id: 'build', parentId: 'planning', name: 'Build', kind: 'Team', effort: 2 },
  { id: 'support', name: 'Support', kind: 'Department', effort: 20 },
  { id: 'support-a', parentId: 'support', name: 'Documentation', kind: 'Task', effort: 6 },
  { id: 'support-b', parentId: 'support', name: 'Training', kind: 'Task', effort: 8 },
];
