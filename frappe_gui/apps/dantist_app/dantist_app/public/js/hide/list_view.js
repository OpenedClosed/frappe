/* ========================================================================
   List View Prune (instant + robust, role-based)
   — Hides: "⋯ Menu", view switcher (List/Report/Kanban), header Filter selector
   — For restricted roles: remove sidebar entirely (Admin/Demo)
   — For super role: keep sidebar but prune to Assigned To / Created By
   — Rows: hide comment/like counters for restricted & super roles
   — Privileged role is always (almost) untouched
   ======================================================================== */
(function () {
  // ===== CONFIG (rename for other projects) =====
  const CONFIG = {
    privilegedRole: "System Manager",
    restrictedRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    superRole: "AIHub Super Admin",

    cssId: "rbac-list-view-css",
    cssInstantId: "rbac-list-view-INSTANT-css",
    htmlClassRestricted: "rbac-list-restricted",
    htmlClassSuper: "rbac-list-super",

    keepGroupByFieldnamesForSuper: ["assigned_to", "owner"],
  };

  // ===== ROLES =====
  function roles() { return (window.frappe?.boot?.user?.roles) || []; }
  function is_privileged() {
    const r = roles();
    if (window.frappe?.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.privilegedRole); } catch {} }
    return r.includes(CONFIG.privilegedRole);
  }
  function in_restricted_group() { return roles().some(r => CONFIG.restrictedRoles.includes(r)); }
  function is_super() { return roles().includes(CONFIG.superRole); }
  function has_any_restriction() { return in_restricted_group() && !is_privileged(); }

  // ===== ROUTE GUARD =====
  function on_list_route() {
    const rt = (window.frappe?.get_route && frappe.get_route()) || [];
    if (rt[0] === "List") return true;
    const dr = document.body?.getAttribute("data-route") || "";
    return /^List\//i.test(dr);
  }

  // ===== INSTANT CSS (anti-flicker) =====
  const INSTANT_CSS = `
    /* Hide view switcher button early */
    .page-actions button:has(.custom-btn-group-label) { display: none !important; }
    /* Fallback when :has() unsupported */
    .page-actions .custom-btn-group-label { display: none !important; }

    /* Always hide the "liked-by-me" heart in the right header area */
    .level-right .list-liked-by-me { display: none !important; }
  `;

  // ===== BASE CSS (scoped by html classes) =====
  const BASE_CSS = `
    html.${CONFIG.htmlClassRestricted} ._hide,
    html.${CONFIG.htmlClassSuper} ._hide { display: none !important; }

    /* "⋯ Menu" group in list header — hide for restricted & super */
    html.${CONFIG.htmlClassRestricted} .page-actions .menu-btn-group,
    html.${CONFIG.htmlClassSuper} .page-actions .menu-btn-group { display: none !important; }

    /* Header filter selector — hide for restricted & super */
    html.${CONFIG.htmlClassRestricted} .filter-selector,
    html.${CONFIG.htmlClassSuper} .filter-selector { display: none !important; }

    /* Sidebar — hidden entirely for restricted (Admin/Demo) */
    html.${CONFIG.htmlClassRestricted} .layout-side-section,
    html.${CONFIG.htmlClassRestricted} .page-title .sidebar-toggle-btn { display: none !important; }

    /* For super: sidebar present but pruned */
    html.${CONFIG.htmlClassSuper} .list-sidebar .views-section,
    html.${CONFIG.htmlClassSuper} .list-sidebar .save-filter-section,
    html.${CONFIG.htmlClassSuper} .list-sidebar .user-actions { display: none !Important; }

    /* In Tags block keep only the stats list; drop extras */
    html.${CONFIG.htmlClassSuper} .list-sidebar .list-tags > :not(.list-stats) { display: none !important; }

    /* In Filter By hide extra sidebar-actions */
    html.${CONFIG.htmlClassSuper} .list-sidebar .filter-section .sidebar-action,
    html.${CONFIG.htmlClassSuper} .list-sidebar .filter-section .add-list-group-by,
    html.${CONFIG.htmlClassSuper} .list-sidebar .filter-section .add-group-by,
    html.${CONFIG.htmlClassSuper} .list-sidebar .filter-section .view-action { display: none !important; }

    /* In list rows: hide comment & like counters for restricted & super */
    html.${CONFIG.htmlClassRestricted} .list-row-activity .comment-count,
    html.${CONFIG.htmlClassRestricted} .list-row-activity .list-row-like,
    html.${CONFIG.htmlClassSuper} .list-row-activity .comment-count,
    html.${CONFIG.htmlClassSuper} .list-row-activity .list-row-like { display: none !important; }
  `;

  // ===== HELPERS =====
  function add_css_once(id, css) {
    if (document.getElementById(id)) return;
    const s = document.createElement("style");
    s.id = id;
    s.textContent = css;
    document.documentElement.appendChild(s);
  }

  function set_html_mode_none() {
    document.documentElement.classList.remove(CONFIG.htmlClassRestricted, CONFIG.htmlClassSuper);
  }
  function set_html_mode_restricted() {
    document.documentElement.classList.add(CONFIG.htmlClassRestricted);
    document.documentElement.classList.remove(CONFIG.htmlClassSuper);
  }
  function set_html_mode_super() {
    document.documentElement.classList.add(CONFIG.htmlClassSuper);
    document.documentElement.classList.remove(CONFIG.htmlClassRestricted);
  }

  const show = el => { if (!el) return; el.style.removeProperty("display"); el.removeAttribute("aria-hidden"); el.classList.remove("hidden","hide"); };
  const hide = el => { if (!el) return; el.style.display = "none"; el.setAttribute("aria-hidden","true"); };

  // Hide the view switcher <button> (JS fallback when :has not supported)
  function hide_view_switcher_button_now() {
    const label = document.querySelector(".page-actions .custom-btn-group-label");
    if (!label) return;
    const btn = label.closest("button");
    if (btn && btn.style.display !== "none") hide(btn);
  }

  // For super role: in "Filter By" keep only Assigned To / Created By
  function prune_group_by_for_super() {
    const sidebar = document.querySelector(".layout-side-section .list-sidebar");
    if (!sidebar) return;
    const filterSection = sidebar.querySelector(".filter-section");
    if (!filterSection) return;
    const wrap = filterSection.querySelector(".list-group-by, .list-group-by-fields") || filterSection;

    wrap.querySelectorAll(".group-by-field.list-link").forEach(li => hide(li));
    wrap.querySelectorAll(".group-by-field.list-link").forEach(li => {
      const fieldname = li.getAttribute("data-fieldname")
        || li.querySelector("a.list-sidebar-button")?.getAttribute("data-fieldname")
        || "";
      if (CONFIG.keepGroupByFieldnamesForSuper.includes((fieldname || "").trim())) show(li);
    });
  }

  // wave of re-applies to catch delayed rendering
  function schedule_apply() { [0, 30, 120, 300, 800].forEach(ms => setTimeout(apply, ms)); }

  // ===== CORE =====
  function apply() {
    if (!on_list_route()) { set_html_mode_none(); return; }

    // base CSS (scoped)
    add_css_once(CONFIG.cssId, BASE_CSS);

    // switcher fallback (prevents flash)
    hide_view_switcher_button_now();

    if (is_privileged()) {
      // SM: untouched aside from global instant CSS things
      set_html_mode_none();
      // restore visibility (in case of inline styles from earlier passes)
      const grp = document.querySelector(".page-actions .menu-btn-group");
      const filt = document.querySelector(".filter-selector");
      const side = document.querySelector(".layout-side-section");
      const tog  = document.querySelector(".page-title .sidebar-toggle-btn");
      [grp, filt, side, tog].forEach(show);
      return;
    }

    if (!has_any_restriction()) { set_html_mode_none(); return; }

    if (is_super()) {
      set_html_mode_super();
      prune_group_by_for_super();
      return;
    }

    // restricted (Admin/Demo)
    set_html_mode_restricted();
  }

  // ===== OBSERVERS & HOOKS =====
  function observe() {
    try {
      new MutationObserver(() => {
        hide_view_switcher_button_now();
        if (on_list_route()) schedule_apply();
      }).observe(document.body || document.documentElement, { childList: true, subtree: true });
    } catch (_) {}
  }
  function hook_router() {
    if (window.frappe?.router?.on) {
      frappe.router.on("change", () => {
        hide_view_switcher_button_now();
        schedule_apply();
      });
    }
  }

  // ===== BOOT =====
  (function instant() {
    add_css_once(CONFIG.cssInstantId, INSTANT_CSS);  // anti-flicker CSS
    hide_view_switcher_button_now();                 // JS fallback immediately
  })();

  function boot() {
    set_html_mode_none();
    apply();
    schedule_apply();
    observe();
    hook_router();
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
