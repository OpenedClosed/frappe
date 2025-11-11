/* ========================================================================
   List View Prune (role-based, только Select Kanban) — v2.4
   — System Manager: вообще не трогаем
   — Super Admin: режим super, показываем только "Select Kanban"
   — Остальные: режим restricted, показываем только "Select Kanban"
   — Для всех, кроме System Manager, в меню "Select Kanban":
       * скрываем "Create New Kanban Board"
       * ПОЛНОСТЬЮ скрываем разделитель(и) рядом, без мерцаний
   ======================================================================== */
(function () {
  const CONFIG = {
    privilegedRole: "System Manager",
    superRole: "AIHub Super Admin",

    cssId: "rbac-list-view-css",
    cssInstantId: "rbac-list-view-INSTANT-css",
    cssInstantMenuNonSM: "rbac-list-view-INSTANT-menu-non-sm-css",
    htmlClassRestricted: "rbac-list-restricted",
    htmlClassSuper: "rbac-list-super",

    showSelectKanbanClass: "rbac-show-select-kanban",
  };

  // ----- roles / route -----
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
  function on_list_route() {
    const rt = (window.frappe?.get_route && frappe.get_route()) || [];
    if (rt[0] === "List") return true;
    const dr = document.body?.getAttribute("data-route") || "";
    return /^List\//i.test(dr);
  }

  // ----- utils -----
  function add_css_once(id, css) {
    if (document.getElementById(id)) return;
    const s = document.createElement("style");
    s.id = id;
    s.textContent = css;
    document.documentElement.appendChild(s);
  }
  function remove_css(id) {
    const s = document.getElementById(id);
    if (s && s.parentNode) s.parentNode.removeChild(s);
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

  // ---- only one target button: "Select Kanban"
  function find_select_kanban_button() {
    const labels = Array.from(document.querySelectorAll(".page-actions .custom-btn-group-label"));
    const match = labels.find(l => {
      const txt = (l.textContent || "").trim();
      return /select\s+kanban/i.test(txt) || /выбрать.*канбан/i.test(txt);
    });
    return match ? match.closest("button") : null;
  }
  function ensure_select_kanban_visible() {
    const btn = find_select_kanban_button();
    if (!btn) return null;
    btn.classList.add(CONFIG.showSelectKanbanClass);
    show(btn);
    return btn;
  }

  // ----- lock/unlock sidebar toggle for restricted -----
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

  /* === 1) INSTANT anti-flicker for action buttons === */
  const INSTANT_CSS = `
    .page-actions button:has(.custom-btn-group-label) { display: none !important; }
    .page-actions .custom-btn-group-label { display: none !important; }
    .level-right .list-liked-by-me { display: none !important; }

    .page-actions button.${CONFIG.showSelectKanbanClass} { display: inline-block !important; }
    .page-actions button.${CONFIG.showSelectKanbanClass} .custom-btn-group-label { display: inline-block !important; }
  `;
  add_css_once(CONFIG.cssInstantId, INSTANT_CSS);

  /* === 2) BASE CSS + global INSTANT hide for menu items/dividers (non-SM) === */
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

  // CSS, который грузится СРАЗУ для всех не-SM и работает где бы ни рисовалось меню (в body, в page-actions и т.п.)
  const INSTANT_MENU_NON_SM_CSS = `
    /* Спрятать сам пункт "Create New Kanban Board" (EN/RU, закодированные/обычные data-label) */
    .dropdown-menu li:has(.menu-item-label[data-label*="Create%20New%20Kanban%20Board"]),
    .dropdown-menu li:has(.menu-item-label[data-label*="Create New Kanban Board"]),
    .dropdown-menu li:has(.menu-item-label[data-label*="%D0%A1%D0%BE%D0%B7%D0%B4"]),
    .dropdown-menu li:has(.menu-item-label[data-label*="%D0%9A%D0%B0%D0%BD%D0%B1%D0%B0%D0%BD"]),
    .dropdown-menu li:has(.menu-item-label[data-label*="%D0%94%D0%BE%D1%81%D0%BA%D1%83"]) { display: none !important; }

    /* БЕЗ МЕРЦАНИЙ: убираем ВЕСЬ разделитель user-action в этом меню для не-SM.
       (В "Select Kanban" обычно один разделитель — тот самый перед Create; прячем его глобально) */
    html.${CONFIG.htmlClassRestricted} .dropdown-menu .dropdown-divider.user-action,
    html.${CONFIG.htmlClassSuper}     .dropdown-menu .dropdown-divider.user-action { display: none !important; }

    /* На всякий случай — удаляем крайние/дублирующиеся divider'ы */
    .dropdown-menu > .dropdown-divider:last-child,
    .dropdown-menu > .dropdown-divider:first-child,
    .dropdown-menu .dropdown-divider + .dropdown-divider { display: none !important; }
  `;

  function schedule_apply() { [0, 60, 200, 500, 1000].forEach(ms => setTimeout(apply, ms)); }

  // Доп. JS-чистка (если вдруг тема/кастомные классы отличны)
  function cleanup_select_kanban_menu(menuEl) {
    if (!menuEl) return;

    // спрятать любые divider'ы user-action (тот, что мерцал в твоём HTML)
    menuEl.querySelectorAll(".dropdown-divider.user-action").forEach(el => el.style.display = "none");

    // подстраховка: если остались крайние/двойные разделители
    const isDivider = el => el && /(^|\s)(dropdown-divider|divider)(\s|$)/.test(el.className || "");
    while (isDivider(menuEl.firstElementChild)) menuEl.firstElementChild.style.display = "none";
    while (isDivider(menuEl.lastElementChild))  menuEl.lastElementChild.style.display  = "none";
    let prevDividerShown = false;
    Array.from(menuEl.children).forEach(el => {
      const d = isDivider(el);
      if (d && prevDividerShown) el.style.display = "none";
      prevDividerShown = d && (el.style.display !== "none");
    });
  }

  function hook_select_kanban_menu_cleanup_for_non_sm() {
    if (is_privileged()) return; // System Manager — untouched

    const btn = find_select_kanban_button();
    if (!btn) return;

    const runCleanup = () => {
      const menu = document.querySelector(".dropdown-menu.show");
      if (menu) cleanup_select_kanban_menu(menu);
    };

    btn.addEventListener("pointerdown", () => setTimeout(runCleanup, 0), true);
    btn.addEventListener("click",       () => setTimeout(runCleanup, 0), true);
    btn.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") setTimeout(runCleanup, 0);
    }, true);

    // наблюдатель на появление show-меню
    const mo = new MutationObserver(() => {
      const menu = document.querySelector(".dropdown-menu.show");
      if (menu) cleanup_select_kanban_menu(menu);
    });
    try { mo.observe(document.body || document.documentElement, { childList: true, subtree: true }); } catch {}
  }

  function apply() {
    if (!on_list_route()) { set_html_mode_none(); return; }

    if (is_privileged()) {
      // System Manager — никаких инъекций
      set_html_mode_none();
      remove_css(CONFIG.cssId);
      remove_css(CONFIG.cssInstantMenuNonSM);
      unblock_sidebar_toggle();
      return;
    }

    // Non-SM
    add_css_once(CONFIG.cssId, BASE_CSS);
    add_css_once(CONFIG.cssInstantMenuNonSM, INSTANT_MENU_NON_SM_CSS);

    if (is_super()) {
      set_html_mode_super();
      unblock_sidebar_toggle();
    } else {
      set_html_mode_restricted();
      block_sidebar_toggle();
    }

    ensure_select_kanban_visible();
    hook_select_kanban_menu_cleanup_for_non_sm();
  }

  function safe_boot() {
    if (!roles_ready()) { setTimeout(safe_boot, 60); return; }
    apply();

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