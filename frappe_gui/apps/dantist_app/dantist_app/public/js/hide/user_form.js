// /* ========================================================================
//    User Form Cleanup (scoped to Form/User, role-based)
//    — Hides: assignments / shared / sidebar-stats / follow (restricted roles)
//    — Route guard: only on Form/User/*
//    — Privileged role is untouched
//    — NOTE: timeline/comments/meta/New Email handled globally in global_forms.js
//    ======================================================================== */
// (function () {
//   // ===== CONFIG =====
//   const CONFIG = {
//     privilegedRole: "System Manager",
//     restrictedRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],

//     cssId: "rbac-hide-user-form-css",
//     cssInstantId: "rbac-hide-user-form-INSTANT-css",

//     cssCommon: `
//       body[data-route*="Form/User/"] .form-assignments,
//       body[data-route*="Form/User/"] .form-shared,
//       body[data-route*="Form/User/"] .form-sidebar-stats,
//       body[data-route*="Form/User/"] .form-sidebar .form-follow { display: none !important; }
//     `,
//     cssInstant: `
//       body[data-route*="Form/User/"] .form-assignments,
//       body[data-route*="Form/User/"] .form-shared,
//       body[data-route*="Form/User/"] .form-sidebar-stats,
//       body[data-route*="Form/User/"] .form-sidebar .form-follow { display: none !important; }
//     `
//   };

//   // ===== ROLES =====
//   function roles() { return (window.frappe?.boot?.user?.roles) || []; }
//   function is_privileged() {
//     const r = roles();
//     if (window.frappe?.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.privilegedRole); } catch {} }
//     return r.includes(CONFIG.privilegedRole);
//   }
//   function in_restricted_group() { return roles().some(r => CONFIG.restrictedRoles.includes(r)); }
//   function should_hide() { return in_restricted_group() && !is_privileged(); }

//   // ===== ROUTE GUARD =====
//   function on_user_form_route() {
//     const rt = (window.frappe?.get_route && frappe.get_route()) || [];
//     if (rt[0] === "Form" && rt[1] === "User") return true;
//     const dr = document.body?.getAttribute("data-route") || "";
//     return /(^|\/)Form\/User\//i.test(dr);
//   }

//   // ===== CSS HELPERS =====
//   function add_css_once(id, css) {
//     if (document.getElementById(id)) return;
//     const s = document.createElement("style");
//     s.id = id;
//     s.textContent = css;
//     document.documentElement.appendChild(s);
//   }
//   function remove_css(id) { const s = document.getElementById(id); if (s) s.remove(); }

//   // ===== CORE =====
//   function apply_once() {
//     if (!on_user_form_route()) return;
//     if (should_hide()) add_css_once(CONFIG.cssId, CONFIG.cssCommon);
//     else remove_css(CONFIG.cssId);
//   }

//   function schedule_apply() { [0, 40, 120, 300, 800].forEach(ms => setTimeout(apply_once, ms)); }

//   function observe() {
//     try {
//       new MutationObserver(() => { if (on_user_form_route()) schedule_apply(); })
//         .observe(document.body || document.documentElement, {
//           childList: true, subtree: true, attributes: true, attributeFilter: ["class","style","data-route"]
//         });
//     } catch (_) {}
//   }
//   function hook_router() { if (window.frappe?.router?.on) frappe.router.on("change", schedule_apply); }

//   // ===== BOOT =====
//   (function instant() { add_css_once(CONFIG.cssInstantId, CONFIG.cssInstant); })();
//   function boot() { schedule_apply(); observe(); hook_router(); }

//   if (window.frappe?.after_ajax) frappe.after_ajax(boot);
//   else document.addEventListener("DOMContentLoaded", boot);
// })();
