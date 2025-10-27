/* Dantist Kanban Hard Reload — v1.0
   — Одноразовая авто-перезагрузка при первом заходе на любой Kanban-борд
   — Флаг хранится в sessionStorage, чтобы не зациклиться в рамках сессии
   — Ничего не меняет в DOM, безопасно жить отдельно от основного skin-скрипта
*/
(() => {
  const CFG = {
    enabled: true,        // включатель
    delay_ms: 250         // задержка перед reload (мс)
  };

  const CLEAN = s => (s || "").trim();

  const isKanbanRoute = () => {
    try {
      const r = frappe.get_route?.() || [];
      if (r[0] === "List" && (r[2] === "Kanban" || r[2] === "Kanban Board")) return true;
    } catch {}
    return (location.pathname || "").includes("/view/kanban/");
  };

  function currentKanbanKey() {
    try {
      const r = frappe.get_route?.() || [];
      const boardName = r?.[3] ? decodeURIComponent(r[3]) : (window.cur_list?.board?.name || "");
      const doctype = window.cur_list?.doctype || window.cur_list?.board?.reference_doctype || "Unknown";
      return `dnt_kanban_hard_reload:${CLEAN(doctype)}:${CLEAN(boardName) || "all"}`;
    } catch {
      return "dnt_kanban_hard_reload:Unknown:all";
    }
  }

  function maybeHardReloadOnce() {
    if (!CFG.enabled) return;
    if (!isKanbanRoute()) return;

    const key = currentKanbanKey();
    if (sessionStorage.getItem(key) === "1") return;

    sessionStorage.setItem(key, "1");
    setTimeout(() => {
      try { console.debug("[DNT] Kanban hard reload:", key); } catch {}
      location.reload();
    }, Math.max(0, CFG.delay_ms | 0));
  }

  // Утилита для ручного сброса (через консоль): DNT.resetKanbanReload()
  window.DNT = Object.assign(window.DNT || {}, {
    resetKanbanReload(flagPrefix = "dnt_kanban_hard_reload:") {
      try {
        Object.keys(sessionStorage).forEach(k => {
          if (k.startsWith(flagPrefix)) sessionStorage.removeItem(k);
        });
        console.info("[DNT] Kanban hard reload flags cleared");
      } catch {}
    }
  });

  function run() {
    if (!isKanbanRoute()) return;
    maybeHardReloadOnce();
  }

  // Подписки на жизненный цикл
  if (frappe?.after_ajax) frappe.after_ajax(run); else document.addEventListener("DOMContentLoaded", run);
  window.addEventListener("load", run);
  frappe?.router?.on && frappe.router.on("change", run);
})();