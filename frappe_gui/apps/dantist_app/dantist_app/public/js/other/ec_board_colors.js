// EC_BOARD_COLORS: цвета колонок из Kanban Board (+ утилиты чипов)
(function () {
  const IND = {
    "Pink":{bg:"#fdf2f8",bd:"#fbcfe8"},"Yellow":{bg:"#fffbeb",bd:"#fef3c7"},
    "Orange":{bg:"#fff7ed",bd:"#fed7aa"},"Light Blue":{bg:"#f0f9ff",bd:"#bae6fd"},
    "Blue":{bg:"#eff6ff",bd:"#dbeafe"},"Purple":{bg:"#f5f3ff",bd:"#e9d5ff"},
    "Green":{bg:"#ecfdf5",bd:"#d1fae5"},"Red":{bg:"#fef2f2",bd:"#fecaca"},
    "Gray":{bg:"#f3f4f6",bd:"#e5e7eb"}
  };

  const CACHE = {};
  async function loadBoard(boardName) {
    if (CACHE[boardName]) return CACHE[boardName];
    try {
      const { message: kb } = await frappe.call({
        method: "frappe.client.get",
        args: { doctype: "Kanban Board", name: boardName }
      });
      const map = {};
      (kb?.columns || []).forEach(c => {
        if ((c.status || "Active") !== "Active") return;
        map[c.column_name] = IND[c.indicator] || IND.Gray;
      });
      CACHE[boardName] = map;
      return map;
    } catch (e) {
      console.warn("[EC_BOARD_COLORS] load failed", boardName, e);
      CACHE[boardName] = {};
      return {};
    }
  }

  window.EC_BOARD_COLORS = window.EC_BOARD_COLORS || {};
  window.getBoardColors = async (boardName) => {
    if (window.EC_BOARD_COLORS[boardName]) return window.EC_BOARD_COLORS[boardName];
    const map = await loadBoard(boardName);
    window.EC_BOARD_COLORS[boardName] = map;
    return map;
  };

  const esc = (s)=>frappe.utils.escape_html(s||"");
  // dashed=true → ТОЛЬКО цветной пунктир, БЕЗ заливки
  window.boardChip = function (boardName, status, dashed=false) {
    const m = window.EC_BOARD_COLORS[boardName] || {};
    const st = status || "";
    const c  = m[st] || IND.Gray;
    const base = `border-color:${c.bd} !important;`;
    const fill = dashed ? "background:transparent !important;border-style:dashed !important;"
                        : `background:${c.bg} !important;`;
    return `<span class="crm-chip -kanban" style="${base}${fill}">${esc(st)}</span>`;
  };
})();