/* ===== AIHub List View Hide / Prune (safe, scoped to List/* only) ===== */
(function () {
  const CONFIG = {
    systemManagerRole: "System Manager",
    aihubRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    superRole: "AIHub Super Admin",
    lsKey: "aihub_hide_list_view",
    keepGroupByFieldnamesForSuper: ["assigned_to", "owner"], // Assigned To, Created By
  };

  /* ---- roles ---- */
  function roles() { return (frappe?.boot?.user?.roles) || []; }
  function isSystemManager() {
    const r = roles();
    if (frappe.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.systemManagerRole); } catch {} }
    return r.includes(CONFIG.systemManagerRole);
  }
  function hasAIHubRole() { return roles().some(r => CONFIG.aihubRoles.includes(r)); }
  function isSuperAdmin() { return roles().includes(CONFIG.superRole); }
  function isRestrictedAIHub() { return hasAIHubRole() && !isSystemManager() && !isSuperAdmin(); }

  /* ---- route guards ---- */
  function onListRoute() {
    const rt = (frappe.get_route && frappe.get_route()) || [];
    if (rt[0] === "List") return true;
    const dr = document.body?.getAttribute("data-route") || "";
    return /^List\//i.test(dr);
  }

  /* ---- helpers ---- */
  function hide(el){ if (!el) return; el.style.display = "none"; el.setAttribute("aria-hidden","true"); }
  function show(el){ if (!el) return; el.style.removeProperty("display"); el.removeAttribute("aria-hidden"); el.classList.remove("hidden","hide"); }

  function pickNodes() {
    const listSidebar = document.querySelector(".layout-side-section .list-sidebar");
    const sidebarCol  = listSidebar ? listSidebar.closest(".layout-side-section") : null;
    const toggleBtn   = document.querySelector(".page-title .sidebar-toggle-btn");

    // переключатель вида (List / Report / Kanban)
    const viewSwitcherBtn = (function(){
      const label = document.querySelector(".page-actions .custom-btn-group-label");
      return label ? label.closest("button") : null;
    })();

    // кнопка «⋯ Menu»
    const threeDotsBtn = (function(){
      const label = document.querySelector(".page-actions .menu-btn-group-label");
      return label ? label.closest("button") : null;
    })();

    // header-фильтры рядом с заголовком списка
    const filterSelector = document.querySelector(".filter-selector");

    const listRows = document.querySelector(".list-view-container, .result, .list-row-container");
    return { listSidebar, sidebarCol, toggleBtn, viewSwitcherBtn, threeDotsBtn, filterSelector, listRows };
  }

  /* ---- prune sidebar just for AIHub Super Admin ---- */
  function pruneSidebarForSuperAdmin(sidebar) {
    if (!sidebar) return;

    // 0) Удаляем/скрываем блок Views (если есть)
    hide(sidebar.querySelector(".views-section"));

    // 1) Оставляем только Filter By → Assigned To / Created By
    const filterSection = sidebar.querySelector(".filter-section");
    if (filterSection) {
      // кнопка "Edit Filters" и прочие действия
      filterSection.querySelectorAll(".add-list-group-by, .add-group-by, .sidebar-action .view-action, .sidebar-action a")
        .forEach(hide);

      const groupWrap = filterSection.querySelector(".list-group-by, .list-group-by-fields") || filterSection;
      groupWrap.querySelectorAll(".group-by-field.list-link").forEach(li => {
        const fieldname = li.getAttribute("data-fieldname")
          || li.querySelector("a.list-sidebar-button")?.getAttribute("data-fieldname")
          || "";
        if (!CONFIG.keepGroupByFieldnamesForSuper.includes((fieldname || "").trim())) hide(li);
        else show(li);
      });
    }

    // 2) Блок Tags: оставить только «Tags» (dropdown), убрать «Show Tags» и др.
    const listTags = sidebar.querySelector(".list-tags");
    if (listTags) {
      listTags.querySelectorAll(":scope > *").forEach(el => {
        if (el.classList.contains("list-stats")) show(el); // кнопка Tags
        else hide(el); // .show-tags и прочее
      });
    }

    // 3) Полностью убрать "Save Filter" секцию и пустые user-actions
    hide(sidebar.querySelector(".save-filter-section"));
    sidebar.querySelectorAll(".user-actions").forEach(hide);
  }

  /* ---- core ---- */
  function apply() {
    if (!onListRoute()) return;

    const restricted = isRestrictedAIHub();
    const aihubButNotSM = hasAIHubRole() && !isSystemManager(); // скрыть switcher/filters у всех AIHub
    try { localStorage.setItem(CONFIG.lsKey, restricted ? "1" : "0"); } catch {}

    const {
      listSidebar, sidebarCol, toggleBtn, viewSwitcherBtn, threeDotsBtn, filterSelector, listRows
    } = pickNodes();

    if (!listRows) return;

    // 1) «⋯ Menu» — скрыт у всех
    if (threeDotsBtn) hide(threeDotsBtn);

    // 2) Переключатель вида — скрыт у всех AIHub (Admin/Demo/Super Admin), но не у System Manager
    if (viewSwitcherBtn) {
      if (aihubButNotSM) hide(viewSwitcherBtn);
      else show(viewSwitcherBtn);
    }

    // 3) Header-фильтры (filter selector) — скрыть у всех AIHub, System Manager видит
    if (filterSelector) {
      if (aihubButNotSM) hide(filterSelector);
      else show(filterSelector);
    }

    // 4) Боковая панель и тоггл
    if (restricted) {
      // Admin/Demo: скрыть боковую и тоггл
      if (sidebarCol) hide(sidebarCol);
      if (toggleBtn) hide(toggleBtn);
    } else {
      // Super Admin / System Manager: показываем колонку и тоггл
      if (sidebarCol) show(sidebarCol);
      if (toggleBtn) show(toggleBtn);

      // Доп. обрезка только для AIHub Super Admin
      if (isSuperAdmin()) pruneSidebarForSuperAdmin(listSidebar);
    }
  }

  /* ---- observe/router ---- */
  function observe() {
    const mo = new MutationObserver(() => { if (onListRoute()) apply(); });
    mo.observe(document.body || document.documentElement, { childList:true, subtree:true });
  }
  function hookRouter(){ if (frappe?.router?.on) frappe.router.on("change", apply); }

  /* ---- boot ---- */
  function boot() {
    apply();
    observe();
    hookRouter();
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
