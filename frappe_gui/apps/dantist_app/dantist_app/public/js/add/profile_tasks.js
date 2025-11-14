// === DNT User Work Tab (User form widgets, Engagement Case + ToDo) — v15.6 ===
//
// Base: v11 (логика вкладки, загрузка данных, счётчики, клики).
// v15:
// • Заголовок задачи берём ИЗ ToDo.description (строго).
// • Добавлены подробные логи по ToDo (какие поля приходят и что уходит в title).
// • Добавлен отступ справа у корня блока (как у обычного контента).
// • "All Cases" ведёт в List → Engagement Case.
// • Расширенные логи по памяти вкладки.
//
// v15.1:
// • Если description = "Assignment for …" и есть Engagement Case, берём title кейса.
// • "All Cases" открывает Engagement Case с фильтром по assigned_to пользователя.
// • Для собственного профиля, если нет памяти, по умолчанию открываем My Work.
//
// v15.2:
// • Память вкладок перенесена в sessionStorage (fallback на localStorage).
// • Логика apply_last_mywork_tab_if_needed упрощена.
//
// v15.3:
// • (было) Зашивали fieldname в route — убрано.
//
// v15.4:
// • Память вкладок стала пер-пользовательской (ключи с doc.name).
// • НЕ переписывали route при клике по табам.
// • Рендер задач как в engagement_case_tasks.js.
// • MyCases сортируются по modified карточки (свежие сверху).
//
// v15.5:
// • Клик по задаче ВСЕГДА открывает ToDo, а не Engagement Case.
// • "All Cases" открывает список Engagement Case c фильтром _assign = ["like", "%user%"].
// • "All Tasks" открывает список ToDo с фильтром allocated_to = user, status = "Open".
// • Логика памяти вкладки полностью переписана:
//   - храним только последний fieldname табы,
//   - при клике только обновляем память,
//   - при refresh один раз ставим вкладку из памяти, без навязывания My Work.
//
// v15.6:
// • Память вкладок переписана ещё раз с нуля:
//   - при клике по любой верхней вкладке User сохраняем её fieldname;
//   - при refresh, после построения вкладок, один раз ищем сохранённую вкладку и триггерим по ней click();
//   - без сторожевых таймеров и флагов, ничего не борется с Frappe, просто переоткрываем нужную вкладку.
//

