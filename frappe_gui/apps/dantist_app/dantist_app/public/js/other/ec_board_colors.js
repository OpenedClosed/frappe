// EC_BOARD_COLORS: цвета колонок из Kanban Board (+ утилиты чипов), с поддержкой тёмной темы
(function () {
  // --- палитры под светлую и тёмную темы ---
  const IND_LIGHT = {
    "Pink":   { bg: "#fdf2f8", bd: "#fbcfe8" },
    "Yellow": { bg: "#fffbeb", bd: "#fef3c7" },
    "Orange": { bg: "#fff7ed", bd: "#fed7aa" },
    "Light Blue": { bg: "#f0f9ff", bd: "#bae6fd" },
    "Blue":   { bg: "#eff6ff", bd: "#dbeafe" },
    "Purple": { bg: "#f5f3ff", bd: "#e9d5ff" },
    "Green":  { bg: "#ecfdf5", bd: "#d1fae5" },
    "Red":    { bg: "#fef2f2", bd: "#fecaca" },
    "Gray":   { bg: "#f3f4f6", bd: "#e5e7eb" }
  };

  // тёмные аналоги, согласованы с твоей темой
  const IND_DARK = {
    "Pink":   { bg: "#34222b", bd: "#6b3a57" },
    "Yellow": { bg: "#332c1d", bd: "#6f5b28" },
    "Orange": { bg: "#35261b", bd: "#6f4028" },
    "Light Blue": { bg: "#1f3238", bd: "#3a5563" },
    "Blue":   { bg: "#1a2a3d", bd: "#2e4b72" },
    "Purple": { bg: "#2b223c", bd: "#4a3b6b" },
    "Green":  { bg: "#1c2f26", bd: "#335a46" },
    "Red":    { bg: "#311d1e", bd: "#6b3a3a" },
    "Gray":   { bg: "#243a3f", bd: "#3e555a" }
  };

  function isDark() {
    try {
      return (document.documentElement.getAttribute("data-theme") || "").toLowerCase() === "dark";
    } catch { return false; }
  }
  function PAL() { return isDark() ? IND_DARK : IND_LIGHT; }

  const CACHE = {};
  async function loadBoard(boardName) {
    const paletteTag = isDark() ? "dark" : "light";
    if (CACHE[boardName] && CACHE[boardName].__palette === paletteTag) {
      return CACHE[boardName];
    }
    try {
      const { message: kb } = await frappe.call({
        method: "frappe.client.get",
        args: { doctype: "Kanban Board", name: boardName }
      });
      const pal = PAL();
      const map = {};
      (kb?.columns || []).forEach(c => {
        if ((c.status || "Active") !== "Active") return;
        const ind = c.indicator && pal[c.indicator] ? c.indicator : "Gray";
        map[c.column_name] = pal[ind];
      });
      map.__palette = paletteTag;
      CACHE[boardName] = map;
      return map;
    } catch (e) {
      console.warn("[EC_BOARD_COLORS] load failed", boardName, e);
      const m = { __palette: paletteTag };
      CACHE[boardName] = m;
      return m;
    }
  }

  // публичный API
  window.EC_BOARD_COLORS = window.EC_BOARD_COLORS || {};
  window.getBoardColors = async (boardName) => {
    const paletteTag = isDark() ? "dark" : "light";
    const cached = window.EC_BOARD_COLORS[boardName];
    if (cached && cached.__palette === paletteTag) return cached;
    const map = await loadBoard(boardName);
    window.EC_BOARD_COLORS[boardName] = map;
    return map;
  };

  // авто-сброс кешей при смене темы
  try {
    const mo = new MutationObserver(() => {
      const tag = isDark() ? "dark" : "light";
      Object.keys(window.EC_BOARD_COLORS).forEach(k => delete window.EC_BOARD_COLORS[k]);
      Object.keys(CACHE).forEach(k => delete CACHE[k]);
      window.dispatchEvent(new CustomEvent("ec_board_colors:theme_changed", { detail: { palette: tag } }));
    });
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  } catch {}

  const esc = (s)=>frappe.utils.escape_html(s||"");
  // dashed=true → только цветной пунктир (без заливки)
  window.boardChip = function (boardName, status, dashed=false) {
    const pal = PAL();
    const m = window.EC_BOARD_COLORS[boardName] || {};
    const st = status || "";
    const currentPalette = isDark() ? "dark" : "light";
    const c  = (m[st] && m.__palette === currentPalette) ? m[st] : pal.Gray;
    const base = `border-color:${c.bd} !important;`;
    const fill = dashed
      ? "background:transparent !important;border-style:dashed !important;"
      : `background:${c.bg} !important;`;
    return `<span class="crm-chip -kanban" style="${base}${fill}">${esc(st)}</span>`;
  };
})();