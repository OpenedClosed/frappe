// List View customizations for DocType: Engagement Case
(function () {
  const C = window.EC_COLORS || {};
  const esc = frappe.utils.escape_html;

  // рисуем именно "таблетку", а не просто точку
  function pill(value, color) {
    const safe = esc(value || "-");
    const c = color || "gray";
    return `<span class="indicator-pill ${c}">${safe}</span>`;
  }

  frappe.listview_settings["Engagement Case"] = {
    hide_name_column: true,
    add_fields: [
      "crm_status", "priority", "runtime_status",
      "channel_platform", "channel_type",
      "last_event_at", "events_count", "unanswered_count"
    ],

    // левый индикатор рядом с названием — оставляем как есть
    get_indicator(doc) {
      const st = doc.crm_status || "New";
      const color = (C.crm_status && C.crm_status[st]) || "gray";
      return [__(st), color, `crm_status,=,${st}`];
    },

    // «таблетки» в ячейках
    formatters: {
      crm_status(val) {
        return pill(val, C.crm_status && C.crm_status[val]);
      },
      priority(val) {
        return pill(val, C.priority && C.priority[val]);
      },
      runtime_status(val) {
        return pill(val, C.runtime_status && C.runtime_status[val]);
      },
      channel_platform(val) {
        return pill(val, C.platform && C.platform[val]);
      },
      channel_type(val) {
        return pill(val, C.channel_type && C.channel_type[val]);
      },
    },
  };
})();