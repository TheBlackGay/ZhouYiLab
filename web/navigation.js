function centerNavigationItem(container) {
  const active = container.querySelector('[aria-current="page"], [aria-selected="true"]');
  if (!active || container.scrollWidth <= container.clientWidth) return;
  const left = active.offsetLeft - (container.clientWidth - active.offsetWidth) / 2;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  container.scrollTo({ left: Math.max(0, left), behavior: reducedMotion ? 'auto' : 'smooth' });
}

function centerCurrentNavigation() {
  document.querySelectorAll('.primary-tabs, .secondary-tabs').forEach(centerNavigationItem);
}

document.addEventListener('click', event => {
  if (event.target.closest('.primary-tabs a, .secondary-tabs a, .secondary-tabs button')) {
    requestAnimationFrame(centerCurrentNavigation);
  }
});

window.addEventListener('resize', centerCurrentNavigation);
centerCurrentNavigation();
