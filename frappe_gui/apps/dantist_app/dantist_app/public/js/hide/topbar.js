/* ========================================================================
   Topbar Visibility Control (role-based, reusable)
   — Hides global search and Help dropdown for restricted roles
   — Disables search palette and hotkeys (Ctrl/Cmd+K, Ctrl/Cmd+G)
   — System Manager (or other privileged role) is always untouched
   ======================================================================== */
(function () {
  // ===== CONFIG (rename roles here for other projects) =====
  const CONFIG = {
    privilegedRole: "System Manager",
    restrictedRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    lsKey: "rbac_hide_topbar",
    cssId: "rbac-hide-topbar-css",
    css: `
      .navbar .search-bar,
      .navbar .global-search,
      .navbar .search-input { display: none !important; }

      .dropdown-help,
      .navbar .dropdown-help,
      .navbar .dropdown .help-dropdown { display: none !important; }
    `
  };

  // ===== ROLE HELPERS =====
  function current_roles() {
    return (window.frappe?.boot?.user?.roles) || [];
  }
  function is_privileged() {
    const roles = current_roles();
    if (window.frappe?.user && typeof frappe.user.has_role === "function") {
      try { return !!frappe.user.has_role(CONFIG.privilegedRole); } catch {}
    }
    return roles.includes(CONFIG.privilegedRole);
  }
  function in_restricted_group() {
    const roles = current_roles();
    return roles.some(r => CONFIG.restrictedRoles.includes(r));
  }
  function should_hide() {
    return in_restricted_group() && !is_privileged();
  }

  // ===== ANTI-FLICKER CSS =====
  (function instant_hide() {
    try {
      if (localStorage.getItem(CONFIG.lsKey) !== "1") return;
      if (document.getElementById(CONFIG.cssId)) return;
      const style = document.createElement("style");
      style.id = CONFIG.cssId;
      style.textContent = CONFIG.css;
      document.documentElement.appendChild(style);
    } catch (_) {}
  })();

  // ===== DOM OPS =====
  function add_css_once() {
    if (document.getElementById(CONFIG.cssId)) return;
    const style = document.createElement("style");
    style.id = CONFIG.cssId;
    style.textContent = CONFIG.css;
    document.documentElement.appendChild(style);
  }
  function remove_css() {
    const css = document.getElementById(CONFIG.cssId);
    if (css) css.remove();
  }
  function hide_topbar_bits() {
    const s = document.querySelector(".navbar .search-bar, .navbar .global-search, .navbar .search-input");
    if (s) { s.style.display = "none"; s.setAttribute("aria-hidden", "true"); }

    const help = document.querySelector(".dropdown-help, .navbar .dropdown-help, .navbar .dropdown .help-dropdown");
    if (help) {
      const container = help.closest(".dropdown, .nav-item") || help;
      container.style.display = "none";
      container.setAttribute("aria-hidden", "true");
    }
  }

  // ===== DISABLE SEARCH PALETTE & HOTKEYS =====
  function disable_palette_and_hotkeys() {
    const stop = e => { e.preventDefault(); e.stopPropagation(); };

    document.addEventListener("keydown", e => {
      const isMac = /Mac|iPhone|iPod|iPad/.test(navigator.platform);
      const mod = isMac ? e.metaKey : e.ctrlKey;
      const k = (e.key || "").toLowerCase();
      if (mod && (k === "k" || k === "g")) stop(e);
    }, true);

    if (window.frappe?.search) {
      try {
        if (typeof frappe.search.open === "function") frappe.search.open = () => {};
        if (frappe.search.utils && typeof frappe.search.utils.show === "function") {
          frappe.search.utils.show = () => {};
        }
      } catch (_) {}
    }
  }

  // ===== OBSERVERS =====
  function observe_dom() {
    try {
      new MutationObserver(() => hide_topbar_bits())
        .observe(document.documentElement, { subtree: true, childList: true });
    } catch (_) {}
  }

  // ===== BOOTSTRAP =====
  function boot() {
    const hide = should_hide();
    try { localStorage.setItem(CONFIG.lsKey, hide ? "1" : "0"); } catch {}
    if (hide) { add_css_once(); hide_topbar_bits(); disable_palette_and_hotkeys(); observe_dom(); }
    else { remove_css(); }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
