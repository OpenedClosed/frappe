// === FILE B: List View (drop-in) ===
// Статусы и теги в списке:
// - Цвет статусов тянется из Kanban (window.EC_BOARD_COLORS) по RAW-значению поля.
// - Текст переводится (__(...)), но цвет остаётся как в доске.
// - Прочие теги используют EC_TAG_COLORS через window.tagChip (тоже с переводом текста).

(function () {
  const esc = frappe.utils.escape_html;

  const BOARDS = [
    { board: "CRM Board",                  flag: "show_board_crm",      field: "status_crm_board" },
    { board: "Leads – Contact Center",     flag: "show_board_leads",    field: "status_leads" },
    { board: "Deals – Contact Center",     flag: "show_board_deals",    field: "status_deals" },
    { board: "Patients – Care Department", flag: "show_board_patients", field: "status_patients" },
  ];

  async function ensureBoards() {
    if (typeof window.getBoardColors === "function") {
      await Promise.all(BOARDS.map(b => window.getBoardColors(b.board)));
    }
  }

  function statusToIndicator(cbd) {
    const m = {
      "#fbcfe8":"pink", "#fef3c7":"yellow", "#fed7aa":"orange", "#bae6fd":"light-blue",
      "#dbeafe":"blue", "#e9d5ff":"purple", "#d1fae5":"green", "#fecaca":"red", "#e5e7eb":"gray"
    };
    return m[(cbd||"").toLowerCase()] || "gray";
  }

  function colorMetaFor(board, status) {
    const map = (window.EC_BOARD_COLORS && window.EC_BOARD_COLORS[board]) || {};
    const v = map?.[status] ?? map?.[status?.toLowerCase?.()] ?? null;
    if (!v) return { bd:"#e5e7eb" };
    if (typeof v === "string") return { bd:v };
    return { bd: v.bd || v.bg || v.tx || "#e5e7eb" };
  }

  function indicatorFor(doc) {
    for (const meta of BOARDS) {
      const raw = doc[meta.field];
      if (raw) {
        const { bd } = colorMetaFor(meta.board, raw);
        // текст индикатора — переведён, цвет — из bd
        return [__(raw), statusToIndicator(bd), `${meta.field},=,${raw}`];
      }
    }
    return [__("New"), "gray", ``];
  }

  // Канбан-чип для статуса (fallback, если window.boardChip нет)
  function boardChipLV(board, rawStatus, dashed=false) {
    if (!rawStatus) return "";
    if (typeof window.boardChip === "function") {
      // Заменим текст внутри на переведённый, сохранив стили из boardChip
      const html = window.boardChip(board, rawStatus, dashed);
      try {
        const tmp = document.createElement("div"); tmp.innerHTML = html || "";
        const el = tmp.firstElementChild || tmp;
        const target = (el.querySelector?.(".crm-chip") || el);
        if (target) target.textContent = __(String(rawStatus));
        return el.outerHTML || el.innerHTML || html;
      } catch { return html; }
    }
    // Наш компактный вариант: мягкая подложка, граница по Kanban, тёмный текст
    const { bd } = colorMetaFor(board, rawStatus);
    const rgba = (hex,a)=>{
      const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex||"");
      if (!m) return `rgba(17,24,39,${a})`;
      const r=parseInt(m[1],16), g=parseInt(m[2],16), b=parseInt(m[3],16);
      return `rgba(${r},${g},${b},${a})`;
    };
    const TEXT_DARK = "#111827";
    const style = dashed
      ? `border-color:${bd};border-style:dashed;background:transparent;color:${TEXT_DARK}`
      : `background:${rgba(bd,.12)};border-color:${rgba(bd,.25)};color:${TEXT_DARK}`;
    return `<span class="crm-chip" style="${style}">${esc(__(String(rawStatus)))}</span>`;
  }

  // НЕКАНБАННЫЕ теги — через EC_TAG_COLORS/tagChip, но с переводом текста
  function tagChipI18n(bucket, rawVal) {
    if (typeof window.tagChip === "function") {
      const html = window.tagChip(bucket, rawVal);
      try {
        const tmp = document.createElement("div"); tmp.innerHTML = html || "";
        const el = tmp.firstElementChild || tmp;
        const target = (el.querySelector?.(".crm-chip") || el);
        if (target) target.textContent = __(String(rawVal || ""));
        return el.outerHTML || el.innerHTML || html;
      } catch { return html; }
    }
    // Фолбэк (серый чип)
    return `<span class="crm-chip">${esc(__(String(rawVal||"")))}</span>`;
  }

  frappe.listview_settings["Engagement Case"] = {
    async onload() { await ensureBoards(); },
    get_indicator(doc) { return indicatorFor(doc); },
    formatters: {
      status_crm_board: (v)=>boardChipLV("CRM Board", v),
      status_leads:     (v)=>boardChipLV("Leads – Contact Center", v),
      status_deals:     (v)=>boardChipLV("Deals – Contact Center", v),
      status_patients:  (v)=>boardChipLV("Patients – Care Department", v),

      priority:         (v)=>tagChipI18n("priority", v),
      runtime_status:   (v)=>tagChipI18n("runtime_status", v),
      channel_platform: (v)=>tagChipI18n("platform", v),
      channel_type:     (v)=>tagChipI18n("channel_type", v),
    },
  };
})();