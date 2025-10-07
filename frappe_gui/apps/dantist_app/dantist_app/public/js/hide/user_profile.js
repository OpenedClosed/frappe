/* ========================================================================
   User Profile Cleanup (role-based, reusable)
   — Hides performance graphs, heatmaps, charts and extra sidebar stats
   — Hides "Change User" action
   — Route guard: applies only on user-profile pages
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
    lsKey: "rbac_hide_user_profile",
    cssId: "rbac-hide-user-profile-css",
    css: `
      body[data-route*="user-profile"] .performance-graphs { display: none !important; }
      body[data-route*="user-profile"] .user-profile-sidebar .user-image-container { display: none !important; }
      body[data-route*="user-profile"] .user-profile-sidebar .user-stats-detail { display: none !important; }
      body[data-route*="user-profile"] .user-profile-sidebar .leaderboard-link { display: none !important; }
      body[data-route*="user-profile"] .heatmap-container,
      body[data-route*="user-profile"] .percentage-chart-container,
      body[data-route*="user-profile"] .line-chart-container { display: none !important; }
      body[data-route*="user-profile"] .page-actions [data-label*="Change User" i],
      body[data-route*="user-profile"] button.btn[data-label*="Change User" i] { display: none !important; }
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

  // ===== ROUTE GUARD =====
  function on_user_profile_route() {
    const r = (window.frappe?.get_route && frappe.get_route()) || [];
    if (r.join("/").toLowerCase().includes("user-profile")) return true;
    const dr = document.body?.getAttribute("data-route") || "";
    return dr.toLowerCase().includes("user-profile");
  }

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

  function hide_user_profile_bits() {
    if (!should_hide() || !on_user_profile_route()) return;

    document.querySelectorAll(
      ".performance-graphs, .heatmap-container, .percentage-chart-container, .line-chart-container"
    ).forEach(el => { el.style.display = "none"; el.setAttribute("aria-hidden","true"); });

    document.querySelectorAll(
      ".user-profile-sidebar .user-image-container, .user-profile-sidebar .user-stats-detail, .user-profile-sidebar .leaderboard-link"
    ).forEach(el => { el.style.display = "none"; el.setAttribute("aria-hidden","true"); });

    document.querySelectorAll(
      '.page-actions [data-label*="Change User" i], button.btn[data-label*="Change User" i]'
    ).forEach(btn => { btn.style.display = "none"; btn.setAttribute("aria-hidden","true"); });

    Array.from(document.querySelectorAll(".page-actions .btn, .page-actions .btn-sm, .page-actions button"))
      .forEach(btn => {
        const t = (btn.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
        if (t.includes("change user")) { btn.style.display = "none"; btn.setAttribute("aria-hidden","true"); }
      });
  }

  // ===== OBSERVERS / ROUTER =====
  function observe_dom() {
    try {
      new MutationObserver(() => hide_user_profile_bits())
        .observe(document.documentElement, { subtree: true, childList: true });
    } catch (_) {}
  }
  function hook_router() { if (window.frappe?.router?.on) frappe.router.on("change", hide_user_profile_bits); }

  // ===== BOOT =====
  function boot() {
    const hide = should_hide();
    try { localStorage.setItem(CONFIG.lsKey, hide ? "1" : "0"); } catch {}
    if (hide) { add_css_once(); hide_user_profile_bits(); observe_dom(); hook_router(); }
    else { remove_css(); }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
