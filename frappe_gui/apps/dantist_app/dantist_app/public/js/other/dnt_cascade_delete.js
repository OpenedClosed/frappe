// === DNT Global Cascade Delete — v3.0 ===
// Перехват ошибок удаления и предложение каскадного delete.
// Работает:
//  - при удалении из формы (Form → Delete),
//  - при bulk-delete из списка (List → Select → Delete).
//
// Логика:
//  1) Если в сообщении есть "Cannot delete or cancel because..." или "Failed to delete...":
//     - НЕ показываем стандартный msgprint Frappe для этого сообщения;
//     - анализируем контекст (List / Form) и, если можем, собираем doctype + имена;
//     - показываем свой frappe.confirm с предложением каскадного удаления.
//  2) При подтверждении вызываем:
//        dantist_app.api.utils.cascade_delete_bulk(doctype, names)
//
// Все пользовательские строки — через __().

(function () {
  if (window.__DNT_GLOBAL_CASCADE_DELETE_V3) return;
  window.__DNT_GLOBAL_CASCADE_DELETE_V3 = true;

  const CFG = {
    exclude_doctypes: new Set([
      "DocType",
      "Customize Form",
      "User",
      "Role",
      "System Settings",
      "Report",
      "Print Format",
      "Dashboard",
      "Dashboard Chart",
      "Workspace"
    ]),
    server_method: "dantist_app.api.utils.cascade_delete_bulk",
    debounce_ms: 2000
  };

  let last_ctx_key = null;
  let last_ctx_at = 0;

  function get_plain_text(msg) {
    if (!msg) return "";
    if (typeof msg === "string") return msg;
    if (typeof msg === "object") {
      if (msg.message) return msg.message;
      if (msg.exc) return msg.exc;
    }
    return String(msg || "");
  }

  function strip_html(text) {
    if (!text) return "";
    return String(text).replace(/<[^>]+>/g, " ");
  }

  function has_delete_link_error(text) {
    if (!text) return false;
    const plain = strip_html(text);
    return (
      /Cannot delete or cancel because/i.test(plain) ||
      /Failed to delete/i.test(plain)
    );
  }

  function extract_names_from_message(text) {
    if (!text) return null;
    const plain = strip_html(text).replace(/\s+/g, " ").trim();

    // Типичный фрагмент:
    // "Failed to delete 2 documents: IE-2025-00816, IE-2025-00815"
    const m = plain.match(/Failed to delete[^:]*:\s*(.+)$/i);
    if (m && m[1]) {
      return m[1]
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    }
    return null;
  }

  function get_delete_context(message_text) {
    // 1) Попробуем вытащить имена из текста
    const msg_names = extract_names_from_message(message_text);

    // 2) Если мы на списке
    if (window.cur_list && cur_list.doctype) {
      const doctype = cur_list.doctype;
      if (CFG.exclude_doctypes.has(doctype)) return null;

      let names = msg_names;
      if (!names || !names.length) {
        try {
          if (typeof cur_list.get_checked_items === "function") {
            const items = cur_list.get_checked_items() || [];
            names = items.map((r) => r && r.name).filter(Boolean);
          } else if (typeof cur_list.get_selected === "function") {
            names = (cur_list.get_selected() || []).filter(Boolean);
          }
        } catch (e) {
          names = [];
        }
      }

      if (names && names.length) {
        return { kind: "list", doctype, names };
      }
    }

    // 3) Если открыта форма
    if (window.cur_frm && cur_frm.doctype && cur_frm.doc && cur_frm.doc.name) {
      const doctype = cur_frm.doctype;
      if (CFG.exclude_doctypes.has(doctype)) return null;
      const names = msg_names && msg_names.length ? msg_names : [cur_frm.doc.name];
      return { kind: "form", doctype, names };
    }

    return null;
  }

  function should_trigger_for(ctx) {
    const key = ctx.doctype + "::" + ctx.names.slice().sort().join(",");
    const now = Date.now();
    if (key === last_ctx_key && now - last_ctx_at < CFG.debounce_ms) {
      return false;
    }
    last_ctx_key = key;
    last_ctx_at = now;
    return true;
  }

  function show_cascade_confirm(ctx) {
    const msg = __(
      "Some documents could not be deleted because they are linked to other records."
    );
    const note = __(
      "You can delete linked records manually or use cascade delete. Do you want to delete the selected documents together with all linked records?"
    );

    const html =
      "<p>" +
      frappe.utils.escape_html(msg) +
      "</p><p><strong>" +
      frappe.utils.escape_html(note) +
      "</strong></p>";

    frappe.confirm(
      html,
      () => {
        frappe.call({
          method: CFG.server_method,
          args: {
            doctype: ctx.doctype,
            names: ctx.names
          },
          freeze: true,
          freeze_message: __("Deleting…"),
          callback(r) {
            if (r && !r.exc) {
              frappe.show_alert({
                message: __("Documents and linked records have been deleted."),
                indicator: "green"
              });

              if (ctx.kind === "list" && window.cur_list) {
                cur_list.refresh();
              } else if (ctx.kind === "form") {
                frappe.set_route("List", ctx.doctype);
              }
            }
          },
          error(err) {
            frappe.msgprint({
              title: __("Error"),
              message: __("Cascade delete failed. Please check server logs."),
              indicator: "red"
            });
          }
        });
      },
      () => {
        // Cancel — ничего не делаем
      }
    );
  }

  // Патчим frappe.msgprint
  const orig_msgprint = frappe.msgprint;
  frappe.msgprint = function (message, title, as_raw) {
    try {
      const text = get_plain_text(message);
      if (has_delete_link_error(text)) {
        const ctx = get_delete_context(text);
        if (ctx && should_trigger_for(ctx)) {
          show_cascade_confirm(ctx);
        }
        // ВАЖНО: не показываем стандартное msgprint для этой ошибки
        return;
      }
    } catch (e) {
      // если что-то пошло не так — откатываемся к стандартному поведению
    }

    return orig_msgprint.apply(this, arguments);
  };
})();