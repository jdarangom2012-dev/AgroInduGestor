(function () {
  'use strict';

  function formatValue(value) {
    const numericValue = Number(value);
    return Number.isInteger(numericValue)
      ? String(numericValue)
      : numericValue.toFixed(1).replace('.', ',');
  }

  function intensityLevel(value) {
    const numericValue = Number(value);
    if (numericValue <= 5) return 'Baja';
    if (numericValue <= 10) return 'Media';
    return 'Alta';
  }

  function updateHeatmap(input, output) {
    const min = Number(input.min || 0);
    const max = Number(input.max || 15);
    const value = Number(input.value || min);
    const percentage = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
    const hue = Math.round(120 - (percentage * 1.2));
    const color = `hsl(${hue} 78% 42%)`;

    input.style.setProperty('--sensory-color', color);
    input.style.background = `linear-gradient(to right, ${color} 0%, ${color} ${percentage}%, #d1d5db ${percentage}%, #d1d5db 100%)`;
    const level = intensityLevel(value);
    input.setAttribute('aria-valuetext', `${formatValue(value)} de 15, intensidad ${level}`);
    output.textContent = `${formatValue(value)} · ${level}`;
    output.style.backgroundColor = color;
  }

  function updateTotal(form) {
    const totalInput = form.querySelector('[data-sensory-total]');
    if (!totalInput) return;

    const total = Array.from(form.querySelectorAll('[data-sensory-score]')).reduce(
      function (sum, field) { return sum + (Number(field.value) || 0); },
      0
    );
    totalInput.value = Number.isInteger(total)
      ? total.toFixed(0)
      : total.toFixed(1).replace('.', ',');
  }

  function initializeScore(form) {
    if (form.dataset.sensoryScoreReady === 'true') {
      updateTotal(form);
      return;
    }

    form.querySelectorAll('[data-sensory-score]').forEach(function (field) {
      field.addEventListener('input', function () { updateTotal(form); });
      field.addEventListener('change', function () { updateTotal(form); });
    });
    form.dataset.sensoryScoreReady = 'true';
    updateTotal(form);
  }

  function enhance(input) {
    if (input.dataset.heatmapReady === 'true') return;

    if (!input.hasAttribute('value')) input.value = input.min || '0';

    const legend = document.createElement('div');
    legend.className = 'sensory-heatmap-legend';
    legend.setAttribute('aria-hidden', 'true');
    legend.innerHTML = [
      '<span><strong>Baja</strong><small>1–5</small></span>',
      '<span><strong>Media</strong><small>5–10</small></span>',
      '<span><strong>Alta</strong><small>10–15</small></span>',
    ].join('');
    input.insertAdjacentElement('beforebegin', legend);

    const output = document.createElement('output');
    output.className = 'sensory-heatmap-value';
    output.setAttribute('for', input.id);
    output.setAttribute('aria-live', 'polite');
    input.insertAdjacentElement('afterend', output);

    const refresh = function () { updateHeatmap(input, output); };
    input.addEventListener('input', refresh);
    input.addEventListener('change', refresh);
    input.dataset.heatmapReady = 'true';
    refresh();
  }

  function initialize(root) {
    if (root.matches && root.matches('input[data-sensory-heatmap]')) enhance(root);
    if (root.querySelectorAll) {
      root.querySelectorAll('input[data-sensory-heatmap]').forEach(enhance);
    }
    if (root.matches && root.matches('form') && root.querySelector('[data-sensory-total]')) {
      initializeScore(root);
    }
    if (root.querySelectorAll) {
      root.querySelectorAll('form').forEach(function (form) {
        if (form.querySelector('[data-sensory-total]')) initializeScore(form);
      });
    }
  }

  function start() {
    initialize(document);
    new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        mutation.addedNodes.forEach(function (node) {
          if (node.nodeType === Node.ELEMENT_NODE) initialize(node);
        });
      });
    }).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
}());
