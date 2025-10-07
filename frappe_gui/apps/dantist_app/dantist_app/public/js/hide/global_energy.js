/* ========================================================================
   Global "Energy" / Leaderboard Cleanup (role-based, reusable)
   — Hides performance/energy widgets globally and leaderboard entry points
   — No route guard: applies across the app
   — Privileged role is always untouched
   ======================================================================== */
(function () {
  // ===== CONFIG (rename for other projects) =====
  const CONFIG = {
    privilegedRole: "System Manager",
    restrictedRoles: [
      "AIHub Super Admin", "AIHub Admin", "AIHub Demo",
      "AIHub User", "AIHub Manager", "AIHub Doctor", "AIHub Assistant",
      "Super Admin"
    ],
    lsKey: "rbac_hide_global_energy",
    cssId: "rbac-hide-global-energy-css",
    css: `
      .performance-graphs,
      .heatmap-container,
      .percentage-chart-container,
      .line-chart-container { display: none !important; }

      .user-profile-sidebar .user-stats-detail,
      .user-profile-sidebar .leaderboard-link { display: none !important; }

      a[href*="/app/leaderboard"],
      .sidebar-item a[href*="leaderboard"],
      .dropdown-menu a[href*="leaderboard"] { display: none !important; }
    `
  };

  // ===== ROLE HELPERS =====
  function current_roles() { return (window.frappe?.boot?.user?.roles) || []; }
  function is_privileged() {
    const roles = current_roles();
    if (window.frappe?.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.privilegedRole); } catch {} }
    return roles.includes(CONFIG.privilegedRole);
  }
  function in_restricted_group() { return current_roles().some(r => CONFIG.restrictedRoles.includes(r)); }
  function should_hide() { return in_restricted_group() && !is_privileged(); }

  // ===== ANTI-FLICKER CSS =====
  (function instant_hide() {
    try {
      if (localStorage.getItem(CONFIG.lsKey) !== "1") return;
      if (document.getElementById(CONFIG.cssId)) return;
      const s = document.createElement("style");
      s.id = CONFIG.cssId;
      s.textContent = CONFIG.css;
      document.documentElement.appendChild(s);
    } catch (_) {}
  })();

  // ===== DOM OPS =====
  function add_css_once() {
    if (document.getElementById(CONFIG.cssId)) return;
    const s = document.createElement("style");
    s.id = CONFIG.cssId;
    s.textContent = CONFIG.css;
    document.documentElement.appendChild(s);
  }
  function remove_css() { const css = document.getElementById(CONFIG.cssId); if (css) css.remove(); }

  function hide_energy_everywhere() {
    if (!should_hide()) return;
    document.querySelectorAll(
      ".performance-graphs, .heatmap-container, .percentage-chart-container, .line-chart-container," +
      ".user-profile-sidebar .user-stats-detail, .user-profile-sidebar .leaderboard-link," +
      'a[href*="/app/leaderboard"], .sidebar-item a[href*="leaderboard"], .dropdown-menu a[href*="leaderboard"]'
    ).forEach(el => { el.style.display = "none"; el.setAttribute("aria-hidden","true"); });
  }

  // ===== OBSERVER =====
  function observe_dom() {
    try {
      new MutationObserver(() => hide_energy_everywhere())
        .observe(document.documentElement, { subtree: true, childList: true });
    } catch (_) {}
  }

  // ===== BOOT =====
  function boot() {
    const hide = should_hide();
    try { localStorage.setItem(CONFIG.lsKey, hide ? "1" : "0"); } catch {}
    if (hide) { add_css_once(); hide_energy_everywhere(); observe_dom(); }
    else { remove_css(); }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
