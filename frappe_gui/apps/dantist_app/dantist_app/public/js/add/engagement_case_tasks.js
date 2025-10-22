// Engagement Case — Tasks UI — v4.19 (newest first, page=5, overdue highlight)
(function () {
  const DOCTYPE = "Engagement Case";
  const PAGE_LEN = 5; // <= по запросу
  const SEC_ID = "ec-tasks-area";
  const SEC_TITLE = "Tasks";
  const LS_KEY_COLLAPSE = "ec_tasks_collapsed"; // "1" collapsed, "0" expanded

  // ======== Rules (как было) ========
  const FORM_RULES = {
    status_leads: {
      "Call Later": {
        showDialog: true,
        title: __("Call Later"),
        baseFields: ["due", "assignees", "assign_me", "priority"],
        extraFields: () => [],
        shouldTrigger: ({ prev, cur }) => prev !== "Call Later" && cur === "Call Later",
        makePayload: (vals, me) => {
          let a = Array.isArray(vals.assignees) ? vals.assignees.slice() : (vals.assignees || []);
          if (vals.assign_me && me && !a.includes(me)) a.push(me);
          return { description: "Manual Callback", due: vals.due, priority: vals.priority || "Medium", assignees: a };
        },
      },
    },
    status_deals: {
      "Appointment Scheduled": {
        showDialog: false,
        shouldTrigger: ({ prev, cur }) => prev !== "Appointment Scheduled" && cur === "Appointment Scheduled",
        makePayload: (_vals, me) => {
          const due = moment().add(1, "day").hour(10).minute(0).second(0).format("YYYY-MM-DD HH:mm:ss");
          return { description: "Next-Day Feedback call", due, priority: "Medium", assignees: me ? [me] : [] };
        },
      },
      "Treatment Completed": {
        showDialog: false,
        shouldTrigger: ({ prev, cur }) => prev !== "Treatment Completed" && cur === "Treatment Completed",
        makePayload: (_vals, me) => {
          const due = moment().add(5, "month").hour(10).minute(0).second(0).format("YYYY-MM-DD HH:mm:ss");
          return { description: "Recall: schedule prophylaxis", due, priority: "Medium", assignees: me ? [me] : [] };
        },
      },
    },
    status_patients: {
      "Stage Checked": {
        showDialog: true,
        title: __("Schedule control X-ray"),
        baseFields: ["assignees", "assign_me", "priority"],
        extraFields: () => ([
          { fieldtype: "Section Break", label: __("This rule (control)") },
          { fieldtype: "Select", fieldname: "treatment_type", label: __("Treatment Type"), reqd: 1,
            options: "Standard Implant\nSinus Lift\nAugmentation\nOther", default: "Standard Implant" },
        ]),
        shouldTrigger: ({ prev, cur }) => prev !== "Stage Checked" && cur === "Stage Checked",
        makePayload: (vals, me) => {
          const tt = (vals.treatment_type || "Standard Implant").toLowerCase();
          const months = (tt.includes("sinus") || tt.includes("augment")) ? 6 : 3;
          const due = moment().add(months, "month").hour(10).minute(0).second(0).format("YYYY-MM-DD HH:mm:ss");
          let a = Array.isArray(vals.assignees) ? vals.assignees.slice() : (vals.assignees || []);
          if (vals.assign_me && me && !a.includes(me)) a.push(me);
          const note = ` (type: ${vals.treatment_type}, +${months}m)`;
          return { description: "Schedule control X-ray" + note, due, priority: vals.priority || "High", assignees: a };
        },
      },
      "Treatment Completed": {
        showDialog: false,
        shouldTrigger: ({ prev, cur }) => prev !== "Treatment Completed" && cur === "Treatment Completed",
        makePayload: (_vals, me) => {
          const due = moment().add(5, "month").hour(10).minute(0).second(0).format("YYYY-MM-DD HH:mm:ss");
          return { description: "Recall: schedule prophylaxis", due, priority: "Medium", assignees: me ? [me] : [] };
        },
      },
    },
  };

  const KANBAN_RULES = {
    "Call Later": {
      showDialog: true,
      title: __("Call Later"),
      baseFields: ["due", "assignees", "assign_me", "priority"],
      extraFields: () => [],
      makePayload: (vals, me) => {
        let a = Array.isArray(vals.assignees) ? vals.assignees.slice() : (vals.assignees || []);
        if (vals.assign_me && me && !a.includes(me)) a.push(me);
        return { description: "Manual Callback", due: vals.due, priority: vals.priority || "Medium", assignees: a };
      },
    },
    "Appointment Scheduled": {
      showDialog: false,
      makePayload: (_vals, me) => {
        const due = moment().add(1, "day").hour(10).minute(0).second(0).format("YYYY-MM-DD HH:mm:ss");
        return { description: "Next-Day Feedback call", due, priority: "Medium", assignees: me ? [me] : [] };
      },
    },
    "Treatment Completed": {
      showDialog: false,
      makePayload: (_vals, me) => {
        const due = moment().add(5, "month").hour(10).minute(0).second(0).format("YYYY-MM-DD HH:mm:ss");
        return { description: "Recall: schedule prophylaxis", due, priority: "Medium", assignees: me ? [me] : [] };
      },
    },
    "Stage Checked": {
      showDialog: true,
      title: __("Schedule control X-ray"),
      baseFields: ["assignees", "assign_me", "priority"],
      extraFields: FORM_RULES.status_patients["Stage Checked"].extraFields,
      makePayload: FORM_RULES.status_patients["Stage Checked"].makePayload,
    },
  };

  const UI = {
    statusTab: "Open",
    page: 1,
    total: 0,
    frm: null,
    baseline: { status_leads: null, status_deals: null, status_patients: null },
    pendingRule: null,
    saveGuard: false,
    kanbanSeen: new Set(),
    openCount: 0,
  };

  // ========== helpers ==========
  function fmtUserDT(dtStr) {
    if (!dtStr) return "";
    try { return moment(frappe.datetime.convert_to_user_tz(dtStr)).format("YYYY-MM-DD HH:mm"); }
    catch { return String(dtStr); }
  }
  function fmtUserD(dStr) {
    if (!dStr) return "";
    try { return moment(dStr).format("YYYY-MM-DD"); }
    catch { return String(dStr); }
  }

  // просрочено по «назначенной дате» (target) — только для Open
  function isOverdue(t) {
    if ((t.status || "Open") !== "Open") return false;
    const now = moment();
    if (t.custom_target_datetime) {
      return moment(t.custom_target_datetime).isBefore(now);
    }
    if (t.date) {
      // конец дня локально
      const endOfDay = moment(t.date).endOf("day");
      return endOfDay.isBefore(now);
    }
    return false;
  }

  // ===== Dashboard section (ядровой коллапс) =====
  function getOrCreateDashSection(frm, id, title) {
    const host = frm?.page?.wrapper?.[0];
    if (!host) return null;
    const dash = host.querySelector(".form-dashboard");
    if (!dash) return null;

    let sec = dash.querySelector(`#${id}`);
    if (!sec) {
      const row = document.createElement("div");
      row.className = "row form-dashboard-section ec-tasks-section";
      row.id = id;

      const head = document.createElement("div");
      head.className = "section-head collapsible";
      head.tabIndex = 0;
      head.innerHTML = `
        <span class="t">${frappe.utils.escape_html(title)}</span>
        <span class="ml-2 ec-red-dot" hidden></span>
        <span class="ml-2 collapse-indicator mb-1" tabindex="0">
          <svg class="es-icon es-line icon-sm" aria-hidden="true">
            <use class="mb-1" href="#es-line-down"></use>
          </svg>
        </span>
      `;
      const body = document.createElement("div");
      body.className = "section-body";

      row.appendChild(head);
      row.appendChild(body);

      if (dash.firstChild) dash.insertBefore(row, dash.firstChild.nextSibling);
      else dash.appendChild(row);

      const ls = localStorage.getItem(LS_KEY_COLLAPSE);
      const collapsed = ls === null ? true : (ls === "1");
      setCollapsed(row, collapsed);

      head.addEventListener("click", (ev) => {
        if (ev.target.closest("button, a")) return;
        toggleCollapsed(row);
      });
      head.querySelector(".collapse-indicator")?.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleCollapsed(row); }
      });

      sec = row;
    }
    return sec;
  }
  function sectionBody(sec) { return sec?.querySelector(".section-body") || null; }
  function sectionHead(sec) { return sec?.querySelector(".section-head") || null; }

  function setCollapsed(sec, collapsed) {
    const head = sectionHead(sec);
    const body = sectionBody(sec);
    if (head) head.classList.toggle("collapsed", !!collapsed);
    if (body) body.classList.toggle("hide", !!collapsed);
    sec.classList.toggle("is-collapsed", !!collapsed);
    localStorage.setItem(LS_KEY_COLLAPSE, collapsed ? "1" : "0");
  }
  function toggleCollapsed(sec) {
    const head = sectionHead(sec);
    const collapsed = !(head?.classList.contains("collapsed"));
    setCollapsed(sec, collapsed);
  }
  function setRedDot(frm, on) {
    const sec = getOrCreateDashSection(frm, SEC_ID, SEC_TITLE);
    const dot = sec?.querySelector(".ec-red-dot");
    if (!dot) return;
    dot.hidden = !on;
  }

  // ===== список задач =====
  function priorityClass(p){ if (p==="High") return "-p-high"; if (p==="Low") return "-p-low"; return "-p-med"; }
  function taskRow(t) {
    const reminder_dt = t.due_datetime || t.custom_due_datetime;
    const reminder = reminder_dt ? fmtUserDT(reminder_dt) : null;
    const target_dt = t.custom_target_datetime || null;
    const target = target_dt ? fmtUserDT(target_dt) : (t.date ? fmtUserD(t.date) : null);

    const who = t.allocated_to || t.owner || "";
    const st  = t.status || "Open";
    const cls = st === "Open" ? "" : " -muted";
    const pcls = priorityClass(t.priority || "Medium");
    const overdue = isOverdue(t);

    const chips = [];
    chips.push(`<span class="chip">${frappe.utils.escape_html(st)}</span>`);
    if (t.priority) chips.push(`<span class="chip ${pcls}">${frappe.utils.escape_html(t.priority)}</span>`);
    if (who) chips.push(`<span class="chip -ghost">@${frappe.utils.escape_html(who)}</span>`);
    if (target) chips.push(`<span class="chip -ghost chip-target${overdue?' -overdue':''}" title="Target at">🗓 ${frappe.utils.escape_html(target)}</span>`);
    if (reminder) chips.push(`<span class="chip -ghost" title="Reminder at">🔔 ${frappe.utils.escape_html(reminder)}</span>`);
    if (t.assigned_by) chips.push(`<span class="chip -ghost">by ${frappe.utils.escape_html(t.assigned_by)}</span>`);
    if (t.creation) chips.push(`<span class="chip -ghost" title="Created">${frappe.utils.escape_html(fmtUserDT(t.creation))}</span>`);

    return `
      <div class="ec-task${cls}">
        <div class="l">
          <div class="title">${frappe.utils.escape_html(t.description || t.name)}</div>
          <div class="meta">${chips.join(" ")}</div>
        </div>
        <div class="r">
          <button class="btn btn-xs btn-default" onclick="frappe.set_route('Form','ToDo','${frappe.utils.escape_html(t.name)}')">Open</button>
          ${st==="Open" ? `
            <button class="btn btn-xs btn-success ml-1" data-act="done" data-name="${frappe.utils.escape_html(t.name)}">Complete</button>
            <button class="btn btn-xs btn-default ml-1" data-act="cancel" data-name="${frappe.utils.escape_html(t.name)}">Cancel</button>
          ` : ``}
        </div>
      </div>`;
  }

  function tabsHtml(active) {
    const mk = (v,t)=>`<li class="nav-item"><a class="nav-link${active===v?' active':''}" href="#" data-act="tab" data-val="${v}">${t}</a></li>`;
    return `<ul class="nav nav-tabs ec-tabs">${mk("Open","Open")}${mk("Closed","Closed")}${mk("All","All")}</ul>`;
  }

  function ensureTasksContainer(frm) {
    UI.frm = frm;
    const sec = getOrCreateDashSection(frm, SEC_ID, SEC_TITLE);
    const body = sectionBody(sec);
    if (!body) return null;

    let wrap = body.querySelector(".ec-tasks-wrap");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.className = "ec-tasks-wrap";
      wrap.innerHTML = `
        <div class="ec-tabs-row">
          ${tabsHtml(UI.statusTab)}
          <div class="actions">
            <button class="btn btn-xs btn-primary" data-act="add" type="button">Add Task</button>
            <button class="btn btn-xs btn-default ml-2" data-act="open-list" type="button">Open All</button>
          </div>
        </div>
        <div class="ec-tasks-hint">
          <div class="h-title">Auto-tasks for this case</div>
          <ul class="h-list">
            <li><b>Next-Day Feedback</b> — on “Appointment Scheduled / Treatment Completed”.</li>
            <li><b>Control X-ray</b> — on “Stage Checked”.</li>
            <li><b>Manual Callback</b> — optional reminder.</li>
          </ul>
        </div>
        <div class="ec-tasks-list"></div>
        <div class="ec-tasks-pager">
          <div class="spacer"></div>
          <span class="info"></span>
          <div class="nav">
            <button class="btn btn-xs btn-default" data-act="prev" type="button">← Prev</button>
            <button class="btn btn-xs btn-default ml-1" data-act="next" type="button">Next →</button>
          </div>
        </div>
      `;
      body.appendChild(wrap);

      wrap.addEventListener("click", (e) => {
        const a = e.target.closest("[data-act]");
        if (!a) return;
        e.preventDefault();
        const act = a.getAttribute("data-act");

        if (act === "tab") {
          UI.statusTab = a.getAttribute("data-val") || "Open";
          UI.page = 1;
          const row = wrap.querySelector(".ec-tabs-row");
          const actions = row.querySelector(".actions").outerHTML;
          row.innerHTML = tabsHtml(UI.statusTab) + actions;
          return loadTasks(frm);
        }

        if (act === "add") return openCreateDialog(frm);
        if (act === "open-list") return frappe.set_route("List","ToDo",{ reference_type: DOCTYPE, reference_name: frm.doc.name });

        if (act === "done" || act === "cancel") {
          const name = a.getAttribute("data-name");
          updateTaskStatus(name, act === "done" ? "Closed" : "Cancelled").then(() => loadTasks(frm));
        }

        if (act === "prev") { if (UI.page > 1) { UI.page -= 1; loadTasks(frm); } }
        if (act === "next") {
          const totalPages = Math.max(1, Math.ceil(UI.total / PAGE_LEN));
          if (UI.page < totalPages) { UI.page += 1; loadTasks(frm); }
        }
      });
    }
    return wrap.querySelector(".ec-tasks-list");
  }

  function updatePagerVisibility(container){
    const pager = container.parentElement.querySelector(".ec-tasks-pager");
    if (!pager) return;
    const totalPages = Math.max(1, Math.ceil(UI.total / PAGE_LEN));
    pager.querySelector(".nav").style.display = (totalPages <= 1) ? "none" : "inline-flex";
    const prevBtn = pager.querySelector('[data-act="prev"]');
    const nextBtn = pager.querySelector('[data-act="next"]');
    const info = pager.querySelector(".info");
    if (prevBtn) prevBtn.disabled = (UI.page <= 1);
    if (nextBtn) nextBtn.disabled = (UI.page >= totalPages);
    if (info) info.textContent = `Page ${UI.page} / ${totalPages} • ${UI.total} total • ${PAGE_LEN} per page`;
  }

  async function loadTasks(frm) {
    const listEl = ensureTasksContainer(frm);
    if (!listEl) return;
    listEl.innerHTML = `<div class="text-muted small">Loading…</div>`;
    try {
      const status = UI.statusTab === "All" ? null : UI.statusTab;
      const start = (UI.page - 1) * PAGE_LEN;
      const { message } = await frappe.call({
        method: "dantist_app.api.tasks.handlers.ec_tasks_for_case",
        args: { name: frm.doc.name, status, limit_start: start, limit_page_length: PAGE_LEN }
      });
      let rows = (message && message.rows) || [];
      UI.total = (message && message.total) || rows.length;

      // *** newest first: backend сортирует по возрастанию — просто выводим в обратном порядке на странице
      rows = rows.slice().reverse();

      // красная точка — по «open на странице»
      UI.openCount = rows.filter(r => (r.status || "Open") === "Open").length;
      setRedDot(frm, UI.openCount > 0);

      listEl.innerHTML = rows.length ? rows.map(taskRow).join("") : `<div class="text-muted small">No tasks.</div>`;
      updatePagerVisibility(listEl);
    } catch (e) {
      console.error(e);
      listEl.innerHTML = `<div class="text-danger small">Failed to load tasks.</div>`;
    }
  }

  // ===== Диалоги (Target / Reminder) =====
  function buildFields(baseKeys, extra) {
    const me = frappe.session.user || "";
    const fields = [
      { fieldtype:"Section Break", label: __("Schedule") },
      { fieldtype:"Datetime", fieldname:"target_at", label: __("Target at"), reqd:0,
        description: __("Optional; saved into custom_target_datetime") },
      { fieldtype:"Check", fieldname:"send_reminder", label: __("Send reminder"), default: 0 },
      { fieldtype:"Datetime", fieldname:"reminder_at", label: __("Reminder at"), reqd:0,
        depends_on: "eval:doc.send_reminder==1" },
      { fieldtype:"Section Break", label: __("Assignment") },
    ];

    if (baseKeys?.includes("assignees")) fields.push({
      fieldtype:"MultiSelectList", fieldname:"assignees", label:__("Assign To (multiple)"), options:"User",
      get_data: (txt)=> frappe.db.get_link_options("User", txt || "")
    });
    if (baseKeys?.includes("assign_me")) fields.push({ fieldtype:"Check", fieldname:"assign_me", label:__(`Assign to me (${me})`), default:1 });
    if (baseKeys?.includes("priority")) fields.push({ fieldtype:"Select", fieldname:"priority", label:__("Priority"), options:"Low\nMedium\nHigh", default:"Medium" });

    if (Array.isArray(extra) && extra.length) fields.push(...extra);
    return fields;
  }

  function wireReminderValidation(dlg) {
    const fSend = dlg.get_field("send_reminder");
    const fRem  = dlg.get_field("reminder_at");
    const apply = () => {
      const on = !!dlg.get_value("send_reminder");
      fRem.df.reqd = on ? 1 : 0;
      fRem.refresh();
    };
    fSend.$input && fSend.$input.on("change", apply);
    setTimeout(apply, 0);

    return () => {
      const on = !!dlg.get_value("send_reminder");
      const v  = dlg.get_value("reminder_at");
      if (on && !v) {
        frappe.msgprint({ title: __("Missing value"), message: __("Please set Reminder at or uncheck Send reminder."), indicator: "red" });
        return false;
      }
      return true;
    };
  }

  async function createTask(caseName, payload, source) {
    return frappe.call({
      method: "dantist_app.api.tasks.handlers.create_task_for_case",
      args: { name: caseName, values: payload, source: source || "auto" }
    });
  }

  function openCreateDialog(frm) {
    const me = frappe.session.user || "";
    const d = new frappe.ui.Dialog({
      title: "New Task",
      fields: buildFields(["assignees","assign_me","priority"], [] )
        .concat([{ fieldtype:"Small Text", fieldname:"description", label:"Description", reqd:1, insert_after:"reminder_at" }])
    });
    const guard = wireReminderValidation(d);

    d.set_primary_action("Create", async () => {
      if (!guard()) return;
      const v = d.get_values();
      try {
        let a = Array.isArray(v.assignees) ? v.assignees.slice() : (v.assignees || []);
        if (v.assign_me && me && !a.includes(me)) a.push(me);

        const payload = { description: v.description, priority: v.priority };
        if (v.target_at) payload.custom_target_datetime = v.target_at;

        if (v.send_reminder) {
          payload.send_reminder = 1;
          if (v.reminder_at) payload.due = v.reminder_at; // уйдет в due_datetime/custom_due_datetime на бэке
        } else {
          payload.send_reminder = 0;
        }
        if (a.length) payload.assignees = a;

        await createTask(frm.doc.name, payload, "manual");
        d.hide();
        frappe.show_alert({ message:"Task created", indicator:"green" });
        UI.page = 1; loadTasks(frm);
      } catch (e) {
        console.error(e);
        frappe.msgprint({ message:"Failed to create task", indicator:"red" });
      }
    });

    d.$wrapper.addClass("ec-task-dialog");
    d.show();
  }

  async function updateTaskStatus(name, status) {
    await frappe.call({ method: "dantist_app.api.tasks.handlers.update_task_status", args: { name, status } });
    frappe.show_alert({ message: status==="Closed"?"Completed":"Cancelled", indicator:"green" });
  }

  // ===== перехват Save =====
  function patchFormSave(frm){
    if (frm.__ecSavePatched) return;
    frm.__ecSavePatched = true;

    const origSave = frm.save.bind(frm);
    frm.save = function(...args){
      if (!UI.pendingRule || UI.saveGuard) return origSave(...args);

      const { rule } = UI.pendingRule;
      const me = frappe.session.user || "";

      if (!rule.showDialog) {
        UI.saveGuard = true;
        Promise.resolve()
          .then(() => createTask(frm.doc.name, rule.makePayload({}, me, frm), "auto"))
          .then(() => frappe.show_alert({ message: __("Auto task created"), indicator: "green" }))
          .catch(e => console.warn("[EC Form Save] auto create failed", e))
          .finally(() => { UI.pendingRule = null; UI.saveGuard = false; origSave(...args); });
        return Promise.resolve();
      }

      const extraFields = (typeof rule.extraFields === "function") ? rule.extraFields(frm) : (rule.extraFields || []);
      const d = new frappe.ui.Dialog({ title: rule.title, fields: buildFields(rule.baseFields || ["due","assignees","assign_me","priority"], extraFields) });
      const guard = wireReminderValidation(d);

      d.set_primary_action(__("OK"), (vals) => {
        if (!guard()) return;
        UI.saveGuard = true;

        const compat = Object.assign({}, vals, { due: vals.send_reminder ? vals.reminder_at : null });
        const draft = rule.makePayload(compat, me, frm) || {};
        const payload = Object.assign({}, draft);

        if (vals.target_at) payload.custom_target_datetime = vals.target_at;

        if (vals.send_reminder) {
          payload.send_reminder = 1;
          if (!payload.due && vals.reminder_at) payload.due = vals.reminder_at;
        } else {
          payload.send_reminder = 0;
          if ("due" in payload) delete payload.due;
        }

        Promise.resolve()
          .then(() => createTask(frm.doc.name, payload, "manual"))
          .then(() => frappe.show_alert({ message: __("Task created"), indicator:"green" }))
          .catch(e => console.warn("[EC Form Save] create failed", e))
          .finally(() => { UI.pendingRule = null; UI.saveGuard = false; origSave(...args); });

        d.hide();
      });

      d.$wrapper.on("hidden.bs.modal", () => { if (UI.saveGuard) return; UI.pendingRule = null; origSave(...args); });
      d.$wrapper.addClass("ec-task-dialog");
      d.show();

      return Promise.resolve();
    };
  }

  // ===== Form bindings =====
  frappe.ui.form.on(DOCTYPE, {
    refresh(frm){
      UI.frm = frm;
      UI.baseline.status_leads    = frm.doc.status_leads || null;
      UI.baseline.status_deals    = frm.doc.status_deals || null;
      UI.baseline.status_patients = frm.doc.status_patients || null;
      UI.pendingRule = null; UI.saveGuard = false;

      patchFormSave(frm);
      loadTasks(frm);
    },
    after_save(frm){
      loadTasks(frm);
      UI.baseline.status_leads    = frm.doc.status_leads || null;
      UI.baseline.status_deals    = frm.doc.status_deals || null;
      UI.baseline.status_patients = frm.doc.status_patients || null;
      UI.pendingRule = null; UI.saveGuard = false;
    },

    status_leads(frm){
      const prev = UI.baseline.status_leads, cur = frm.doc.status_leads || null;
      const rule = FORM_RULES.status_leads["Call Later"];
      const need = rule && rule.shouldTrigger({ prev, cur, frm });
      UI.pendingRule = need ? { df:"status_leads", rule } : null;
      if (need) frappe.show_alert({ message: __("You can set Target and optional Reminder on Save"), indicator:"blue" });
    },
    status_deals(frm){
      const prev = UI.baseline.status_deals, cur = frm.doc.status_deals || null;
      const r1 = FORM_RULES.status_deals["Appointment Scheduled"];
      const r2 = FORM_RULES.status_deals["Treatment Completed"];
      const rule = (cur==="Appointment Scheduled") ? r1 : (cur==="Treatment Completed" ? r2 : null);
      const need = rule && rule.shouldTrigger({ prev, cur, frm });
      UI.pendingRule = need ? { df:"status_deals", rule } : null;
      if (need && !rule.showDialog) frappe.show_alert({ message: __("An auto task will be created"), indicator:"blue" });
    },
    status_patients(frm){
      const prev = UI.baseline.status_patients, cur = frm.doc.status_patients || null;
      const r1 = FORM_RULES.status_patients["Stage Checked"];
      const r2 = FORM_RULES.status_patients["Treatment Completed"];
      const rule = (cur==="Stage Checked") ? r1 : (cur==="Treatment Completed" ? r2 : null);
      const need = rule && rule.shouldTrigger({ prev, cur, frm });
      UI.pendingRule = need ? { df:"status_patients", rule } : null;
      if (!need) return;
      if (rule.showDialog) {
        frappe.show_alert({ message: __("You can set Target and optional Reminder on Save"), indicator:"blue" });
      } else {
        frappe.show_alert({ message: __("An auto task will be created"), indicator:"blue" });
      }
    },
  });

  // ===== Kanban hook =====
  (function patchKanban(){
    if (frappe.__ec_call_patched_v419) return;
    const orig = frappe.call;

    frappe.call = function(opts){
      const isObj  = opts && typeof opts === "object";
      const method = isObj ? (opts.method || "") : "";
      const args   = isObj ? (opts.args   || {}) : {};

      const isKanban =
        method === "frappe.desk.doctype.kanban_board.kanban_board.update_order_for_single_card" ||
        method === "frappe.desk.doctype.kanban_board.kanban_board.update_order";

      if (!isKanban) return orig.apply(this, arguments);

      const p = orig.apply(this, arguments);
      Promise.resolve(p).then(() => {
        const toCol = (args.to_colname || args.to_column || args.column || args.column_name || "").toString().trim();
        const card  = args.docname || args.card || args.name || (Array.isArray(args.cards) ? args.cards[0] : null);
        const key   = card && `${card}::${toCol}`;
        const rule  = KANBAN_RULES[toCol];

        if (!rule || !card || !toCol) return;
        if (key && UI.kanbanSeen.has(key)) return;
        if (key) UI.kanbanSeen.add(key), setTimeout(()=> UI.kanbanSeen.delete(key), 3000);

        const me = frappe.session.user || "";

        if (!rule.showDialog) {
          createTask(card, rule.makePayload({}, me, { toCol, card }), "auto")
            .then(()=> frappe.show_alert({ message: __("Auto task created"), indicator:"green" }))
            .catch(e => console.warn("[EC Kanban] auto create failed", e));
          return;
        }

        const d = new frappe.ui.Dialog({
          title: rule.title,
          fields: buildFields(rule.baseFields || ["due","assignees","assign_me","priority"], (typeof rule.extraFields === "function") ? rule.extraFields({ toCol, card }) : rule.extraFields)
        });
        const guard = wireReminderValidation(d);
        d.set_primary_action(__("OK"), () => {
          if (!guard()) return;
          const vals = d.get_values();
          const compat = Object.assign({}, vals, { due: vals.send_reminder ? vals.reminder_at : null });
          const draft = rule.makePayload(compat, me, { toCol, card }) || {};
          const payload = Object.assign({}, draft);
          if (vals.target_at) payload.custom_target_datetime = vals.target_at;
          if (vals.send_reminder) {
            payload.send_reminder = 1;
            if (!payload.due && vals.reminder_at) payload.due = vals.reminder_at;
          } else {
            payload.send_reminder = 0;
            if ("due" in payload) delete payload.due;
          }
          createTask(card, payload, "manual")
            .then(()=> frappe.show_alert({ message: __("Task created"), indicator:"green" }))
            .catch(e => console.warn("[EC Kanban] create failed", e));
          d.hide();
        });
        d.$wrapper.addClass("ec-task-dialog");
        d.show();
      }).catch(()=>{});
      return p;
    };

    frappe.__ec_call_patched_v419 = true;
  })();

  // ===== styles =====
  const css = document.createElement("style");
  css.textContent = `
  .ec-tasks-section .section-head{
    display:flex;align-items:center;gap:6px;
    font-weight:600;padding:8px 12px;border-bottom:1px solid var(--border-color,#e5e7eb);
    cursor:pointer;
  }
  .ec-tasks-section .section-head .t{flex:0 1 auto}
  .ec-tasks-section .collapse-indicator .es-icon{transition: transform .15s ease;}
  .ec-tasks-section .section-head.collapsed .collapse-indicator .es-icon{transform: rotate(-90deg);}
  .ec-tasks-section .ec-red-dot{width:8px;height:8px;border-radius:999px;background:#ef4444;display:inline-block}
  .ec-tasks-section .section-body{padding:12px}
  .ec-tasks-section .section-body.hide{display:none!important}

  .ec-tabs-row{ display:flex; align-items:center; justify-content:space-between; gap:10px; }
  .ec-tabs .nav-link{ padding:6px 10px; }
  .ml-1{margin-left:6px}.ml-2{margin-left:8px}
  .ec-tasks-hint{ margin:8px 0 10px; padding:8px 10px; border-left:3px solid #e5e7eb; background:#fafafa; border-radius:6px; font-size:12px; color:#4b5563; }
  .ec-tasks-hint .h-title{font-weight:600; margin-bottom:4px; color:#374151}
  .ec-tasks-hint .h-list{margin:0; padding-left:18px}
  .ec-tasks-hint .h-list li{margin:1px 0}
  .ec-task{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;padding:10px 0;border-top:1px solid #eef2f7}
  .ec-task:first-child{border-top:none}
  .ec-task.-muted{opacity:.78}
  .ec-task .title{font-weight:600;font-size:13px}
  .ec-task .meta{display:flex;gap:6px;flex-wrap:wrap;margin-top:3px;color:#6b7280;font-size:11px}
  .ec-task .chip{border:1px solid #e5e7eb;border-radius:999px;padding:2px 6px;background:#f3f4f6}
  .ec-task .chip.-ghost{background:#f8fafc}
  .ec-task .chip.-p-high{ background:#fee2e2; border-color:#fecaca; }
  .ec-task .chip.-p-med{  background:#e5f0ff; border-color:#dbeafe; }
  .ec-task .chip.-p-low{  background:#e8f5e9; border-color:#d7f0da; }

  /* мягкая подсветка просроченной целевой даты */
  .ec-task .chip-target.-overdue{
    background: #fee2e2;       /* розоватая */
    border-color: #fecaca;
    color: #991b1b;            /* тёмно-красный текст */
  }

  .ec-task-dialog .modal-body{padding:14px 16px}
  .ec-task-dialog .frappe-control{margin-bottom:8px}
  .ec-task-dialog .control-label{margin-bottom:4px}
  .ec-tasks-pager{ display:flex; align-items:center; gap:8px; justify-content:space-between; margin-top:8px; }
  .ec-tasks-pager .info{ font-size:11px; color:#6b7280; }
  `;
  document.head.appendChild(css);
})();