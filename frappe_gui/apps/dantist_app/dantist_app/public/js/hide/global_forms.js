/* ===== AIHub Global Forms Tab Hide (Connections + Settings) ===== */
(function () {
  const CONFIG = {
    systemManagerRole: "System Manager",
    // все AIHub роли, для которых прячем вкладки
    aihubRoles: [
      "AIHub Super Admin", "AIHub Admin", "AIHub Demo",
      "AIHub User", "AIHub Manager", "AIHub Doctor",
      "AIHub Assistant", "Super Admin"
    ],
    lsKey: "aihub_hide_global_tabs",
    cssId: "aihub-hide-global-tabs-css",

    // какие вкладки скрывать (по «человекочитаемому» названию)
    targetTabNames: ["connections", "settings"],

    // anti-flicker CSS: прячет самые типовые варианты id/атрибутов,
    // JS ниже дочищает надёжно по тексту/атрибутам
    css: `
      /* headers by common id/attrs */
      .form-tabs .nav-link[id$="connections_tab-tab"],
      .form-tabs .nav-link[aria-controls*="connections" i],
      .form-tabs .nav-link[id$="settings_tab-tab"],
      .form-tabs .nav-link[aria-controls*="settings" i] { display: none !important; }

      /* tab panes by common id/attrs */
      .tab-content [id$="connections_tab"],
      .tab-content [data-fieldname="connections_tab"],
      .tab-content [id$="settings_tab"],
      .tab-content [data-fieldname="settings_tab"] { display: none !important; }
    `
  };

  /* ---- roles ---- */
  function roles() { return (frappe?.boot?.user?.roles) || []; }
  function isSystemManager() {
    const r = roles();
    if (frappe.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.systemManagerRole); } catch {} }
    return r.includes(CONFIG.systemManagerRole);
  }
  function hasAIHubRole() { return roles().some(r => CONFIG.aihubRoles.includes(r)); }
  function shouldHide() { return hasAIHubRole() && !isSystemManager(); }

  /* ---- anti-flicker ---- */
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

  /* ---- helpers ---- */
  function addCssOnce() {
    if (document.getElementById(CONFIG.cssId)) return;
    const s = document.createElement("style");
    s.id = CONFIG.cssId;
    s.textContent = CONFIG.css;
    document.documentElement.appendChild(s);
  }
  function removeCss(){ const s = document.getElementById(CONFIG.cssId); if (s) s.remove(); }

  function hideEl(el){ if (!el) return; el.style.display = "none"; el.setAttribute("aria-hidden","true"); }

  function hideTargetTabsEverywhere() {
    if (!shouldHide()) return;

    const targets = CONFIG.targetTabNames;

    // 1) заголовки вкладок — надёжно по тексту
    document.querySelectorAll(".form-tabs .nav-link, .form-tabs button").forEach(btn => {
      const t = (btn.textContent || btn.getAttribute("aria-label") || "").trim().toLowerCase();
      if (targets.includes(t)) {
        const li = btn.closest(".nav-item") || btn;
        hideEl(li);
      }
    });

    // 2) панели вкладок — по aria-labelledby/aria-controls/id
    document.querySelectorAll('.tab-content [role="tabpanel"]').forEach(pane => {
      const label = (pane.getAttribute("aria-labelledby") || "").toLowerCase();
      const controls = (pane.getAttribute("aria-controls") || "").toLowerCase();
      const id = (pane.id || "").toLowerCase();
      if (
        targets.some(x =>
          label.includes(x) || controls.includes(x) || id.includes(x + "_tab") || id.endsWith(x)
        )
      ) {
        hideEl(pane);
      }
    });
  }

  /* ---- observers / router ---- */
  function observeDom() {
    new MutationObserver(() => hideTargetTabsEverywhere())
      .observe(document.documentElement, { subtree:true, childList:true, attributes:true, attributeFilter:["class","style","id","aria-labelledby","aria-controls"] });
  }
  function hookRouter(){ if (frappe?.router?.on) frappe.router.on("change", hideTargetTabsEverywhere); }

  /* ---- boot ---- */
  function boot() {
    const need = shouldHide();
    try { localStorage.setItem(CONFIG.lsKey, need ? "1" : "0"); } catch {}
    if (need) { addCssOnce(); hideTargetTabsEverywhere(); observeDom(); hookRouter(); }
    else { removeCss(); }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
