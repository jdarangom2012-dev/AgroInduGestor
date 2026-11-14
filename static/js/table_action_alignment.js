(function () {
  'use strict';

  const ACTION_HEADERS = new Set(['editar', 'eliminar', 'acciones']);
  const CENTERED_VALUE_HEADERS = [
    '#',
    'id',
    'fecha',
    'orden',
    'peso',
    'rendimiento',
    'humedad',
    'densidad',
    'cantidad',
    'sacos',
    'bolsas',
    'paquetes',
    'factor',
    'puntaje',
    'temperatura',
    'potencia'
  ];

  function normalize(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
  }

  function isCenteredValueHeader(value) {
    const header = normalize(value);
    return CENTERED_VALUE_HEADERS.some(label => (
      label.length === 1 ? header === label : header.includes(label)
    ));
  }

  function alignActionCell(cell) {
    if (!cell) return;
    // Las columnas permanecen al extremo derecho de la tabla, pero su
    // contenido se centra para que encabezado y acción formen una línea visual.
    cell.style.textAlign = 'center';
    cell.style.whiteSpace = 'nowrap';
    cell.style.width = '6.5rem';
    cell.style.minWidth = '6.5rem';
    cell.style.paddingLeft = '0.75rem';
    cell.style.paddingRight = '0.75rem';
    cell.dataset.actionColumn = '1';
  }

  function alignValueCell(cell) {
    if (!cell) return;
    // Los datos cortos y numéricos quedan debajo de su encabezado, sin
    // pegarse al límite de la siguiente columna.
    cell.style.textAlign = 'center';
    cell.style.verticalAlign = 'middle';
    cell.style.whiteSpace = 'nowrap';
    cell.style.fontVariantNumeric = 'tabular-nums';
    cell.style.paddingLeft = '0.65rem';
    cell.style.paddingRight = '0.65rem';
    cell.dataset.valueColumn = '1';
  }

  function alignTable(table) {
    if (!table || !table.tHead) return;

    const headerRow = table.tHead.rows[table.tHead.rows.length - 1];
    if (!headerRow) return;

    Array.from(headerRow.cells).forEach((header, columnIndex) => {
      const headerName = normalize(header.textContent);
      const isAction = ACTION_HEADERS.has(headerName);
      const isCenteredValue = isCenteredValueHeader(headerName);
      if (!isAction && !isCenteredValue) return;

      if (isAction) alignActionCell(header);
      else alignValueCell(header);
      Array.from(table.tBodies).forEach(body => {
        Array.from(body.rows).forEach(row => {
          // Las filas informativas con colspan no representan columnas de datos.
          if (row.cells.length !== headerRow.cells.length) return;
          if (isAction) alignActionCell(row.cells[columnIndex]);
          else alignValueCell(row.cells[columnIndex]);
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
