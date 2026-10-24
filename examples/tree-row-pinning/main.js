import { AllCommunityModule, ModuleRegistry, createGrid, themeQuartz } from 'ag-grid-community';
import { AllEnterpriseModule } from 'ag-grid-enterprise';
import { rowData } from './data.js';
import { PinnedTreeToggle } from './pinned-tree-toggle.js';
ModuleRegistry.registerModules([AllCommunityModule, AllEnterpriseModule]);
let getRowIdCalls = 0;
const events = { opened: [], selectionEvents: 0, sortEvents: 0 };
function render(api) {
  const rows = [];
  api.forEachNode(n => rows.push({ id: n.id, parent: n.data?.parentId || null, expanded: !!n.expanded }));
  document.querySelector('#state').textContent = JSON.stringify({ ...events, getRowIdCalls, rows, selected: api.getSelectedRows().map(d=>d.id).sort(), originalData: rowData }, null, 2);
}
createGrid(document.querySelector('#grid'), {
  theme: themeQuartz,
  rowData,
  treeData: true,
  treeDataParentIdField: 'parentId',
  getRowId: p => { getRowIdCalls++; return p.data.id; },
  autoGroupColumnDef: {
    headerName: 'Name', field: 'name', minWidth: 310,
    cellRendererSelector: params => params.node.rowPinned ? {
      component: PinnedTreeToggle,
      params: { suppressMouseEventHandling: () => true },
    } : { component: 'agGroupCellRenderer' },
  },
  columnDefs: [{field:'kind'}, {field:'effort'}],
  defaultColDef: { flex:1, sortable:true },
  groupDefaultExpanded: 0,
  rowSelection: { mode:'multiRow', headerCheckbox:false },
  enableRowPinning: true,
  isRowPinned: node => node.id === 'planning' ? 'top' : null,
  onGridReady: e => render(e.api),
  onModelUpdated: e => render(e.api),
  onRowGroupOpened: e => { events.opened.push({id:e.node.id,expanded:e.node.expanded}); render(e.api); },
  onSelectionChanged: e => { events.selectionEvents++; render(e.api); },
  onSortChanged: e => { events.sortEvents++; render(e.api); },
});
