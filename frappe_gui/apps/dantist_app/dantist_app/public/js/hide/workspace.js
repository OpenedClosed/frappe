/* ===== AIHub Workspace Hide (configurable) ===== */
(function () {
  const CONFIG = {
    systemManagerRole: "System Manager",
    aihubRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    lsKey: "aihub_hide_workspace",
    cssId: "aihub-hide-workspace-css",
    css: `
      .workspace-footer .btn-new-workspace,
      .workspace-footer .btn-edit-workspace { display: none !important; }
    `
  };

  /* ===== Role checks ===== */
  function getRoles() {
    return (frappe.boot?.user?.roles) || [];
  }
  function isSystemManager() {
    const roles = getRoles();
    if (frappe.user && typeof frappe.user.has_role === "function") {
      try { return !!frappe.user.has_role(CONFIG.systemManagerRole); } catch {}
    }
    return roles.includes(CONFIG.systemManagerRole);
  }
  function hasAIHubRole() {
    const roles = getRoles();
    return roles.some(r => CONFIG.aihubRoles.includes(r));
  }
  function shouldHide() {
    return hasAIHubRole() && !isSystemManager();
  }

  /* ===== Context ===== */
  function inWorkspaceContext() {
    const r = (frappe.get_route && frappe.get_route()) || [];
    return (r[0] && r[0].toLowerCase() === "workspaces") ||
           (r[0] === "List" && r[1] === "Workspace") ||
           (r[0] === "Form" && r[1] === "Workspace");
  }

  /* ===== Anti-flicker ===== */
  (function instantHide() {
    try {
      if (localStorage.getItem(CONFIG.lsKey) !== "1") return;
      if (document.getElementById(CONFIG.cssId)) return;
      const style = document.createElement("style");
      style.id = CONFIG.cssId;
      style.textContent = CONFIG.css;
      document.documentElement.appendChild(style);
    } catch (_) {}
  })();

  /* ===== DOM ops ===== */
  function addCssOnce() {
    if (document.getElementById(CONFIG.cssId)) return;
    const style = document.createElement("style");
    style.id = CONFIG.cssId;
    style.textContent = CONFIG.css;
    document.documentElement.appendChild(style);
  }
  function removeCss() {
    const css = document.getElementById(CONFIG.cssId);
    if (css) css.remove();
  }
  function hideDom() {
    if (!inWorkspaceContext()) return;
    document.querySelectorAll(".workspace-footer .btn-new-workspace, .workspace-footer .btn-edit-workspace")
      .forEach(b => { b.style.display = "none"; b.setAttribute("aria-hidden", "true"); });
  }

  /* ===== Block programmatic creation/edit ===== */
  function blockProgrammatic() {
    if (!shouldHide()) return;

    const orig_new = frappe.new_doc;
    frappe.new_doc = function (doctype, ...rest) {
      if (doctype === "Workspace") return;
      return orig_new ? orig_new.call(this, doctype, ...rest) : undefined;
    };

    if (frappe.ui?.form?.make_quick_entry) {
      const orig_quick = frappe.ui.form.make_quick_entry;
      frappe.ui.form.make_quick_entry = function (doctype, ...rest) {
        if (doctype === "Workspace") return;
        return orig_quick.call(this, doctype, ...rest);
      };
    }
  }

  /* ===== Observers / Router ===== */
  function observeDom() {
    new MutationObserver(() => hideDom()).observe(document.documentElement, { subtree: true, childList: true });
  }
  function hookRouter() {
    if (frappe.router?.on) frappe.router.on("change", () => hideDom());
  }

  /* ===== Boot ===== */
  function boot() {
    const hide = shouldHide();
    try { localStorage.setItem(CONFIG.lsKey, hide ? "1" : "0"); } catch {}
    if (hide) { addCssOnce(); hideDom(); observeDom(); hookRouter(); blockProgrammatic(); }
    else { removeCss(); }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
