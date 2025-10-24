/* ========================================================================
   User Roles & Modules Controls (scoped to Form/User, role-based)
   — For restricted (AIHub* except System Manager):
       · Hide "Allow Modules" section (data-fieldname="sb_allow_modules")
       · Roles section (data-fieldname="sb1"):
           · Super role: show section, hide "Role Profile", keep only AIHub* roles
           · Others: hide entire Roles section
   — System Manager: untouched (and inline styles are reverted if needed)
   ======================================================================== */
(function () {
  // ===== CONFIG (rename roles for other projects) =====
  const CONFIG = {
    privilegedRole: "System Manager",
    restrictedRoles: [
      "AIHub Super Admin", "AIHub Admin", "AIHub Demo",
      "AIHub User", "AIHub Manager", "AIHub Doctor",
      "AIHub Assistant", "Super Admin"
    ],
    superRole: "AIHub Super Admin",

    // route guard
    formRouteDoctype: "User",
    // selectors
    selAllowModulesSection: '.row.form-section[data-fieldname="sb_allow_modules"]',
    selRolesSection:        '.row.form-section[data-fieldname="sb1"]',
    selRoleProfileCtrl:     '.frappe-control[data-fieldname="role_profile_name"]',
    selRolesMultiCheck:     '.frappe-control[data-fieldname="roles"] .checkbox-options .checkbox.unit-checkbox'
  };

  // ===== roles =====
  function roles() { return (window.frappe?.boot?.user?.roles) || []; }
  function is_privileged() {
    const r = roles();
    if (window.frappe?.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.privilegedRole); } catch {} }
    return r.includes(CONFIG.privilegedRole);
  }
  function in_restricted_group() { return roles().some(r => CONFIG.restrictedRoles.includes(r)); }
  function is_super() { return roles().includes(CONFIG.superRole); }
  function restricted_active() { return in_restricted_group() && !is_privileged(); }

  // ===== route guard: only Form/User/* =====
  function on_user_form_route() {
    const rt = (window.frappe?.get_route && frappe.get_route()) || [];
    if (rt[0] === "Form" && rt[1] === CONFIG.formRouteDoctype) return true;
    const dr = document.body?.getAttribute("data-route") || "";
    const re = new RegExp(`(^|/)Form/${CONFIG.formRouteDoctype}/`, "i");
    return re.test(dr);
  }

  // ===== DOM helpers =====
  function hide(el){ if (!el) return; el.style.display = "none"; el.setAttribute("aria-hidden","true"); }
  function show_imp(el, display="block"){
    if (!el) return;
    el.style.setProperty("display", display, "important");
    el.style.setProperty("visibility", "visible", "important");
    el.style.setProperty("opacity", "1", "important");
    el.removeAttribute("aria-hidden");
    el.classList.remove("hidden","hide");
  }
  function unhide_tree_to(el, stopSelector) {
    if (!el) return;
    let p = el;
    while (p && p !== document.documentElement) {
      if (p.matches(stopSelector)) show_imp(p, "block");
      p = p.parentElement;
    }
  }

  // ===== core apply =====
  function apply_once() {
    if (!on_user_form_route()) return;

    const secAllow = document.querySelector(CONFIG.selAllowModulesSection);
    const secRoles = document.querySelector(CONFIG.selRolesSection);
    const roleProfile = secRoles?.querySelector(CONFIG.selRoleProfileCtrl);

    if (!restricted_active()) {
      // System Manager or non-restricted — restore visibility if something was hidden
      [secAllow, secRoles, roleProfile].forEach(el => { if (el){ el.style.removeProperty("display"); el.removeAttribute("aria-hidden"); }});
      if (secRoles) {
        // restore all role checkboxes
        secRoles.querySelectorAll(CONFIG.selRolesMultiCheck).forEach(li => {
          li.style.removeProperty("display"); li.removeAttribute("aria-hidden");
        });
      }
      return;
    }

    // Hide Allow Modules for all restricted
    if (secAllow) hide(secAllow);

    // Roles section per restricted role
    if (!secRoles) return;

    if (is_super()) {
      // Super: show section, hide Role Profile control, keep only AIHub* roles
      show_imp(secRoles, "block");
      unhide_tree_to(secRoles, ".row.form-section, .section-body, .layout-main-section, .page-form");

      if (roleProfile) hide(roleProfile);

      // keep only checkboxes with data-unit starting with "AIHub"
      secRoles.querySelectorAll(CONFIG.selRolesMultiCheck).forEach(li => {
        const unit = li.querySelector('[data-unit]')?.getAttribute('data-unit') || "";
        if (/^AIHub(\s|$)/.test(unit)) {
          li.style.removeProperty("display"); li.removeAttribute("aria-hidden");
        } else {
          hide(li);
        }
      });
    } else {
      // Other restricted (Admin/Demo/etc.): hide entire Roles section
      hide(secRoles);
    }
  }

  // ===== debounced observer =====
  let scheduled = false;
  function schedule_apply() {
    if (scheduled) return;
    scheduled = true;
    setTimeout(() => { scheduled = false; apply_once(); }, 60);
  }

  function observe() {
    try {
      new MutationObserver(() => { if (on_user_form_route()) schedule_apply(); })
        .observe(document.body || document.documentElement, { childList: true, subtree: true });
    } catch (_) {}
  }
  function hook_router(){ if (window.frappe?.router?.on) frappe.router.on("change", () => { if (on_user_form_route()) schedule_apply(); }); }

  // ===== boot =====
  function boot() { apply_once(); observe(); hook_router(); }
  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
