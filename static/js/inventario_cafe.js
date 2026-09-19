// Vista previa del saldo; el servidor vuelve a calcularlo al guardar.
(function () {
  function cents(value) {
    const number = Number.parseFloat(String(value || '0').replace(',', '.'));
    return Number.isFinite(number) ? Math.round(number * 100) : 0;
  }

  function actualizarSaldo(form) {
    const saldo = form.querySelector('[data-cantidad-existente]');
    const cantidad = form.querySelector('[name="cantidad"]');
    const ingresar = form.querySelector('[name="kilos_ingresar"]');
    const sacar = form.querySelector('[name="kilos_sacar"]');
    if (!saldo || !ingresar || !sacar) return;

    let total;
    if (form.dataset.inventarioCafeForm === 'editar') {
      total = cents(form.dataset.saldoInicial)
        + cents(ingresar.value) - cents(form.dataset.kilosIngresarInicial)
        - cents(sacar.value) + cents(form.dataset.kilosSacarInicial);
    } else {
      total = cents(cantidad && cantidad.value) + cents(ingresar.value) - cents(sacar.value);
    }
    saldo.value = (total / 100).toFixed(2);
  }

  document.addEventListener('input', function (event) {
    const form = event.target.closest('[data-inventario-cafe-form]');
    if (form && ['cantidad', 'kilos_ingresar', 'kilos_sacar'].includes(event.target.name)) {
      actualizarSaldo(form);
    }
  });

  document.addEventListener('change', function (event) {
    const form = event.target.closest('[data-inventario-cafe-form]');
    if (form && ['cantidad', 'kilos_ingresar', 'kilos_sacar'].includes(event.target.name)) {
      actualizarSaldo(form);
    }
  });
})();
