(function () {
  'use strict';

  const descriptions = {
    'orden': 'Número que identifica la orden dentro del proceso. Úselo para buscar y relacionar sus etapas.',
    'cliente': 'Cliente propietario del café o asociado a la operación.',
    'empleado': 'Empleado responsable de ejecutar o registrar la actividad.',
    'estado orden': 'Situación actual de la orden. Al marcarla Completada se aplican las validaciones y movimientos correspondientes.',
    'estado tareas': 'Estado de avance de la tarea dentro del proceso productivo.',
    'inventario cafe': 'Lote de café del cual se toma o al cual se agrega la cantidad registrada.',
    'variedad cafe': 'Variedad del café seleccionada desde el maestro de variedades.',
    'proceso cafe': 'Proceso aplicado al café, seleccionado desde el maestro correspondiente.',
    'peso bruto (kg)': 'Peso total registrado antes de descontar pérdidas, empaques u otros ajustes.',
    'peso neto (kg)': 'Peso efectivo del café usado para inventario y cálculos del proceso.',
    'cantidad ingresada (kg)': 'Cantidad inicial registrada para el lote de inventario.',
    'cantidad existe (kg)': 'Saldo disponible actualmente en el inventario.',
    'kilos ingresar (kg)': 'Cantidad que se sumará al saldo existente al guardar.',
    'kilos sacar (kg)': 'Cantidad que se restará del saldo existente al guardar.',
    'notas': 'Observaciones adicionales que ayudan a documentar el registro.',
    'fecha inicio orden': 'Fecha prevista o real en la que inicia la orden.',
    'fecha entrega': 'Fecha prevista para entregar o finalizar la orden.',
    'prioridad': 'Nivel de atención asignado a la orden.',
    'buscar': 'Escriba parte del dato para filtrar automáticamente el listado.',
    'nuevo': 'Crea un registro nuevo si su perfil tiene permiso para adicionar.',
    'editar': 'Abre el registro para modificar los campos autorizados.',
    'eliminar': 'Solicita confirmación para eliminar el registro si tiene permiso.',
    'guardar': 'Valida y guarda la información ingresada en el formulario.',
    'cancelar': 'Cierra o abandona el formulario sin guardar cambios pendientes.',
    'cerrar': 'Cierra la ventana actual.',
    'consultar': 'Ejecuta la consulta con la información o filtros ingresados.',
    'exportar a pdf': 'Genera un archivo PDF con la información mostrada.',
    'imprimir o guardar pdf': 'Abre las opciones del navegador para imprimir o guardar este contenido como PDF.'
  };

  function normalize(value) {
    return String(value || '')
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/[\s:*#]+/g, ' ').trim().toLowerCase();
  }

  function labelFor(control) {
    const explicit = control.getAttribute('data-tooltip');
    if (explicit) return { label: '', text: explicit };

    let label = '';
    if (control.id) {
      const associated = document.querySelector(`label[for="${CSS.escape(control.id)}"]`);
      if (associated) label = associated.textContent;
    }
    if (!label) {
      const container = control.closest('div, td, section');
      const nearby = container && container.querySelector('label');
      if (nearby) label = nearby.textContent;
    }
    if (!label && control.matches('button, a')) label = control.textContent;
    if (!label) label = control.getAttribute('aria-label') || control.getAttribute('placeholder') || control.name;

    const cleanLabel = String(label || '').replace(/\s+/g, ' ').trim();
    return { label: cleanLabel, text: '' };
  }

  function descriptionFor(control) {
    const found = labelFor(control);
    if (found.text) return found.text;
    const key = normalize(found.label);

    if (descriptions[key]) return descriptions[key];
    const partial = Object.keys(descriptions).find(item => key === item || key.includes(item));
    if (partial) return descriptions[partial];

    if (control.matches('select')) return `${found.label || 'Lista de selección'}: seleccione una de las opciones disponibles.`;
    if (control.matches('textarea')) return `${found.label || 'Campo de texto'}: escriba las observaciones o información solicitada.`;
    if (control.matches('input[type="checkbox"], input[type="radio"]')) return `${found.label || 'Opción'}: active o desactive esta opción según corresponda.`;
    if (control.matches('input')) return `${found.label || 'Campo'}: ingrese la información solicitada.`;
    return found.label ? `${found.label}: seleccione esta opción para ejecutar la acción.` : '';
  }

  function enhance(root) {
    const scope = root && root.querySelectorAll ? root : document;
    const selector = [
      'form input:not([type="hidden"])', 'form select', 'form textarea', 'form button',
      '[data-modal-root] button', '[data-modal-root] a',
      'header button', 'header a', 'aside button', 'aside a', '[data-tooltip]'
    ].join(',');

    scope.querySelectorAll(selector).forEach(control => {
      if (control.dataset.tooltipReady === '1') return;
      const description = descriptionFor(control);
      if (!description) return;
      control.dataset.tooltipReady = '1';
      if (!control.getAttribute('title')) control.setAttribute('title', description);
      if (!control.getAttribute('aria-label') && !String(control.textContent || '').trim()) {
        control.setAttribute('aria-label', description);
      }
      const label = control.closest('div, td')?.querySelector('label');
      if (label && !label.getAttribute('title')) label.setAttribute('title', description);
    });
  }

  function start() {
    enhance(document);
    const observer = new MutationObserver(mutations => {
      mutations.forEach(mutation => mutation.addedNodes.forEach(node => {
        if (node.nodeType === 1) {
          if (node.matches && node.matches('[data-tooltip], input, select, textarea, button, a')) enhance(node.parentElement || document);
          else enhance(node);
        }
      }));
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