(() => {
  if (window.DNT_USER_WORK_TAB_V15_6) return;
  window.DNT_USER_WORK_TAB_V15_6 = true;

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
    mainClass: "dnt-user-work-main",
    cardsListAttr: "data-role-cards-list",
    tasksListAttr: "data-role-tasks-list",
    logPrefix: "[DNT-USER-WORK v15.6]",
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
    lastTabKeyBase: "dnt.user.last_tab_fieldname"
  };

  function log(...args) {
    try {
      if (console && console.log) console.log(cfg.logPrefix, ...args);
    } catch (e) {}
  }

  // ===== storage helpers (sessionStorage + fallback localStorage) =====

  function get_pref(key) {
    try {
      if (window.sessionStorage) {
        const v = window.sessionStorage.getItem(key);
        if (v !== null && v !== undefined) return v;
      }
    } catch (e) {}
    try {
      if (window.localStorage) {
        const v2 = window.localStorage.getItem(key);
        if (v2 !== null && v2 !== undefined) return v2;
      }
    } catch (e2) {}
    return "";
  }

  function set_pref(key, val) {
    const value = String(val);
    try {
      if (window.sessionStorage) {
        window.sessionStorage.setItem(key, value);
        return;
      }
    } catch (e) {}
    try {
      if (window.localStorage) {
        window.localStorage.setItem(key, value);
      }
    } catch (e2) {}
  }

  // ===== per-user tab memory helpers =====

  function get_last_tab(docname) {
    const key = cfg.lastTabKeyBase + "::" + (docname || "");
    return get_pref(key) || "";
  }

  function set_last_tab(docname, fieldname) {
    if (!docname || !fieldname) return;
    const key = cfg.lastTabKeyBase + "::" + docname;
    set_pref(key, fieldname);
  }

  // Восстановление последней основной вкладки User (User Details / My Work / и т.д.)
  function restore_last_main_tab(frm) {
    try {
      const docname = frm.doc && frm.doc.name ? frm.doc.name : "";
      if (!docname) {
        log("restore_last_main_tab: no docname");
        return;
      }

      const last_fieldname = get_last_tab(docname);
      if (!last_fieldname) {
        log("restore_last_main_tab: nothing stored, keep default");
        return;
      }

      const $wrapper = frm.$wrapper;
      if (!$wrapper || !$wrapper.length) {
        log("restore_last_main_tab: no wrapper");
        return;
      }

      const $tabs = $wrapper.find("ul.form-tabs .nav-link");
      if (!$tabs.length) {
        log("restore_last_main_tab: no tabs");
        return;
      }

      let $target = $tabs.filter(`[data-fieldname="${last_fieldname}"]`);
      if (!$target.length && last_fieldname === cfg.tabFieldname) {
        $target = $tabs.filter(`#${cfg.tabBtnId}`);
      }
      if (!$target.length) {
        log("restore_last_main_tab: stored tab not found", {
          docname,
          last_fieldname
        });
        return;
      }

      if ($target.hasClass("active")) {
        log("restore_last_main_tab: stored tab already active", {
          docname,
          last_fieldname
        });
        return;
      }

      log("restore_last_main_tab: triggering click on stored tab", {
        docname,
        last_fieldname
      });
      $target.trigger("click");
    } catch (e) {
      log("restore_last_main_tab error", e);
    }
  }

  // ===== CSS =====

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

      #${cfg.rootId} {
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
        padding-left: 0.75rem;
        padding-right: 0.75rem;
        padding-bottom: 0.5rem;
      }

      .${cfg.containerClass}{
        margin-top: 0;
        margin-bottom: 0;
      }

      .${cfg.mainClass}{
        min-width: 0;
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
        background: var(--bg-light-gray,#f3f4f6);
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

  function full_path(p) {
    if (!p) return "";
    return p.startsWith("/") ? p : `/${p}`;
  }

  // Взято из engagement_case_tasks.js — лимит 40 символов
  function clean_title(raw) {
    const s = String(raw || "")
      .replace(/<[^>]*>/g, "")
      .replace(/\s+/g, " ")
      .trim();
    return s.length > 40 ? s.slice(0, 40).trimEnd() + "…" : s;
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

  // как в engagement_case_tasks.js — по custom_target_datetime
  function is_overdue(t) {
    if ((t.status || "Open") !== "Open") return false;
    try {
      if (!window.moment) return false;
      const now = moment();
      if (t.custom_target_datetime) return moment(t.custom_target_datetime).isBefore(now);
      return false;
    } catch (e) {
      return false;
    }
  }

  function priority_class(p) {
    if (p === "High") return "-p-high";
    if (p === "Low") return "-p-low";
    return "-p-med";
  }

  function update_counts(frm, partial) {
    const prev = frm.dnt_user_work_counts || { cards: 0, tasks: 0 };
    const next = Object.assign({}, prev, partial || {});
    frm.dnt_user_work_counts = next;

    const $main = frm.$wrapper.find("." + cfg.mainClass);
    if (!$main.length) return;

    const cards_text = `${next.cards} ${next.cards === 1 ? tr("case") : tr("cases")}`;
    const tasks_text = `${next.tasks} ${next.tasks === 1 ? tr("task") : tr("tasks")}`;

    const summary = cfg.labels.summaryTemplate
      .replace("{cards}", cards_text)
      .replace("{tasks}", tasks_text);

    $main.find("[data-role='summary']").text(summary);
    $main.find("[data-role='footer-info']").text(tr(cfg.labels.footerHint));

    $main.find("[data-role='cards-tab-count']").text(next.cards ? `(${next.cards})` : "");
    $main.find("[data-role='tasks-tab-count']").text(next.tasks ? `(${next.tasks})` : "");

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

    let $tabLi = $tabs.find("#" + cfg.tabBtnId).closest("li");
    if ($tabLi.length) {
      $tabLi.detach();
      log("tab button exists, detach & move to first");
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

    let $tabPane = $tabContent.find("#" + cfg.tabId);
    if (!$tabPane.length) {
      const paneHtml = `
        <div class="tab-pane fade"
             id="${cfg.tabId}"
             role="tabpanel"
             aria-labelledby="${cfg.tabBtnId}">
          <div class="row.form-section.card-section empty-section"
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

    let $root = $tabPane.find("#" + cfg.rootId);
    if (!$root.length) {
      $root = $(`<div id="${cfg.rootId}"></div>`);
      if ($sectionBody.length) {
        $sectionBody.empty().append($root);
      } else if ($section.length) {
        $section.append($root);
      } else {
        $tabPane.append($root);
      }
      log("root created");
    }

    $root.empty().append(`
      <div class="${cfg.containerClass} ${cfg.mainClass}">
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

  // ===== RENDER: кейсы (MyCases), сортировка по modified карточки =====

  function render_cards(list_el, rows, case_details, is_self) {
    log("render_cards input", {
      rowsCount: rows ? rows.length : 0,
      caseDetailsCount: case_details ? case_details.length : 0
    });

    if (!rows || !rows.length) {
      render_empty(list_el, is_self, "cards");
      return;
    }

    const row_by_case = new Map();
    rows.forEach(row => {
      const key = row.reference_name || row.name;
      if (!key) return;
      if (!row_by_case.has(key)) row_by_case.set(key, row);
    });

    const index_case = {};
    (case_details || []).forEach(doc => {
      index_case[doc.name] = doc;
    });

    const items = [];
    (case_details || []).forEach(doc => {
      const r = row_by_case.get(doc.name);
      if (r) items.push({ row: r, doc });
    });

    const limited = items.slice(0, cfg.limits.cards);
    const labelUpdated = tr(cfg.labels.updated);

    const html = limited
      .map(item => {
        const doc = item.doc || {};
        const row = item.row || {};
        const case_name = doc.name || row.reference_name || row.name;

        const title =
          doc.display_name ||
          doc.title ||
          row.description ||
          case_name;

        const priority = doc.priority || row.priority || "";

        const updated_dt = doc.modified || doc.last_event_at || row.modified;
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

  // ===== RENDER: задачи — как в engagement_case_tasks.js, + Assignment for =====

  function render_tasks(list_el, rows, is_self, case_index) {
    log("render_tasks input", {
      rowsCount: rows ? rows.length : 0,
      hasCaseIndex: !!case_index
    });

    if (!rows || !rows.length) {
      render_empty(list_el, is_self, "tasks");
      return;
    }

    const items = rows.slice(0, cfg.limits.tasks);

    try {
      const dbg = items.map(r => ({
        name: r.name,
        description: r.description,
        cleaned_title: clean_title(r.description || r.name || ""),
        status: r.status,
        priority: r.priority,
        reference_type: r.reference_type,
        reference_name: r.reference_name
      }));
      log("render_tasks mapping", dbg);
    } catch (e) {}

    const html = items
      .map(row => {
        const raw_desc = row.description || "";
        let base_title = "";

        if (raw_desc && !/^Assignment for\b/i.test(raw_desc)) {
          base_title = clean_title(raw_desc);
        } else if (
          /^Assignment for\b/i.test(raw_desc) &&
          row.reference_type === cfg.doctypes.case &&
          row.reference_name &&
          case_index &&
          case_index[row.reference_name]
        ) {
          const cdoc = case_index[row.reference_name];
          const ctitle = cdoc.display_name || cdoc.title || "";
          base_title = clean_title(ctitle || raw_desc || row.name || "");
        } else {
          base_title = clean_title(raw_desc || row.name || "");
        }

        const title = base_title;

        const reminder_dt = row.custom_due_datetime || null;
        const reminder = reminder_dt ? fmt_user_dt(reminder_dt) : null;

        const target_dt = row.custom_target_datetime || null;
        const target = target_dt ? fmt_user_dt(target_dt) : null;

        const who = row.allocated_to || row.owner || "";
        const st  = row.status || "Open";
        const clsMuted = st === "Open" ? "" : " -muted";
        const p = row.priority || "Medium";
        const pcls = priority_class(p);
        const overdue = is_overdue(row);
        const created = row.creation ? fmt_user_dt(row.creation) : "";
        const assigned_by = row.assigned_by || "";

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
        if (target) {
          chips.push(
            `<span class="chip -ghost chip-target${overdue ? " -overdue" : ""}" title="${frappe.utils.escape_html(tr("Target at"))}">🗓 ${frappe.utils.escape_html(target)}</span>`
          );
        }
        if (reminder) {
          chips.push(
            `<span class="chip -ghost" title="${frappe.utils.escape_html(tr("Reminder at"))}">🔔 ${frappe.utils.escape_html(reminder)}</span>`
          );
        }
        if (assigned_by) {
          chips.push(
            `<span class="chip -ghost">${frappe.utils.escape_html(tr("by"))} ${frappe.utils.escape_html(assigned_by)}</span>`
          );
        }
        if (created) {
          chips.push(
            `<span class="chip -ghost" title="${frappe.utils.escape_html(tr("Created"))}">${frappe.utils.escape_html(created)}</span>`
          );
        }

        if (
          row.reference_type === cfg.doctypes.case &&
          row.reference_name &&
          case_index &&
          case_index[row.reference_name]
        ) {
          const cdoc = case_index[row.reference_name];
          const ctitle = cdoc.display_name || cdoc.title || "";
          if (ctitle) {
            chips.push(
              `<span class="chip -ghost">${frappe.utils.escape_html(ctitle)}</span>`
            );
          }
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
            order_by: "modified desc",
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
          "creation",
          "owner"
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
        log("load_tasks ToDo raw rows", rows);

        try {
          const dbg = rows.map(row => ({
            name: row.name,
            description: row.description,
            status: row.status,
            priority: row.priority,
            reference_type: row.reference_type,
            reference_name: row.reference_name
          }));
          log("load_tasks ToDo fields snapshot", dbg);
        } catch (e) {}

        update_counts(frm, { tasks: rows.length });

        if (!rows.length) {
          render_tasks(list_el, rows, is_self, null);
          return;
        }

        const caseNamesSet = new Set();
        rows.forEach(row => {
          if (row.reference_type === cfg.doctypes.case && row.reference_name) {
            caseNamesSet.add(row.reference_name);
          }
        });

        if (!caseNamesSet.size) {
          render_tasks(list_el, rows, is_self, null);
          return;
        }

        const case_names = Array.from(caseNamesSet);

        frappe.call({
          method: "frappe.client.get_list",
          args: {
            doctype: cfg.doctypes.case,
            fields: ["name", "title", "display_name"],
            filters: [[cfg.doctypes.case, "name", "in", case_names]],
            limit_page_length: case_names.length
          },
          callback(r2) {
            const details = r2.message || [];
            const index_case = {};
            details.forEach(doc => {
              index_case[doc.name] = doc;
            });

            log("load_tasks Engagement Case result", {
              caseNames: case_names,
              detailsCount: details.length,
              details
            });

            render_tasks(list_el, rows, is_self, index_case);
          }
        });
      }
    });
  }

  // ===== табы + память активной вкладки =====

  function bind_actions(frm) {
    if (frm.dnt_user_work_tab_bound) return;
    frm.dnt_user_work_tab_bound = true;

    const $w = frm.$wrapper;

    $w.on("click", ".dnt-user-work-tab-btn", function () {
      const btn = $(this);
      const kind = btn.attr("data-kind");
      if (!kind) return;

      const main = btn.closest("." + cfg.mainClass);
      if (!main.length) return;

      main.find(".dnt-user-work-tab-btn").removeClass("active");
      btn.addClass("active");

      main.find(".dnt-user-work-pane").removeClass("active");
      main.find(`.dnt-user-work-pane[data-kind='${kind}']`).addClass("active");

      log("inner tab switch", { kind });
    });

    $w.on("click", ".dnt-user-case-item", function () {
      const el = $(this);
      const doctype = el.attr("data-doctype") || cfg.doctypes.case;
      const name = el.attr("data-name");
      if (!doctype || !name) return;
      log("open case", { doctype, name });
      frappe.set_route("Form", doctype, name);
    });

    // Клик по задаче: ВСЕГДА открываем ToDo, а не Engagement Case
    $w.on("click", ".dnt-user-task", function () {
      const el = $(this);
      const todo_name = el.attr("data-name");
      const ref_doctype = el.attr("data-ref-doctype");
      const ref_name = el.attr("data-ref-name");

      log("open task click", { todo_name, ref_doctype, ref_name });

      if (todo_name) {
        frappe.set_route("Form", cfg.doctypes.todo, todo_name);
      } else if (ref_doctype && ref_name) {
        frappe.set_route("Form", ref_doctype, ref_name);
      }
    });

    // All Cases / All Tasks — через route_options с фильтрами
    $w.on("click", ".dnt-user-work-all-link", function (e) {
      e.preventDefault();
      const el = $(this);
      const kind = el.attr("data-kind");
      const user_email = el.attr("data-user");
      if (!kind || !user_email) return;

      log("open list from all-link", { kind, user_email });

      if (kind === "cards") {
        // Engagement Case, фильтр по _assign like "%user%"
        frappe.route_options = {
          _assign: ["like", "%" + user_email + "%"]
        };
        frappe.set_route("List", cfg.doctypes.case);
      } else if (kind === "tasks") {
        // ToDo, фильтр по allocated_to = user, status = Open
        frappe.route_options = {
          _assign: ["like", "%" + user_email + "%"]
        };
        frappe.set_route("List", cfg.doctypes.todo);
      }
    });

    // Память верхних вкладок User: при клике запоминаем последнее data-fieldname
    $w.on("click", "ul.form-tabs .nav-link", function () {
      const fieldname = $(this).attr("data-fieldname") || "";
      const docname = frm.doc && frm.doc.name ? frm.doc.name : "";

      if (docname && fieldname) {
        set_last_tab(docname, fieldname);
      }

      log("outer tab click", {
        clicked_fieldname: fieldname,
        docname,
        lastTabForDoc: docname ? get_last_tab(docname) : ""
      });

      // Никаких set_route здесь — даём Frappe самому переключать вкладки
    });
  }

  function start_visibility_guard(frm) {
    if (frm.dnt_user_work_guard_started) return;
    frm.dnt_user_work_guard_started = true;

    let left = 20;
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
      } catch (e) {}
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

    // Восстанавливаем последнюю открытую основную вкладку User (если сохранена)
    restore_last_main_tab(frm);

    const user_email = frm.doc.name;

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

    start_visibility_guard(frm);
    attempt_init(frm, is_self, cfg.retries.layout);
  }

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