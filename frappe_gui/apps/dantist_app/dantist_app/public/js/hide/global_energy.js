/* ===== AIHub Global Energy Hide (configurable) ===== */
(function () {
  const CONFIG = {
    systemManagerRole: "System Manager",
    aihubRoles: [
      "AIHub Super Admin", "AIHub Admin", "AIHub Demo",
      "AIHub User", "AIHub Manager", "AIHub Doctor", "AIHub Assistant",
      "Super Admin"
    ],
    lsKey: "aihub_hide_global_energy",
    cssId: "aihub-hide-global-energy-css",
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

  /* ===== Role checks ===== */
  function getRoles() { return (frappe?.boot?.user?.roles) || []; }
  function isSystemManager() {
    const roles = getRoles();
    if (frappe.user && typeof frappe.user.has_role === "function") {
      try { return !!frappe.user.has_role(CONFIG.systemManagerRole); } catch {}
    }
    return roles.includes(CONFIG.systemManagerRole);
  }
  function hasAIHubRole() {
    const roles = getRoles();
    return roles.some(r => CONFIG.aihubRoles.includes(r));
  }
  function shouldHide() { return hasAIHubRole() && !isSystemManager(); }

  /* ===== Anti-flicker ===== */
  (function instantHide() {
    try {
      if (localStorage.getItem(CONFIG.lsKey) !== "1") return;
      if (document.getElementById(CONFIG.cssId)) return;
      const s = document.createElement("style");
      s.id = CONFIG.cssId;
      s.textContent = CONFIG.css;
      document.documentElement.appendChild(s);
    } catch (_) {}
  })();

  /* ===== DOM ops ===== */
  function addCssOnce() {
    if (document.getElementById(CONFIG.cssId)) return;
    const s = document.createElement("style");
    s.id = CONFIG.cssId;
    s.textContent = CONFIG.css;
    document.documentElement.appendChild(s);
  }
  function removeCss() {
    const css = document.getElementById(CONFIG.cssId);
    if (css) css.remove();
  }
  function hideDom() {
    if (!shouldHide()) return;
    document.querySelectorAll(
      ".performance-graphs, .heatmap-container, .percentage-chart-container, .line-chart-container," +
      ".user-profile-sidebar .user-stats-detail, .user-profile-sidebar .leaderboard-link," +
      'a[href*="/app/leaderboard"], .sidebar-item a[href*="leaderboard"], .dropdown-menu a[href*="leaderboard"]'
    ).forEach(el => { el.style.display = "none"; el.setAttribute("aria-hidden","true"); });
  }

  /* ===== Observer ===== */
  function observeDom() {
    new MutationObserver(() => hideDom()).observe(document.documentElement, { subtree: true, childList: true });
  }

  /* ===== Boot ===== */
  function boot() {
    const hide = shouldHide();
    try { localStorage.setItem(CONFIG.lsKey, hide ? "1" : "0"); } catch {}
    if (hide) { addCssOnce(); hideDom(); observeDom(); }
    else { removeCss(); }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
