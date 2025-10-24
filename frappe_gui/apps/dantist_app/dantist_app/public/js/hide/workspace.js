/* ========================================================================
   Workspace Controls (role-based, reusable)
   — Hides “New Workspace” and “Edit Workspace” UI for restricted roles
   — Blocks programmatic Workspace creation via frappe APIs
   — Route guard: only applies on Workspace contexts
   — System Manager (or other privileged role) is always untouched
   ======================================================================== */
(function () {
  // ===== CONFIG (rename roles here for other projects) =====
  const CONFIG = {
    privilegedRole: "System Manager",
    restrictedRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    lsKey: "rbac_hide_workspace",
    cssId: "rbac-hide-workspace-css",
    css: `
      .workspace-footer .btn-new-workspace,
      .workspace-footer .btn-edit-workspace { display: none !important; }
    `
  };

  // ===== ROLE HELPERS =====
  function current_roles() {
    return (window.frappe?.boot?.user?.roles) || [];
  }
  function is_privileged() {
    const roles = current_roles();
    if (window.frappe?.user && typeof frappe.user.has_role === "function") {
      try { return !!frappe.user.has_role(CONFIG.privilegedRole); } catch {}
    }
    return roles.includes(CONFIG.privilegedRole);
  }
  function in_restricted_group() {
    const roles = current_roles();
    return roles.some(r => CONFIG.restrictedRoles.includes(r));
  }
  function should_hide() {
    return in_restricted_group() && !is_privileged();
  }

  // ===== CONTEXT GUARD =====
  function in_workspace_context() {
    const r = (window.frappe?.get_route && frappe.get_route()) || [];
    return (r[0] && String(r[0]).toLowerCase() === "workspaces") ||
           (r[0] === "List" && r[1] === "Workspace") ||
           (r[0] === "Form" && r[1] === "Workspace");
  }

  // ===== ANTI-FLICKER CSS =====
  (function instant_hide() {
    try {
      if (localStorage.getItem(CONFIG.lsKey) !== "1") return;
      if (document.getElementById(CONFIG.cssId)) return;
      const style = document.createElement("style");
      style.id = CONFIG.cssId;
      style.textContent = CONFIG.css;
      document.documentElement.appendChild(style);
    } catch (_) {}
  })();

  // ===== DOM OPS =====
  function add_css_once() {
    if (document.getElementById(CONFIG.cssId)) return;
    const style = document.createElement("style");
    style.id = CONFIG.cssId;
    style.textContent = CONFIG.css;
    document.documentElement.appendChild(style);
  }
  function remove_css() {
    const css = document.getElementById(CONFIG.cssId);
    if (css) css.remove();
  }
  function hide_workspace_buttons() {
    if (!in_workspace_context()) return;
    document
      .querySelectorAll(".workspace-footer .btn-new-workspace, .workspace-footer .btn-edit-workspace")
      .forEach(btn => { btn.style.display = "none"; btn.setAttribute("aria-hidden", "true"); });
  }

  // ===== BLOCK PROGRAMMATIC CREATION/EDIT =====
  function block_programmatic_api() {
    if (!should_hide()) return;

    // Block quick creation
    if (window.frappe?.ui?.form?.make_quick_entry) {
      const original_quick = frappe.ui.form.make_quick_entry;
      frappe.ui.form.make_quick_entry = function (doctype, ...rest) {
        if (doctype === "Workspace") return; // swallow
        return original_quick.call(this, doctype, ...rest);
      };
    }

    // Block standard new_doc
    if (window.frappe?.new_doc) {
      const original_new = frappe.new_doc;
      frappe.new_doc = function (doctype, ...rest) {
        if (doctype === "Workspace") return; // swallow
        return typeof original_new === "function" ? original_new.call(this, doctype, ...rest) : undefined;
      };
    }
  }

  // ===== OBSERVERS / ROUTER =====
  function observe_dom() {
    try {
      new MutationObserver(() => hide_workspace_buttons())
        .observe(document.documentElement, { subtree: true, childList: true });
    } catch (_) {}
  }
  function hook_router() {
    try {
      if (window.frappe?.router?.on) {
        frappe.router.on("change", () => hide_workspace_buttons());
      }
    } catch (_) {}
  }

  // ===== BOOTSTRAP =====
  function boot() {
    const hide = should_hide();
    try { localStorage.setItem(CONFIG.lsKey, hide ? "1" : "0"); } catch {}
    if (hide) {
      add_css_once();
      hide_workspace_buttons();
      observe_dom();
      hook_router();
      block_programmatic_api();
    } else {
      remove_css();
    }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
