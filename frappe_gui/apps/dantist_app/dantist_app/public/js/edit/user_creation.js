// === DNT User Roles UX — v1.1 ===
// Блокируем автопереход в Role Profile после создания User,
// форсим вкладку "Roles & Permissions" с нормальными ролями,
// и для User вместо quick entry всегда открываем полную форму.

(() => {
  if (window.dntUserRolesUxReady) return;
  window.dntUserRolesUxReady = true;

  // ===== Helpers =====

  function open_roles_tab(frm) {
    if (!frm || frm.doctype !== "User") return;

    const nav = frm.$wrapper && frm.$wrapper.find(
      '.form-tabs .nav-link[data-fieldname="roles_permissions_tab"]'
    );

    if (nav && nav.length) {
      nav[0].click();
    }
  }

  function tune_roles_section(frm) {
    if (!frm || frm.doctype !== "User") return;

    if (frm.fields_dict && frm.fields_dict.role_profile_name) {
      const field = frm.fields_dict.role_profile_name;
      if (field.df && !field.df.hidden) {
        field.df.hidden = 1;
        field.refresh();
      }
    }

    if (frm.get_field) {
      const sb1 = frm.get_field("sb1");
      if (sb1 && sb1.$wrapper) {
        sb1.$wrapper.css({
          display: "block",
          visibility: "visible",
          opacity: 1
        });
      }
    }
  }

  // ===== Route patch: режем переход к списку Role Profile =====

  const original_set_route = frappe.set_route;

  frappe.set_route = function () {
    const args = Array.from(arguments);
    let goes_to_role_profile = false;

    if (args.length === 1 && typeof args[0] === "string") {
      const token = String(args[0] || "");
      if (
        token.includes("List/Role Profile") ||
        token.includes("List/Role%20Profile") ||
        token.includes("app/role-profile")
      ) {
        goes_to_role_profile = true;
      }
    }

    if (
      args[0] === "List" &&
      (args[1] === "Role Profile" || args[1] === "Role%20Profile")
    ) {
      goes_to_role_profile = true;
    }

    if (goes_to_role_profile && cur_frm && cur_frm.doctype === "User") {
      setTimeout(() => {
        tune_roles_section(cur_frm);
        open_roles_tab(cur_frm);
      });

      return cur_frm;
    }

    return original_set_route.apply(this, args);
  };

  // ===== Quick Entry patch: для User всегда полная форма =====

  const original_new_doc = frappe.new_doc;

  frappe.new_doc = function () {
    const args = Array.from(arguments);
    const doctype = args[0];

    if (doctype === "User") {
      let opts = null;
      let callback = null;

      if (args.length > 1) {
        if (typeof args[1] === "function") {
          callback = args[1];
        } else if (args[1] && typeof args[1] === "object") {
          opts = args[1];
          if (typeof opts.callback === "function") {
            callback = opts.callback;
          }
        }
      }

      frappe.model.with_doctype("User", () => {
        const doc = frappe.model.get_new_doc("User");

        if (opts && opts.fields && typeof opts.fields === "object") {
          Object.assign(doc, opts.fields);
        }

        if (callback) {
          try {
            callback(doc);
          } catch (e) {
            // глушим, чтобы не ломать основной флоу
          }
        }

        frappe.set_route("Form", "User", doc.name);
      });

      return;
    }

    return original_new_doc.apply(this, args);
  };

  // ===== User form hooks =====

  frappe.ui.form.on("User", {
    refresh(frm) {
      tune_roles_section(frm);
    }
  });
})();