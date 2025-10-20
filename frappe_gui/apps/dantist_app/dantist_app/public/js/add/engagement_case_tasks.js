// Engagement Case — Tasks UI (ToDo + Kanban “Call Later”) — v4.7
(function () {
  const DOCTYPE = "Engagement Case";
  const PAGE_LEN = 10;

  const UI = { statusTab: "Open", page: 1, total: 0, frm: null };

  function domOf(w) {
    if (!w) return null;
    if (w instanceof HTMLElement) return w;
    if (w[0] instanceof HTMLElement) return w[0];
    if (w.$wrapper && w.$wrapper[0]) return w.$wrapper[0];
    if (w.wrapper && w.wrapper[0]) return w.wrapper[0];
    if (w.wrapper instanceof HTMLElement) return w.wrapper;
    return null;
  }

  // ==== Дата/время: корректное отображение в часовой зоне пользователя ====
  function fmtUserDT(dtStr) {
    if (!dtStr) return "-";
    try {
      const userTzISO = frappe.datetime.convert_to_user_tz(dtStr); // -> ISO в зоне пользователя
      // формат: YYYY-MM-DD HH:mm (понятно и явно)
      return moment(userTzISO).format("YYYY-MM-DD HH:mm");
    } catch (e) {
      return String(dtStr);
    }
  }

  function openDueDialog(label, onOk, onCancel) {
    const d = new frappe.ui.Dialog({
      title: label || "Set follow-up time",
      fields: [{ fieldtype: "Datetime", fieldname: "due", label: "Due At", reqd: 1 }],
      primary_action_label: "OK",
      primary_action(values) { onOk && onOk(values.due); d.hide(); }
    });
    d.$wrapper.addClass("ec-task-dialog");
    d.on("hide", () => { if (d.get_value("due") == null && onCancel) onCancel(); });
    d.show();
  }

  function tabsHtml(active) {
    const mk = (v,t)=>`<li class="nav-item"><a class="nav-link${active===v?' active':''}" href="#" data-act="tab" data-val="${v}">${t}</a></li>`;
    return `<ul class="nav nav-tabs ec-tabs">${mk("Open","Open")}${mk("Closed","Closed")}${mk("All","All")}</ul>`;
  }

  function ensureTasksContainer(frm) {
    UI.frm = frm;
    const anchorField = frm.fields_dict["notes_section"] || frm.fields_dict["internal_notes"];
    const anchorEl = domOf(anchorField) || domOf(frm.wrapper);
    if (!anchorEl) return null;

    const column = anchorEl.closest(".form-section")?.querySelector(".section-body .form-column") || anchorEl.parentNode;

    const existed = column.querySelectorAll(".ec-tasks-wrap");
    for (let i = 1; i < existed.length; i++) existed[i].remove();

    let wrap = column.querySelector(".ec-tasks-wrap");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.className = "ec-tasks-wrap";
      wrap.innerHTML = `
        <div class="ec-tasks-head">
          <div class="t">Tasks</div>
        </div>

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
            <li><b>Next-Day Feedback</b> — on “Appointment Scheduled / Stage Appointment Scheduled”.</li>
            <li><b>Recall</b> — on “Recommended Recall Added / Treatment Completed” (~5 months).</li>
            <li><b>Control X-ray</b> — on “Stage Checked” (in 3–6 months by treatment type).</li>
            <li><b>Manual Callback</b> — on “Call Later” (due time required; alert −2h).</li>
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
      column.appendChild(wrap);

      wrap.addEventListener("click", (e) => {
        const a = e.target.closest("[data-act]");
        if (!a) return;
        e.preventDefault();
        const act = a.getAttribute("data-act");

        if (act === "tab") {
          UI.statusTab = a.getAttribute("data-val") || "Open";
          UI.page = 1;
          const row = wrap.querySelector(".ec-tabs-row");
          const actionsHtml = row.querySelector(".actions").outerHTML;
          row.innerHTML = tabsHtml(UI.statusTab) + actionsHtml;
          return loadTasks(frm);
        }

        if (act === "add") return openCreateDialog(frm);

        if (act === "open-list") {
          return frappe.set_route("List", "ToDo", { reference_type: DOCTYPE, reference_name: frm.doc.name });
        }

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

  function priorityClass(p) {
    if (p === "High") return "-p-high";
    if (p === "Low")  return "-p-low";
    return "-p-med";
  }

  function taskRow(t) {
    const due_dt = t.due_datetime || t.custom_due_datetime;
    const due = due_dt ? fmtUserDT(due_dt) :
                (t.date ? moment(t.date).format("YYYY-MM-DD") : "-");
    const who = t.allocated_to || t.owner || "";
    const st  = t.status || "Open";
    const cls = st === "Open" ? "" : " -muted";
    const pcls = priorityClass(t.priority || "Medium");
    return `
      <div class="ec-task${cls}">
        <div class="l">
          <div class="title">${frappe.utils.escape_html(t.description || t.name)}</div>
          <div class="meta">
            <span class="chip">${frappe.utils.escape_html(st)}</span>
            ${t.priority ? `<span class="chip ${pcls}">${frappe.utils.escape_html(t.priority)}</span>` : ""}
            ${who ? `<span class="chip -ghost">@${frappe.utils.escape_html(who)}</span>` : ""}
            ${due ? `<span class="chip -ghost">${frappe.utils.escape_html(due)}</span>` : ""}
            ${t.assigned_by ? `<span class="chip -ghost">by ${frappe.utils.escape_html(t.assigned_by)}</span>` : ""}
          </div>
        </div>
        <div class="r">
          <button class="btn btn-xs btn-default" onclick="frappe.set_route('Form','ToDo','${frappe.utils.escape_html(t.name)}')">Open</button>
          ${st === "Open"
            ? `<button class="btn btn-xs btn-success ml-1" data-act="done" data-name="${frappe.utils.escape_html(t.name)}">Complete</button>
               <button class="btn btn-xs btn-default ml-1" data-act="cancel" data-name="${frappe.utils.escape_html(t.name)}">Cancel</button>`
            : ``
          }
        </div>
      </div>`;
  }

  function updatePagerVisibility(container){
    const pager = container.parentElement.querySelector(".ec-tasks-pager");
    if (!pager) return;
    const totalPages = Math.max(1, Math.ceil(UI.total / PAGE_LEN));
    const prevBtn = pager.querySelector('[data-act="prev"]');
    const nextBtn = pager.querySelector('[data-act="next"]');
    const info = pager.querySelector(".info");

    pager.querySelector(".nav").style.display = (totalPages <= 1) ? "none" : "inline-flex";
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
      const rows = (message && message.rows) || [];
      UI.total = (message && message.total) || rows.length;

      listEl.innerHTML = rows.length ? rows.map(taskRow).join("") : `<div class="text-muted small">No tasks.</div>`;
      updatePagerVisibility(listEl);
    } catch (e) {
      console.error(e);
      listEl.innerHTML = `<div class="text-danger small">Failed to load tasks.</div>`;
    }
  }

  function openCreateDialog(frm) {
    const me = frappe.session.user || "";
    const d = new frappe.ui.Dialog({
      title: "New Task",
      fields: [
        { fieldtype:"Small Text", fieldname:"description", label:"Description", reqd:1 },
        { fieldtype:"Datetime", fieldname:"due", label:"Due At", reqd:1 },

        // ВАЖНО: без filters=null → иначе /search_link падает
        { fieldtype:"MultiSelectList", fieldname:"assignees", label:"Assign To (multiple)", options:"User",
          get_data: function(txt) {
            return frappe.db.get_link_options("User", txt || "");
          }
        },

        { fieldtype:"Check", fieldname:"assign_me", label:`Assign to me (${me})`, default:1 },
        { fieldtype:"Select", fieldname:"priority", label:"Priority", options:"Low\nMedium\nHigh", default:"Medium" },
      ],
      primary_action_label: "Create",
      primary_action: async (v) => {
        try {
          let assignees = Array.isArray(v.assignees) ? v.assignees.slice() : (v.assignees || []);
          if (v.assign_me && me && !assignees.includes(me)) assignees.push(me);

          const payload = { description: v.description, due: v.due, priority: v.priority };
          if (assignees.length) payload.assignees = assignees;

          await frappe.call({
            method: "dantist_app.api.tasks.handlers.create_task_for_case",
            args: { name: frm.doc.name, values: payload, source: "manual" }
          });
          d.hide();
          frappe.show_alert({ message:"Task created", indicator:"green" });
          UI.page = 1;
          loadTasks(frm);
        } catch (e) {
          console.error(e);
          frappe.msgprint({ message:"Failed to create task", indicator:"red" });
        }
      }
    });
    d.$wrapper.addClass("ec-task-dialog");
    d.show();
  }

  async function updateTaskStatus(name, status) {
    await frappe.call({
      method: "dantist_app.api.tasks.handlers.update_task_status",
      args: { name, status }
    });
    frappe.show_alert({ message: status==="Closed"?"Completed":"Cancelled", indicator:"green" });
  }

  // Форма: Call Later → due + assignees=[me]
  frappe.ui.form.on(DOCTYPE, {
    refresh(frm){ loadTasks(frm); },
    after_save(frm){ loadTasks(frm); },

    status_leads(frm) {
      if (frm.doc.status_leads === "Call Later") {
        const me = frappe.session.user || "";
        openDueDialog(__("Call Later at"), async (due) => {
          await frappe.call({
            method: "dantist_app.api.tasks.handlers.create_task_for_case",
            args: { name: frm.doc.name,
                    values: { description:"Manual Callback", due, priority:"Medium", assignees: me ? [me] : [] },
                    source:"manual" }
          });
          frappe.show_alert({ message:"Callback scheduled", indicator:"green" });
          loadTasks(frm);
        });
      }
    }
  });

  // === KANBAN: диалог ПЕРЕД сохранением статуса ===
  (function patchKanbanBeforeSave(){
    const KV = frappe.views && frappe.views.KanbanView && frappe.views.KanbanView.prototype;
    if (!KV || KV.__ecPatched_v47) return;

    const origSingle = KV.update_order_for_single_card;

    KV.update_order_for_single_card = function(args) {
      // args: { card, from_colname, to_colname, old_index, new_index, ... }
      const to = String(args?.to_colname || "").trim();
      if ((this.board?.reference_doctype === DOCTYPE) && to === "Call Later" && args?.card) {
        const self = this;
        const me = frappe.session.user || "";
        openDueDialog(__("Call Later at"),
          async (due) => {
            try {
              // 1) создаём ToDo
              await frappe.call({
                method: "dantist_app.api.tasks.handlers.create_task_for_case",
                args: { name: args.card,
                        values: { description:"Manual Callback", due, priority:"Medium", assignees: me ? [me] : [] },
                        source: "manual" }
              });
              // 2) меняем статус карточки (теперь уже можно)
              origSingle.call(self, args);
              frappe.show_alert({ message:"Callback scheduled", indicator:"green" });
            } catch(e){ console.warn("[EC Kanban] create failed", e); }
          },
          () => {
            // Отмена → откатываем визуально
            try { self.refresh(); } catch(e){}
          }
        );
        // прерываем изменение статуса до подтверждения
        return Promise.resolve();
      }
      return origSingle.call(this, args);
    };

    // Пакетное перемещение — аналогичный подход
    const origBatch = KV.update_order;
    KV.update_order = function(args) {
      const to = String(args?.to_column || args?.column || args?.column_name || "").trim();
      if ((this.board?.reference_doctype === DOCTYPE) && to === "Call Later" && Array.isArray(args?.cards) && args.cards.length) {
        const self = this;
        const me = frappe.session.user || "";
        openDueDialog(__("Call Later at"),
          async (due) => {
            try {
              await Promise.all(args.cards.map(n => frappe.call({
                method: "dantist_app.api.tasks.handlers.create_task_for_case",
                args: { name: n, values: { description:"Manual Callback", due, priority:"Medium", assignees: me ? [me] : [] }, source:"manual" }
              })));
              origBatch.call(self, args);
              frappe.show_alert({ message:"Callback scheduled", indicator:"green" });
            } catch(e){ console.warn("[EC Kanban] batch create failed", e); }
          },
          () => { try { self.refresh(); } catch(e){} }
        );
        return Promise.resolve();
      }
      return origBatch.call(this, args);
    };

    KV.__ecPatched_v47 = true;
    console.log("[EC Kanban] patched v4.7 (pre-save dialog)");
  })();

  // ==== Стили ====
  const css = document.createElement("style");
  css.textContent = `
  /* отделяем блок задач тонкой линией, как соседние секции */
  .form-section .section-body .form-column .ec-tasks-wrap{ padding:12px 14px 0 14px; border-top:1px solid #e5e7eb; }
  .ec-tasks-wrap{ margin:12px 0 0; }

  .ec-tasks-head{display:flex;align-items:center;justify-content:space-between;margin:6px 0 8px}
  .ec-tasks-head .t{font-weight:600}

  .ec-tabs-row{ display:flex; align-items:center; justify-content:space-between; gap:10px; }
  .ec-tabs-row .actions .btn + .btn{ margin-left:6px; }
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

  .ec-tasks-pager{ display:flex; align-items:center; gap:8px; justify-content:space-between; margin-top:8px; }
  .ec-tasks-pager .info{ font-size:11px; color:#6b7280; }
  `;
  document.head.appendChild(css);
})();