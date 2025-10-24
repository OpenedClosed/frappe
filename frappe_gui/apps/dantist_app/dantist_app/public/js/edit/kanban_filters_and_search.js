// EC Kanban Filter UI (non-invasive, v3.9.1 • THEME & i18n & header-resolver)
// - Статусы: показываем ПЕРЕВОД (disp), но храним RAW и фильтруем по RAW
// - Сопоставление заголовков колонок → RAW (если заголовки переведены, колонки всё равно скрываются корректно)
// - Цвета чипов обновляются при смене темы мгновенно (ec_board_colors:theme_changed)
// - Контрастное выделение выбранных чипов; служебные ключи (__*) исключены
// - Платформа/приоритет без изменений
// - Даты через Frappe Date-контролы; All/None/Reset мгновенно

(function () {
  const DOCTYPE = "Engagement Case";

  const BOARD_META = {
    "CRM Board":                  { flag: "show_board_crm",      status_field: "status_crm_board" },
    "Leads – Contact Center":     { flag: "show_board_leads",    status_field: "status_leads" },
    "Deals – Contact Center":     { flag: "show_board_deals",    status_field: "status_deals" },
    "Patients – Care Department": { flag: "show_board_patients", status_field: "status_patients" },
  };

  const DATE_FIELDS = [
    { key: "modified",       label: "Modified" },
    { key: "first_event_at", label: "First Event At" },
    { key: "last_event_at",  label: "Last Event At" },
  ];

  const UI = {
    q: "",
    board: null,
    status_field: null,

    statusesAll: [],          // массив RAW
    statuses: new Set(),      // выбранные RAW

    // карта сопоставления для заголовков колонок:
    // { raw -> disp, disp -> raw } + нормализованные ключи
    statusMaps: {
      raw2disp: new Map(),
      disp2raw: new Map(),
      n_disp2raw: new Map(),  // нормализованный disp -> raw
      n_raw2raw:  new Map(),  // нормализованный raw -> raw
    },

    platformAll: [],
    priorityAll: [],
    platform: new Set(),
    priority: new Set(),

    wrap: null,
    dateCtrls: {},
    lastBoard: null,
    _topbarMo: null,
  };

  const esc = frappe.utils.escape_html;
  const debounce = frappe.utils.debounce;
  const N = (s) => (s || "").normalize("NFC").trim().toLowerCase();

  function isKanbanEC() {
    const r = frappe.get_route?.() || [];
    return r[0] === "List" && r[1] === DOCTYPE && (r[2] === "Kanban" || r[2] === "Kanban Board");
  }
  function currentBoard() {
    const r = frappe.get_route?.() || [];
    return (isKanbanEC() && r[3]) ? decodeURIComponent(r[3]) : null;
  }
  const themeTag = () =>
    (document.documentElement.getAttribute("data-theme") || "").toLowerCase() === "dark" ? "dark" : "light";

  /* ---------- chips renderers ---------- */
  const kchip = (board, raw_status) => {
    const disp = __(raw_status) || raw_status; // показываем перевод
    const palMap = (window.EC_BOARD_COLORS && board) ? window.EC_BOARD_COLORS[board] : null;

    let bg = "var(--control-bg, #f3f4f6)";
    let bd = "var(--border-color, #e5e7eb)";
    const cur = themeTag();

    if (palMap && palMap.__palette === cur && palMap[raw_status]) {
      bg = palMap[raw_status].bg || bg;
      bd = palMap[raw_status].bd || bd;
    }
    return `<span class="crm-chip -kanban" style="background:${bg};border-color:${bd}">${esc(disp)}</span>`;
  };

  const tchip = (bucket, key) =>
    (typeof window.tagChip === "function")
      ? window.tagChip(bucket, key, false)
      : `<span class="crm-chip">${esc(key||"")}</span>`;

  /* ---------- панель ---------- */
  function ensurePanel() {
    if (!isKanbanEC()) return;
    ensureFilterButton();

    if (UI.wrap && document.body.contains(UI.wrap)) return;

    const wrap = document.createElement("div");
    wrap.className = "ec-kanban-filter";
    wrap.innerHTML = `
      <div class="ec-kf-header">
        <div class="t">${esc(__("Filters"))}</div>
        <button class="btn btn-xs btn-default" data-act="close" type="button">${esc(__("Close"))}</button>
      </div>
      <div class="ec-kf-body">
        <div class="ec-kf-block">
          <label>${esc(__("Search"))}</label>
          <input type="text" class="form-control input-xs" placeholder="${esc(__("name, title, phone, email"))}" data-kf="q">
        </div>

        <div class="ec-kf-block" data-kf="status-block">
          <div class="ec-kf-line">
            <label>${esc(__("Status (current board)"))}</label>
            <div class="ec-kf-quick">
              <button class="btn btn-xs btn-default" type="button" data-act="status-all">${esc(__("All"))}</button>
              <button class="btn btn-xs btn-default" type="button" data-act="status-none">${esc(__("None"))}</button>
            </div>
          </div>
          <div class="ec-kf-statuses"></div>
          <div class="text-muted tiny">${esc(__("Tip: unselect a status to hide that column."))}</div>
        </div>

        <div class="ec-kf-block">
          <div class="ec-kf-line">
            <label>${esc(__("Platform"))}</label>
            <div class="ec-kf-quick">
              <button class="btn btn-xs btn-default" type="button" data-act="platform-all">${esc(__("All"))}</button>
              <button class="btn btn-xs btn-default" type="button" data-act="platform-none">${esc(__("None"))}</button>
            </div>
          </div>
          <div class="ec-kf-platform"></div>
        </div>

        <div class="ec-kf-block">
          <div class="ec-kf-line">
            <label>${esc(__("Priority"))}</label>
            <div class="ec-kf-quick">
              <button class="btn btn-xs btn-default" type="button" data-act="priority-all">${esc(__("All"))}</button>
              <button class="btn btn-xs btn-default" type="button" data-act="priority-none">${esc(__("None"))}</button>
            </div>
          </div>
          <div class="ec-kf-priority"></div>
        </div>

        <div class="ec-kf-block">
          <div class="ec-kf-line">
            <label>${esc(__("Date ranges"))}</label>
            <div class="ec-kf-quick">
              <button class="btn btn-xs btn-default" type="button" data-act="dates-clear">${esc(__("All time"))}</button>
            </div>
          </div>

          <div class="ec-kf-dates">
            ${DATE_FIELDS.map(d => `
              <div class="ec-kf-date-card" data-key="${esc(d.key)}">
                <div class="ec-kf-date-title">${esc(__(d.label))}</div>
                <div class="ec-kf-date-row">
                  <div class="ec-kf-date-ctl" data-kf="date-ctl" data-key="${esc(d.key)}" data-which="from"></div>
                </div>
                <div class="ec-kf-date-row">
                  <div class="ec-kf-date-ctl" data-kf="date-ctl" data-key="${esc(d.key)}" data-which="to"></div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      </div>
      <div class="ec-kf-footer">
        <button class="btn btn-xs btn-secondary" data-act="reset" type="button">${esc(__("Reset"))}</button>
      </div>
    `;
    document.body.appendChild(wrap);
    UI.wrap = wrap;

    // кнопки
    wrap.addEventListener("click", (e) => {
      const target = e.target.closest("[data-act]");
      if (!target || !wrap.contains(target)) return;
      const act = target.getAttribute("data-act");
      if (act === "close") return togglePanel(false);
      if (act === "reset") return resetFilters();
      if (act === "status-all")    return setAllStatus(true);
      if (act === "status-none")   return setAllStatus(false);
      if (act === "platform-all")  return setAll("platform", true);
      if (act === "platform-none") return setAll("platform", false);
      if (act === "priority-all")  return setAll("priority", true);
      if (act === "priority-none") return setAll("priority", false);
      if (act === "dates-clear")   return clearAllDates();
    });

    // поиск
    wrap.querySelector('input[data-kf="q"]')?.addEventListener("input", (e) => {
      UI.q = e.target.value.trim();
      applyFiltersDebounced();
    });

    // чипы
    wrap.addEventListener("click", (e) => {
      const btn = e.target.closest(".ec-kf-chip");
      if (!btn || !wrap.contains(btn)) return;
      e.preventDefault();
      const bucket = btn.getAttribute("data-b"); // status / platform / priority
      const val = btn.getAttribute("data-val");  // для статуса — RAW
      if (!bucket || !val) return;

      if (bucket === "status") {
        toggleSet(UI.statuses, val);
        markPressed(btn, UI.statuses.has(val));
        hideKanbanColumnsBySelectedStatuses();
        return applyFiltersNow();
      }

      const set = UI[bucket];
      toggleSet(set, val);
      markPressed(btn, set.has(val));
      applyFiltersNow();
    });

    // init
    initBucketsAll();
    buildAllChips();
    initDateControls();
  }

  /* ---------- toolbar button ---------- */
  function ensureFilterButton() {
    const id = "ec-kanban-filter-btn";

    const place = () => {
      const anchor =
        document.querySelector(".standard-actions .page-icon-group") ||
        document.querySelector(".page-actions .page-icon-group");
      if (!anchor) return false;

      let btn = document.getElementById(id);
      if (!btn) {
        btn = document.createElement("button");
        btn.id = id;
        btn.className = "btn btn-default icon-btn";
        btn.title = __("Filters");
        btn.innerHTML = frappe.utils.icon("filter", "sm");
        btn.addEventListener("click", () => togglePanel(true));
        anchor.insertAdjacentElement("afterend", btn);
      }
      return true;
    };

    if (place()) return;

    let tries = 0;
    const t = setInterval(() => {
      if (place() || ++tries >= 12) clearInterval(t);
    }, 100);

    try { UI._topbarMo?.disconnect(); } catch {}
    const containers = [
      document.querySelector(".standard-actions") || document.body,
      document.querySelector(".page-actions") || document.body
    ];
    const mo = new MutationObserver(() => place());
    containers.forEach(c => c && mo.observe(c, { childList: true, subtree: true }));
    UI._topbarMo = mo;
  }

  async function buildAllChips() {
    await buildStatusChips();            // статусы (board) + statusMaps
    buildTagChips("platform", ".ec-kf-platform");
    buildTagChips("priority", ".ec-kf-priority");

    setAllStatus(true,       { silent: true });
    setAll("platform", true, { silent: true });
    setAll("priority", true, { silent: true });

    updatePressedStates();
    hideKanbanColumnsBySelectedStatuses();
  }

  function initBucketsAll() {
    const p  = (window.EC_TAG_COLORS && window.EC_TAG_COLORS.platform) || {};
    const pr = (window.EC_TAG_COLORS && window.EC_TAG_COLORS.priority) || {};
    UI.platformAll = Object.keys(p);
    UI.priorityAll = Object.keys(pr);
  }

  function resetStatusMaps() {
    UI.statusMaps.raw2disp = new Map();
    UI.statusMaps.disp2raw = new Map();
    UI.statusMaps.n_disp2raw = new Map();
    UI.statusMaps.n_raw2raw = new Map();
  }

  async function buildStatusChips() {
    const block = UI.wrap?.querySelector(".ec-kf-statuses");
    if (!block) return;
    block.innerHTML = `<div class="text-muted small">${esc(__("Loading…"))}</div>`;

    UI.board = currentBoard();
    const meta = UI.board ? BOARD_META[UI.board] : null;
    UI.status_field = meta?.status_field || null;

    if (typeof window.getBoardColors === "function" && UI.board) {
      try { await window.getBoardColors(UI.board); } catch {}
    }

    let statusesRaw = [];
    const colmap = (window.EC_BOARD_COLORS && UI.board) ? window.EC_BOARD_COLORS[UI.board] : null;
    if (colmap && Object.keys(colmap).length) {
      statusesRaw = Object.keys(colmap).filter(k => k && typeof k === "string" && !k.startsWith("__"));
    } else {
      const metaDT = await new Promise(res => frappe.model.with_doctype(DOCTYPE, () => res(frappe.get_meta(DOCTYPE))));
      const sf = (metaDT.fields || []).find(f => f.fieldname === UI.status_field);
      statusesRaw = String(sf?.options || "").split("\n").map(s => s.trim()).filter(Boolean);
    }
    UI.statusesAll = statusesRaw.slice();
    if (!UI.statuses.size) UI.statuses = new Set(UI.statusesAll);

    // построим карты соответствий RAW <-> DISP (перевод)
    resetStatusMaps();
    statusesRaw.forEach(raw => {
      const disp = __(raw) || raw;
      UI.statusMaps.raw2disp.set(raw, disp);
      UI.statusMaps.disp2raw.set(disp, raw);
      UI.statusMaps.n_disp2raw.set(N(disp), raw);
      UI.statusMaps.n_raw2raw.set(N(raw), raw);
    });

    block.innerHTML = statusesRaw.map(raw => {
      const html = kchip(UI.board, raw); // текст — перевод
      return `
        <button class="ec-kf-chip${UI.statuses.has(raw) ? " -pressed":""}" data-b="status" data-val="${esc(raw)}" type="button">
          ${html}
        </button>`;
    }).join("");
  }

  function buildTagChips(bucket, sel) {
    const block = UI.wrap?.querySelector(sel);
    if (!block) return;
    const dict = (window.EC_TAG_COLORS && window.EC_TAG_COLORS[bucket]) || {};
    const keys = Object.keys(dict);
    if (!keys.length) {
      block.closest(".ec-kf-block")?.classList.add("hidden");
      block.innerHTML = "";
      return;
    }
    if (!UI[bucket].size) keys.forEach(k => UI[bucket].add(k));

    block.innerHTML = keys.map(k => {
      const html = tchip(bucket, k);
      const pressed = UI[bucket].has(k);
      return `
        <button class="ec-kf-chip${pressed ? " -pressed":""}" data-b="${bucket}" data-val="${esc(k)}" type="button">
          ${html}
        </button>`;
    }).join("");
  }

  /* ---------- Date Controls ---------- */
  function initDateControls() {
    Object.values(UI.dateCtrls || {}).forEach(ctrl => {
      try { ctrl?.$wrapper?.remove(); } catch {}
    });
    UI.dateCtrls = {};

    const make = (key, which, parent) => {
      const fieldname = `ec_kf_${key}_${which}`;
      const ctrl = frappe.ui.form.make_control({
        df: {
          fieldname,
          fieldtype: "Date",
          placeholder: "YYYY-MM-DD",
          reqd: 0,
          label: which === "from" ? __("From") : __("To"),
        },
        parent,
        render_input: true,
      });
      setTimeout(() => {
        try {
          if (ctrl?.flatpickr) {
            ctrl.flatpickr.set("locale", "en");
            ctrl.flatpickr.set("dateFormat", "Y-m-d");
          }
        } catch {}
      }, 0);

      const onAny = () => applyFiltersDebounced();
      try { ctrl.$input && ctrl.$input.on("change input", onAny); } catch {}
      UI.dateCtrls[`${key}-${which}`] = ctrl;
    };

    UI.wrap?.querySelectorAll('[data-kf="date-ctl"]').forEach(host => {
      const key = host.getAttribute("data-key");
      const which = host.getAttribute("data-which"); // from|to
      if (!key || !which) return;
      make(key, which, host);
    });
  }

  function readDateRange(key) {
    const from = UI.dateCtrls[`${key}-from`]?.get_value?.() || "";
    const to   = UI.dateCtrls[`${key}-to`]?.get_value?.()   || "";
    return { from, to };
  }

  function clearAllDates(opts={}) {
    DATE_FIELDS.forEach(d => {
      ["from","to"].forEach(which => {
        const c = UI.dateCtrls[`${d.key}-${which}`];
        try { c?.set_value?.(""); } catch {}
      });
    });
    if (!opts.silent) applyFiltersNow();
  }

  /* ---------- Панель on/off ---------- */
  function togglePanel(show) {
    if (!UI.wrap) ensurePanel();
    if (!UI.wrap) return;
    UI.wrap.classList.toggle("-open", !!show);
    if (show) {
      const qin = UI.wrap.querySelector('input[data-kf="q"]');
      if (qin) qin.value = UI.q || "";
      const now = currentBoard();
      if (now !== UI.board) {
        buildAllChips();
        initDateControls();
      }
    }
  }

  /* ---------- Helpers ---------- */
  function toggleSet(set, val) { if (set.has(val)) set.delete(val); else set.add(val); }

  function setAll(bucket, selAll, opts={}) {
    const all = UI[`${bucket}All`] || [];
    UI[bucket].clear();
    if (selAll) all.forEach(v => UI[bucket].add(v));
    const block = UI.wrap?.querySelector(`.ec-kf-${bucket}`);
    block?.querySelectorAll(".ec-kf-chip").forEach(btn => {
      const v = btn.getAttribute("data-val");
      markPressed(btn, UI[bucket].has(v));
    });
    if (!opts.silent) applyFiltersNow();
  }

  function setAllStatus(selAll, opts={}) {
    UI.statuses.clear();
    if (selAll) UI.statusesAll.forEach(v => UI.statuses.add(v));
    const block = UI.wrap?.querySelector(".ec-kf-statuses");
    block?.querySelectorAll(".ec-kf-chip").forEach(btn => {
      const v = btn.getAttribute("data-val"); // RAW
      markPressed(btn, UI.statuses.has(v));
    });
    hideKanbanColumnsBySelectedStatuses();
    if (!opts.silent) applyFiltersNow();
  }

  function markPressed(btn, on) {
    btn.classList.toggle("-pressed", !!on);
    const chip = btn.querySelector(".crm-chip");
    if (chip) chip.classList.toggle("-selected", !!on);
  }

  function updatePressedStates() {
    UI.wrap?.querySelectorAll(".ec-kf-chip").forEach(btn => {
      const b = btn.getAttribute("data-b");
      const v = btn.getAttribute("data-val");
      const set = (b === "status") ? UI.statuses : UI[b];
      const on = !!(set && set.has(v));
      markPressed(btn, on);
    });
  }

  function resetFilters() {
    UI.q = "";
    const qin = UI.wrap?.querySelector('input[data-kf="q"]'); if (qin) qin.value = "";

    setAllStatus(true,       { silent: true });
    setAll("platform", true, { silent: true });
    setAll("priority", true, { silent: true });

    clearAllDates({ silent: true });

    updatePressedStates();
    hideKanbanColumnsBySelectedStatuses();
    applyFiltersNow();
  }

  /* ---------- get_args ---------- */
  const LView = frappe.views.ListView && frappe.views.ListView.prototype;
  if (LView && typeof LView.get_args === "function" && !LView.get_args._ec_filter_ui_wrapped_v3_9_1) {
    const orig_get_args = LView.get_args;
    LView.get_args = function () {
      const args = orig_get_args.call(this);
      try {
        if (this.doctype !== DOCTYPE || !isKanbanEC()) return args;

        const filters = Array.isArray(args.filters) ? args.filters.slice() : [];
        const board = currentBoard();
        const meta = board ? BOARD_META[board] : null;
        const field = meta?.status_field;

        // Поиск (OR)
        if (UI.q) {
          const like = `%${UI.q}%`;
          const or_local = [
            [DOCTYPE, "name", "like", like],
            [DOCTYPE, "title", "like", like],
            [DOCTYPE, "display_name", "like", like],
            [DOCTYPE, "phone", "like", like],
            [DOCTYPE, "email", "like", like],
          ];
          args.or_filters = Array.isArray(args.or_filters) ? args.or_filters.concat(or_local) : or_local;
        }

        // Статусы текущей доски (RAW)
        if (field && UI.statuses.size && UI.statuses.size !== UI.statusesAll.length) {
          filters.push([DOCTYPE, field, "in", Array.from(UI.statuses)]);
        }

        // Platform / Priority
        if (UI.platform.size && UI.platform.size !== UI.platformAll.length) {
          filters.push([DOCTYPE, "channel_platform", "in", Array.from(UI.platform)]);
        }
        if (UI.priority.size && UI.priority.size !== UI.priorityAll.length) {
          filters.push([DOCTYPE, "priority", "in", Array.from(UI.priority)]);
        }

        // Даты → between
        DATE_FIELDS.forEach(d => {
          const range = readDateRange(d.key);
          if (range.from || range.to) {
            const fromDT = range.from ? `${range.from} 00:00:00` : "1900-01-01 00:00:00";
            const toDT   = range.to   ? `${range.to} 23:59:59` : "2999-12-31 23:59:59";
            filters.push([DOCTYPE, d.key, "between", [fromDT, toDT]]);
          }
        });

        args.filters = filters;
      } catch (e) {
        console.warn("[EC Kanban UI v3.9.1] inject error", e);
      }
      return args;
    };
    LView.get_args._ec_filter_ui_wrapped_v3_9_1 = true;
  }

  /* ---------- refresh + hide columns ---------- */
  const applyFiltersDebounced = debounce(() => applyFiltersNow(), 100);

  function resolveRawStatusFromHeader(headerText) {
    // headerText может быть переведённым заголовком колонки; пробуем найти RAW
    const t = (headerText || "").trim();
    if (!t) return t;

    // 1) прямое совпадение по нормализованному DISP -> RAW
    const n = N(t);
    const rawFromDisp = UI.statusMaps.n_disp2raw.get(n);
    if (rawFromDisp) return rawFromDisp;

    // 2) иногда фреймворк показывает оригинал (RAW) — проверим по raw->raw
    const rawFromRaw = UI.statusMaps.n_raw2raw.get(n);
    if (rawFromRaw) return rawFromRaw;

    // 3) fallback — вернём как есть
    return t;
  }

  function hideKanbanColumnsBySelectedStatuses() {
    if (!isKanbanEC()) return;
    const selected = new Set(UI.statuses);
    const all = UI.statusesAll;

    const columns = Array.from(document.querySelectorAll(".kanban-column"));
    columns.forEach(col => {
      const titleNode = col.querySelector(".kanban-column-header .kanban-column-title");
      const headerText = titleNode ? (titleNode.textContent || "").trim() : "";
      const raw = resolveRawStatusFromHeader(headerText);
      const show = (selected.size === 0)
        ? false
        : (selected.size === all.length ? true : selected.has(raw));
      col.style.display = show ? "" : "none";
    });
  }

  // наблюдатель за DOM (кнопка, скрытие колонок)
  const mo = new MutationObserver(() => {
    if (!isKanbanEC()) return;
    ensureFilterButton();
    hideKanbanColumnsBySelectedStatuses();
  });

  /* ---------- Theme repaint hooks ---------- */
  (function hookThemeRepaint(){
    window.addEventListener("ec_board_colors:theme_changed", () => {
      if (!UI.wrap) return;
      const savedStatuses = new Set(UI.statuses);
      const savedPlat = new Set(UI.platform);
      const savedPrio = new Set(UI.priority);

      buildStatusChips().then(() => {
        UI.statuses = savedStatuses;
        updatePressedStates();
        hideKanbanColumnsBySelectedStatuses();
      });
      buildTagChips("platform", ".ec-kf-platform");
      buildTagChips("priority", ".ec-kf-priority");
      UI.platform = savedPlat;
      UI.priority = savedPrio;
      updatePressedStates();
    });

    try {
      const moTheme = new MutationObserver((muts) => {
        if (!muts.some(m => m.attributeName === "data-theme")) return;
        window.dispatchEvent(new CustomEvent("ec_board_colors:theme_changed"));
      });
      moTheme.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    } catch {}
  })();

  /* ---------- Стили ---------- */
  (function injectCSS(){
    if (document.getElementById("ec-kanban-filter-ui-v3-css")) return;
    const style = document.createElement("style");
    style.id = "ec-kanban-filter-ui-v3-css";
    style.textContent = `
    .ec-kanban-filter{
      position:fixed; top:64px; right:16px; width:320px; max-width:92vw;
      background: var(--card-bg, #ffffff);
      color: var(--text-color, #111827);
      border:1px solid var(--border-color, #e5e7eb);
      border-radius:12px;
      box-shadow: var(--shadow-lg, 0 8px 32px rgba(0,0,0,.12));
      transform:translateX(120%); opacity:.0;
      transition:transform .14s ease, opacity .14s ease; z-index:1002;
    }
    .ec-kanban-filter.-open{ transform:translateX(0); opacity:1; }
    .ec-kf-header{
      display:flex;align-items:center;justify-content:space-between;gap:8px;
      padding:10px 12px;border-bottom:1px solid var(--table-border-color, var(--border-color, #f1f5f9));
    }
    .ec-kf-header .t{font-weight:600}
    .ec-kf-body{padding:10px 12px;max-height:min(60vh,560px);overflow:auto}
    .ec-kf-block{margin-bottom:12px}
    .ec-kf-block>label{display:block;font-size:12px;color:var(--text-muted, #6b7280);margin-bottom:6px}
    .ec-kf-line{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
    .ec-kf-quick .btn{margin-left:6px}
    .ec-kf-footer{
      padding:10px 12px;border-top:1px solid var(--table-border-color, var(--border-color, #f1f5f9));
      display:flex;gap:8px;justify-content:flex-end
    }
    .tiny{font-size:11px;margin-top:4px;color:var(--text-muted, #6b7280)}
    .hidden{display:none !important}

    .ec-kf-chip{border:none;background:transparent;padding:0;margin:0 6px 6px 0;cursor:pointer;user-select:none}
    .ec-kf-chip .crm-chip{transition:box-shadow .12s, transform .04s, background .14s, border-color .14s}
    .ec-kf-chip.-pressed .crm-chip,
    .ec-kf-chip .crm-chip.-selected{
      box-shadow:0 0 0 2px var(--ring-strong, color-mix(in oklab, var(--primary, #6366f1) 60%, transparent));
      background: color-mix(in oklab, var(--primary, #6366f1) 12%, var(--control-bg, #f3f4f6));
      border-color: color-mix(in oklab, var(--primary, #6366f1) 45%, var(--border-color, #e5e7eb));
    }
    .ec-kf-chip:active .crm-chip{ transform:translateY(1px); }

    .crm-chip{
      font-size:10px; padding:2px 6px; border-radius:999px;
      border:1px solid var(--border-color, #e5e7eb);
      background: var(--control-bg, #f3f4f6);
      color: var(--text-color, #111827);
    }
    .crm-chip.-ghost{ background: var(--control-bg-muted, #f8fafc); }

    .ec-kf-dates{display:flex;flex-direction:column;gap:10px}
    .ec-kf-date-card{
      border:1px dashed var(--border-color, #e5e7eb);
      border-radius:10px; padding:8px;
      background: var(--surface-muted, color-mix(in oklab, var(--card-bg, #fff) 90%, black 10%));
    }
    .ec-kf-date-title{font-weight:600; font-size:12px; margin:2px 0 6px; color:var(--text-color, #374151)}
    .ec-kf-date-row{display:flex; flex-direction:column; gap:4px; margin-top:6px}

    .ec-kanban-filter .frappe-control .control-input .form-control{
      background: var(--input-bg, var(--card-bg, #fff)) !important;
      border:1px solid var(--border-color, #d1d5db) !important;
      color: var(--text-color, #111827) !important;
    }
    .ec-kanban-filter .frappe-control .control-label{ color: var(--text-muted, #6b7280) !important; }
    .ec-kanban-filter .awesomplete > input{
      background: var(--input-bg, var(--card-bg, #fff)) !important;
      border-color: var(--border-color, #d1d5db) !important;
      color: var(--text-color, #111827) !important;
    }
    .ec-kanban-filter input.form-control{
      background: var(--input-bg, var(--card-bg, #fff));
      border:1px solid var(--border-color, #d1d5db);
      color: var(--text-color, #111827);
    }
    `;
    document.head.appendChild(style);
  })();

  /* ---------- Boot / Router ---------- */
  function applyFiltersNow() {
    try {
      if (window.cur_list?.run) window.cur_list.run();
      else if (window.cur_list?.refresh) window.cur_list.refresh();
    } catch {}
    hideKanbanColumnsBySelectedStatuses();
    setTimeout(ensureFilterButton, 0);
    setTimeout(ensureFilterButton, 150);
  }

  function initIfKanban() {
    if (!isKanbanEC()) { UI.wrap && UI.wrap.classList.remove("-open"); return; }
    try {
      ensurePanel();
      const nowBoard = currentBoard();
      if (UI.lastBoard && UI.lastBoard !== nowBoard) {
        togglePanel(false);
        ensureFilterButton();
      }
      UI.lastBoard = nowBoard;

      mo.disconnect();
      mo.observe(document.body || document.documentElement, { childList: true, subtree: true });
      hideKanbanColumnsBySelectedStatuses();

      setTimeout(ensureFilterButton, 0);
      setTimeout(ensureFilterButton, 200);
    } catch (e) { console.warn(e); }
  }
  if (frappe?.after_ajax) frappe.after_ajax(initIfKanban); else document.addEventListener("DOMContentLoaded", initIfKanban);
  frappe?.router?.on && frappe.router.on("change", initIfKanban);
})();