// === DNT User Work Tab (User form widgets, Engagement Case + ToDo) — v12 ===
//
// Base: v11 (логика вкладки, загрузка данных, счётчики, клики).
// v12:
// • Даты из comment_when без HTML-тегов (только текст).
// • Кейсы (Engagement Case): CRM-стиль как в widget-превью: avatar + title + platform + lang + Updated + P-badge.
//   — убран статус колонки и любые Events / Unanswered из виджета User Work.
// • Задачи: стиль как в engagement_case_tasks.js (ec-task + chips), без авто-правил и кнопок Complete/Cancel.
// • "My Work" таб:
//   — всегда первая вкладка;
//   — если пользователь был на "My Work", это запоминается и при refresh снова активируется "My Work"
//     (остальные вкладки не переопределяем, чтобы не ломать роуты типа "открыть сразу Settings").
//

(() => {
  if (window.DNT_USER_WORK_TAB_V12) return;
  window.DNT_USER_WORK_TAB_V12 = true;

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
    logPrefix: "[DNT-USER-WORK v12]",
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
      footerHint: "Click a card or task to open it",
      summaryTemplate: "{cards} • {tasks}",
      updated: "Updated"
    },
    retries: {
      layout: 10,
      delayMs: 80
    },
    lastMyWorkKey: "dnt.user.last_tab_mywork"
  };

  function log(...args) {
    try {
      if (console && console.log) console.log(cfg.logPrefix, ...args);
    } catch (e) {}
  }

  // ===== CSS: секция видима + рамка + CRM-стиль кейсов + EC-стиль задач =====

  function ensure_css() {
    if (document.getElementById(cfg.cssId)) return;

    const css = `
      /* === DNT User Work: формальная секция — всегда видима (fallback) === */
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

      /* === EC-style задачи (как в engagement_case_tasks) === */
      .ec-task{
        display:flex;
        align-items:flex-start;
        justify-content:space-between;
        gap:10px;
        padding:10px 0;
        border-top:1px solid var(--table-border-color, var(--border-color,#eef2f7));
      }
      .ec-task:first-child{border-top:none}
      .ec-task.-muted{opacity:.78}
      .ec-task .l{
        flex:1 1 auto;
        min-width:0;
        display:flex;
        flex-direction:column;
        gap:4px;
      }
      .ec-task .title{
        font-weight:600;
        font-size:13px;
        color: var(--text-color, #111827);
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
      }
      .ec-task .meta{
        display:flex;
        gap:6px;
        flex-wrap:wrap;
        margin-top:3px;
        color:var(--text-muted,#6b7280);
        font-size:11px;
      }
      .ec-task .chip{
        border:1px solid var(--border-color,#e5e7eb);
        border-radius:999px;
        padding:2px 6px;
        background: var(--bg-light-gray,#f3f4f6);
        color: var(--text-color,#111827);
      }
      .ec-task .chip.-ghost{
        background: var(--control-bg,#f8fafc);
        color: var(--text-color,#111827);
      }
      .ec-task .chip.-p-high{
        background: var(--alert-bg-danger, #fee2e2);
        border-color: color-mix(in oklab, var(--alert-bg-danger, #fee2e2) 60%, #ffffff);
        color: var(--alert-text-danger, #991b1b);
      }
      .ec-task .chip.-p-med{
        background: var(--bg-light-blue, #e5f0ff);
        border-color: var(--text-on-light-blue, #dbeafe);
        color: color-mix(in oklab, var(--text-on-light-blue, #1e3a8a) 80%, #111);
      }
      .ec-task .chip.-p-low{
        background: var(--bg-green, #e8f5e9);
        border-color: color-mix(in oklab, var(--bg-green, #e8f5e9) 60%, #ffffff);
        color: var(--text-on-green, #14532d);
      }
      .ec-task .chip-target.-overdue{
        background: var(--alert-bg-danger, #fee2e2);
        border-color: color-mix(in oklab, var(--alert-bg-danger, #fecaca) 70%, #ffffff);
        color: var(--alert-text-danger, #991b1b);
      }
      .ec-task .r{
        flex:0 0 auto;
        display:flex;
        align-items:center;
        gap:4px;
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

  // comment_when → выкидываем HTML-теги, оставляем только текст ("2 hours ago" и т. п.)
  function rel_time(value) {
    if (!value) return "";
    try {
      if (window.frappe?.datetime?.comment_when) {
        const html = frappe.datetime.comment_when(value);
        const tmp = document.createElement("div");
        tmp.innerHTML = html;
        return (tmp.textContent || tmp.innerText || "").trim();
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

  function clean_title(raw){
    const s = String(raw || "")
      .replace(/<[^>]*>/g, "")
      .replace(/\s+/g, " ").trim();
    return s.length > 60 ? s.slice(0, 60).trimEnd() + "…" : s;
  }

  function fmt_user_dt(dtStr) {
    if (!dtStr) return "";
    try {
      if (window.moment && window.frappe?.datetime?.convert_to_user_tz) {
        return moment(frappe.datetime.convert_to_user_tz(dtStr)).format("YYYY-MM-DD HH:mm");
      }
    } catch (e) {}
    return String(dtStr);
  }

  function is_overdue(t) {
    if ((t.status || "Open") !== "Open") return false;
    try {
      if (!window.moment) return false;
      const now = moment();
      const target = t.custom_target_datetime || t.date || null;
      if (!target) return false;
      return moment(target).isBefore(now);
    } catch (e) {
      return false;
    }
  }

  function priority_class(p){
    if (p === "High") return "-p-high";
    if (p === "Low") return "-p-low";
    return "-p-med";
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

    // --- Tab button: ВСЕГДА ПЕРВАЯ вкладка ---
    let $tabLi = $tabs.find("#" + cfg.tabBtnId).closest("li");
    if ($tabLi.length) {
      $tabLi.detach();
    } else {
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
      log("tab button created");
    }
    $tabs.prepend($tabLi);
    $tabLi.find(".nav-link").text(tr(titles.tab));

    // --- Tab pane (bootstrap-tab) ---
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
    if ($section.length) {
      $section.removeClass("empty-section hide-control").addClass("visible-section");
      $section.css({ display: "block", visibility: "visible" });
      $sectionBody.css("display", "block");
      log("section visibility patched (fallback)");
    }

    // --- Наш root, не зависящий от section-body ---
    let $root = $tabPane.find("#" + cfg.rootId);
    if (!$root.length) {
      $root = $(`<div id="${cfg.rootId}"></div>`);
      if ($section.length) {
        $section.after($root);
      } else {
        $tabPane.append($root);
      }
      log("root created");
    }

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

  // ===== RENDER: кейсы — CRM-стиль, но только platform/lang/Updated/P =====

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

        const priority = doc.priority || row.priority || "";

        const updated_dt = doc.last_event_at || doc.modified || row.modified;
        const updated_rel = rel_time(updated_dt);

        const avatar_src = full_path(doc.avatar || "/assets/dantist_app/files/egg.png");
        const platform = doc.channel_platform || "";
        const lang = doc.preferred_language || "";

        const platform_chip = platform
          ? `<span class="crm-chip">${frappe.utils.escape_html(tr(platform))}</span>`
          : "";

        const lang_chip = lang
          ? `<span class="crm-chip -ghost">${frappe.utils.escape_html(String(lang).toLowerCase())}</span>`
          : "";

        const time_chip = updated_rel
          ? `<span class="crm-chip -ghost"><span class="lbl">${frappe.utils.escape_html(labelUpdated)}:</span> ${frappe.utils.escape_html(updated_rel)}</span>`
          : "";

        const metaMain = [platform_chip, lang_chip].filter(Boolean).join(" ");
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

  // ===== RENDER: задачи — EC-стиль (ec-task + chips) =====

  function render_tasks(list_el, rows, is_self) {
    log("render_tasks input", { rowsCount: rows ? rows.length : 0 });

    if (!rows || !rows.length) {
      render_empty(list_el, is_self, "tasks");
      return;
    }

    const items = rows.slice(0, cfg.limits.tasks);
    const html = items
      .map(row => {
        const title_raw =
          row.description ||
          (row.reference_type && row.reference_name
            ? `${row.reference_type}: ${row.reference_name}`
            : row.name);

        const title = clean_title(title_raw);

        const reminder_dt = row.custom_due_datetime || null;
        const reminder = reminder_dt ? fmt_user_dt(reminder_dt) : null;

        const target_dt = row.custom_target_datetime || row.date || null;
        const target = target_dt ? fmt_user_dt(target_dt) : null;

        const who = row.allocated_to || "";
        const st  = row.status || "Open";
        const clsMuted = st === "Open" ? "" : " -muted";
        const p = row.priority || "Medium";
        const pcls = priority_class(p);
        const overdue = is_overdue(row);
        const created = row.creation ? fmt_user_dt(row.creation) : "";
        const ref_info =
          row.reference_type && row.reference_name
            ? `${row.reference_type}: ${row.reference_name}`
            : "";

        const chips = [];
        chips.push(
          `<span class="chip">${frappe.utils.escape_html(tr(st))}</span>`
        );
        if (row.priority) {
          chips.push(
            `<span class="chip ${pcls}">${frappe.utils.escape_html(tr(row.priority))}</span>`
          );
        }
        if (who) {
          chips.push(
            `<span class="chip -ghost">@${frappe.utils.escape_html(who)}</span>`
          );
        }
        if (ref_info) {
          chips.push(
            `<span class="chip -ghost">${frappe.utils.escape_html(ref_info)}</span>`
          );
        }
        if (target) {
          chips.push(
            `<span class="chip -ghost chip-target${overdue ? " -overdue" : ""}">🗓 ${frappe.utils.escape_html(target)}</span>`
          );
        }
        if (reminder) {
          chips.push(
            `<span class="chip -ghost">🔔 ${frappe.utils.escape_html(reminder)}</span>`
          );
        }
        if (created) {
          chips.push(
            `<span class="chip -ghost">${frappe.utils.escape_html(created)}</span>`
          );
        }

        return `
          <div class="ec-task dnt-user-task${clsMuted}"
               data-doctype="${cfg.doctypes.todo}"
               data-name="${frappe.utils.escape_html(row.name)}"
               data-ref-doctype="${frappe.utils.escape_html(row.reference_type || "")}"
               data-ref-name="${frappe.utils.escape_html(row.reference_name || "")}">
            <div class="l">
              <div class="title" title="${frappe.utils.escape_html(title)}">
                ${frappe.utils.escape_html(title)}
              </div>
              <div class="meta">
                ${chips.join(" ")}
              </div>
            </div>
            <div class="r">
              <button class="btn btn-xs btn-default" type="button">
                ${frappe.utils.escape_html(tr("Open"))}
              </button>
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
              "modified",
              "channel_platform",
              "preferred_language"
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
          "modified",
          "allocated_to",
          "assigned_by",
          "custom_target_datetime",
          "custom_due_datetime",
          "creation"
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

  // ===== tab activation memory for My Work =====

  function activate_main_tab(frm, fieldname) {
    try {
      const $wrapper = frm.$wrapper;
      if (!$wrapper || !$wrapper.length) return;

      const $tabs = $wrapper.find("ul.form-tabs .nav-link");
      if (!$tabs.length) return;

      let $target = $tabs.filter(`#${cfg.tabBtnId}`);
      if (!$target.length && fieldname) {
        $target = $tabs.filter(`[data-fieldname="${fieldname}"]`);
      }
      if (!$target.length) return;

      if ($.fn.tab) {
        $target.tab("show");
      } else {
        $target.trigger("click");
      }

      localStorage.setItem(cfg.lastMyWorkKey, "1");
      log("activate_main_tab → My Work shown");
    } catch (e) {
      log("activate_main_tab error", e);
    }
  }

  function bind_actions(frm) {
    if (frm.dnt_user_work_tab_bound) return;
    frm.dnt_user_work_tab_bound = true;

    const $w = frm.$wrapper;

    // Внутренние табы "Cases / Tasks" внутри карточки
    $w.on("click", ".dnt-user-work-tab-btn", function () {
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

    // Клик по кейсу
    $w.on("click", ".dnt-user-case-item", function () {
      const el = $(this);
      const doctype = el.attr("data-doctype") || cfg.doctypes.case;
      const name = el.attr("data-name");
      if (!doctype || !name) return;
      log("open case", { doctype, name });
      frappe.set_route("Form", doctype, name);
    });

    // Клик по задаче (любой клик по строке)
    $w.on("click", ".dnt-user-task", function () {
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
    $w.on("click", ".dnt-user-work-all-link", function (e) {
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

    // Запоминаем, что пользователь активировал именно "My Work" таб
    $w.on("click", "ul.form-tabs .nav-link", function () {
      const fieldname = $(this).attr("data-fieldname") || "";
      const isMyWork = fieldname === cfg.tabFieldname || this.id === cfg.tabBtnId;
      localStorage.setItem(cfg.lastMyWorkKey, isMyWork ? "1" : "0");
      log("outer tab click", { fieldname, isMyWork });
    });
  }

  function apply_last_mywork_tab_if_needed(frm) {
    try {
      const prefer = localStorage.getItem(cfg.lastMyWorkKey) === "1";
      if (!prefer) return;

      const $wrapper = frm.$wrapper;
      if (!$wrapper || !$wrapper.length) return;

      const $tabs = $wrapper.find("ul.form-tabs .nav-link");
      if (!$tabs.length) return;

      const $active = $tabs.filter(".active");
      if ($active.length) {
        const fieldname = $active.attr("data-fieldname") || "";
        // Не трогаем, если явно открыт не "User Details" и не наш таб
        if (fieldname && fieldname !== "user_details_tab" && fieldname !== cfg.tabFieldname) {
          log("skip auto My Work (another tab active)", { fieldname });
          return;
        }
      }

      activate_main_tab(frm, cfg.tabFieldname);
      log("auto-activated My Work from memory");
    } catch (e) {
      log("apply_last_mywork_tab_if_needed error", e);
    }
  }

  // Лёгкий guard против повторного hide секции Frappe
  function start_visibility_guard(frm) {
    if (frm.dnt_user_work_guard_started) return;
    frm.dnt_user_work_guard_started = true;

    let left = 20; // ~4 секунды после refresh
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

    bind_actions(frm);
    update_counts(frm, { cards: 0, tasks: 0 });

    const user_email = frm.doc.name; // User.name = email / user id
    load_cards(frm, panel.cardsList, user_email, is_self);
    load_tasks(frm, panel.tasksList, user_email, is_self);

    // После того, как всё отрисовали, пробуем восстановить таб "My Work"
    apply_last_mywork_tab_if_needed(frm);
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