/* ===== AIHub User Form Hide (robust, no flicker) ===== */
(function () {
  const CONFIG = {
    systemManagerRole: "System Manager",
    aihubRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    superRole: "AIHub Super Admin",

    cssId: "aihub-hide-user-form-css",
    cssInstantId: "aihub-hide-user-form-INSTANT-css",

    // общий CSS — скрыть у всех AIHub (включая Super Admin) то, что всегда прячем
    cssCommon: `
      body[data-route*="Form/User/"] .form-assignments,
      body[data-route*="Form/User/"] .form-shared,
      body[data-route*="Form/User/"] .form-sidebar-stats,
      body[data-route*="Form/User/"] .form-sidebar .form-follow { display: none !important; }
    `,
    // мгновенный CSS: ничего «лишнего» не делает, просто готов прятать общий блок как можно раньше
    cssInstant: `
      /* Ничего, кроме "общего" — ровно те же селекторы, чтобы не было мигания */
      body[data-route*="Form/User/"] .form-assignments,
      body[data-route*="Form/User/"] .form-shared,
      body[data-route*="Form/User/"] .form-sidebar-stats,
      body[data-route*="Form/User/"] .form-sidebar .form-follow { display: none !important; }
    `
  };

  /* ===== Roles ===== */
  function rolesSafe() { return (frappe?.boot?.user?.roles) || []; }
  function isSystemManager() {
    const r = rolesSafe();
    if (frappe?.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.systemManagerRole); } catch {} }
    return r.includes(CONFIG.systemManagerRole);
  }
  function hasAIHubRole() { return rolesSafe().some(r => CONFIG.aihubRoles.includes(r)); }
  function isSuperAdmin() { return rolesSafe().includes(CONFIG.superRole); }
  function shouldHide() { return hasAIHubRole() && !isSystemManager(); }

  /* ===== Route guard ===== */
  function onUserFormRoute() {
    const rt = (frappe?.get_route && frappe.get_route()) || [];
    if (rt[0] === "Form" && rt[1] === "User") return true;
    const dr = document.body?.getAttribute("data-route") || "";
    return /(^|\/)Form\/User\//i.test(dr);
  }

  /* ===== CSS helpers ===== */
  function addCssOnce(id, css) {
    if (document.getElementById(id)) return;
    const s = document.createElement("style");
    s.id = id;
    s.textContent = css;
    document.documentElement.appendChild(s);
  }
  function removeCss(id) { const s = document.getElementById(id); if (s) s.remove(); }

  /* ===== DOM helpers ===== */
  function hide(el){ if (!el) return; el.style.display = "none"; el.setAttribute("aria-hidden","true"); }
  function unhideImportant(el, display = "block") {
    if (!el) return;
    el.style.setProperty("display", display, "important");
    el.style.setProperty("visibility", "visible", "important");
    el.style.setProperty("opacity", "1", "important");
    el.removeAttribute("aria-hidden");
    el.classList.remove("hidden","hide");
  }
  function parentsChain(el) {
    const arr = []; let n = el && el.parentElement;
    while (n && n !== document.documentElement) { arr.push(n); n = n.parentElement; }
    return arr;
  }
  function pickNodes() {
    const meta = document.querySelector('ul.list-unstyled.sidebar-menu.text-muted'); // мета-блок (pageviews/modified/created)
    const timeline   = document.querySelector(".new-timeline");
    const commentBox = document.querySelector(".form-footer .comment-box");
    const commentBtn = document.querySelector(".form-footer .btn-comment");
    const side = document.querySelector(".form-sidebar, .layout-side-section, .overlay-sidebar");
    const hrBeforeMeta = meta ? meta.previousElementSibling : null;
    return { meta, timeline, commentBox, commentBtn, side, hrBeforeMeta };
  }

  /* ===== Core apply ===== */
  function applyOnce() {
    if (!onUserFormRoute()) return;

    // общий CSS — для всех AIHub (но System Manager не трогаем совсем)
    if (shouldHide()) addCssOnce(CONFIG.cssId, CONFIG.cssCommon); else removeCss(CONFIG.cssId);

    // точечная логика по ролям
    if (!shouldHide()) return;

    const { meta, timeline, commentBox, commentBtn, side, hrBeforeMeta } = pickNodes();

    if (isSuperAdmin()) {
      // показать мета-блок + родители
      if (meta) {
        unhideImportant(meta, "block");
        parentsChain(meta).forEach(p => {
          if (p.matches(".form-sidebar, .overlay-sidebar, .layout-side-section, .layout-side-section-wrapper")) {
            unhideImportant(p, "block");
          }
        });
      }
      // показать активность/комменты
      unhideImportant(timeline, "block");
      unhideImportant(commentBox, "block");
      unhideImportant(commentBtn, "inline-block");
      if (hrBeforeMeta && hrBeforeMeta.tagName === "HR") unhideImportant(hrBeforeMeta, "block");
      if (side) unhideImportant(side, "block");
    } else {
      // Admin/Demo — прячем точечно
      hide(pickNodes().meta);
      hide(pickNodes().timeline);
      hide(pickNodes().commentBox);
      hide(pickNodes().commentBtn);
    }
  }

  // несколько повторов, чтобы поймать отложенный рендер
  function scheduleApply() { [0, 40, 120, 300, 800].forEach(ms => setTimeout(applyOnce, ms)); }

  /* ===== Observe & Router ===== */
  function observe() {
    const mo = new MutationObserver(() => { if (onUserFormRoute()) scheduleApply(); });
    mo.observe(document.body || document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["class","style","data-route"] });
  }
  function hookRouter() { if (frappe?.router?.on) frappe.router.on("change", scheduleApply); }

  /* ===== Boot ===== */
  (function instant() {
    // анти-фликер сразу (не ждём ролей): он совпадает с «общим» набором и безопасен
    addCssOnce(CONFIG.cssInstantId, CONFIG.cssInstant);
  })();

  function boot() {
    scheduleApply();
    observe();
    hookRouter();
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
