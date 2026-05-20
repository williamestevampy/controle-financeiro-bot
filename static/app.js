// ── Service Worker ────────────────────────────────────────────────────────────
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/static/sw.js").catch(() => {});
}

// ── Animação de contagem KPI ──────────────────────────────────────────────────
function animateCount(el, target, duration = 800) {
  const start = performance.now();
  const fmt = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    const current = target * ease;
    el.textContent = "R$ " + fmt.format(current);
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = "R$ " + fmt.format(target);
  }
  requestAnimationFrame(step);
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-count]").forEach(el => {
    const target = parseFloat(el.dataset.count);
    if (!isNaN(target)) animateCount(el, target);
  });
});
