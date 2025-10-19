// List View — статусы по цветам Kanban, прочие теги из EC_TAG_COLORS
(function () {
  const esc = frappe.utils.escape_html;

  const BOARDS = [
    { board: "CRM Board",                  flag: "show_board_crm",      field: "status_crm_board" },
    { board: "Leads – Contact Center",     flag: "show_board_leads",    field: "status_leads" },
    { board: "Deals – Contact Center",     flag: "show_board_deals",    field: "status_deals" },
    { board: "Patients – Care Department", flag: "show_board_patients", field: "status_patients" },
  ];

  function statusToIndicator(cbd) {
    const m = {
      "#fbcfe8":"pink","#fef3c7":"yellow","#fed7aa":"orange","#bae6fd":"light-blue",
      "#dbeafe":"blue","#e9d5ff":"purple","#d1fae5":"green","#fecaca":"red","#e5e7eb":"gray"
    };
    return m[(cbd||"").toLowerCase()] || "gray";
  }

  async function ensureBoards() {
    if (!window.getBoardColors) return;
    await Promise.all(BOARDS.map(b => getBoardColors(b.board)));
  }

  function indicatorFor(doc) {
    for (const meta of BOARDS) {
      const st = doc[meta.field];
      if (st) {
        const map = (window.EC_BOARD_COLORS && window.EC_BOARD_COLORS[meta.board]) || {};
        const col = map[st] || { bd:"#e5e7eb" };
        return [__(st), statusToIndicator(col.bd), `${meta.field},=,${st}`];
      }
    }
    return [__("New"), "gray", ``];
  }

  function chipBoard(board, text, dashed=false) {
    return window.boardChip ? window.boardChip(board, text, dashed) : `<span class="crm-chip">${esc(text||"")}</span>`;
  }
  function chipTag(bucket, val) {
    return window.tagChip ? window.tagChip(bucket, val) : `<span class="crm-chip">${esc(val||"")}</span>`;
  }

  frappe.listview_settings["Engagement Case"] = {
    async onload() { await ensureBoards(); },
    get_indicator(doc) { return indicatorFor(doc); },
    formatters: {
      status_crm_board: (v)=>chipBoard("CRM Board", v),
      status_leads:     (v)=>chipBoard("Leads – Contact Center", v),
      status_deals:     (v)=>chipBoard("Deals – Contact Center", v),
      status_patients:  (v)=>chipBoard("Patients – Care Department", v),

      priority:         (v)=>chipTag("priority", v),
      runtime_status:   (v)=>chipTag("runtime_status", v),
      channel_platform: (v)=>chipTag("platform", v),
      channel_type:     (v)=>chipTag("channel_type", v),
    },
  };
})();