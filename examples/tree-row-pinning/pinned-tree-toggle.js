// The pinned row is a copy. Expand the original tree node in the body.
export class PinnedTreeToggle {
  init(params) {
    this.params = params;
    this.button = document.createElement('button');
    this.button.type = 'button';
    this.button.dataset.treeToggle = '';
    this.onClick = event => {
      event.stopPropagation();
      const node = this.originalNode();
      if (node) this.params.api.setRowNodeExpanded(node, !node.expanded);
    };
    this.onKeyDown = event => {
      if (event.key === 'Enter' || event.key === ' ') event.stopPropagation();
    };
    this.onTreeChange = () => this.update();
    this.button.addEventListener('click', this.onClick);
    this.button.addEventListener('keydown', this.onKeyDown);
    params.api.addEventListener('rowGroupOpened', this.onTreeChange);
    params.api.addEventListener('modelUpdated', this.onTreeChange);
    this.update();
  }

  originalNode() {
    return this.params.api.getRowNode(this.params.data.id);
  }

  update() {
    const node = this.originalNode();
    const expanded = !!node?.expanded;
    const name = this.params.data.name;
    this.button.disabled = !node?.isExpandable();
    this.button.textContent = `${expanded ? '▾' : '▸'} ${name}`;
    this.button.setAttribute('aria-label', `${expanded ? 'Collapse' : 'Expand'} ${name}`);
    this.button.setAttribute('aria-expanded', String(expanded));
  }

  getGui() { return this.button; }

  refresh(params) {
    this.params = params;
    this.update();
    return true;
  }

  destroy() {
    this.params.api.removeEventListener('rowGroupOpened', this.onTreeChange);
    this.params.api.removeEventListener('modelUpdated', this.onTreeChange);
    this.button.removeEventListener('click', this.onClick);
    this.button.removeEventListener('keydown', this.onKeyDown);
  }
}
