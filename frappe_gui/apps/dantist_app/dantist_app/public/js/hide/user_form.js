/* ===== AIHub User Form Hide (same style as topbar/workspace) ===== */
(function () {
  const CONFIG = {
    systemManagerRole: "System Manager",
    aihubRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    superRole: "AIHub Super Admin",
    lsKey: "aihub_hide_user_form",
    cssId: "aihub-hide-user-form-css",
    // общий CSS — скрыть у всех AIHub (включая Super Admin) то, что всегда прячем
    cssCommon: `
      body[data-route*="Form/User/"] .form-assignments,
      body[data-route*="Form/User/"] .form-shared,
      body[data-route*="Form/User/"] .form-sidebar-stats,
      body[data-route*="Form/User/"] .form-sidebar .form-follow { display: none !important; }
    `
  };

  /* ===== Role checks ===== */
  function roles() { return (frappe.boot?.user?.roles) || []; }
  function isSystemManager() {
    const r = roles();
    if (frappe.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.systemManagerRole); } catch {} }
    return r.includes(CONFIG.systemManagerRole);
  }
  function hasAIHubRole() { return roles().some(r => CONFIG.aihubRoles.includes(r)); }
  function isSuperAdmin() { return roles().includes(CONFIG.superRole); }
  function shouldHide() { return hasAIHubRole() && !isSystemManager(); }

  /* ===== Route check ===== */
  function onUserFormRoute() {
    const rt = (frappe.get_route && frappe.get_route()) || [];
    if (rt[0] === "Form" && rt[1] === "User") return true;
    const dr = document.body?.getAttribute("data-route") || "";
    return /Form\/User\//i.test(dr);
  }

  /* ===== Anti-flicker ===== */
  (function instantHide() {
    try {
      if (localStorage.getItem(CONFIG.lsKey) !== "1") return;
      if (!document.getElementById(CONFIG.cssId)) {
        const s = document.createElement("style");
        s.id = CONFIG.cssId;
        s.textContent = CONFIG.cssCommon;
        document.documentElement.appendChild(s);
      }
    } catch (_) {}
  })();

  /* ===== DOM helpers ===== */
  function addCssOnce(id, css) {
    if (document.getElementById(id)) return;
    const s = document.createElement("style");
    s.id = id;
    s.textContent = css;
    document.documentElement.appendChild(s);
  }
  function removeCss(id) { const s = document.getElementById(id); if (s) s.remove(); }

  function unhideImportant(el, display = "block") {
    if (!el) return;
    el.style.setProperty("display", display, "important");
    el.style.setProperty("visibility", "visible", "important");
    el.style.setProperty("opacity", "1", "important");
    el.removeAttribute("aria-hidden");
    el.classList.remove("hidden","hide");
  }
  function hide(el){ if (!el) return; el.style.display = "none"; el.setAttribute("aria-hidden","true"); }

  function metaUL() {
    return document.querySelector('ul.list-unstyled.sidebar-menu.text-muted');
  }
  function parentsChain(el) {
    const arr = [];
    let n = el && el.parentElement;
    while (n && n !== document.documentElement) { arr.push(n); n = n.parentElement; }
    return arr;
  }

  /* ===== Core visibility ===== */
  function applyUserFormVisibility() {
    if (!onUserFormRoute() || !shouldHide()) return;

    const meta = metaUL();
    const timeline   = document.querySelector(".new-timeline");
    const commentBox = document.querySelector(".form-footer .comment-box");
    const commentBtn = document.querySelector(".form-footer .btn-comment");

    if (isSuperAdmin()) {
      // 1) Принудительно раскрываем сам блок меты и всех его родителей
      if (meta) {
        unhideImportant(meta, "block");
        parentsChain(meta).forEach(p => {
          if (p.matches(".form-sidebar, .overlay-sidebar, .layout-side-section, .layout-side-section-wrapper"))
            unhideImportant(p, "block");
        });
      }
      // 2) Принудительно раскрываем Activity & Comments
      unhideImportant(timeline, "block");
      unhideImportant(commentBox, "block");
      unhideImportant(commentBtn, "inline-block");
      // 3) На всякий — не даём ближайшему <hr> влиять (если тема его прячет вместе с блоком)
      const hr = meta ? meta.previousElementSibling : null;
      if (hr && hr.tagName === "HR") unhideImportant(hr, "block");
    } else {
      // Для Admin/Demo — прячем точечно
      hide(meta);
      hide(timeline); hide(commentBox); hide(commentBtn);
    }
  }

  /* ===== Observer / Router ===== */
  function observeDom() {
    new MutationObserver(() => applyUserFormVisibility())
      .observe(document.documentElement, { subtree:true, childList:true });
  }
  function hookRouter() {
    if (frappe.router?.on) frappe.router.on("change", applyUserFormVisibility);
  }

  /* ===== Boot ===== */
  function boot() {
    const need = shouldHide();
    try { localStorage.setItem(CONFIG.lsKey, need ? "1" : "0"); } catch {}
    if (need) {
      addCssOnce(CONFIG.cssId, CONFIG.cssCommon);
      applyUserFormVisibility();
      observeDom();
      hookRouter();
    } else {
      removeCss(CONFIG.cssId);
    }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
