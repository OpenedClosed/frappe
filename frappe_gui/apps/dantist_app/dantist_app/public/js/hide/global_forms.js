/* ===== AIHub Global Forms Tab Hide (configurable) ===== */
(function () {
  const CONFIG = {
    systemManagerRole: "System Manager",
    aihubRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo", "AIHub User", "AIHub Manager", "AIHub Doctor", "AIHub Assistant", "Super Admin"],
    lsKey: "aihub_hide_global_connections",
    cssId: "aihub-hide-global-connections-css",
    css: `
      /* Connections tab headers */
      .form-tabs .nav-link[id$="connections_tab-tab"],
      .form-tabs button[data-fieldname*="connections" i],
      .form-tabs .nav-link[aria-controls*="connections" i] { display: none !important; }

      /* Connections tab panes */
      .tab-content [id$="connections_tab"],
      .tab-content [data-fieldname="connections_tab"] { display: none !important; }
    `
  };

  function roles() { return (frappe?.boot?.user?.roles) || []; }
  function isSystemManager() {
    const r = roles();
    if (frappe.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.systemManagerRole); } catch {} }
    return r.includes(CONFIG.systemManagerRole);
  }
  function hasAIHubRole() { return roles().some(r => CONFIG.aihubRoles.includes(r)); }
  function shouldHide() { return hasAIHubRole() && !isSystemManager(); }

  (function instantHide() {
    try {
      if (!shouldHide()) return;
      if (!document.getElementById(CONFIG.cssId)) {
        const s = document.createElement("style");
        s.id = CONFIG.cssId;
        s.textContent = CONFIG.css;
        document.documentElement.appendChild(s);
      }
    } catch (_) {}
  })();

  function addCssOnce() {
    if (document.getElementById(CONFIG.cssId)) return;
    const s = document.createElement("style");
    s.id = CONFIG.cssId;
    s.textContent = CONFIG.css;
    document.documentElement.appendChild(s);
  }
  function removeCss(){ const s = document.getElementById(CONFIG.cssId); if (s) s.remove(); }

  function hideConnectionsEverywhere() {
    if (!shouldHide()) return;

    // header by text fallback
    document.querySelectorAll(".form-tabs .nav-link").forEach(btn => {
      const t = (btn.textContent || "").trim().toLowerCase();
      if (t === "connections") {
        const li = btn.closest(".nav-item") || btn;
        li.style.display = "none";
        li.setAttribute("aria-hidden", "true");
      }
    });

    // tab panes by label/id
    document.querySelectorAll('.tab-content [role="tabpanel"]').forEach(pane => {
      const label = (pane.getAttribute("aria-labelledby") || "").toLowerCase();
      const id = (pane.id || "").toLowerCase();
      if (label.includes("connections") || id.includes("connections")) {
        pane.style.display = "none";
        pane.setAttribute("aria-hidden", "true");
      }
    });
  }

  function observeDom() {
    new MutationObserver(() => hideConnectionsEverywhere())
      .observe(document.documentElement, { subtree:true, childList:true });
  }
  function hookRouter(){ if (frappe.router?.on) frappe.router.on("change", hideConnectionsEverywhere); }

  function boot() {
    const need = shouldHide();
    try { localStorage.setItem(CONFIG.lsKey, need ? "1" : "0"); } catch {}
    if (need) { addCssOnce(); hideConnectionsEverywhere(); observeDom(); hookRouter(); }
    else { removeCss(); }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
