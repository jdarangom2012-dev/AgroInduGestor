// Manejo de submit AJAX para formularios en modales
// Solo aplica si el formulario está dentro de un modal cargado por AJAX


function getRendimientoFields(scope) {
  if (!scope || !scope.querySelector) {
    return null;
  }

  const trillaNeto =
    scope.querySelector('#id_peso_cafe_neto') ||
    scope.querySelector('#id_peso_cafe_bruto') ||
    scope.querySelector('input[name="peso_cafe_neto"], input[name="peso_cafe_bruto"]');
  const trillaVerde =
    scope.querySelector('#id_peso_cafe_verde') ||
    scope.querySelector('input[name="peso_cafe_verde"]');

  const tuesteTostado =
    scope.querySelector('#id_peso_cafe_tostado_total') ||
    scope.querySelector('input[name="peso_cafe_tostado_total"]');
  const tuesteVerde =
    scope.querySelector('#id_peso_cafe_vede_total') ||
    scope.querySelector('#id_peso_cafe_verde_total') ||
    scope.querySelector('input[name="peso_cafe_vede_total"], input[name="peso_cafe_verde_total"]');

  const rendimiento =
    scope.querySelector('#id_rendimiento') ||
    scope.querySelector('input[name="rendimiento"]:not([type="hidden"])');

  if (trillaNeto && trillaVerde && rendimiento) {
    return { pesoNeto: trillaNeto, pesoVerde: trillaVerde, rendimiento, tipo: 'trilla' };
  }

  if (tuesteTostado && tuesteVerde && rendimiento) {
    return { pesoTostado: tuesteTostado, pesoVerde: tuesteVerde, rendimiento, tipo: 'tueste' };
  }

  if (!tuesteTostado && !trillaNeto) {
    return null;
  }

  if (!tuesteVerde && !trillaVerde) {
    return null;
  }

  return { pesoTostado: tuesteTostado || trillaNeto, pesoVerde: tuesteVerde || trillaVerde, rendimiento, tipo: 'generic' };
}


function calcularRendimiento(scope) {
  const fields = getRendimientoFields(scope);
  if (!fields) {
    return;
  }

  const { pesoVerde, rendimiento, tipo } = fields;
  rendimiento.readOnly = true;
  rendimiento.setAttribute('readonly', 'readonly');

  const verde = parseFloat(String(pesoVerde.value || '').replace(',', '.'));
  if (!verde || verde === 0) {
    rendimiento.value = '0.00';
    return;
  }

  let resultado = 0;
  if (tipo === 'trilla') {
    const neto = parseFloat(String(fields.pesoNeto.value || '').replace(',', '.'));
    if (!neto || neto === 0) {
      rendimiento.value = '0.00';
      return;
    }
    resultado = (verde / neto) * 100;
  } else {
    const tostado = parseFloat(String(fields.pesoTostado.value || '').replace(',', '.'));
    resultado = ((tostado || 0) / verde) * 100;
  }

  rendimiento.value = resultado.toFixed(2);
}


function bindRendimientoCalc(scope) {
  const fields = getRendimientoFields(scope);
  if (!fields) {
    return;
  }

  const { pesoTostado, pesoNeto, pesoVerde, rendimiento } = fields;
  const origen = pesoTostado || pesoNeto;
  if (!origen || !pesoVerde) {
    return;
  }

  const bindKey = [(origen.id || origen.name), (pesoVerde.id || pesoVerde.name)].join('|');

  if (rendimiento.dataset.rendimientoCalcInit === bindKey) {
    calcularRendimiento(scope);
    return;
  }

  const handler = function () {
    calcularRendimiento(scope);
  };

  origen.addEventListener('input', handler);
  pesoVerde.addEventListener('input', handler);
  origen.addEventListener('change', handler);
  pesoVerde.addEventListener('change', handler);
  rendimiento.dataset.rendimientoCalcInit = bindKey;

  calcularRendimiento(scope);
}


window.calcularRendimiento = calcularRendimiento;


function initRendimientoCalc(container) {
  const scopes = [];
  if (container && container.nodeType === 1 && container.matches && container.matches('[data-modal-root]')) {
    scopes.push(container);
  } else if (container && container.querySelectorAll) {
    scopes.push(...container.querySelectorAll('[data-modal-root]'));
  }
  if (!scopes.length) scopes.push(container && container.querySelector ? container : document);

  for (const scope of scopes) {
    if (!scope || !scope.querySelector) continue;
    bindRendimientoCalc(scope);
  }
}

// Exponer por compatibilidad / reutilización
window.initRendimientoCalc = initRendimientoCalc;


function initRendimientoTrilla(scope) {
  initRendimientoCalc(scope);
}

// Mantener el nombre antiguo para no romper nada existente
window.initRendimientoTrilla = initRendimientoTrilla;


