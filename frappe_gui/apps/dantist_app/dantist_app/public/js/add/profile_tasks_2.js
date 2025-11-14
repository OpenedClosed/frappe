// === DNT User Work Tab (User form widgets, Engagement Case + ToDo) — v9 ===
//
// Key points:
// • English labels only, but wrapped with tr() => _("...") / __("..."), Frappe-style.
// • Stable queries: ToDo.allocated_to + Engagement Case via reference_name.
// • Robust tab init: retries until User form tabs exist, plus CSS override to keep section visible.
// • Logs: detailed info about ToDos, cases, counts, current user, etc.

(() => {
  if (window.DNT_USER_WORK_TAB_V9) return;
  window.DNT_USER_WORK_TAB_V9 = true;

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
    containerClass: "dnt-user-work-widgets",
    cardsListAttr: "data-role-cards-list",
    tasksListAttr: "data-role-tasks-list",
    logPrefix: "[DNT-USER-WORK v9]",
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
      summaryTemplate: "{cards} • {tasks}"
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

  // ===== CSS: keep dnt_work_tab visible, nice card styling =====

  function ensure_css() {
    if (document.getElementById(cfg.cssId)) return;

    const css = `
        /* === DNT User Work: force section ALWAYS visible === */
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

        /* Подстрахуемся: когда наша таба активна — она точно показывается */
        #${cfg.tabId}.tab-pane {
          visibility: visible !important;
        }

        /* Force section-body visible for our custom tab, even if Frappe marks it empty-section */
        .row.form-section.card-section[data-fieldname="${cfg.tabFieldname}"] .section-body {
          display: block !important;
        }
        .row.form-section.card-section[data-fieldname="${cfg.tabFieldname}"] {
          margin-bottom: 0.75rem;
        }

        .${cfg.containerClass}{
          margin-top: 0.75rem;
          margin-bottom: 1.5rem;
        }

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

  function status_class(raw) {
    if (!raw) return "";
    const s = String(raw).toLowerCase();
    const closed_tokens = ["closed", "completed", "cancelled", "archived", "lost"];
    return closed_tokens.some(t => s.includes(t))
      ? "dnt-user-pill-status-closed"
      : "dnt-user-pill-status-open";
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

  // ===== DOM: tab + section =====

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

    // --- Tab button ---
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

    // --- Tab pane ---
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

    const $section = $tabPane.find(`.row.form-section[data-fieldname="${cfg.tabFieldname}"]`);
    const $sectionBody = $section.find(".section-body");

    // Make sure Frappe doesn't hide it
    if ($section.length) {
      $section.removeClass("empty-section").addClass("visible-section");
      $sectionBody.css("display", "block");
      log("section visibility patched");
    }

    // Rebuild section-body content every time
    $sectionBody.empty().append(`
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
            <div class="dnt-user-widget-list" ${cfg.cardsListAttr}="1">
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

    const cardsList = $sectionBody.find("[" + cfg.cardsListAttr + "]");
    const tasksList = $sectionBody.find("[" + cfg.tasksListAttr + "]");

    $section.removeClass("empty-section").addClass("visible-section");
    $sectionBody.css("display", "block");

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

    const html = items
      .map(row => {
        const case_name = row.reference_name || row.name;
        const doc = index_case[case_name] || {};
        const title = row.description || doc.title || case_name;
        const status_raw = doc.runtime_status || row.status;
        const status_label = status_raw ? tr(status_raw) : "";
        const status_cls = status_raw ? status_class(status_raw) : "";
        const priority = doc.priority || row.priority || "";
        const date = format_date(doc.last_event_at || doc.modified || row.modified);
        const events_count = doc.events_count || 0;
        const unanswered_count = doc.unanswered_count || 0;

        return `
          <div class="dnt-user-item dnt-user-item-case"
               data-doctype="${cfg.doctypes.case}"
               data-name="${frappe.utils.escape_html(case_name)}">
            <div class="dnt-user-item-main">
              <div>
                <div class="dnt-user-item-title">
                  ${frappe.utils.escape_html(title)}
                </div>
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
                    priority
                      ? `<span class="dnt-user-pill">
                           ${frappe.utils.escape_html(tr(priority))}
                         </span>`
                      : ""
                  }
                  ${
                    events_count
                      ? `<span class="dnt-user-pill">
                           ${frappe.utils.escape_html(tr(cfg.labels.eventsCount))}: ${String(events_count)}
                         </span>`
                      : ""
                  }
                  ${
                    unanswered_count
                      ? `<span class="dnt-user-pill dnt-user-pill-unanswered">
                           ${frappe.utils.escape_html(tr(cfg.labels.unanswered))}: ${String(unanswered_count)}
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

    frm.$wrapper.on("click", ".dnt-user-item-case", function () {
      const el = $(this);
      const doctype = el.attr("data-doctype") || cfg.doctypes.case;
      const name = el.attr("data-name");
      if (!doctype || !name) return;
      log("open case", { doctype, name });
      frappe.set_route("Form", doctype, name);
    });

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

    const user_email = frm.doc.name; // in ERPNext, User.name is usually email / user id
    load_cards(frm, panel.cardsList, user_email, is_self);
    load_tasks(frm, panel.tasksList, user_email, is_self);
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