// === FILE A: EC_TAG_COLORS (drop-in) ===
// EC_TAG_COLORS + tagChip: различимая палитра для НЕ-канбанных "тегов"
// Теперь с поддержкой тёмной темы (как у доски): светлые мягкие бейджи в light,
// приглушённые, но контрастные в dark. API не менялся.
(function (w) {
  function isDark() {
    try {
      return (document.documentElement.getAttribute("data-theme") || "").toLowerCase() === "dark";
    } catch { return false; }
  }

  // --- палитры ---
  const PALETTE_LIGHT = {
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

  // Согласовано с дарк-темой (см. твою тему и палитру для канбана)
  const PALETTE_DARK = {
    gray:   {bg:"#243a3f", bd:"#3e555a"},
    blue:   {bg:"#1a2a3d", bd:"#2e4b72"},
    lightb: {bg:"#1f3238", bd:"#3a5563"},
    purple: {bg:"#2b223c", bd:"#4a3b6b"},
    green:  {bg:"#1c2f26", bd:"#335a46"},
    yellow: {bg:"#332c1d", bd:"#6f5b28"},
    orange: {bg:"#35261b", bd:"#6f4028"},
    red:    {bg:"#311d1e", bd:"#6b3a3a"},
    pink:   {bg:"#34222b", bd:"#6b3a57"},
    teal:   {bg:"#1b2f2b", bd:"#2f5f57"},
    indigo: {bg:"#1f2a3f", bd:"#3c4f78"},
  };

  function PAL() { return isDark() ? PALETTE_DARK : PALETTE_LIGHT; }

  const platform = {
    "Internal": PAL().gray,
    "Instagram": PAL().purple,
    "Facebook": PAL().blue,
    "WhatsApp": PAL().green,
    "Telegram": PAL().indigo,
    "Telegram Mini-App": PAL().lightb,
    "Telephony": PAL().teal,
    "SMS": PAL().yellow,
    "Email": PAL().orange,
  };

  const channel_type = {
    "Chat": PAL().blue,
    "Call": PAL().green,
    "SMS": PAL().yellow,
    "Email": PAL().orange,
    "Web Form": PAL().lightb,
  };

  const priority = {
    "Low": PAL().gray,
    "Normal": PAL().blue,
    "High": PAL().orange,
    "Urgent": PAL().red,
  };

  const runtime_status = {
    "New Session": PAL().lightb,
    "Brief In Progress": PAL().purple,
    "Brief Completed": PAL().green,
    "Waiting for AI": PAL().yellow,
    "Waiting for Client (AI)": PAL().yellow,
    "Waiting for Consultant": PAL().orange,
    "Read by Consultant": PAL().indigo,
    "Waiting for Client": PAL().orange,
    "Closed – No Messages": PAL().gray,
    "Closed by Timeout": PAL().gray,
    "Closed by Operator": PAL().green,
  };

  const badge = {
    "Hidden": PAL().orange,
    "Parent": PAL().indigo,
  };

  w.EC_TAG_COLORS = { platform, channel_type, priority, runtime_status, badge };

  const esc = frappe.utils.escape_html;
  const TEXT_LIGHT = "#f4f8f9"; // для дарка
  const TEXT_DARK  = "#111827"; // для лайта

  // dashed=true → пунктир, иначе — мягкая заливка
  w.tagChip = function (bucket, rawKey, dashed=false) {
    const colorsMap = w.EC_TAG_COLORS?.[bucket] || {};
    const pal = colorsMap[rawKey] || PAL().gray;
    const extra = dashed ? "border-style:dashed; background:transparent;" : `background:${pal.bg};`;
    const textColor = isDark() ? TEXT_LIGHT : TEXT_DARK;
    // Текст переводим, цвет — от ключа/палитры
    return `<span class="crm-chip" style="border-color:${pal.bd};${extra}color:${textColor}">${esc(__(String(rawKey||"")))}</span>`;
  };

  // авто-реинициализация при смене темы (чтобы новые чипы были уже с нужной палитрой)
  try {
    const mo = new MutationObserver(() => {
      // ничего не кэшируем — новые вызовы PAL() возьмут свежую палитру
      w.dispatchEvent(new CustomEvent("ec_tag_colors:theme_changed", { detail: { palette: isDark() ? "dark" : "light" } }));
    });
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  } catch {}
})(window);