function initOrdenTrillaDefaults(container) {
  const scopes = [];
  if (container && container.nodeType === 1 && container.matches && container.matches('[data-modal-root]')) {
    scopes.push(container);
  } else if (container && container.querySelectorAll) {
    scopes.push(...container.querySelectorAll('[data-modal-root]'));
  }
  if (!scopes.length) scopes.push(container && container.querySelector ? container : document);

  for (const scope of scopes) {
    if (!scope || !scope.querySelector) continue;

    const defaultsUrl = scope.getAttribute('data-orden-trilla-defaults-url');
    if (!defaultsUrl) continue;

    const ordenField = scope.querySelector('#id_orden');
    const clienteField = scope.querySelector('#id_cliente');
    const pesoField = scope.querySelector('#id_peso_cafe_bruto');
    const estadoField = scope.querySelector('#id_estado_tareas');
    if (!ordenField || !clienteField || !pesoField || !estadoField) continue;

    function applyDefaults(data) {
      clienteField.value = data && data.cliente_id ? String(data.cliente_id) : '';
      pesoField.value = data && data.peso_cafe_bruto != null ? String(data.peso_cafe_bruto) : '';
      estadoField.value = data && data.estado_tareas_id ? String(data.estado_tareas_id) : '';

      clienteField.dispatchEvent(new Event('change', { bubbles: true }));
      pesoField.dispatchEvent(new Event('input', { bubbles: true }));
      pesoField.dispatchEvent(new Event('change', { bubbles: true }));
      estadoField.dispatchEvent(new Event('change', { bubbles: true }));
    }

    let currentRequest = 0;
    async function syncOrdenDefaults() {
      const ordenId = String(ordenField.value || '').trim();
      const requestId = ++currentRequest;

      try {
        const url = ordenId ? defaultsUrl + '?orden_id=' + encodeURIComponent(ordenId) : defaultsUrl;
        const response = await fetch(url, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          credentials: 'same-origin',
        });
        if (!response.ok) throw new Error('Error ' + response.status);
        const data = await response.json();
        if (requestId !== currentRequest) return;
        applyDefaults(data);
      } catch (_) {
        if (requestId !== currentRequest) return;
      }
    }

    if (ordenField.dataset.trillaDefaultsInit !== '1') {
      ordenField.addEventListener('change', syncOrdenDefaults);
      ordenField.dataset.trillaDefaultsInit = '1';
    }

    const shouldSyncOnLoad =
      !scope.dataset.trillaDefaultsSynced ||
      (String(ordenField.value || '').trim() && !String(clienteField.value || '').trim() && !String(pesoField.value || '').trim());

    if (shouldSyncOnLoad) {
      scope.dataset.trillaDefaultsSynced = '1';
      syncOrdenDefaults();
    }
  }
}

window.initOrdenTrillaDefaults = initOrdenTrillaDefaults;


function initOrdenTuesteDefaults(container) {
  const scopes = [];
  if (container && container.nodeType === 1 && container.matches && container.matches('[data-modal-root]')) {
    scopes.push(container);
  } else if (container && container.querySelectorAll) {
    scopes.push(...container.querySelectorAll('[data-modal-root]'));
  }
  if (!scopes.length) scopes.push(container && container.querySelector ? container : document);

  for (const scope of scopes) {
    if (!scope || !scope.querySelector) continue;

    const defaultsUrl = scope.getAttribute('data-orden-tueste-defaults-url');
    if (!defaultsUrl) continue;

    const ordenField = scope.querySelector('#id_orden');
    const clienteField = scope.querySelector('#id_cliente');
    const cafeField = scope.querySelector('#id_inventario_cafe_ref');
    const estadoField = scope.querySelector('#id_estado_tareas');
    if (!ordenField || !clienteField || !cafeField || !estadoField) continue;

    function applyDefaults(data) {
      clienteField.value = data && data.cliente_id ? String(data.cliente_id) : '';
      cafeField.value = data && data.inventario_cafe_ref_id ? String(data.inventario_cafe_ref_id) : '';
      estadoField.value = data && data.estado_tareas_id ? String(data.estado_tareas_id) : '';

      clienteField.dispatchEvent(new Event('change', { bubbles: true }));
      cafeField.dispatchEvent(new Event('change', { bubbles: true }));
      estadoField.dispatchEvent(new Event('change', { bubbles: true }));
    }

    let currentRequest = 0;
    async function syncOrdenDefaults() {
      const ordenId = String(ordenField.value || '').trim();
      const requestId = ++currentRequest;

      try {
        const url = ordenId ? defaultsUrl + '?orden_id=' + encodeURIComponent(ordenId) : defaultsUrl;
        const response = await fetch(url, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          credentials: 'same-origin',
        });
        if (!response.ok) throw new Error('Error ' + response.status);
        const data = await response.json();
        if (requestId !== currentRequest) return;
        applyDefaults(data);
      } catch (_) {
        if (requestId !== currentRequest) return;
      }
    }

    if (ordenField.dataset.tuesteDefaultsInit !== '1') {
      ordenField.addEventListener('change', syncOrdenDefaults);
      ordenField.dataset.tuesteDefaultsInit = '1';
    }

    const shouldSyncOnLoad =
      !scope.dataset.tuesteDefaultsSynced ||
      (String(ordenField.value || '').trim() && (!String(clienteField.value || '').trim() || !String(cafeField.value || '').trim()));

    if (shouldSyncOnLoad) {
      scope.dataset.tuesteDefaultsSynced = '1';
      syncOrdenDefaults();
    }
  }
}

window.initOrdenTuesteDefaults = initOrdenTuesteDefaults;


