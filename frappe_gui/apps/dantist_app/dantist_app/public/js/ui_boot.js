// Оркестратор
(() => {
  function kick() {
    try { window.dantist_apply_role_flags?.(); } catch {}
    try { window.dantist_ui_cleanup?.(); } catch {}
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', kick, { once: true });
  else kick();

  frappe?.router?.on?.('change', () => setTimeout(kick, 0));
  frappe?.after_ajax && frappe.after_ajax(() => setTimeout(kick, 0));

  window.ui_boot_ping = kick;
})();
