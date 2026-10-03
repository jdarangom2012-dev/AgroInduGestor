(function () {
  'use strict';

  function formatValue(value) {
    const numericValue = Number(value);
    return Number.isInteger(numericValue)
      ? String(numericValue)
      : numericValue.toFixed(1).replace('.', ',');
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
    input.setAttribute('aria-valuetext', `${formatValue(value)} de 15`);
    output.textContent = formatValue(value);
    output.style.backgroundColor = color;
  }

  function enhance(input) {
    if (input.dataset.heatmapReady === 'true') return;

    if (!input.hasAttribute('value')) input.value = input.min || '0';

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