function initOrdenSeleccionTuesteDefaults(container) {
  const scopes = [];
  if (container && container.nodeType === 1 && container.matches && container.matches('[data-modal-root]')) {
    scopes.push(container);
  } else if (container && container.querySelectorAll) {
    scopes.push(...container.querySelectorAll('[data-modal-root]'));
  }
  if (!scopes.length) scopes.push(container && container.querySelector ? container : document);

  for (const scope of scopes) {
    if (!scope || !scope.querySelector) continue;

    const defaultsUrl = scope.getAttribute('data-orden-seleccion-tueste-defaults-url');
    if (!defaultsUrl) continue;

    const ordenField = scope.querySelector('#id_orden');
    const clienteField = scope.querySelector('#id_cliente');
    if (!ordenField || !clienteField) continue;

    function applyDefaults(data) {
      clienteField.value = data && data.cliente_id ? String(data.cliente_id) : '';
      clienteField.dispatchEvent(new Event('change', { bubbles: true }));
    }

    let currentRequest = 0;
    async function syncOrdenDefaults() {
      const ordenId = String(ordenField.value || '').trim();
      const requestId = ++currentRequest;

      try {
        const url = ordenId ? defaultsUrl + '?orden_id=' + encodeURIComponent(ordenId) : defaultsUrl;
        const response = await fetch(url, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          credentials: 'same-origin',
        });
        if (!response.ok) throw new Error('Error ' + response.status);
        const data = await response.json();
        if (requestId !== currentRequest) return;
        applyDefaults(data);
      } catch (_) {
        if (requestId !== currentRequest) return;
      }
    }

    if (ordenField.dataset.seleccionTuesteDefaultsInit !== '1') {
      ordenField.addEventListener('change', syncOrdenDefaults);
      ordenField.dataset.seleccionTuesteDefaultsInit = '1';
    }

    const shouldSyncOnLoad =
      !scope.dataset.seleccionTuesteDefaultsSynced ||
      (String(ordenField.value || '').trim() && !String(clienteField.value || '').trim());

    if (shouldSyncOnLoad) {
      scope.dataset.seleccionTuesteDefaultsSynced = '1';
      syncOrdenDefaults();
    }
  }
}

window.initOrdenSeleccionTuesteDefaults = initOrdenSeleccionTuesteDefaults;


function initOrdenSeleccionTostadoDefaults(container) {
  const scopes = [];
  if (container && container.nodeType === 1 && container.matches && container.matches('[data-modal-root]')) {
    scopes.push(container);
  } else if (container && container.querySelectorAll) {
    scopes.push(...container.querySelectorAll('[data-modal-root]'));
  }
  if (!scopes.length) scopes.push(container && container.querySelector ? container : document);

  for (const scope of scopes) {
    if (!scope || !scope.querySelector) continue;

    const defaultsUrl = scope.getAttribute('data-orden-seleccion-tostado-defaults-url');
    if (!defaultsUrl) continue;

    const ordenField = scope.querySelector('#id_orden');
    const clienteField = scope.querySelector('#id_cliente');
    const cafeField = scope.querySelector('#id_inventario_cafe_ref');
    const estadoField = scope.querySelector('#id_estado_tareas');
    if (!ordenField || !clienteField || !cafeField || !estadoField) continue;

    function applyDefaults(data) {
      clienteField.value = data && data.cliente_id ? String(data.cliente_id) : '';
      cafeField.value = data && data.inventario_cafe_ref_id ? String(data.inventario_cafe_ref_id) : '';
      estadoField.value = data && data.estado_tareas_id ? String(data.estado_tareas_id) : '';

      clienteField.dispatchEvent(new Event('change', { bubbles: true }));
      cafeField.dispatchEvent(new Event('change', { bubbles: true }));
      estadoField.dispatchEvent(new Event('change', { bubbles: true }));
    }

    let currentRequest = 0;
    async function syncOrdenDefaults() {
      const ordenId = String(ordenField.value || '').trim();
      const requestId = ++currentRequest;

      try {
        const url = ordenId ? defaultsUrl + '?orden_id=' + encodeURIComponent(ordenId) : defaultsUrl;
        const response = await fetch(url, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          credentials: 'same-origin',
        });
        if (!response.ok) throw new Error('Error ' + response.status);
        const data = await response.json();
        if (requestId !== currentRequest) return;
        applyDefaults(data);
      } catch (_) {
        if (requestId !== currentRequest) return;
      }
    }

    if (ordenField.dataset.seleccionTostadoDefaultsInit !== '1') {
      ordenField.addEventListener('change', syncOrdenDefaults);
      ordenField.dataset.seleccionTostadoDefaultsInit = '1';
    }

    const shouldSyncOnLoad =
      !scope.dataset.seleccionTostadoDefaultsSynced ||
      (String(ordenField.value || '').trim() && (!String(clienteField.value || '').trim() || !String(cafeField.value || '').trim()));

    if (shouldSyncOnLoad) {
      scope.dataset.seleccionTostadoDefaultsSynced = '1';
      syncOrdenDefaults();
    }
  }
}

window.initOrdenSeleccionTostadoDefaults = initOrdenSeleccionTostadoDefaults;


