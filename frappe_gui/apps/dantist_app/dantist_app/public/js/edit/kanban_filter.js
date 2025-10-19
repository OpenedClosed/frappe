// EC Kanban INV (Frappe 15): невидимые фильтры БЕЗ серверных оверрайдов и без async из get_args().

(function () {
  const DOCTYPE = "Engagement Case";
  const BOARD_FLAGS = {
    "CRM Board": "show_board_crm",
    "Leads – Contact Center": "show_board_leads",
    "Deals – Contact Center": "show_board_deals",
    "Patients – Care Department": "show_board_patients",
  };

  const cache = {
    board: null,      // текущее имя доски
    flag: null,       // show_board_*
    allowed: [],      // разрешённые name[]
    hidden: [],       // скрытые name[]
    loaded: false,    // готовы ли списки для текущей доски
  };

  function routeInfo() {
    const r = frappe.get_route(); // ["List","Engagement Case","Kanban","<Board Name>"]
    const ok = Array.isArray(r) && r[0] === "List" && r[1] === DOCTYPE && r[2] === "Kanban";
    const board = ok ? (r[3] || "") : "";
    const flag = ok ? (BOARD_FLAGS[board] || null) : null;
    return { ok, board, flag };
  }

  async function loadLists(flag) {
    const [allowedRes, hiddenRes] = await Promise.all([
      frappe.call({
        method: "dantist_app.api.engagement.handlers.engagement_allowed_for_board",
        args: { flag_field: flag },
      }),
      frappe.call({
        method: "dantist_app.api.engagement.handlers.engagement_hidden_children",
      }),
    ]);
    cache.allowed = Array.isArray(allowedRes.message) ? allowedRes.message : [];
    cache.hidden  = Array.isArray(hiddenRes.message)  ? hiddenRes.message  : [];
    cache.loaded  = true;
    console.debug("[EC Kanban INV] loaded lists:", {
      flag, allowed: cache.allowed.length, hidden: cache.hidden.length
    });
  }

  // ——— Патч 1: предзагрузка allow/hidden во время получения борда ———
  const KView = frappe.views.KanbanView && frappe.views.KanbanView.prototype;
  if (!KView || typeof KView.get_board !== "function") {
    console.warn("[EC Kanban INV] KanbanView.get_board not found; aborting.");
    return;
  }

  const orig_get_board = KView.get_board;
  KView.get_board = function () {
    // определяем доску/флаг с текущего маршрута
    const { ok, board, flag } = routeInfo();

    // если зашли не на нашу канбан-вью — просто вызываем ядро
    if (!ok || !flag) {
      return orig_get_board.call(this);
    }

    // если сменился борт/флаг — сбросим кэш
    if (cache.board !== board || cache.flag !== flag) {
      cache.board = board;
      cache.flag = flag;
      cache.loaded = false;
    }

    // 1) сначала получаем борд (как в ядре),
    // 2) ПАРАЛЛЕЛЬНО грузим наши списки,
    // 3) ждём оба промиса и только потом продолжаем пайплайн KanbanView.
    const pBoard = orig_get_board.call(this);
    const pLists = cache.loaded ? Promise.resolve() : loadLists(flag);

    return Promise.all([pBoard, pLists]).then(() => {
      // к этому моменту cache.loaded == true
      return;
    });
  };

  // ——— Патч 2: синхронная инъекция фильтров в ListView.get_args() ———
  const LView = frappe.views.ListView && frappe.views.ListView.prototype;
  if (!LView || typeof LView.get_args !== "function") {
    console.warn("[EC Kanban INV] ListView.get_args not found; aborting.");
    return;
  }

  const orig_get_args = LView.get_args;
  LView.get_args = function () {
    const args = orig_get_args.call(this);

    try {
      if (this.doctype !== DOCTYPE) return args;

      const { ok, flag } = routeInfo();
      if (!ok || !flag) return args;

      if (!cache.loaded) {
        // первый самый ранний вызов: списки ещё не подгружены.
        // ничего не ломаем — пропускаем без инъекций (последующий refresh уже будет с кэшем).
        console.debug("[EC Kanban INV] skip inject: lists not loaded yet");
        return args;
      }

      // аккуратно подмешиваем наши условия
      const filters = Array.isArray(args.filters) ? args.filters.slice() : [];
      const cleaned = filters.filter(f =>
        !(Array.isArray(f)
          && f[0] === DOCTYPE
          && f[1] === "name"
          && (f[2] === "in" || f[2] === "not in"))
      );

      cleaned.push([DOCTYPE, "name", "in", cache.allowed.length ? cache.allowed : []]);
      if (cache.hidden.length) {
        cleaned.push([DOCTYPE, "name", "not in", cache.hidden]);
      }

      args.filters = cleaned;
      console.debug("[EC Kanban INV] filters injected:", {
        in_count: cache.allowed.length,
        not_in_count: cache.hidden.length,
        total_clauses: cleaned.length,
      });

    } catch (e) {
      console.warn("[EC Kanban INV] inject error:", e);
    }

    return args; // ВАЖНО: всегда синхронный возврат объекта!
  };

  console.debug("[EC Kanban INV] installed (sync get_args + prefetch in get_board)");
})();