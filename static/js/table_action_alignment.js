(function () {
  'use strict';

  const ACTION_HEADERS = new Set(['editar', 'eliminar', 'acciones']);

  function normalize(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
  }

  function alignCell(cell) {
    if (!cell) return;
    cell.style.textAlign = 'right';
    cell.style.whiteSpace = 'nowrap';
    cell.style.paddingRight = '1rem';
    cell.dataset.actionColumn = '1';
  }

  function alignTable(table) {
    if (!table || !table.tHead) return;

    const headerRow = table.tHead.rows[table.tHead.rows.length - 1];
    if (!headerRow) return;

    Array.from(headerRow.cells).forEach((header, columnIndex) => {
      if (!ACTION_HEADERS.has(normalize(header.textContent))) return;

      alignCell(header);
      Array.from(table.tBodies).forEach(body => {
        Array.from(body.rows).forEach(row => {
          // Las filas informativas con colspan no representan columnas de datos.
          if (row.cells.length !== headerRow.cells.length) return;
          alignCell(row.cells[columnIndex]);
        });
      });
    });
  }

  function alignTables(root) {
    const scope = root && root.querySelectorAll ? root : document;
    if (scope.matches && scope.matches('table')) alignTable(scope);
    scope.querySelectorAll('table').forEach(alignTable);
  }

  function start() {
    alignTables(document);

    const observer = new MutationObserver(mutations => {
      mutations.forEach(mutation => {
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === 1) alignTables(node);
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