function initOrdenSeleccionVerdeDefaults(container) {
  const scopes = [];
  if (container && container.nodeType === 1 && container.matches && container.matches('[data-modal-root]')) {
    scopes.push(container);
  } else if (container && container.querySelectorAll) {
    scopes.push(...container.querySelectorAll('[data-modal-root]'));
  }
  if (!scopes.length) scopes.push(container && container.querySelector ? container : document);

  for (const scope of scopes) {
    if (!scope || !scope.querySelector) continue;

    const defaultsUrl = scope.getAttribute('data-orden-seleccion-verde-defaults-url');
    if (!defaultsUrl) continue;

    const ordenField = scope.querySelector('#id_orden');
    const clienteField = scope.querySelector('#id_cliente');
    if (!ordenField) continue;

    function bloquearMedicionesCliente(bloquear) {
      scope.dataset.medicionesClienteBloqueadas = bloquear ? '1' : '0';
      const aviso = scope.querySelector('[data-mediciones-cliente-aviso]');
      if (aviso) aviso.classList.toggle('hidden', !bloquear);
      ['#id_medir_humedad', '#id_medir_densidad'].forEach(function(selector) {
        const checkbox = scope.querySelector(selector);
        if (!checkbox) return;
        checkbox.disabled = bloquear;
        if (bloquear) checkbox.checked = false;
      });
      initSeleccionVerdeCamposDependientes(scope);
    }

    function applyDefaults(data) {
      if (clienteField) {
        clienteField.value = data && data.cliente_id ? String(data.cliente_id) : '';
        clienteField.dispatchEvent(new Event('change', { bubbles: true }));
      }
      bloquearMedicionesCliente(!!(data && data.mediciones_bloqueadas));
    }

    let currentRequest = 0;
    async function syncOrdenDefaults() {
      const ordenId = String(ordenField.value || '').trim();
      const requestId = ++currentRequest;

      try {
        const params = new URLSearchParams();
        if (ordenId) params.set('orden_id', ordenId);
        if (scope.dataset.seleccionVerdeId) params.set('excluir_pk', scope.dataset.seleccionVerdeId);
        const url = params.toString() ? defaultsUrl + '?' + params.toString() : defaultsUrl;
        const response = await fetch(url, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          credentials: 'same-origin',
        });
        if (!response.ok) throw new Error('Error ' + response.status);
        const data = await response.json();
        if (requestId !== currentRequest) return;
        applyDefaults(data);
      } catch (_) {
        if (requestId !== currentRequest) return;
      }
    }

    if (ordenField.dataset.seleccionVerdeDefaultsInit !== '1') {
      ordenField.addEventListener('change', syncOrdenDefaults);
      ordenField.dataset.seleccionVerdeDefaultsInit = '1';
    }

    const shouldSyncOnLoad =
      !scope.dataset.seleccionVerdeDefaultsSynced ||
      String(ordenField.value || '').trim();

    if (shouldSyncOnLoad) {
      scope.dataset.seleccionVerdeDefaultsSynced = '1';
      syncOrdenDefaults();
    }
  }
}

window.initOrdenSeleccionVerdeDefaults = initOrdenSeleccionVerdeDefaults;


function initSeleccionVerdeZaranda(container) {
  const scopes = [];
  if (container && container.nodeType === 1 && container.matches && container.matches('[data-modal-root]')) {
    scopes.push(container);
  } else if (container && container.querySelectorAll) {
    scopes.push(...container.querySelectorAll('[data-modal-root]'));
  }
  if (!scopes.length) scopes.push(container && container.querySelector ? container : document);

  for (const scope of scopes) {
    if (!scope || !scope.querySelector) continue;

    const zaranda = scope.querySelector('#id_zaranda');
    if (!zaranda) continue;

    const campos = [
      '#id_IdZarandaGrupo1',
      '#id_IdZarandaGrupo2',
      '#id_IdZarandaGrupo3',
      '#id_IdZarandaGrupo4',
      '#id_IdZarandaGrupo5',
      '#id_peso_grupo1',
      '#id_peso_grupo2',
      '#id_peso_grupo3',
      '#id_peso_grupo4',
      '#id_peso_grupo5'
    ];

    function lockSelect(field, lock) {
      if (lock) {
        field.setAttribute('readonly', 'readonly');
        field.setAttribute('aria-readonly', 'true');
        field.style.pointerEvents = 'none';
        field.classList.add('bg-gray-200', 'cursor-not-allowed');
        if (!field.hasAttribute('data-prev-tabindex')) {
          field.setAttribute('data-prev-tabindex', field.getAttribute('tabindex') || '');
        }
        field.setAttribute('tabindex', '-1');
      } else {
        field.removeAttribute('readonly');
        field.removeAttribute('aria-readonly');
        field.style.pointerEvents = '';
        field.classList.remove('bg-gray-200', 'cursor-not-allowed');
        const prev = field.getAttribute('data-prev-tabindex');
        if (prev === '') {
          field.removeAttribute('tabindex');
        } else if (prev !== null) {
          field.setAttribute('tabindex', prev);
        }
      }
    }

    function toggleCampos() {
      const enabled = !!zaranda.checked;
      campos.forEach(selector => {
        const field = scope.querySelector(selector);
        if (!field) return;

        if (field.tagName === 'SELECT') {
          lockSelect(field, !enabled);
        } else {
          field.readOnly = !enabled;
          if (!enabled) {
            field.setAttribute('readonly', 'readonly');
            field.classList.add('bg-gray-200', 'cursor-not-allowed');
          } else {
            field.removeAttribute('readonly');
            field.classList.remove('bg-gray-200', 'cursor-not-allowed');
          }
        }
      });
    }

    if (zaranda.dataset.zarandaToggleInit !== '1') {
      zaranda.addEventListener('change', toggleCampos);
      zaranda.dataset.zarandaToggleInit = '1';
    }

    toggleCampos();
  }
}

window.initSeleccionVerdeZaranda = initSeleccionVerdeZaranda;


function initSeleccionVerdeCamposDependientes(container) {
  const scopes = [];
  if (container && container.nodeType === 1 && container.matches && container.matches('[data-modal-root]')) {
    scopes.push(container);
  } else if (container && container.querySelectorAll) {
    scopes.push(...container.querySelectorAll('[data-modal-root]'));
  }
  if (!scopes.length) scopes.push(container && container.querySelector ? container : document);

  const relaciones = [
    ['#id_catacion_ripio', '#id_peso_cat_ripio'],
    ['#id_catacion_balsos', '#id_peso_cat_balsos'],
    ['#id_catacion_grupo1', '#id_peso_cat_grupo1'],
    ['#id_catacion_grupo2', '#id_peso_cat_grupo2'],
    ['#id_medir_humedad', '#id_humedad'],
    ['#id_medir_densidad', '#id_densidad']
  ];

  for (const scope of scopes) {
    if (!scope || !scope.querySelector) continue;

    relaciones.forEach(function(relacion) {
      const checkbox = scope.querySelector(relacion[0]);
      const campo = scope.querySelector(relacion[1]);
      if (!checkbox || !campo) return;

      if (!campo.dataset.seleccionVerdePermisoDetectado) {
        campo.dataset.bloqueadoPorPermiso =
          campo.disabled && campo.dataset.medicionClienteBloqueada !== '1' ? '1' : '0';
        campo.dataset.seleccionVerdePermisoDetectado = '1';
      }
      const campoBloqueadoPorPermiso = campo.dataset.bloqueadoPorPermiso === '1';
      function sincronizar(limpiarAlDesmarcar) {
        const bloqueadoPorCliente = scope.dataset.medicionesClienteBloqueadas === '1';
        const habilitado = checkbox.checked && !checkbox.disabled && !campoBloqueadoPorPermiso && !bloqueadoPorCliente;
        campo.disabled = !habilitado;
        campo.classList.toggle('bg-gray-200', !habilitado);
        campo.classList.toggle('cursor-not-allowed', !habilitado);
        if (limpiarAlDesmarcar && !checkbox.checked) campo.value = '';
      }

      if (checkbox.dataset.seleccionVerdeDependienteInit !== '1') {
        checkbox.addEventListener('change', function() {
          sincronizar(true);
        });
        checkbox.dataset.seleccionVerdeDependienteInit = '1';
      }

      sincronizar(false);
    });
  }
}

