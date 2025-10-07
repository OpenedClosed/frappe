/* ===== AIHub List View Hide / Prune (instant + robust) ===== */
(function () {
  const CONFIG = {
    systemManagerRole: "System Manager",
    aihubRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    superRole: "AIHub Super Admin",

    cssId: "aihub-list-view-css",
    cssInstantId: "aihub-list-view-INSTANT-css",
    htmlClassRestricted: "aihub-list-restricted",
    htmlClassSuper: "aihub-list-super",

    keepGroupByFieldnamesForSuper: ["assigned_to", "owner"],
  };

  /* ---------- roles ---------- */
  function roles() { return (frappe?.boot?.user?.roles) || []; }
  function isSystemManager() {
    const r = roles();
    if (frappe.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.systemManagerRole); } catch {} }
    return r.includes(CONFIG.systemManagerRole);
  }
  function hasAIHubRole() { return roles().some(r => CONFIG.aihubRoles.includes(r)); }
  function isSuperAdmin() { return roles().includes(CONFIG.superRole); }

  /* ---------- route guard ---------- */
  function onListRoute() {
    const rt = (frappe.get_route && frappe.get_route()) || [];
    if (rt[0] === "List") return true;
    const dr = document.body?.getAttribute("data-route") || "";
    return /^List\//i.test(dr);
  }

  /* ---------- INSTANT CSS (анти-фликер, работает до любых хукoв) ---------- */
  const INSTANT_CSS = `
    /* Прячем переключатель вида для всех (включая System Manager) */
    .page-actions button:has(.custom-btn-group-label) { display: none !important; }
    /* Фолбэк на случай отсутствия :has() — убираем хотя бы контент, JS добьёт сам <button> */
    .page-actions .custom-btn-group-label { display: none !important; }

    /* Глобально для всех — убираем «сердце» в правой части заголовка листа */
    .level-right .list-liked-by-me { display: none !important; }
  `;

  /* ---------- base CSS (по классам на <html>) ---------- */
  const BASE_CSS = `
    html.aihub-list-restricted ._hide,
    html.aihub-list-super ._hide { display: none !important; }

    /* «⋯ Menu» (вся группа) в хедере списка — скрыть у всех AIHub */
    html.aihub-list-restricted .page-actions .menu-btn-group,
    html.aihub-list-super .page-actions .menu-btn-group { display: none !important; }

    /* Header-фильтры (Filter selector) — скрыть у всех AIHub */
    html.aihub-list-restricted .filter-selector,
    html.aihub-list-super .filter-selector { display: none !important; }

    /* Боковая колонка — целиком скрыта только у Admin/Demo */
    html.aihub-list-restricted .layout-side-section,
    html.aihub-list-restricted .page-title .sidebar-toggle-btn { display: none !important; }

    /* Для SuperAdmin боковая есть, но «обрезаем» лишнее */
    html.aihub-list-super .list-sidebar .views-section,
    html.aihub-list-super .list-sidebar .save-filter-section,
    html.aihub-list-super .list-sidebar .user-actions { display: none !important; }

    /* В блоке Tags оставить только dropdown "Tags" */
    html.aihub-list-super .list-sidebar .list-tags > :not(.list-stats) { display: none !important; }

    /* В Filter By скрыть "Edit Filters" и прочие sidebar-action */
    html.aihub-list-super .list-sidebar .filter-section .sidebar-action,
    html.aihub-list-super .list-sidebar .filter-section .add-list-group-by,
    html.aihub-list-super .list-sidebar .filter-section .add-group-by,
    html.aihub-list-super .list-sidebar .filter-section .view-action { display: none !important; }

    /* В строках списка у всех AIHub скрыть комменты и лайки, оставить только "modified" */
    html.aihub-list-restricted .list-row-activity .comment-count,
    html.aihub-list-restricted .list-row-activity .list-row-like,
    html.aihub-list-super .list-row-activity .comment-count,
    html.aihub-list-super .list-row-activity .list-row-like { display: none !important; }
  `;

  /* ---------- helpers ---------- */
  function addCssOnce(id, css) {
    if (document.getElementById(id)) return;
    const s = document.createElement("style");
    s.id = id;
    s.textContent = css;
    document.documentElement.appendChild(s);
  }

  function setHtmlModeNone() {
    document.documentElement.classList.remove(CONFIG.htmlClassRestricted, CONFIG.htmlClassSuper);
  }
  function setHtmlModeRestricted() {
    document.documentElement.classList.add(CONFIG.htmlClassRestricted);
    document.documentElement.classList.remove(CONFIG.htmlClassSuper);
  }
  function setHtmlModeSuper() {
    document.documentElement.classList.add(CONFIG.htmlClassSuper);
    document.documentElement.classList.remove(CONFIG.htmlClassRestricted);
  }

  const show = el => { if (!el) return; el.style.removeProperty("display"); el.removeAttribute("aria-hidden"); el.classList.remove("hidden","hide"); };
  const hide = el => { if (!el) return; el.style.display = "none"; el.setAttribute("aria-hidden","true"); };

  // Прячем сам <button> переключателя вида — жёсткий фолбэк на старые браузеры без :has()
  function hideViewSwitcherButtonNow() {
    const label = document.querySelector(".page-actions .custom-btn-group-label");
    if (!label) return;
    const btn = label.closest("button");
    if (btn && btn.style.display !== "none") hide(btn);
  }

  // Суперадмину в Filter By оставляем только Assigned To / Created By
  function pruneGroupByForSuper() {
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

  // «веер» повторных применений — ловим отложенный рендер
  function scheduleApply() { [0, 30, 120, 300, 800].forEach(ms => setTimeout(apply, ms)); }

  /* ---------- core ---------- */
  function apply() {
    if (!onListRoute()) { setHtmlModeNone(); return; }

    // базовый CSS (по классам)
    addCssOnce(CONFIG.cssId, BASE_CSS);

    // переключатель вида: фолбэк-хайд на случай отсутствия :has()
    hideViewSwitcherButtonNow();

    if (isSystemManager()) {
      // SM — максимально нетронут (кроме того, что глобально скрываем свитчер и «сердце»)
      setHtmlModeNone();
      // вернуть видимость остальному на случай инлайн-стилей от прошлых версий
      const grp = document.querySelector(".page-actions .menu-btn-group");
      const filt = document.querySelector(".filter-selector");
      const side = document.querySelector(".layout-side-section");
      const tog  = document.querySelector(".page-title .sidebar-toggle-btn");
      [grp, filt, side, tog].forEach(show);
      return;
    }

    if (!hasAIHubRole()) { setHtmlModeNone(); return; }

    if (isSuperAdmin()) {
      setHtmlModeSuper();
      pruneGroupByForSuper();
      return;
    }

    // AIHub Admin / Demo
    setHtmlModeRestricted();
  }

  /* ---------- observers & hooks ---------- */
  function observe() {
    const mo = new MutationObserver(() => {
      // моментально скрываем свитчер при любых мутациях (появился — сразу спрятали)
      hideViewSwitcherButtonNow();
      if (onListRoute()) scheduleApply();
    });
    mo.observe(document.body || document.documentElement, { childList: true, subtree: true });
  }
  function hookRouter() {
    if (frappe?.router?.on) {
      frappe.router.on("change", () => {
        // ещё до отрисовки — включаем анти-фликер свитчера
        hideViewSwitcherButtonNow();
        scheduleApply();
      });
    }
  }

  /* ---------- boot ---------- */
  (function instant() {
    // 1) кидаем мгновенный CSS (анти-фликер и «сердце»)
    addCssOnce(CONFIG.cssInstantId, INSTANT_CSS);
    // 2) пробуем прямо сейчас прибить кнопку свитчера (JS-фолбэк)
    hideViewSwitcherButtonNow();
  })();

  function boot() {
    setHtmlModeNone();
    apply();
    scheduleApply();
    observe();
    hookRouter();
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
