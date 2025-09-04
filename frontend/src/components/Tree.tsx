import React from 'react';

export type TreeItemData = {
  id: string;
  label: string;
  icon?: React.ReactNode;
  count?: number;
  depth?: number;
  expanded?: boolean;
  selected?: boolean;
  muted?: boolean;
  children?: TreeItemData[];
  onClick?: () => void;
  onToggle?: () => void;
  className?: string;
};

interface TreeProps {
  items: TreeItemData[];
}

const TreeRow: React.FC<{ item: TreeItemData; depth: number }> = ({ item, depth }) => {
  const hasChildren = (item.children?.length || 0) > 0;
  return (
    <div
      className={`tree-row ${item.selected ? 'selected' : ''} ${item.muted ? 'muted' : ''} ${item.className || ''}`}
      style={{ paddingLeft: 8 + depth * 12, ['--depth' as any]: String(depth) }}
      onClick={item.onClick}
      role="treeitem"
      aria-expanded={item.expanded}
    >
      <button
        className={`tree-toggle ${item.expanded ? 'open' : ''}`}
        onClick={(e) => { e.stopPropagation(); item.onToggle?.(); }}
        aria-hidden={!hasChildren}
        style={{ visibility: hasChildren ? 'visible' : 'hidden' }}
        tabIndex={-1}
      />
      <span className="tree-icon">{item.icon}</span>
      <span className="tree-label">{item.label}</span>
      {typeof item.count === 'number' && (
        <span className="tree-count">({item.count})</span>
      )}
    </div>
  );
};

const Tree: React.FC<TreeProps> = ({ items }) => {
  const render = (list: TreeItemData[], depth = 0): React.ReactNode => (
    <>
      {list.map((it) => (
        <React.Fragment key={it.id}>
          <TreeRow item={it} depth={depth} />
          {it.expanded && it.children && it.children.length > 0 && render(it.children, depth + 1)}
        </React.Fragment>
      ))}
    </>
  );

  return (
    <div className="tree-container" role="tree">
      {render(items, 0)}
    </div>
  );
};

export default Tree;
