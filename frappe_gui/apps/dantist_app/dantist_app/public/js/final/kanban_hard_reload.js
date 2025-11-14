/* Dantist Kanban Hard Reload — v1.9
   — Уникальный ключ на основе точного URL + board + doctype
   — Мгновенный "route-enter" перезапуск (один раз на вход в канбан)
   — Хуки fetch/XHR/frappe.call + гард-таймер
   — Повторный reload разрешён после небольшого cooldown (без циклов)
*/
(() => {
  const CFG = {
    enabled: true,
    delay_ms: 250,
    debounce_ms: 300,
    guard_ms: 1200,
    route_enter_ms: 200, // мягкий «на входе»
    cooldown_ms: 3000,   // через сколько миллисекунд можно снова перезагрузить тот же URL
    watch_methods: new Set([
      "frappe.desk.doctype.kanban_board.kanban_board.get_kanban_boards",
      "frappe.desk.doctype.kanban_board.kanban_board.get_kanban_board",
      "frappe.desk.doctype.kanban_board.kanban_board.get_cards",
      "frappe.desk.doctype.kanban_board.kanban_board.update_order",
      "frappe.desk.reportview.get",
      "frappe.desk.listview.get_list_settings",
      "frappe.client.get_doc_permissions",
      "frappe.client.get_list",
      "frappe.client.get_value",
      // кастомные:
      "dantist_app.api.engagement.handlers.engagement_hidden_children",
      "dantist_app.api.engagement.handlers.engagement_allowed_for_board",
      "dantist_app.api.tasks.handlers.ec_tasks_for_case"
    ]),
    watch_urls_contains: [
      "/api/method/frappe.desk.doctype.kanban_board.kanban_board.get_kanban_boards",
      "/api/method/frappe.desk.doctype.kanban_board.kanban_board.get_kanban_board",
      "/api/method/frappe.desk.doctype.kanban_board.kanban_board.get_cards",
      "/api/method/frappe.desk.doctype.kanban_board.kanban_board.update_order",
      "/api/method/frappe.desk.reportview.get",
      "/api/method/frappe.desk.listview.get_list_settings",
      "/api/method/frappe.client.get_doc_permissions",
      "/api/method/frappe.client.get_list",
      "/api/method/frappe.client.get_value",
      "/api/method/frappe.client.get", // GET Kanban Board
      "/api/method/dantist_app.api.engagement.handlers.engagement_hidden_children",
      "/api/method/dantist_app.api.engagement.handlers.engagement_allowed_for_board",
      "/api/method/dantist_app.api.tasks.handlers.ec_tasks_for_case"
    ]
  };

  const CLEAN = s => (s || "").trim();

  function is_kanban_url() {
    try {
      const p = location.pathname || "";
      const q = location.search || "";
      if (p.includes("/view/kanban/")) return true;
      if (p.includes("/app/kanban-board/")) return true;
      if (/([?&#])view=Kanban(\+Board)?(&|$)/i.test(q)) return true;
    } catch {}
    try {
      const h = location.hash || "";
      if (/\/view\/kanban\//.test(h)) return true;
      if (/([?&#])view=Kanban(\+Board)?(&|$)/i.test(h)) return true;
    } catch {}
    try {
      const r = frappe.get_route?.() || [];
      if (r[0] === "List" && (r[2] === "Kanban" || r[2] === "Kanban Board")) return true;
    } catch {}
    return false;
  }

  function route_bits() {
    let board = "", dt = "Unknown";
    try {
      const r = frappe.get_route?.() || [];
      board = r?.[3] ? decodeURIComponent(r[3]) : (window.cur_list?.board?.name || "");
      dt = window.cur_list?.doctype || window.cur_list?.board?.reference_doctype || "Unknown";
    } catch {}
    const p = location.pathname || "";
    const h = location.hash || "";
    const q = location.search || "";
    return { board: CLEAN(board) || "all", dt: CLEAN(dt), p, h, q };
  }

  function key_for_current() {
    const { board, dt, p, h, q } = route_bits();
    const url_fingerprint = [p, q, h].join("|");
    return `dnt_kanban_hard_reload:${dt}:${board}:${url_fingerprint}`;
  }

  let armed_key = null;
  let guard_timer = null;
  let debounce_timer = null;
  let enter_timer = null;

  function arm() {
    if (!CFG.enabled) return;
    if (!is_kanban_url()) { disarm(); return; }
    const key = key_for_current();
    if (armed_key === key) return;
    armed_key = key;

    // 1) «на входе» — мягкий одноразовый перезапуск для этого захода
    clearTimeout(enter_timer);
    enter_timer = setTimeout(() => {
      maybe_reload_once("route-enter");
    }, CFG.route_enter_ms);

    // 2) гард — если не поймали сетевой триггер
    clearTimeout(guard_timer);
    guard_timer = setTimeout(() => {
      if (!armed_key) return;
      maybe_reload_once("guard");
    }, CFG.guard_ms);

    try { console.debug("[DNT] Kanban HR armed for", armed_key); } catch {}
  }

  function disarm() {
    armed_key = null;
    clearTimeout(guard_timer);
    clearTimeout(enter_timer);
    guard_timer = null;
    enter_timer = null;
  }

  function debounce(fn, ms) {
    clearTimeout(debounce_timer);
    debounce_timer = setTimeout(fn, ms);
  }

  function maybe_reload_once(reason = "") {
    if (!CFG.enabled || !is_kanban_url()) return;
    const key = key_for_current();
    if (!armed_key || armed_key !== key) return;

    const now = Date.now();
    let last_ts = 0;

    try {
      const raw = sessionStorage.getItem(key);
      if (raw) {
        const parsed = parseInt(raw, 10);
        if (!isNaN(parsed)) last_ts = parsed;
      }
    } catch {}

    // Если уже перезагружались по этому URL недавно — не делаем ещё раз (защита от цикла)
    if (last_ts && now - last_ts < (CFG.cooldown_ms || 2000)) {
      disarm();
      try {
        console.debug(
          "[DNT] Kanban hard reload skipped (cooldown)",
          key,
          reason ? `(${reason})` : ""
        );
      } catch {}
      return;
    }

    // Фиксируем момент последнего reload для этого URL
    try {
      sessionStorage.setItem(key, String(now));
    } catch {}

    disarm();
    try {
      console.debug(
        "[DNT] Kanban hard reload:",
        key,
        reason ? `(${reason})` : ""
      );
    } catch {}
    setTimeout(() => {
      location.reload();
    }, Math.max(0, CFG.delay_ms | 0));
  }

  function url_is_get_kanban_board(url) {
    if (!url) return false;
    if (!url.includes("/api/method/frappe.client.get")) return false;
    try {
      const u = new URL(url, location.origin);
      const dt = (u.searchParams.get("doctype") || "").toLowerCase();
      return dt === "kanban board" || dt === "kanban%20board";
    } catch { return false; }
  }

  // ===== Hook: frappe.call
  (function hook_frappe_call() {
    if (!window.frappe || !frappe.call || frappe.call.__dntHooked) return;
    const orig = frappe.call.bind(frappe);

    const wrapped = function(...args) {
      const m = (typeof args[0] === "string")
        ? args[0]
        : (args[0] && typeof args[0] === "object" ? (args[0].method || "") : "");

      if (typeof args[0] === "string" && typeof args[2] === "function") {
        const cb = args[2];
        args[2] = function(res) {
          try {
            if (is_kanban_url() && CFG.watch_methods.has(m)) {
              debounce(() => maybe_reload_once("frappe.call(cb):" + m), CFG.debounce_ms);
            }
          } catch {}
          return cb.apply(this, arguments);
        };
      }

      const ret = orig.apply(this, args);
      try {
        if (ret && typeof ret.then === "function") {
          ret.then(() => {
            if (is_kanban_url() && CFG.watch_methods.has(m)) {
              debounce(() => maybe_reload_once("frappe.call(then):" + m), CFG.debounce_ms);
            }
          }).catch(() => {});
        }
      } catch {}
      return ret;
    };

    wrapped.__dntHooked = true;
    frappe.call = wrapped;
  })();

  // ===== Hook: fetch
  (function hook_fetch() {
    if (!window.fetch || window.fetch.__dntHooked) return;
    const orig = window.fetch.bind(window);

    const wrapped = async function(input, init) {
      const url = typeof input === "string" ? input : (input?.url || "");
      const res = await orig(input, init);
      try {
        if (
          is_kanban_url() &&
          (
            (url && CFG.watch_urls_contains.some(s => url.includes(s))) ||
            url_is_get_kanban_board(url)
          )
        ) {
          const tag = url.split("/api/method/")[1] || url;
          debounce(() => maybe_reload_once("fetch:" + tag), CFG.debounce_ms);
        }
      } catch {}
      return res;
    };

    wrapped.__dntHooked = true;
    window.fetch = wrapped;
  })();

  // ===== Hook: XHR
  (function hook_xhr() {
    if (!window.XMLHttpRequest || window.XMLHttpRequest.__dntHooked) return;
    const Orig = window.XMLHttpRequest;

    function DntXHR() {
      const xhr = new Orig();
      let req_url = "";
      const o_open = xhr.open;
      const o_send = xhr.send;

      xhr.open = function(method, url) {
        try { req_url = url || ""; } catch {}
        return o_open.apply(xhr, arguments);
      };

      xhr.send = function(body) {
        xhr.addEventListener("load", function() {
          try {
            if (
              is_kanban_url() &&
              (
                (req_url && CFG.watch_urls_contains.some(s => req_url.includes(s))) ||
                url_is_get_kanban_board(req_url)
              )
            ) {
              const tag = req_url.split("/api/method/")[1] || req_url;
              debounce(() => maybe_reload_once("xhr:" + tag), CFG.debounce_ms);
            }
          } catch {}
        });
        return o_send.apply(xhr, arguments);
      };

      return xhr;
    }

    DntXHR.__dntHooked = true;
    window.XMLHttpRequest = DntXHR;
  })();

  // ===== Утилиты
  window.DNT = Object.assign(window.DNT || {}, {
    resetKanbanReload(prefix = "dnt_kanban_hard_reload:") {
      try {
        Object.keys(sessionStorage).forEach(k => {
          if (k.startsWith(prefix)) sessionStorage.removeItem(k);
        });
        console.info("[DNT] Kanban hard reload flags cleared");
      } catch {}
    }
  });

  // ===== Вооружаемся как можно раньше + дублируем
  try { arm(); } catch {}
  setTimeout(arm, 0);
  if (frappe?.router?.on) frappe.router.on("change", arm);
  window.addEventListener?.("load", arm);
  document.addEventListener?.("visibilitychange", () => {
    if (!document.hidden) arm();
  });
})();