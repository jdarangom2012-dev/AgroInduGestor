(function () {
  'use strict';

  const MIN_DRAG_WIDTH = 768;
  const VIEWPORT_MARGIN = 8;

  function initializeDraggableModal(root) {
    if (!root || root.dataset.modalDragReady === '1') return;

    const modal = root.firstElementChild;
    const handle = modal && modal.querySelector('.modal-head');
    if (!modal || !handle) return;

    root.dataset.modalDragReady = '1';
    handle.style.cursor = 'grab';
    handle.style.touchAction = 'none';

    let offsetX = 0;
    let offsetY = 0;
    let startX = 0;
    let startY = 0;
    let startOffsetX = 0;
    let startOffsetY = 0;
    let dragging = false;

    function applyPosition() {
      modal.style.transform = `translate3d(${offsetX}px, ${offsetY}px, 0)`;
    }

    handle.addEventListener('pointerdown', function (event) {
      if (window.innerWidth < MIN_DRAG_WIDTH || event.button !== 0) return;
      if (event.target.closest('button, a, input, select, textarea, label')) return;

      dragging = true;
      startX = event.clientX;
      startY = event.clientY;
      startOffsetX = offsetX;
      startOffsetY = offsetY;
      handle.style.cursor = 'grabbing';
      handle.setPointerCapture(event.pointerId);
      event.preventDefault();
    });

    handle.addEventListener('pointermove', function (event) {
      if (!dragging) return;

      const proposedX = startOffsetX + event.clientX - startX;
      const proposedY = startOffsetY + event.clientY - startY;
      const rect = modal.getBoundingClientRect();
      const deltaX = proposedX - offsetX;
      const deltaY = proposedY - offsetY;
      const availableWidth = window.innerWidth - VIEWPORT_MARGIN * 2;
      const availableHeight = window.innerHeight - VIEWPORT_MARGIN * 2;

      if (rect.width <= availableWidth) {
        const left = Math.min(
          Math.max(rect.left + deltaX, VIEWPORT_MARGIN),
          window.innerWidth - VIEWPORT_MARGIN - rect.width
        );
        offsetX += left - rect.left;
      }
      if (rect.height <= availableHeight) {
        const top = Math.min(
          Math.max(rect.top + deltaY, VIEWPORT_MARGIN),
          window.innerHeight - VIEWPORT_MARGIN - rect.height
        );
        offsetY += top - rect.top;
      }
      applyPosition();
    });

    function stopDragging(event) {
      if (!dragging) return;
      dragging = false;
      handle.style.cursor = 'grab';
      if (handle.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId);
    }

    handle.addEventListener('pointerup', stopDragging);
    handle.addEventListener('pointercancel', stopDragging);

    window.addEventListener('resize', function () {
      if (window.innerWidth >= MIN_DRAG_WIDTH) return;
      offsetX = 0;
      offsetY = 0;
      applyPosition();
    });
  }

  function scan(node) {
    if (!(node instanceof Element)) return;
    if (node.matches('[data-modal-root]')) initializeDraggableModal(node);
    node.querySelectorAll('[data-modal-root]').forEach(initializeDraggableModal);
  }

  function start() {
    scan(document.body);
    new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        mutation.addedNodes.forEach(scan);
      });
    }).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
