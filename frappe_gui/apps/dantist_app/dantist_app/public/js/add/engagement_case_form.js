// Form (card) customizations for DocType: Engagement Case
(function () {
  const C = window.EC_COLORS || {};

  function addIndicator(frm, label, val, color) {
    if (!val) return;
    frm.dashboard.add_indicator(__("{0}: {1}", [label, val]), color || "gray");
  }

  frappe.ui.form.on("Engagement Case", {
    refresh(frm) {
      frm.dashboard.clear_headline && frm.dashboard.clear_headline();

      const crm = frm.doc.crm_status || "New";
      const run = frm.doc.runtime_status || "";
      const pri = frm.doc.priority || "";
      const chp = frm.doc.channel_platform || "";
      const cht = frm.doc.channel_type || "";

      addIndicator(frm, "CRM", crm, C.crm_status && C.crm_status[crm]);
      addIndicator(frm, "Runtime", run, C.runtime_status && C.runtime_status[run]);
      addIndicator(frm, "Priority", pri, C.priority && C.priority[pri]);
      addIndicator(frm, "Channel", chp, C.platform && C.platform[chp]);
      addIndicator(frm, "Transport", cht, C.channel_type && C.channel_type[cht]);
    },
  });
})();