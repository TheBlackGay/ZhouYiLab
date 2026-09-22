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

document.addEventListener('keydown', event => {
  const tab = event.target.closest?.('[role="tab"]');
  if (!tab) return;
  const tabs = [...tab.parentElement.querySelectorAll('[role="tab"]')];
  if (!tabs.length || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  const current = tabs.indexOf(tab);
  const next = event.key === 'Home' ? 0
    : event.key === 'End' ? tabs.length - 1
      : (current + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
  tabs[next].click();
  tabs[next].focus();
});

window.addEventListener('resize', centerCurrentNavigation);
centerCurrentNavigation();
