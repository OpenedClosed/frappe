// EC_TAG_COLORS + tagChip: различимая палитра для не-канбанных "тегов"
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

  // максимально разные цвета источников:
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

  w.EC_TAG_COLORS = { platform, channel_type, priority, runtime_status };

  w.tagChip = function (bucket, key, dashed=false) {
    const c = (w.EC_TAG_COLORS[bucket] && w.EC_TAG_COLORS[bucket][key]) || PALETTE.gray;
    const esc = frappe.utils.escape_html;
    const extra = dashed ? "border-style:dashed;" : "";
    return `<span class="crm-chip" style="background:${c.bg};border-color:${c.bd};${extra}">${esc(key||"")}</span>`;
  };
})(window);