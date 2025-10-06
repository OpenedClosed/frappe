/* ===== AIHub Topbar Hide (configurable) ===== */
(function () {
  const CONFIG = {
    systemManagerRole: "System Manager",
    aihubRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    lsKey: "aihub_hide_topbar",
    cssId: "aihub-hide-topbar-css",
    css: `
      .navbar .search-bar, .navbar .global-search, .navbar .search-input { display: none !important; }
      .dropdown-help, .navbar .dropdown-help, .navbar .dropdown .help-dropdown { display: none !important; }
    `
  };

  /* ===== Role checks ===== */
  function getRoles() {
    return (frappe.boot?.user?.roles) || [];
  }
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
  function shouldHide() {
    return hasAIHubRole() && !isSystemManager();
  }

  /* ===== Anti-flicker ===== */
  (function instantHide() {
    try {
      if (localStorage.getItem(CONFIG.lsKey) !== "1") return;
      if (document.getElementById(CONFIG.cssId)) return;
      const style = document.createElement("style");
      style.id = CONFIG.cssId;
      style.textContent = CONFIG.css;
      document.documentElement.appendChild(style);
    } catch (_) {}
  })();

  /* ===== DOM ops ===== */
  function addCssOnce() {
    if (document.getElementById(CONFIG.cssId)) return;
    const style = document.createElement("style");
    style.id = CONFIG.cssId;
    style.textContent = CONFIG.css;
    document.documentElement.appendChild(style);
  }
  function removeCss() {
    const css = document.getElementById(CONFIG.cssId);
    if (css) css.remove();
  }
  function hideDom() {
    const s = document.querySelector(".navbar .search-bar, .navbar .global-search, .navbar .search-input");
    if (s) { s.style.display = "none"; s.setAttribute("aria-hidden", "true"); }
    const h = document.querySelector(".dropdown-help, .navbar .dropdown-help, .navbar .dropdown .help-dropdown");
    if (h) {
      const n = h.closest(".dropdown, .nav-item") || h;
      n.style.display = "none";
      n.setAttribute("aria-hidden", "true");
    }
  }

  /* ===== Disable palette & hotkeys ===== */
  function disableHotkeysAndPalette() {
    const stop = e => { e.preventDefault(); e.stopPropagation(); };
    document.addEventListener("keydown", e => {
      const isMac = /Mac|iPhone|iPod|iPad/.test(navigator.platform);
      const mod = isMac ? e.metaKey : e.ctrlKey;
      const k = (e.key || "").toLowerCase();
      if (mod && (k === "k" || k === "g")) stop(e);
    }, true);

    if (frappe.search) {
      if (typeof frappe.search.open === "function") frappe.search.open = () => {};
      if (frappe.search.utils && typeof frappe.search.utils.show === "function") frappe.search.utils.show = () => {};
    }
  }

  /* ===== Observers ===== */
  function observeDom() {
    new MutationObserver(() => hideDom()).observe(document.documentElement, { subtree: true, childList: true });
  }

  /* ===== Boot ===== */
  function boot() {
    const hide = shouldHide();
    try { localStorage.setItem(CONFIG.lsKey, hide ? "1" : "0"); } catch {}
    if (hide) { addCssOnce(); hideDom(); disableHotkeysAndPalette(); observeDom(); }
    else { removeCss(); }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