window.initSeleccionVerdeCamposDependientes = initSeleccionVerdeCamposDependientes;


function initSeleccionTuesteValidations(container) {
  const scopes = [];
  if (container && container.nodeType === 1 && container.matches && container.matches('[data-modal-root]')) {
    scopes.push(container);
  } else if (container && container.querySelectorAll) {
    scopes.push(...container.querySelectorAll('[data-modal-root]'));
  }
  if (!scopes.length) scopes.push(container && container.querySelector ? container : document);

  for (const scope of scopes) {
    if (!scope || !scope.querySelector) continue;

    const catQuaker = scope.querySelector('#id_cat_quaker');
    const pesoQuaker = scope.querySelector('#id_peso_quaker');
    const groupConfigs = [
      ['#id_cat_grupo1', '#id_desc_grupo1', '#id_peso_grupo1'],
      ['#id_cat_grupo2', '#id_desc_grupo2', '#id_peso_grupo2'],
      ['#id_cat_grupo3', '#id_desc_grupo3', '#id_peso_grupo3']
    ];

    function setFieldEnabled(field, enabled, blockedByPermission) {
      if (!field) return;
      const shouldEnable = enabled && !blockedByPermission;
      field.disabled = !shouldEnable;
      if (shouldEnable) {
        field.classList.remove('bg-gray-100', 'text-gray-500', 'cursor-not-allowed');
      } else {
        field.classList.add('bg-gray-100', 'text-gray-500', 'cursor-not-allowed');
      }
    }

    const pesoQuakerBlockedByPermission = !!(pesoQuaker && pesoQuaker.disabled);

    function syncQuaker(clearWhenUnchecked) {
      if (!catQuaker || !pesoQuaker) return;
      const enabled = !!catQuaker.checked;
      if (clearWhenUnchecked && !enabled && !pesoQuakerBlockedByPermission) pesoQuaker.value = '';
      setFieldEnabled(pesoQuaker, enabled, pesoQuakerBlockedByPermission);
      pesoQuaker.required = enabled && !pesoQuakerBlockedByPermission;

      const peso = parseFloat(String(pesoQuaker.value || '').replace(',', '.'));
      if (pesoQuaker.required && (!peso || peso <= 0)) {
        pesoQuaker.setCustomValidity('Debe ingresar un peso mayor a 0 cuando Cat. Quaker está marcado.');
      } else {
        pesoQuaker.setCustomValidity('');
      }
    }

    function bindGroupToggle(toggleSelector, descSelector, weightSelector) {
      const toggle = scope.querySelector(toggleSelector);
      const desc = scope.querySelector(descSelector);
      const weight = scope.querySelector(weightSelector);
      if (!toggle || !desc || !weight) return;
      const descBlockedByPermission = desc.disabled;
      const weightBlockedByPermission = weight.disabled;

      function sync(clearWhenUnchecked) {
        const enabled = !!toggle.checked;
        if (clearWhenUnchecked && !enabled) {
          if (!descBlockedByPermission) desc.value = '';
          if (!weightBlockedByPermission) weight.value = '';
        }
        setFieldEnabled(desc, enabled, descBlockedByPermission);
        setFieldEnabled(weight, enabled, weightBlockedByPermission);
        desc.required = enabled && !descBlockedByPermission;
        if (desc.required && !String(desc.value || '').trim()) {
          desc.setCustomValidity('Este campo es obligatorio cuando el grupo está marcado.');
        } else {
          desc.setCustomValidity('');
        }
      }

      if (toggle.dataset.seleccionTuesteToggleInit !== '1') {
        toggle.addEventListener('change', function() { sync(true); });
        toggle.dataset.seleccionTuesteToggleInit = '1';
      }
      if (desc.dataset.seleccionTuesteDescInit !== '1') {
        desc.addEventListener('input', function() { sync(false); });
        desc.addEventListener('change', function() { sync(false); });
        desc.dataset.seleccionTuesteDescInit = '1';
      }

      sync(false);
    }

    if (catQuaker && pesoQuaker) {
      if (catQuaker.dataset.seleccionTuesteQuakerInit !== '1') {
        catQuaker.addEventListener('change', function() { syncQuaker(true); });
        catQuaker.dataset.seleccionTuesteQuakerInit = '1';
      }
      if (pesoQuaker.dataset.seleccionTuestePesoInit !== '1') {
        pesoQuaker.addEventListener('input', function() { syncQuaker(false); });
        pesoQuaker.addEventListener('change', function() { syncQuaker(false); });
        pesoQuaker.dataset.seleccionTuestePesoInit = '1';
      }
      syncQuaker(false);
    }

    groupConfigs.forEach(function (config) {
      bindGroupToggle(config[0], config[1], config[2]);
    });
  }
}

