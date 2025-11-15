/* Dantist Kanban Simple Reload — v2.0
   — ОДИН жёсткий reload на каждый Kanban-борд (doctype + board) в рамках вкладки.
   — Без хуков fetch / XHR / frappe.call — только по событию смены роута.
   — Флаг :done в sessionStorage убивает любые лупы даже при долгой загрузке.
*/
(() => {
  const CFG = {
    enabled: true,
    delay_ms: 350 // задержка перед reload, чтобы Frappe успел дорисовать роут
  };

  const PREFIX = "dnt_kanban_simple";

  const CLEAN = s => (s || "").trim();

  function is_kanban_route() {
    try {
      if (window.frappe && typeof frappe.get_route === "function") {
        const r = frappe.get_route() || [];
        // Живой пример: ["List", "Engagement Case", "Kanban", "Main Board"]
        if (r[0] === "List" && (r[2] === "Kanban" || r[2] === "Kanban Board")) {
          return true;
        }
      }
    } catch {}

    // Фолбэки на случай прямого URL
    try {
      const p = location.pathname || "";
      const q = location.search || "";
      const h = location.hash || "";
      if (p.includes("/view/kanban/")) return true;
      if (p.includes("/app/kanban-board/")) return true;
      if (/([?&#])view=Kanban(\+Board)?(&|$)/i.test(q)) return true;
      if (/\/view\/kanban\//.test(h)) return true;
      if (/([?&#])view=Kanban(\+Board)?(&|$)/i.test(h)) return true;
    } catch {}

    return false;
  }

  function route_bits() {
    let board = "all";
    let dt = "Unknown";

    try {
      const r = (window.frappe && typeof frappe.get_route === "function")
        ? (frappe.get_route() || [])
        : [];

      // Doctype максимально стабильно: сначала из route, потом из cur_list
      dt =
        CLEAN(r[1]) ||
        CLEAN(window.cur_list?.doctype) ||
        CLEAN(window.cur_list?.board?.reference_doctype) ||
        "Unknown";

      // Name борда: сначала из route, потом из cur_list.board
      board =
        (r[3] ? CLEAN(decodeURIComponent(r[3])) : "") ||
        CLEAN(window.cur_list?.board?.name) ||
        "all";
    } catch {}

    return { dt, board };
  }

  function key_for_current() {
    const { dt, board } = route_bits();
    return `${PREFIX}:${dt}:${board}`;
  }

  function done_key_for_current() {
    return key_for_current() + ":done";
  }

  let pending_timer = null;
  let last_armed_key = null;

  function schedule_reload_once(reason = "") {
    if (!CFG.enabled) return;
    if (!is_kanban_route()) return;

    const key = key_for_current();
    const done_key = done_key_for_current();

    // Уже ставили флаг для ЭТОГО борда в ЭТОЙ вкладке → выходим
    try {
      const done_flag = sessionStorage.getItem(done_key);
      if (done_flag === "1") {
        try {
          console.debug("[DNT] Kanban simple reload skipped (done)", key, reason || "");
        } catch {}
        return;
      }
    } catch {}

    // Если уже ждём reload для текущего key — второй раз не ставим таймер
    if (pending_timer && last_armed_key === key) {
      return;
    }

    last_armed_key = key;

    if (pending_timer) {
      clearTimeout(pending_timer);
      pending_timer = null;
    }

    pending_timer = setTimeout(() => {
      pending_timer = null;

      // Перед самым reload ещё раз убеждаемся, что мы всё ещё на канбане
      if (!is_kanban_route()) return;

      const key_now = key_for_current();
      const done_now_key = done_key_for_current();

      // Если в процессе route сменился — не перезагружаем
      if (key_now !== key) return;

      try {
        sessionStorage.setItem(done_now_key, "1");
      } catch {}

      try {
        console.debug("[DNT] Kanban simple reload:", key_now, reason || "");
      } catch {}

      location.reload();
    }, CFG.delay_ms);
  }

  function on_route_change() {
    try {
      if (!is_kanban_route()) {
        // Если ушли с канбана — простаиваем
        return;
      }
      schedule_reload_once("route-change");
    } catch (e) {
      try {
        console.error("[DNT] Kanban simple reload error in on_route_change", e);
      } catch {}
    }
  }

  // Публичный ресет для отладки
  window.DNT = Object.assign(window.DNT || {}, {
    resetKanbanSimple(prefix = PREFIX + ":") {
      try {
        Object.keys(sessionStorage).forEach(k => {
          if (k.startsWith(prefix)) sessionStorage.removeItem(k);
        });
        console.info("[DNT] Kanban simple reload flags cleared");
      } catch (e) {
        console.error("[DNT] resetKanbanSimple error", e);
      }
    }
  });

  // Инициализация
  try {
    // Первый заход после загрузки
    setTimeout(on_route_change, 0);

    // Подписка на SPA-роутер Frappe
    if (window.frappe?.router?.on) {
      frappe.router.on("change", () => {
        setTimeout(on_route_change, 0);
      });
    }

    // На всякий случай, если что-то лениво подгружается
    window.addEventListener?.("load", () => {
      setTimeout(on_route_change, 0);
    });
  } catch (e) {
    try {
      console.error("[DNT] Kanban simple reload init error", e);
    } catch {}
  }
})();