// EC Kanban INV (Frappe 15): невидимые фильтры БЕЗ серверных оверрайдов
// и БЕЗ async-возвратов из ListView.get_args().

(function () {
  const DOCTYPE = "Engagement Case";
  const BOARD_FLAGS = {
    "CRM Board": "show_board_crm",
    "Leads – Contact Center": "show_board_leads",
    "Deals – Contact Center": "show_board_deals",
    "Patients – Care Department": "show_board_patients",
  };

  const cache = {
    board: null,
    flag: null,
    allowed: [],
    hidden: [],
    loaded: false,
  };

  function routeInfo() {
    const r = frappe.get_route(); // ["List","Engagement Case","Kanban","<Board>"]
    const ok = Array.isArray(r) && r[0] === "List" && r[1] === DOCTYPE && r[2] === "Kanban";
    const board = ok ? (r[3] || "") : "";
    const flag  = ok ? (BOARD_FLAGS[board] || null) : null;
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
    console.debug("[EC Kanban INV] lists loaded", { flag, allowed: cache.allowed.length, hidden: cache.hidden.length });
  }

  // 1) prefetch списков на этапе get_board()
  const KView = frappe.views.KanbanView && frappe.views.KanbanView.prototype;
  if (!KView || typeof KView.get_board !== "function") {
    console.warn("[EC Kanban INV] KanbanView.get_board not found; abort");
    return;
  }
  const orig_get_board = KView.get_board;
  KView.get_board = function () {
    const { ok, board, flag } = routeInfo();
    if (!ok || !flag) return orig_get_board.call(this);

    if (cache.board !== board || cache.flag !== flag) {
      cache.board = board;
      cache.flag = flag;
      cache.loaded = false;
    }
    const pBoard = orig_get_board.call(this);
    const pLists = cache.loaded ? Promise.resolve() : loadLists(flag);
    return Promise.all([pBoard, pLists]).then(() => void 0);
  };

  // 2) синхронная инъекция фильтров в get_args()
  const LView = frappe.views.ListView && frappe.views.ListView.prototype;
  if (!LView || typeof LView.get_args !== "function") {
    console.warn("[EC Kanban INV] ListView.get_args not found; abort");
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
        console.debug("[EC Kanban INV] skip inject (lists not loaded yet)");
        return args;
      }
      const filters = Array.isArray(args.filters) ? args.filters.slice() : [];
      const cleaned = filters.filter(f =>
        !(Array.isArray(f) && f[0] === DOCTYPE && f[1] === "name" && (f[2] === "in" || f[2] === "not in"))
      );
      cleaned.push([DOCTYPE, "name", "in", cache.allowed.length ? cache.allowed : []]);
      if (cache.hidden.length) cleaned.push([DOCTYPE, "name", "not in", cache.hidden]);
      args.filters = cleaned;
      console.debug("[EC Kanban INV] injected", { in: cache.allowed.length, not_in: cache.hidden.length, clauses: cleaned.length });
    } catch (e) {
      console.warn("[EC Kanban INV] inject error", e);
    }
    return args; // строго синхронный возврат
  };

  console.debug("[EC Kanban INV] installed");
})();