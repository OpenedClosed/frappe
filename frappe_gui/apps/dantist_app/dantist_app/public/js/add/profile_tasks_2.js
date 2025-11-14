// === DNT User Work Tab (User form widgets, Engagement Case + ToDo) — v11 ===
//
// Base: v9 (логика вкладки, загрузка данных, счётчики, клики).
// Правки v11:
// • Наполнение рендера вынесено из form-section во свой корень #dnt-user-work-root внутри tab-pane
//   => Frappe может скрывать секцию, но наш блок остаётся видимым.
// • Карточки Engagement Case отрисовываются в CRM-стиле (как в CRM widget preview):
//   avatar + title + chips (status, priority, events, unanswered, updated).
// • Дизайн задач ОСТАЁТСЯ как в v9 (inline dnt-user-item).
//
// Важно: мы НЕ вмешиваемся в выбор активной вкладки User
// (Frappe по-прежнему открывает нужную вкладку по route / settings / и т. п.).

(() => {
  if (window.DNT_USER_WORK_TAB_V11) return;
  window.DNT_USER_WORK_TAB_V11 = true;

  function tr(s) {
    try { if (typeof _ === "function") return _(s); } catch (e) {}
    try { if (typeof __ === "function") return __(s); } catch (e2) {}
    return s;
  }

  const cfg = {
    cssId: "dnt-user-work-tab-css",
    tabId: "user-dnt_work_tab",
    tabBtnId: "user-dnt_work_tab-tab",
    tabFieldname: "dnt_work_tab",
    rootId: "dnt-user-work-root",
    containerClass: "dnt-user-work-widgets",
    cardsListAttr: "data-role-cards-list",
    tasksListAttr: "data-role-tasks-list",
    logPrefix: "[DNT-USER-WORK v11]",
    limits: {
      cards: 4,
      tasks: 6
    },
    doctypes: {
      todo: "ToDo",
      case: "Engagement Case"
    },
    titles: {
      self: {
        tab: "My Work",
        cards: "My Cases",
        tasks: "My Tasks",
        allCards: "All My Cases",
        allTasks: "All My Tasks"
      },
      other: {
        tab: "User Work",
        cards: "Cases",
        tasks: "Tasks",
        allCards: "All Cases",
        allTasks: "All Tasks"
      }
    },
    labels: {
      emptyCardsSelf: "You have no cases yet",
      emptyCardsOther: "This user has no cases yet",
      emptyTasksSelf: "You have no tasks yet",
      emptyTasksOther: "This user has no tasks yet",
      loading: "Loading…",
      eventsCount: "Events",
      unanswered: "Unanswered",
      footerHint: "Click a card or task to open it",
      summaryTemplate: "{cards} • {tasks}",
      updated: "Updated"
    },
    retries: {
      layout: 10,
      delayMs: 80
    }
  };

  function log(...args) {
    try {
      if (console && console.log) console.log(cfg.logPrefix, ...args);
    } catch (e) {}
  }

  // ===== CSS: таба всегда видима + базовый стиль карточек + CRM-стиль для кейсов =====

  function ensure_css() {
    if (document.getElementById(cfg.cssId)) return;

    const css = `
      /* === DNT User Work: формальная секция — всегда видима (на всякий случай) === */
      .row.form-section.card-section[data-fieldname="${cfg.tabFieldname}"] {
        display: block !important;
        visibility: visible !important;
      }
      .row.form-section.card-section[data-fieldname="${cfg.tabFieldname}"].empty-section,
      .row.form-section.card-section[data-fieldname="${cfg.tabFieldname}"].hide-control {
        display: block !important;
        visibility: visible !important;
      }
      .row.form-section.card-section[data-fieldname="${cfg.tabFieldname}"] .section-body {
        display: block !important;
      }
      #${cfg.tabId}.tab-pane {
        visibility: visible !important;
      }
      .row.form-section.card-section[data-fieldname="${cfg.tabFieldname}"] {
        margin-bottom: 0.75rem;
      }

      /* Корень нашего виджета в табе User Work */
      #${cfg.rootId} {
        margin-top: 0.5rem;
        margin-bottom: 1.5rem;
      }

      .${cfg.containerClass}{
        margin-top: 0.25rem;
        margin-bottom: 0;
      }

      /* === Основная карточка блока (как "рамка") === */
      .dnt-user-work-card{
        border-radius: var(--border-radius-lg, 0.75rem);
        background: color-mix(in srgb, var(--bg-color, #ffffff) 92%, #020617 8%);
        border: 1px solid rgba(15,23,42,0.06);
        box-shadow: 0 16px 40px rgba(15,23,42,0.08);
        backdrop-filter: blur(10px);
        padding: 0.85rem 1rem 0.9rem;
        min-width: 0;
      }
      @supports not (color-mix: in srgb, white 50%, black 50%) {
        .dnt-user-work-card{
          background: rgba(255,255,255,0.9);
        }
      }

      .dnt-user-work-header{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.4rem;
        margin-bottom: 0.3rem;
      }
      .dnt-user-work-title{
        font-weight: 600;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
      }
      .dnt-user-work-summary{
        font-size: 0.72rem;
        opacity: 0.7;
        white-space: nowrap;
      }

      .dnt-user-work-tabs-nav{
        display: flex;
        align-items: center;
        gap: 0.4rem;
        margin-bottom: 0.4rem;
        border-bottom: 1px solid rgba(15,23,42,0.08);
        padding-bottom: 0.25rem;
      }
      .dnt-user-work-tab-btn{
        border: none;
        background: transparent;
        padding: 0.2rem 0.7rem;
        border-radius: 999px;
        font-size: 0.78rem;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        color: rgba(15,23,42,0.7);
        transition: background 120ms ease, color 120ms ease, transform 120ms ease;
      }
      .dnt-user-work-tab-btn:hover{
        background: rgba(15,23,42,0.04);
        transform: translateY(-0.5px);
      }
      .dnt-user-work-tab-btn.active{
        background: rgba(37,99,235,0.10);
        color: #1d4ed8;
      }
      .dnt-user-work-tab-btn .dnt-pill-dot{
        width: 0.35rem;
        height: 0.35rem;
        border-radius: 999px;
        background: rgba(15,23,42,0.4);
      }
      .dnt-user-work-tab-count{
        font-size: 0.7rem;
        opacity: 0.7;
      }
      .dnt-user-work-tab-spacer{
        flex: 1 1 auto;
      }

      .dnt-user-work-all-link{
        font-size: 0.75rem;
        white-space: nowrap;
        display: inline-flex;
        align-items: center;
        gap: 0.2rem;
        cursor: pointer;
        text-decoration: none;
        font-weight: 500;
      }
      .dnt-user-work-all-link svg{
        width: 0.9rem;
        height: 0.9rem;
      }
      .dnt-user-work-all-link:hover{
        text-decoration: underline;
      }

      .dnt-user-work-pane{
        display: none;
        min-height: 3rem;
        padding-top: 0.15rem;
      }
      .dnt-user-work-pane.active{
        display: block;
      }

      .dnt-user-pane-header{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.3rem;
        margin-bottom: 0.25rem;
      }
      .dnt-user-pane-title{
        font-size: 0.8rem;
        font-weight: 500;
        opacity: 0.9;
      }

      .dnt-user-widget-list{
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
        min-height: 1.8rem;
      }
      .dnt-user-widget-empty,
      .dnt-user-widget-loading{
        font-size: 0.8rem;
        opacity: 0.7;
        padding: 0.3rem 0.1rem;
      }

      .dnt-user-widget-footer{
        margin-top: 0.35rem;
        display: flex;
        justify-content: flex-end;
        font-size: 0.7rem;
        opacity: 0.75;
      }
      .dnt-user-widget-footer span{
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
      }

      /* === v9 tasks: dnt-user-item (оставляем как было) === */
      .dnt-user-item{
        border-radius: 0.6rem;
        padding: 0.4rem 0.55rem;
        background: rgba(15,23,42,0.03);
        cursor: pointer;
        transition: background 120ms ease, transform 120ms ease, box-shadow 120ms ease;
      }
      .dnt-user-item:hover{
        background: rgba(15,23,42,0.06);
        transform: translateY(-1px);
        box-shadow: 0 8px 22px rgba(15,23,42,0.12);
      }
      .dnt-user-item-main{
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
        align-items: flex-start;
      }
      .dnt-user-item-title{
        font-size: 0.78rem;
        font-weight: 500;
        word-break: break-word;
      }
      .dnt-user-item-meta{
        margin-top: 0.18rem;
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.28rem;
        font-size: 0.7rem;
        opacity: 0.8;
      }
      .dnt-user-pill{
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        border-radius: 999px;
        padding: 0.15rem 0.6rem;
        font-size: 0.7rem;
        background: rgba(15,23,42,0.04);
      }
      .dnt-user-pill-status-open{
        color: #15803d;
        background: rgba(34,197,94,0.08);
      }
      .dnt-user-pill-status-closed{
        color: #b91c1c;
        background: rgba(248,113,113,0.08);
      }
      .dnt-user-pill-unanswered{
        color: #b45309;
        background: rgba(251,191,36,0.12);
      }
      .dnt-user-dot{
        width: 0.32rem;
        height: 0.32rem;
        border-radius: 999px;
        background: rgba(15,23,42,0.35);
      }
      .dnt-user-item-sub{
        font-size: 0.7rem;
        opacity: 0.8;
        margin-top: 0.15rem;
        word-break: break-word;
      }

      /* === CRM-стиль для кейсов внутри User Work (как в CRM widget preview) === */
      .dnt-user-cases-list{
        margin-top: 0.1rem;
      }

      .dnt-user-cases-list .crm-item{
        display:flex;
        align-items:flex-start;
        justify-content:space-between;
        gap:10px;
        padding:10px;
        border:1px solid var(--border-color,#eef2f7);
        border-radius:10px;
        margin-top:8px;
        cursor:pointer;
        background: var(--card-bg, #ffffff);
        color: var(--text-color);
        transition: background .15s ease, box-shadow .15s ease, transform .15s ease;
      }
      .dnt-user-cases-list .crm-item:hover{
        background: var(--fg-hover-color,#fafafa);
        box-shadow:0 8px 22px rgba(15,23,42,0.12);
        transform: translateY(-1px);
      }
      .dnt-user-cases-list .crm-left{
        display:flex;
        gap:10px;
        align-items:flex-start;
        min-width:0;
      }
      .dnt-user-cases-list .crm-avatar{
        width:28px;
        height:28px;
        border-radius:8px;
        background:var(--bg-light-gray,#e5e7eb);
        flex:0 0 auto;
        overflow:hidden;
      }
      .dnt-user-cases-list .crm-avatar img{
        width:100%;
        height:100%;
        object-fit:cover;
        display:block;
      }
      .dnt-user-cases-list .crm-body{min-width:0}
      .dnt-user-cases-list .crm-title{
        font-weight:600;
        font-size:13px;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
        color:var(--text-color);
      }
      .dnt-user-cases-list .crm-meta{
        color:var(--text-muted,#6b7280);
        font-size:11px;
        margin-top:2px;
        display:flex;
        gap:6px;
        flex-wrap:wrap;
      }
      .dnt-user-cases-list .crm-meta.-time .frappe-timestamp{opacity:.9}
      .dnt-user-cases-list .crm-right{
        display:flex;
        align-items:center;
        gap:8px;
      }
      .dnt-user-cases-list .crm-chip{
        font-size:10px;
        padding:2px 6px;
        border-radius:999px;
        border:1px solid var(--border-color,#e5e7eb);
        background: var(--bg-light-gray, #f3f4f6);
        color: var(--text-color);
      }
      .dnt-user-cases-list .crm-chip.-ghost{
        background: var(--control-bg,#f8fafc);
      }
      .dnt-user-cases-list .crm-badge{
        font-size:10px;
        padding:3px 8px;
        border-radius:999px;
        border:1px dashed var(--border-color,#d1d5db);
        color:var(--text-color);
      }
      .dnt-user-cases-list .crm-vsep{
        display:inline-block;
        width:0;
        border-left:1px dashed var(--border-color,#d1d5db);
        margin:0 6px;
        align-self:stretch;
      }
    `;

    const s = document.createElement("style");
    s.id = cfg.cssId;
    s.textContent = css;
    document.head.appendChild(s);
  }

  // ===== helpers =====

  function get_titles(is_self) {
    return is_self ? cfg.titles.self : cfg.titles.other;
  }

  function format_date(value) {
    if (!value) return "";
    if (window.frappe?.datetime?.str_to_user) {
      try {
        return frappe.datetime.str_to_user(value);
      } catch (e) {
        return String(value).split(" ")[0];
      }
    }
    return String(value).split(" ")[0];
  }

  function rel_time(value) {
    if (!value) return "";
    try {
      if (window.frappe?.datetime?.comment_when) {
        return frappe.datetime.comment_when(value);
      }
    } catch (e) {}
    return format_date(value);
  }

  function status_class(raw) {
    if (!raw) return "";
    const s = String(raw).toLowerCase();
    const closed_tokens = ["closed", "completed", "cancelled", "archived", "lost"];
    return closed_tokens.some(t => s.includes(t))
      ? "dnt-user-pill-status-closed"
      : "dnt-user-pill-status-open";
  }

  function full_path(p) {
    if (!p) return "";
    return p.startsWith("/") ? p : `/${p}`;
  }

  function update_counts(frm, partial) {
    const prev = frm.dnt_user_work_counts || { cards: 0, tasks: 0 };
    const next = Object.assign({}, prev, partial || {});
    frm.dnt_user_work_counts = next;

    const $card = frm.$wrapper.find(".dnt-user-work-card");
    if (!$card.length) return;

    const cards_text = `${next.cards} ${next.cards === 1 ? tr("case") : tr("cases")}`;
    const tasks_text = `${next.tasks} ${next.tasks === 1 ? tr("task") : tr("tasks")}`;

    const summary = cfg.labels.summaryTemplate
      .replace("{cards}", cards_text)
      .replace("{tasks}", tasks_text);

    $card.find("[data-role='summary']").text(summary);
    $card.find("[data-role='footer-info']").text(tr(cfg.labels.footerHint));

    $card.find("[data-role='cards-tab-count']").text(next.cards ? `(${next.cards})` : "");
    $card.find("[data-role='tasks-tab-count']").text(next.tasks ? `(${next.tasks})` : "");

    log("update_counts", next);
  }

  // ===== DOM: таба + наш root в tab-pane =====

  function ensure_tab_structures(frm, is_self) {
    const $wrapper = frm.$wrapper;
    if (!$wrapper || !$wrapper.length) {
      log("no frm.$wrapper yet");
      return null;
    }

    const $tabs = $wrapper.find("ul.form-tabs").first();
    const $tabContent = $wrapper.find(".form-tab-content.tab-content").first();

    if (!$tabs.length || !$tabContent.length) {
      log("no tab structures on User form yet", {
        tabs_len: $tabs.length,
        content_len: $tabContent.length
      });
      return null;
    }

    const titles = get_titles(is_self);

    // --- Tab button (НЕ делаем активной, НЕ двигаем порядок) ---
    let $tabLi = $tabs.find("#" + cfg.tabBtnId).closest("li");
    if (!$tabLi.length) {
      const btnHtml = `
        <li class="nav-item show">
          <button class="nav-link"
                  id="${cfg.tabBtnId}"
                  data-toggle="tab"
                  data-fieldname="${cfg.tabFieldname}"
                  href="#${cfg.tabId}"
                  role="tab"
                  aria-controls="${cfg.tabId}"
                  aria-selected="false">
            ${frappe.utils.escape_html(tr(titles.tab))}
          </button>
        </li>
      `;
      $tabLi = $(btnHtml);
      $tabs.append($tabLi);
      log("tab button created");
    } else {
      $tabLi.find(".nav-link").text(tr(titles.tab));
      log("tab button text updated");
    }

    // --- Tab pane (стандартный bootstrap-tab) ---
    let $tabPane = $tabContent.find("#" + cfg.tabId);
    if (!$tabPane.length) {
      const paneHtml = `
        <div class="tab-pane fade"
             id="${cfg.tabId}"
             role="tabpanel"
             aria-labelledby="${cfg.tabBtnId}">
          <div class="row form-section card-section empty-section"
               data-fieldname="${cfg.tabFieldname}">
            <div class="section-head">
              <span data-role="tab-title">${frappe.utils.escape_html(tr(titles.tab))}</span>
            </div>
            <div class="section-body"></div>
          </div>
        </div>
      `;
      $tabPane = $(paneHtml);
      $tabContent.append($tabPane);
      log("tab pane created");
    }

    // Секция может жить своей жизнью — мы на неё не опираемся, но подстрахуемся
    const $section = $tabPane.find(`.row.form-section[data-fieldname="${cfg.tabFieldname}"]`);
    const $sectionBody = $section.find(".section-body");
    if ($section.length) {
      $section.removeClass("empty-section hide-control").addClass("visible-section");
      $section.css({ display: "block", visibility: "visible" });
      $sectionBody.css("display", "block");
      log("section visibility patched (fallback)");
    }

    // --- Наш собственный root, не зависящий от section-body ---
    let $root = $tabPane.find("#" + cfg.rootId);
    if (!$root.length) {
      $root = $(`<div id="${cfg.rootId}"></div>`);
      // Добавим после form-section, чтобы выглядело как "контент секции"
      if ($section.length) {
        $section.after($root);
      } else {
        $tabPane.append($root);
      }
      log("root created");
    }

    // Полностью перерисовываем содержимое root
    $root.empty().append(`
      <div class="${cfg.containerClass}">
        <div class="dnt-user-work-card">
          <div class="dnt-user-work-header">
            <div class="dnt-user-work-title" data-role="tab-title-main">
              ${frappe.utils.escape_html(tr(titles.tab))}
            </div>
            <div class="dnt-user-work-summary" data-role="summary"></div>
          </div>

          <div class="dnt-user-work-tabs-nav" data-role="tabs-nav">
            <button class="dnt-user-work-tab-btn active" data-kind="cards">
              <span class="dnt-pill-dot"></span>
              <span data-role="cards-tab-title">
                ${frappe.utils.escape_html(tr(titles.cards))}
              </span>
              <span class="dnt-user-work-tab-count" data-role="cards-tab-count"></span>
            </button>
            <button class="dnt-user-work-tab-btn" data-kind="tasks">
              <span class="dnt-pill-dot"></span>
              <span data-role="tasks-tab-title">
                ${frappe.utils.escape_html(tr(titles.tasks))}
              </span>
              <span class="dnt-user-work-tab-count" data-role="tasks-tab-count"></span>
            </button>
            <div class="dnt-user-work-tab-spacer"></div>
          </div>

          <div class="dnt-user-work-pane active" data-kind="cards">
            <div class="dnt-user-pane-header">
              <div class="dnt-user-pane-title" data-role="cards-pane-title">
                ${frappe.utils.escape_html(tr(titles.cards))}
              </div>
              <a class="dnt-user-work-all-link"
                 data-kind="cards"
                 data-user="${frappe.utils.escape_html(frm.doc.name || "")}"
                 data-role="cards-all-link">
                <span data-role="cards-all-title">
                  ${frappe.utils.escape_html(tr(titles.allCards))}
                </span>
                <svg class="icon icon-xs" aria-hidden="true">
                  <use href="#icon-right"></use>
                </svg>
              </a>
            </div>
            <div class="dnt-user-widget-list dnt-user-cases-list" ${cfg.cardsListAttr}="1">
              <div class="dnt-user-widget-loading">
                ${frappe.utils.escape_html(tr(cfg.labels.loading))}
              </div>
            </div>
          </div>

          <div class="dnt-user-work-pane" data-kind="tasks">
            <div class="dnt-user-pane-header">
              <div class="dnt-user-pane-title" data-role="tasks-pane-title">
                ${frappe.utils.escape_html(tr(titles.tasks))}
              </div>
              <a class="dnt-user-work-all-link"
                 data-kind="tasks"
                 data-user="${frappe.utils.escape_html(frm.doc.name || "")}"
                 data-role="tasks-all-link">
                <span data-role="tasks-all-title">
                  ${frappe.utils.escape_html(tr(titles.allTasks))}
                </span>
                <svg class="icon icon-xs" aria-hidden="true">
                  <use href="#icon-right"></use>
                </svg>
              </a>
            </div>
            <div class="dnt-user-widget-list" ${cfg.tasksListAttr}="1">
              <div class="dnt-user-widget-loading">
                ${frappe.utils.escape_html(tr(cfg.labels.loading))}
              </div>
            </div>
          </div>

          <div class="dnt-user-widget-footer">
            <span data-role="footer-info"></span>
          </div>
        </div>
      </div>
    `);

    const cardsList = $root.find("[" + cfg.cardsListAttr + "]");
    const tasksList = $root.find("[" + cfg.tasksListAttr + "]");

    return { tabPane: $tabPane, cardsList, tasksList };
  }

  function render_empty(list_el, is_self, kind) {
    const label =
      kind === "cards"
        ? (is_self ? cfg.labels.emptyCardsSelf : cfg.labels.emptyCardsOther)
        : (is_self ? cfg.labels.emptyTasksSelf : cfg.labels.emptyTasksOther);

    list_el.html(
      `<div class="dnt-user-widget-empty">${frappe.utils.escape_html(tr(label))}</div>`
    );
  }

  // ===== RENDER: кейсы — CRM-стиль =====

  function render_cards(list_el, rows, case_details, is_self) {
    log("render_cards input", {
      rowsCount: rows ? rows.length : 0,
      caseDetailsCount: case_details ? case_details.length : 0
    });

    if (!rows || !rows.length) {
      render_empty(list_el, is_self, "cards");
      return;
    }

    const by_case = new Map();
    rows.forEach(row => {
      const key = row.reference_name || row.name;
      if (!key) return;
      if (!by_case.has(key)) by_case.set(key, row);
    });

    const items = Array.from(by_case.values()).slice(0, cfg.limits.cards);

    const index_case = {};
    (case_details || []).forEach(doc => {
      index_case[doc.name] = doc;
    });

    const sepChip = `<span class="crm-vsep" aria-hidden="true"></span>`;
    const labelUpdated = tr(cfg.labels.updated);

    const html = items
      .map(row => {
        const case_name = row.reference_name || row.name;
        const doc = index_case[case_name] || {};

        const title =
          row.description ||
          doc.title ||
          doc.display_name ||
          case_name;

        const status_raw = doc.runtime_status || row.status;
        const status_label = status_raw ? tr(status_raw) : "";
        const priority = doc.priority || row.priority || "";
        const events_count = doc.events_count || 0;
        const unanswered_count = doc.unanswered_count || 0;

        const updated_dt = doc.last_event_at || doc.modified || row.modified;
        const updated_rel = rel_time(updated_dt);

        const avatar_src = full_path(doc.avatar || "/assets/dantist_app/files/egg.png");

        const status_chip = status_label
          ? `<span class="crm-chip">${frappe.utils.escape_html(status_label)}</span>`
          : "";

        const pr_chip = priority
          ? `<span class="crm-chip">${frappe.utils.escape_html(tr(priority))}</span>`
          : "";

        const events_chip = events_count
          ? `<span class="crm-chip">${frappe.utils.escape_html(tr(cfg.labels.eventsCount))}: ${String(events_count)}</span>`
          : "";

        const unans_chip = unanswered_count
          ? `<span class="crm-chip">${frappe.utils.escape_html(tr(cfg.labels.unanswered))}: ${String(unanswered_count)}</span>`
          : "";

        const time_chip = updated_rel
          ? `<span class="crm-chip -ghost"><span class="lbl">${frappe.utils.escape_html(labelUpdated)}:</span> ${frappe.utils.escape_html(updated_rel)}</span>`
          : "";

        const metaMain = [
          status_chip,
          pr_chip,
          events_chip,
          unans_chip
        ].filter(Boolean).join(" ");

        const metaTime = [time_chip].filter(Boolean).join(" ");

        const pr_badge = priority
          ? `<span class="crm-badge">P: ${frappe.utils.escape_html(tr(priority))}</span>`
          : "";

        return `
          <div class="crm-item dnt-user-case-item"
               data-doctype="${cfg.doctypes.case}"
               data-name="${frappe.utils.escape_html(case_name)}">
            <div class="crm-left">
              <div class="crm-avatar">
                <img src="${frappe.utils.escape_html(avatar_src)}" alt="">
              </div>
              <div class="crm-body">
                <div class="crm-title">
                  ${frappe.utils.escape_html(title)}
                </div>
                <div class="crm-meta">
                  ${metaMain}
                </div>
                <div class="crm-meta -time">
                  ${metaTime}
                </div>
              </div>
            </div>
            <div class="crm-right">
              ${pr_badge}
            </div>
          </div>
        `;
      })
      .join("");

    list_el.html(html);
  }

  // ===== RENDER: задачи — как в v9 (dnt-user-item) =====

  function render_tasks(list_el, rows, is_self) {
    log("render_tasks input", { rowsCount: rows ? rows.length : 0 });

    if (!rows || !rows.length) {
      render_empty(list_el, is_self, "tasks");
      return;
    }

    const items = rows.slice(0, cfg.limits.tasks);
    const html = items
      .map(row => {
        const title =
          row.description ||
          (row.reference_type && row.reference_name
            ? `${row.reference_type}: ${row.reference_name}`
            : row.name);

        const status_raw = row.status;
        const status_label = status_raw ? tr(status_raw) : "";
        const status_cls = status_raw ? status_class(status_raw) : "";
        const date = format_date(row.date || row.modified) || "";
        const ref_info =
          row.reference_type && row.reference_name
            ? `${row.reference_type}: ${row.reference_name}`
            : "";

        return `
          <div class="dnt-user-item dnt-user-item-task"
               data-doctype="${cfg.doctypes.todo}"
               data-name="${frappe.utils.escape_html(row.name)}"
               data-ref-doctype="${frappe.utils.escape_html(row.reference_type || "")}"
               data-ref-name="${frappe.utils.escape_html(row.reference_name || "")}">
            <div class="dnt-user-item-main">
              <div>
                <div class="dnt-user-item-title">
                  ${frappe.utils.escape_html(title)}
                </div>
                ${
                  ref_info
                    ? `<div class="dnt-user-item-sub">
                         ${frappe.utils.escape_html(ref_info)}
                       </div>`
                    : ""
                }
                <div class="dnt-user-item-meta">
                  ${
                    status_label
                      ? `<span class="dnt-user-pill ${status_cls}">
                           <span class="dnt-user-dot"></span>
                           <span>${frappe.utils.escape_html(status_label)}</span>
                         </span>`
                      : ""
                  }
                  ${
                    row.priority
                      ? `<span class="dnt-user-pill">
                           ${frappe.utils.escape_html(tr(row.priority))}
                         </span>`
                      : ""
                  }
                  ${date ? `<span>${frappe.utils.escape_html(date)}</span>` : ""}
                </div>
              </div>
            </div>
          </div>
        `;
      })
      .join("");

    list_el.html(html);
  }

  // ===== data loading =====

  function load_cards(frm, list_el, user_email, is_self) {
    list_el.html(
      `<div class="dnt-user-widget-loading">${frappe.utils.escape_html(tr(cfg.labels.loading))}</div>`
    );

    log("load_cards start", {
      user_email,
      user_doc_name: frm.doc.name,
      user_doc_email: frm.doc.email
    });

    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: cfg.doctypes.todo,
        fields: [
          "name",
          "description",
          "reference_type",
          "reference_name",
          "status",
          "priority",
          "date",
          "modified"
        ],
        filters: [
          ["ToDo", "allocated_to", "=", user_email],
          ["ToDo", "status", "!=", "Cancelled"],
          ["ToDo", "reference_type", "=", cfg.doctypes.case]
        ],
        order_by: "modified desc",
        limit_page_length: 50
      },
      callback(r) {
        const rows = r.message || [];
        log("load_cards ToDo result", {
          rowsCount: rows.length,
          rows
        });

        const names_set = new Set();
        rows.forEach(row => {
          const key = row.reference_name || row.name;
          if (key) names_set.add(key);
        });
        update_counts(frm, { cards: names_set.size });

        if (!rows.length) {
          render_empty(list_el, is_self, "cards");
          return;
        }

        const case_names = Array.from(names_set);
        if (!case_names.length) {
          render_cards(list_el, rows, [], is_self);
          return;
        }

        frappe.call({
          method: "frappe.client.get_list",
          args: {
            doctype: cfg.doctypes.case,
            fields: [
              "name",
              "title",
              "display_name",
              "avatar",
              "priority",
              "runtime_status",
              "last_event_at",
              "events_count",
              "unanswered_count",
              "modified"
            ],
            filters: [[cfg.doctypes.case, "name", "in", case_names]],
            limit_page_length: case_names.length
          },
          callback(r2) {
            const details = r2.message || [];
            log("load_cards Engagement Case result", {
              caseNames: case_names,
              detailsCount: details.length,
              details
            });
            render_cards(list_el, rows, details, is_self);
          }
        });
      }
    });
  }

  function load_tasks(frm, list_el, user_email, is_self) {
    list_el.html(
      `<div class="dnt-user-widget-loading">${frappe.utils.escape_html(tr(cfg.labels.loading))}</div>`
    );

    log("load_tasks start", {
      user_email,
      user_doc_name: frm.doc.name,
      user_doc_email: frm.doc.email
    });

    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: cfg.doctypes.todo,
        fields: [
          "name",
          "description",
          "reference_type",
          "reference_name",
          "status",
          "priority",
          "date",
          "modified"
        ],
        filters: [
          ["ToDo", "allocated_to", "=", user_email],
          ["ToDo", "status", "!=", "Cancelled"]
        ],
        order_by: "modified desc",
        limit_page_length: 50
      },
      callback(r) {
        const rows = r.message || [];
        log("load_tasks ToDo result", {
          rowsCount: rows.length,
          rows
        });

        update_counts(frm, { tasks: rows.length });
        render_tasks(list_el, rows, is_self);
      }
    });
  }

  // ===== actions / handlers =====

  function bind_actions(frm) {
    if (frm.dnt_user_work_tab_bound) return;
    frm.dnt_user_work_tab_bound = true;

    // Переключение "Cases / Tasks" внутри карточки
    frm.$wrapper.on("click", ".dnt-user-work-tab-btn", function () {
      const btn = $(this);
      const kind = btn.attr("data-kind");
      if (!kind) return;

      const card = btn.closest(".dnt-user-work-card");
      if (!card.length) return;

      card.find(".dnt-user-work-tab-btn").removeClass("active");
      btn.addClass("active");

      card.find(".dnt-user-work-pane").removeClass("active");
      card.find(`.dnt-user-work-pane[data-kind='${kind}']`).addClass("active");

      log("inner tab switch", { kind });
    });

    // Открытие кейса
    frm.$wrapper.on("click", ".dnt-user-case-item, .crm-item.dnt-user-case-item", function () {
      const el = $(this);
      const doctype = el.attr("data-doctype") || cfg.doctypes.case;
      const name = el.attr("data-name");
      if (!doctype || !name) return;
      log("open case", { doctype, name });
      frappe.set_route("Form", doctype, name);
    });

    // Открытие задачи
    frm.$wrapper.on("click", ".dnt-user-item-task", function () {
      const el = $(this);
      const ref_doctype = el.attr("data-ref-doctype");
      const ref_name = el.attr("data-ref-name");
      const todo_name = el.attr("data-name");

      log("open task click", { ref_doctype, ref_name, todo_name });

      if (ref_doctype && ref_name) {
        frappe.set_route("Form", ref_doctype, ref_name);
      } else if (todo_name) {
        frappe.set_route("Form", cfg.doctypes.todo, todo_name);
      }
    });

    // "All Cases / All Tasks"
    frm.$wrapper.on("click", ".dnt-user-work-all-link", function (e) {
      e.preventDefault();
      const el = $(this);
      const kind = el.attr("data-kind");
      const user_email = el.attr("data-user");
      if (!kind || !user_email) return;

      log("open list from all-link", { kind, user_email });

      if (kind === "cards") {
        frappe.set_route("List", cfg.doctypes.todo, {
          allocated_to: user_email,
          reference_type: cfg.doctypes.case,
          status: "Open"
        });
      } else if (kind === "tasks") {
        frappe.set_route("List", cfg.doctypes.todo, {
          allocated_to: user_email,
          status: "Open"
        });
      }
    });
  }

  // ===== init with retries =====

  function attempt_init(frm, is_self, tries_left) {
    if (!frm || !frm.doc || !frm.doc.name) {
      log("attempt_init: no frm.doc yet");
      return;
    }

    const panel = ensure_tab_structures(frm, is_self);
    if (!panel) {
      if (tries_left > 0) {
        log("panel not ready yet, retrying…", { tries_left });
        setTimeout(() => attempt_init(frm, is_self, tries_left - 1), cfg.retries.delayMs);
      } else {
        log("panel not ready after retries, giving up");
      }
      return;
    }

    log("panel ready, binding actions and loading data");

    bind_actions(frm);
    update_counts(frm, { cards: 0, tasks: 0 });

    const user_email = frm.doc.name; // User.name = email / user id
    load_cards(frm, panel.cardsList, user_email, is_self);
    load_tasks(frm, panel.tasksList, user_email, is_self);
  }

  // Лёгкий "анти-hide" цикл: если Frappe вдруг снова пометит секцию empty/hide-control —
  // через небольшой интервал вернём ей display:block. Но сам контент уже не зависит от секции.
  function start_visibility_guard(frm) {
    if (frm.dnt_user_work_guard_started) return;
    frm.dnt_user_work_guard_started = true;

    let left = 20; // ~20 * 200ms = ~4 сек после refresh
    (function tick() {
      if (left-- <= 0) return;
      try {
        const $wrapper = frm.$wrapper;
        if (!$wrapper || !$wrapper.length) return;
        const $section = $wrapper.find(`.row.form-section[data-fieldname="${cfg.tabFieldname}"]`);
        const $body = $section.find(".section-body");
        if ($section.length) {
          $section.removeClass("empty-section hide-control").addClass("visible-section");
          $section.css({ display: "block", visibility: "visible" });
          $body.css({ display: "block", visibility: "visible" });
        }
      } catch (e) {
        // молча
      }
      setTimeout(tick, 200);
    })();
  }

  function init_for_form(frm) {
    if (!frm || !frm.doc || !frm.doc.name) {
      log("init_for_form: missing frm.doc");
      return;
    }

    ensure_css();

    const is_self =
      frappe.session &&
      frappe.session.user &&
      frappe.session.user === frm.doc.name;

    log("refresh", {
      user_doc_name: frm.doc.name,
      user_doc_email: frm.doc.email,
      is_self
    });

    start_visibility_guard(frm);
    attempt_init(frm, is_self, cfg.retries.layout);
  }

  // ===== hook into User.refresh =====

  frappe.ui.form.on("User", {
    refresh(frm) {
      setTimeout(() => {
        try {
          init_for_form(frm);
        } catch (e) {
          log("init error", e);
        }
      }, 0);
    }
  });
})();