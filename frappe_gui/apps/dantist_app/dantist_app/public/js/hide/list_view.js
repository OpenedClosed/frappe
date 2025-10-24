/* ========================================================================
   List View Prune (role-based, без побочек для System Manager)
   — Super Admin: sidebar работает, сайдбар пруним
   — Admin/Demo: sidebar скрыта, кнопка sidebar выключена
   — System Manager: вообще не трогаем (никаких CSS/обработчиков/хуков)
   ======================================================================== */
(function () {
  const CONFIG = {
    privilegedRole: "System Manager",
    restrictedRoles: ["AIHub Admin", "AIHub Demo"],
    superRole: "AIHub Super Admin",

    cssId: "rbac-list-view-css",
    cssInstantId: "rbac-list-view-INSTANT-css",
    htmlClassRestricted: "rbac-list-restricted",
    htmlClassSuper: "rbac-list-super",

    keepGroupByFieldnamesForSuper: ["assigned_to", "owner"],
  };

  // ----- utils -----
  function roles_ready() {
    const rr = window.frappe?.boot?.user?.roles;
    return Array.isArray(rr) && rr.length > 0;
  }
  function roles() { return window.frappe?.boot?.user?.roles || []; }
  function is_privileged() {
    const r = roles();
    if (window.frappe?.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.privilegedRole); } catch {} }
    return r.includes(CONFIG.privilegedRole);
  }
  function is_super() { return roles().includes(CONFIG.superRole); }
  function is_restricted() { return roles().some(r => CONFIG.restrictedRoles.includes(r)); }

  function on_list_route() {
    const rt = (window.frappe?.get_route && frappe.get_route()) || [];
    if (rt[0] === "List") return true;
    const dr = document.body?.getAttribute("data-route") || "";
    return /^List\//i.test(dr);
  }

  const INSTANT_CSS = `
    .page-actions button:has(.custom-btn-group-label) { display: none !important; }
    .page-actions .custom-btn-group-label { display: none !important; }
    .level-right .list-liked-by-me { display: none !important; }
  `;
  const BASE_CSS = `
    html.${CONFIG.htmlClassRestricted} ._hide,
    html.${CONFIG.htmlClassSuper} ._hide { display: none !important; }

    html.${CONFIG.htmlClassRestricted} .page-actions .menu-btn-group,
    html.${CONFIG.htmlClassSuper} .page-actions .menu-btn-group { display: none !important; }

    html.${CONFIG.htmlClassRestricted} .filter-selector,
    html.${CONFIG.htmlClassSuper} .filter-selector { display: none !important; }

    html.${CONFIG.htmlClassRestricted} .layout-side-section,
    html.${CONFIG.htmlClassRestricted} .page-title .sidebar-toggle-btn { display: none !important; }

    html.${CONFIG.htmlClassSuper} .list-sidebar .views-section,
    html.${CONFIG.htmlClassSuper} .list-sidebar .save-filter-section,
    html.${CONFIG.htmlClassSuper} .list-sidebar .user-actions { display: none !important; }

    html.${CONFIG.htmlClassSuper} .list-sidebar .list-tags > :not(.list-stats) { display: none !important; }

    html.${CONFIG.htmlClassSuper} .list-sidebar .filter-section .sidebar-action,
    html.${CONFIG.htmlClassSuper} .list-sidebar .filter-section .add-list-group-by,
    html.${CONFIG.htmlClassSuper} .list-sidebar .filter-section .add-group-by,
    html.${CONFIG.htmlClassSuper} .list-sidebar .filter-section .view-action { display: none !important; }

    html.${CONFIG.htmlClassRestricted} .list-row-activity .comment-count,
    html.${CONFIG.htmlClassRestricted} .list-row-activity .list-row-like,
    html.${CONFIG.htmlClassSuper} .list-row-activity .comment-count,
    html.${CONFIG.htmlClassSuper} .list-row-activity .list-row-like { display: none !important; }
  `;

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

  const show = el => { if (!el) return; el.style.removeProperty("display"); el.removeAttribute("aria-hidden"); el.classList.remove("hidden","hide","disabled"); el.style.pointerEvents = ""; el.removeAttribute("aria-disabled"); };
  const hide = el => { if (!el) return; el.style.display = "none"; el.setAttribute("aria-hidden","true"); };

  function get_sidebar_toggle_btn() { return document.querySelector(".page-title .sidebar-toggle-btn"); }
  function get_view_switcher_label() { return document.querySelector(".page-actions .custom-btn-group-label"); }
  function show_view_switcher_button_now() {
    const label = get_view_switcher_label();
    if (!label) return;
    const btn = label.closest("button");
    if (btn) show(btn);
  }
  function hide_view_switcher_button_now() {
    const label = get_view_switcher_label();
    if (!label) return;
    const btn = label.closest("button");
    if (btn && btn.style.display !== "none") hide(btn);
  }

  // ----- блокировка/разблокировка sidebar-тоггла только для restricted -----
  const TOGGLE_NS = "rbac_list_toggle_block";
  function block_sidebar_toggle() {
    const btn = get_sidebar_toggle_btn();
    if (!btn) return;
    if (!btn[TOGGLE_NS]) {
      btn[TOGGLE_NS] = e => { e.preventDefault(); e.stopImmediatePropagation(); };
      btn.addEventListener("click", btn[TOGGLE_NS], true);
    }
    btn.classList.add("disabled");
    btn.setAttribute("aria-disabled","true");
    btn.style.pointerEvents = "none";
  }
  function unblock_sidebar_toggle() {
    const btn = get_sidebar_toggle_btn();
    if (!btn) return;
    if (btn[TOGGLE_NS]) {
      btn.removeEventListener("click", btn[TOGGLE_NS], true);
      delete btn[TOGGLE_NS];
    }
    show(btn);
  }

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

  function schedule_apply() { [0, 50, 180, 400, 900].forEach(ms => setTimeout(apply, ms)); }

  function apply() {
    if (!on_list_route()) { set_html_mode_none(); return; }

    // System Manager: вообще не трогаем
    if (is_privileged()) {
      set_html_mode_none();
      // на всякий случай почистим возможные следы, если пользователь сменил роль без перезагрузки
      unblock_sidebar_toggle();
      const grp = document.querySelector(".page-actions .menu-btn-group");
      const filt = document.querySelector(".filter-selector");
      const side = document.querySelector(".layout-side-section");
      const tog  = get_sidebar_toggle_btn();
      [grp, filt, side, tog].forEach(show);
      show_view_switcher_button_now();
      return;
    }

    add_css_once(CONFIG.cssId, BASE_CSS);

    if (is_super()) {
      set_html_mode_super();
      unblock_sidebar_toggle();
      hide_view_switcher_button_now();
      prune_group_by_for_super();
      return;
    }

    if (is_restricted()) {
      set_html_mode_restricted();
      block_sidebar_toggle();
      hide_view_switcher_button_now();
      return;
    }

    set_html_mode_none();
  }

  // ----- старт без побочек для SM: ждём роли, потом решаемся -----
  function safe_boot() {
    if (!roles_ready()) { setTimeout(safe_boot, 60); return; }

    if (is_privileged()) {
      // ничего не инъектим: ни INSTANT_CSS, ни BASE_CSS, ни наблюдателей/хуков
      set_html_mode_none();
      apply();
      return;
    }

    // не-SM: можно антифликер и инфраструктуру
    add_css_once(CONFIG.cssInstantId, INSTANT_CSS);
    apply();
    schedule_apply();

    try {
      new MutationObserver(() => { if (on_list_route()) schedule_apply(); })
        .observe(document.body || document.documentElement, { childList: true, subtree: true });
    } catch {}

    if (window.frappe?.router?.on) {
      frappe.router.on("change", () => schedule_apply());
    }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(safe_boot);
  else document.addEventListener("DOMContentLoaded", safe_boot);
})();