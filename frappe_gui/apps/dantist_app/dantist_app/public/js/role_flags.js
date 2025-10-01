// Навешиваем классы на <html>: is-admin / is-privileged / is-user
(() => {
  const HTML = document.documentElement;

  const DEFAULT_PRIV_ROLES = [
    'System Manager',
    'AIHub Super Admin',
    'AIHub Admin',
    'AIHub Demo Admin',
  ];

  const get_priv_roles = () => {
    const from_window = Array.isArray(window.DANTIST_PRIV_ROLES) ? window.DANTIST_PRIV_ROLES : [];
    return Array.from(new Set([...DEFAULT_PRIV_ROLES, ...from_window]));
  };

  const has_role = (role) => (frappe?.boot?.user?.roles || []).includes(role);
  const cur_user = () => frappe?.session?.user || 'Guest';

  function is_privileged() {
    const user = cur_user();
    if (user === 'Administrator') return true;
    const list = get_priv_roles();
    return list.some((r) => has_role(r) || r === user);
  }

  function apply() {
    const user = cur_user();
    const priv = is_privileged();

    HTML.classList.remove('is-admin', 'is-privileged', 'is-user');
    if (user === 'Administrator') HTML.classList.add('is-admin');
    if (priv) HTML.classList.add('is-privileged');
    if (!priv) HTML.classList.add('is-user');
  }

  const boot = () => { try { apply(); } catch {} };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();

  frappe?.router?.on?.('change', () => setTimeout(boot, 0));
  frappe?.after_ajax && frappe.after_ajax(() => setTimeout(boot, 0));

  window.dantist_apply_role_flags = boot;
})();
