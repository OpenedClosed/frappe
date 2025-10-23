// === FILE A: EC_TAG_COLORS (drop-in) ===
// EC_TAG_COLORS + tagChip: различимая палитра для НЕ-канбанных "тегов"
// Текст переводим (__(...)), цвет подбираем по исходному значению ключа (raw).
(function (w) {
  const PALETTE = {
    gray:   {bg:"#f3f4f6", bd:"#e5e7eb"},
    blue:   {bg:"#eff6ff", bd:"#dbeafe"},
    lightb: {bg:"#f0f9ff", bd:"#bae6fd"},
    purple: {bg:"#f5f3ff", bd:"#e9d5ff"},
    green:  {bg:"#ecfdf5", bd:"#d1fae5"},
    yellow: {bg:"#fffbeb", bd:"#fef3c7"},
    orange: {bg:"#fff7ed", bd:"#fed7aa"},
    red:    {bg:"#fef2f2", bd:"#fecaca"},
    pink:   {bg:"#fdf2f8", bd:"#fbcfe8"},
    teal:   {bg:"#f0fdfa", bd:"#99f6e4"},
    indigo: {bg:"#eef2ff", bd:"#c7d2fe"},
  };

  const platform = {
    "Internal": PALETTE.gray,
    "Instagram": PALETTE.purple,
    "Facebook": PALETTE.blue,
    "WhatsApp": PALETTE.green,
    "Telegram": PALETTE.indigo,
    "Telegram Mini-App": PALETTE.lightb,
    "Telephony": PALETTE.teal,
    "SMS": PALETTE.yellow,
    "Email": PALETTE.orange,
  };

  const channel_type = {
    "Chat": PALETTE.blue,
    "Call": PALETTE.green,
    "SMS": PALETTE.yellow,
    "Email": PALETTE.orange,
    "Web Form": PALETTE.lightb,
  };

  const priority = {
    "Low": PALETTE.gray,
    "Normal": PALETTE.blue,
    "High": PALETTE.orange,
    "Urgent": PALETTE.red,
  };

  const runtime_status = {
    "New Session": PALETTE.lightb,
    "Brief In Progress": PALETTE.purple,
    "Brief Completed": PALETTE.green,
    "Waiting for AI": PALETTE.yellow,
    "Waiting for Client (AI)": PALETTE.yellow,
    "Waiting for Consultant": PALETTE.orange,
    "Read by Consultant": PALETTE.indigo,
    "Waiting for Client": PALETTE.orange,
    "Closed – No Messages": PALETTE.gray,
    "Closed by Timeout": PALETTE.gray,
    "Closed by Operator": PALETTE.green,
  };

  const badge = {
    "Hidden": PALETTE.orange,
    "Parent": PALETTE.indigo,
  };

  w.EC_TAG_COLORS = { platform, channel_type, priority, runtime_status, badge };

  const esc = frappe.utils.escape_html;
  const TEXT_DARK = "#111827";

  // dashed=true → пунктир, иначе — мягкая заливка
  w.tagChip = function (bucket, rawKey, dashed=false) {
    const colorsMap = w.EC_TAG_COLORS?.[bucket] || {};
    const pal = colorsMap[rawKey] || PALETTE.gray;
    const extra = dashed ? "border-style:dashed; background:transparent;" : `background:${pal.bg};`;
    // Текст переводим, цвет — нет
    return `<span class="crm-chip" style="border-color:${pal.bd};${extra}color:${TEXT_DARK}">${esc(__(String(rawKey||"")))}</span>`;
  };
})(window);