window.initSeleccionTuesteValidations = initSeleccionTuesteValidations;


function initOrdenEmpaqueToggle(container) {
  const scopes = [];
  if (container && container.nodeType === 1 && container.matches && container.matches('[data-modal-root]')) {
    scopes.push(container);
  } else if (container && container.querySelectorAll) {
    scopes.push(...container.querySelectorAll('[data-modal-root]'));
  }
  if (!scopes.length) scopes.push(container && container.querySelector ? container : document);

  for (const scope of scopes) {
    if (!scope || !scope.querySelector) continue;

    const trabajoEmpaque = scope.querySelector('#id_trabajo_empaque');
    const extraBlock = scope.querySelector('[data-orden-empaque-extra]');
    const grid = scope.querySelector('[data-detalle-empaque-grid]');
    const body = scope.querySelector('[data-detalle-empaque-body]');
    const totalForms = scope.querySelector('#id_detalle_empaque-TOTAL_FORMS');
    const emptyTemplate = scope.querySelector('template[data-detalle-empaque-empty-form]');

    if (!extraBlock || !trabajoEmpaque || !grid || !body || !totalForms || !emptyTemplate) continue;

    function getRows() {
      return Array.from(body.querySelectorAll('[data-detalle-empaque-row]'));
    }

    function rowHasPersistentId(row) {
      const hiddenId = row.querySelector('input[name$="-id"]');
      return !!String(hiddenId && hiddenId.value ? hiddenId.value : '').trim();
    }

    function rowHasValues(row) {
      const fields = row.querySelectorAll('select, input[type="number"]');
      return Array.from(fields).some(function (field) {
        return !!String(field.value || '').trim();
      });
    }

    function updateRowState(row, index) {
      const indexCell = row.querySelector('[data-detalle-empaque-index]');

      if (indexCell) {
        indexCell.textContent = String(index + 1);
      }
    }

    function refreshRows() {
      getRows().forEach(function (row, index) {
        updateRowState(row, index);
      });
    }

    function appendEmptyRow() {
      const nextIndex = parseInt(totalForms.value || '0', 10) || 0;
      const html = emptyTemplate.innerHTML.replace(/__prefix__/g, String(nextIndex));
      body.insertAdjacentHTML('beforeend', html);
      totalForms.value = String(nextIndex + 1);
      refreshRows();
    }

    function ensureTrailingBlankRow() {
      const rows = getRows();

      if (!rows.length) {
        appendEmptyRow();
        return;
      }

      const lastRow = rows[rows.length - 1];
      if (rowHasPersistentId(lastRow) || rowHasValues(lastRow)) {
        appendEmptyRow();
      } else {
        refreshRows();
      }
    }

    function sync() {
      const shouldShow = !!trabajoEmpaque.checked;

      extraBlock.classList.toggle('hidden', !shouldShow);

      if (shouldShow) {
        ensureTrailingBlankRow();
      }
    }

    if (trabajoEmpaque.dataset.ordenEmpaqueToggleInit !== '1') {
      trabajoEmpaque.addEventListener('change', sync);
      trabajoEmpaque.dataset.ordenEmpaqueToggleInit = '1';
    }

    if (body.dataset.detalleEmpaqueInit !== '1') {
      body.addEventListener('input', function (event) {
        const row = event.target && event.target.closest ? event.target.closest('[data-detalle-empaque-row]') : null;
        if (!row) return;

        refreshRows();
        if (trabajoEmpaque.checked) {
          ensureTrailingBlankRow();
        }
      });

      body.addEventListener('change', function (event) {
        const row = event.target && event.target.closest ? event.target.closest('[data-detalle-empaque-row]') : null;
        if (!row) return;

        refreshRows();
        if (trabajoEmpaque.checked) {
          ensureTrailingBlankRow();
        }
      });

      body.dataset.detalleEmpaqueInit = '1';
    }

    refreshRows();
    sync();
  }
}

window.initOrdenEmpaqueToggle = initOrdenEmpaqueToggle;


function initEmpaqueOrderToggle(container) {
  const scopes = [];
  if (container && container.nodeType === 1 && container.matches && container.matches('[data-modal-root]')) {
    scopes.push(container);
  } else if (container && container.querySelectorAll) {
    scopes.push(...container.querySelectorAll('[data-modal-root]'));
  }
  if (!scopes.length) scopes.push(container && container.querySelector ? container : document);

  for (const scope of scopes) {
    if (!scope || !scope.querySelector) continue;

    const orderSelect = scope.querySelector('select[name="orden"], select#id_orden');
    const orderSections = Array.from(scope.querySelectorAll('[data-orden-empaque-section]'));
    if (!orderSelect || !orderSections.length) continue;

    function syncSection() {
      const option = orderSelect.options[orderSelect.selectedIndex];
      const value = option ? option.getAttribute('data-trabajo-empaque') : null;
      const shouldShow = value === '1';
      orderSections.forEach((section) => section.classList.toggle('hidden', !shouldShow));
    }

    orderSelect.addEventListener('change', syncSection);
    syncSection();
  }
}

window.initEmpaqueOrderToggle = initEmpaqueOrderToggle;


