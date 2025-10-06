/* ===== AIHub User Profile Hide (configurable) ===== */
(function () {
  const CONFIG = {
    systemManagerRole: "System Manager",
    aihubRoles: [
      "AIHub Super Admin", "AIHub Admin", "AIHub Demo",
      "AIHub User", "AIHub Manager", "AIHub Doctor", "AIHub Assistant",
      "Super Admin"
    ],
    lsKey: "aihub_hide_user_profile",
    cssId: "aihub-hide-user-profile-css",
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

  /* ===== Route check ===== */
  function onUserProfileRoute() {
    const r = (frappe.get_route && frappe.get_route()) || [];
    if (r.join("/").toLowerCase().includes("user-profile")) return true;
    const dr = document.body?.getAttribute("data-route") || "";
    return dr.toLowerCase().includes("user-profile");
  }

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
    if (!shouldHide() || !onUserProfileRoute()) return;

    document.querySelectorAll(
      ".performance-graphs, .heatmap-container, .percentage-chart-container, .line-chart-container"
    ).forEach(el => { el.style.display = "none"; el.setAttribute("aria-hidden","true"); });

    document.querySelectorAll(
      ".user-profile-sidebar .user-image-container, .user-profile-sidebar .user-stats-detail, .user-profile-sidebar .leaderboard-link"
    ).forEach(el => { el.style.display = "none"; el.setAttribute("aria-hidden","true"); });

    document.querySelectorAll(
      '.page-actions [data-label*="Change User" i], button.btn[data-label*="Change User" i]'
    ).forEach(btn => { btn.style.display = "none"; btn.setAttribute("aria-hidden","true"); });

    Array.from(document.querySelectorAll(".page-actions .btn, .page-actions .btn-sm, .page-actions button")).forEach(btn => {
      const t = (btn.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
      if (t.includes("change user")) { btn.style.display = "none"; btn.setAttribute("aria-hidden","true"); }
    });
  }

  /* ===== Observers / Router ===== */
  function observeDom() {
    new MutationObserver(() => hideDom()).observe(document.documentElement, { subtree: true, childList: true });
  }
  function hookRouter() { if (frappe?.router?.on) frappe.router.on("change", hideDom); }

  /* ===== Boot ===== */
  function boot() {
    const hide = shouldHide();
    try { localStorage.setItem(CONFIG.lsKey, hide ? "1" : "0"); } catch {}
    if (hide) { addCssOnce(); hideDom(); observeDom(); hookRouter(); }
    else { removeCss(); }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
