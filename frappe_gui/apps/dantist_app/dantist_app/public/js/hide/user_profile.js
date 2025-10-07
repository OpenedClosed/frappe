/* ========================================================================
   Form Toolbar: hide "Permissions" group for restricted roles (AIHub*)
   — Scope: any Form/* (route guard)
   — Hides: the inner group button "Permissions" and its dropdown items
   — SM untouched. Debounced observer. Anti-flicker CSS.
   ======================================================================== */
(function () {
  const CONFIG = {
    privilegedRole: "System Manager",
    restrictedRoles: [
      "AIHub Super Admin", "AIHub Admin", "AIHub Demo",
      "AIHub User", "AIHub Manager", "AIHub Doctor",
      "AIHub Assistant", "Super Admin"
    ],
    cssId: "rbac-form-permissions-INSTANT-css"
  };

  // ---- roles ------------------------------------------------------------
  function roles() { return (window.frappe?.boot?.user?.roles) || []; }
  function isPrivileged() {
    const r = roles();
    if (window.frappe?.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.privilegedRole); } catch {} }
    return r.includes(CONFIG.privilegedRole);
  }
  function isRestricted() { return roles().some(r => CONFIG.restrictedRoles.includes(r)) && !isPrivileged(); }

  // ---- route guard ------------------------------------------------------
  function onFormRoute() {
    const rt = (window.frappe?.get_route && frappe.get_route()) || [];
    if (rt[0] === "Form") return true;
    const dr = document.body?.getAttribute("data-route") || "";
    return /^Form\//i.test(dr);
  }

  // ---- anti-flicker -----------------------------------------------------
  (function instantCSS(){
    if (!isRestricted()) return;
    if (document.getElementById(CONFIG.cssId)) return;
    const s = document.createElement("style");
    s.id = CONFIG.cssId;
    s.textContent = `
      body[data-route^="Form/"] .page-actions .inner-group-button[data-label="Permissions"] { display: none !important; }
      body[data-route^="Form/"] .page-actions .inner-group-button .dropdown-menu [data-label="Set%20User%20Permissions"],
      body[data-route^="Form/"] .page-actions .inner-group-button .dropdown-menu [data-label="View%20Permitted%20Documents"] { display: none !important; }
    `;
    document.documentElement.appendChild(s);
  })();

  // ---- dom helpers ------------------------------------------------------
  const hide = el => { if (!el) return; el.style.display = "none"; el.setAttribute("aria-hidden","true"); };
  const norm = s => (s || "").replace(/\s+/g, " ").trim().toLowerCase();

  function applyOnce() {
    if (!onFormRoute() || !isRestricted()) return;

    // сама группа
    document.querySelectorAll('.page-actions .inner-group-button[data-label="Permissions"]').forEach(hide);

    // fallback по тексту, если нет data-label на контейнере
    document.querySelectorAll('.page-actions .inner-group-button').forEach(div => {
      const btn = div.querySelector('button.btn, button');
      if (btn && norm(btn.textContent).startsWith("permissions")) hide(div);
    });

    // пункты дропдауна этой группы
    document.querySelectorAll('.page-actions .inner-group-button .dropdown-menu .dropdown-item')
      .forEach(a => {
        const dl = a.getAttribute("data-label") || "";
        const txt = norm(a.textContent);
        if (dl === "Set%20User%20Permissions" || dl === "View%20Permitted%20Documents" ||
            txt.includes("set user permissions") || txt.includes("view permitted documents")) {
          hide(a);
        }
      });
  }

  // ---- debounced observer & router --------------------------------------
  let scheduled = false;
  function schedule(){ if (scheduled) return; scheduled = true; setTimeout(() => { scheduled = false; applyOnce(); }, 60); }

  function observe() {
    try {
      new MutationObserver(() => { if (onFormRoute()) schedule(); })
        .observe(document.body || document.documentElement, { childList: true, subtree: true });
    } catch {}
  }

  function hookRouter(){ if (window.frappe?.router?.on) frappe.router.on("change", () => { if (onFormRoute()) schedule(); }); }

  // ---- boot -------------------------------------------------------------
  function boot() { applyOnce(); observe(); hookRouter(); }
  if (window.frappe?.after_ajax) frappe.after_ajax(boot); else document.addEventListener("DOMContentLoaded", boot);
})();