function initEmpaqueDetalleGrid(container) {
  const scopes = [];
  if (container && container.nodeType === 1 && container.matches && container.matches('[data-modal-root]')) {
    scopes.push(container);
  } else if (container && container.querySelectorAll) {
    scopes.push(...container.querySelectorAll('[data-modal-root]'));
  }
  if (!scopes.length) scopes.push(container && container.querySelector ? container : document);

  for (const scope of scopes) {
    if (!scope || !scope.querySelector) continue;

    const grid = scope.querySelector('[data-empaque-detalle-grid]');
    if (!grid || grid.dataset.empaqueDetalleInit === '1') continue;

    const body = grid.querySelector('[data-empaque-detalle-body]');
    const totalForms = grid.querySelector('#id_detalle_empaque-TOTAL_FORMS');
    const template = grid.querySelector('template[data-empaque-detalle-template]');
    const addButton = grid.querySelector('[data-empaque-detalle-add]');

    if (!body || !totalForms || !template || !addButton) continue;

    function rows() {
      return Array.from(body.querySelectorAll('[data-empaque-detalle-row]'));
    }

    function visibleRows() {
      return rows().filter(function (row) {
        return !row.classList.contains('hidden');
      });
    }

    function syncEmpacadoTotal() {
      const totalField = scope.querySelector('#id_emp_clientes');
      if (!totalField) return;

      const total = visibleRows().reduce(function (sum, row) {
        const field = row.querySelector('input[name$="-empacado"]');
        if (!field || field.disabled) return sum;
        const value = parseInt(field.value || '0', 10);
        return sum + (Number.isNaN(value) ? 0 : value);
      }, 0);

      totalField.value = String(total);
    }

    function refreshIndexes() {
      visibleRows().forEach(function (row, index) {
        const indexCell = row.querySelector('[data-empaque-detalle-index]');
        if (indexCell) indexCell.textContent = String(index + 1);
      });
    }

    function appendRow() {
      const nextIndex = parseInt(totalForms.value || '0', 10) || 0;
      const html = template.innerHTML.replace(/__prefix__/g, String(nextIndex));
      body.insertAdjacentHTML('beforeend', html);
      totalForms.value = String(nextIndex + 1);
      refreshIndexes();
      syncEmpacadoTotal();
    }

    function removeRow(row) {
      const deleteInput = row.querySelector('input[name$="-DELETE"]');
      if (deleteInput) deleteInput.checked = true;

      row.classList.add('hidden');
      row.setAttribute('aria-hidden', 'true');

      row.querySelectorAll('input, select, textarea').forEach(function (field) {
        if (field === deleteInput) return;
        field.disabled = true;
      });

      if (!visibleRows().length) {
        appendRow();
      } else {
        refreshIndexes();
        syncEmpacadoTotal();
      }
    }

    addButton.addEventListener('click', function () {
      appendRow();
    });

    body.addEventListener('click', function (event) {
      const button = event.target && event.target.closest ? event.target.closest('[data-empaque-detalle-remove]') : null;
      if (!button) return;
      const row = button.closest('[data-empaque-detalle-row]');
      if (!row) return;
      removeRow(row);
    });

    body.addEventListener('input', function (event) {
      const target = event.target;
      if (!target || !target.matches || !target.matches('input[name$="-empacado"]')) return;
      syncEmpacadoTotal();
    });

    body.addEventListener('change', function (event) {
      const target = event.target;
      if (!target || !target.matches || !target.matches('input[name$="-empacado"]')) return;
      syncEmpacadoTotal();
    });

    if (!visibleRows().length) {
      appendRow();
    } else {
      refreshIndexes();
      syncEmpacadoTotal();
    }

    grid.dataset.empaqueDetalleInit = '1';
  }
}

window.initEmpaqueDetalleGrid = initEmpaqueDetalleGrid;


function syncEmpaqueEmpacadoTotal(scope) {
  if (!scope || !scope.querySelector) return;

  const grid = scope.querySelector('[data-empaque-detalle-grid]');
  const totalField = scope.querySelector('#id_emp_clientes');
  if (!grid || !totalField) return;

  const rows = Array.from(grid.querySelectorAll('[data-empaque-detalle-row]')).filter(function (row) {
    return !row.classList.contains('hidden');
  });

  const total = rows.reduce(function (sum, row) {
    const field = row.querySelector('input[name$="-empacado"]');
    if (!field || field.disabled) return sum;
    const value = parseInt(field.value || '0', 10);
    return sum + (Number.isNaN(value) ? 0 : value);
  }, 0);

  totalField.value = String(total);
}


function syncEmpaqueEmpacadoTotalFromEventTarget(target) {
  if (!target || !target.closest) return;
  const modal = target.closest('[data-modal-root]');
  if (!modal) return;
  syncEmpaqueEmpacadoTotal(modal);
}


window.syncEmpaqueEmpacadoTotal = syncEmpaqueEmpacadoTotal;


// Recalcular en tiempo real (delegado) cuando cambien los pesos dentro de un modal
document.addEventListener(
  'input',
  function (e) {
    const t = e.target;
    if (!t || !t.closest) return;
    const modal = t.closest('[data-modal-root]');
    if (!modal) return;
    if (
      t.matches(
        'input[name="peso_cafe_neto"], input[name="peso_cafe_bruto"], input[name="peso_cafe_verde"], input[name="peso_cafe_vede_total"], input[name="peso_cafe_verde_total"], input[name="peso_cafe_tostado_total"], #id_peso_cafe_neto, #id_peso_cafe_bruto, #id_peso_cafe_verde, #id_peso_cafe_vede_total, #id_peso_cafe_verde_total, #id_peso_cafe_tostado_total'
      )
    ) {
      initRendimientoCalc(modal);
    }

    if (t.matches('input[name$="-empacado"]')) {
      syncEmpaqueEmpacadoTotal(modal);
    }
  },
  true
);

document.addEventListener(
  'change',
  function (e) {
    const t = e.target;
    if (!t || !t.matches) return;
    if (t.matches('input[name$="-empacado"]')) {
      syncEmpaqueEmpacadoTotalFromEventTarget(t);
    }
  },
  true
);

document.addEventListener(
  'blur',
  function (e) {
    const t = e.target;
    if (!t || !t.matches) return;
    if (t.matches('input[name$="-empacado"]')) {
      syncEmpaqueEmpacadoTotalFromEventTarget(t);
    }
  },
  true
);

// Bloquear edición manual aunque el usuario haga foco directo
document.addEventListener(
  'focusin',
  function (e) {
    const t = e.target;
    if (!t || !t.matches) return;
    if (t.matches('input[name="rendimiento"]:not([type="hidden"]), #id_rendimiento')) {
      t.readOnly = true;
      t.setAttribute('readonly', 'readonly');
    }
  },
  true
);

// Inicializar cuando se inserte un modal en el DOM (AJAX)
const _rendMo = new MutationObserver(function (mutations) {
  for (const m of mutations) {
    for (const node of m.addedNodes) {
      if (!node || node.nodeType !== 1) continue;
      if (node.matches && node.matches('[data-modal-root]')) {
        initRendimientoCalc(node);
        initOrdenTrillaDefaults(node);
        initOrdenTuesteDefaults(node);
        initOrdenSeleccionTuesteDefaults(node);
        initOrdenSeleccionTostadoDefaults(node);
        initOrdenSeleccionVerdeDefaults(node);
        initSeleccionVerdeZaranda(node);
        initSeleccionVerdeCamposDependientes(node);
        initSeleccionTuesteValidations(node);
        initOrdenEmpaqueToggle(node);
        initEmpaqueDetalleGrid(node);
      } else if (node.querySelector) {
        const modal = node.querySelector('[data-modal-root]');
        if (modal) {
          initRendimientoCalc(modal);
          initOrdenTrillaDefaults(modal);
          initOrdenTuesteDefaults(modal);
          initOrdenSeleccionTuesteDefaults(modal);
          initOrdenSeleccionTostadoDefaults(modal);
          initOrdenSeleccionVerdeDefaults(modal);
          initSeleccionVerdeZaranda(modal);
          initSeleccionVerdeCamposDependientes(modal);
          initSeleccionTuesteValidations(modal);
          initOrdenEmpaqueToggle(modal);
          initEmpaqueOrderToggle(modal);
          initEmpaqueDetalleGrid(modal);
        }
      }
    }
  }
});

if (document.body) {
  _rendMo.observe(document.body, { childList: true, subtree: true });
}

document.addEventListener('DOMContentLoaded', function () {
  // Adjuntar el MutationObserver ahora que document.body existe
  if (document.body && !document.body.dataset.rendMoAttached) {
    _rendMo.observe(document.body, { childList: true, subtree: true });
    document.body.dataset.rendMoAttached = '1';
  }
  initRendimientoCalc(document);
  initOrdenTrillaDefaults(document);
  initOrdenTuesteDefaults(document);
  initOrdenSeleccionTuesteDefaults(document);
  initOrdenSeleccionTostadoDefaults(document);
  initOrdenSeleccionVerdeDefaults(document);
  initSeleccionVerdeZaranda(document);
  initSeleccionVerdeCamposDependientes(document);
  initSeleccionTuesteValidations(document);
  initOrdenEmpaqueToggle(document);
  initEmpaqueOrderToggle(document);
  initEmpaqueDetalleGrid(document);
  syncEmpaqueEmpacadoTotal(document);
});

// Compatibilidad con HTMX (contenido dinámico)
document.addEventListener('DOMContentLoaded', function () {
  if (document.body && document.body.addEventListener) {
    document.body.addEventListener('htmx:afterSwap', function (evt) {
      const target = evt && evt.target ? evt.target : document;
      initRendimientoCalc(target);
      calcularRendimiento(target);
      initOrdenTrillaDefaults(target);
      initOrdenTuesteDefaults(target);
      initOrdenSeleccionTuesteDefaults(target);
      initOrdenSeleccionTostadoDefaults(target);
      initOrdenSeleccionVerdeDefaults(target);
      initSeleccionVerdeZaranda(evt && evt.target ? evt.target : document);
      initSeleccionVerdeCamposDependientes(evt && evt.target ? evt.target : document);
      initSeleccionTuesteValidations(target);
      initOrdenEmpaqueToggle(target);
      initEmpaqueOrderToggle(target);
      initEmpaqueDetalleGrid(target);
      syncEmpaqueEmpacadoTotal(target);
    });
  }
});


document.addEventListener('submit', async function(e) {
  const form = e.target;
  if (!form.closest('[data-modal-root]')) return;
  if (form.matches('[data-modal-form]')) return;
  e.preventDefault();

  // Re-habilitar campos deshabilitados por catadora antes de serializar
  const catadoraToggled = ['#id_catacion_ripio','#id_peso_cat_ripio','#id_catacion_balsos','#id_peso_cat_balsos'];
  catadoraToggled.forEach(function(sel) {
    const el = form.querySelector(sel);
    if (el && el.disabled) el.disabled = false;
  });

  const url = form.getAttribute('action') || window.location.href;
  const method = form.getAttribute('method') || 'post';
  const target = form.closest('[data-modal-root]');
  const formData = new FormData(form);
  try {
    const resp = await fetch(url, {
      method: method.toUpperCase(),
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      body: formData
    });
    const html = await resp.text();
    // Validar que el HTML retornado contiene un modal
    if (/<div[^>]*data-modal-root/.test(html)) {
      target.outerHTML = html;
    } else {
      // Si no es modal, recargar la página principal
      window.location.reload();
    }
  } catch (err) {
    console.error('Error en submit AJAX modal:', err);
  }
});
