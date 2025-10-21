// Engagement Case — Form UX (stacked pipelines, dynamic steps, safe scoping)
// - Пайплайны по одной доске в строку, шаги тянутся из df.options
// - Скрываем title-indicator ТОЛЬКО на Engagement Case
// - Linked Cases оставлены «как было»; ✎ надёжно открывает строку
// - FIX: убран crm_status из server-side get_list (ломал превью)

(function () {
  const DOCTYPE = "Engagement Case";
  const esc = frappe.utils.escape_html;

  // --- Boards meta (динамические шаги берём из options) ---
  const BOARDS = [
    { name: "CRM Board",                  flag: "show_board_crm",      fields: ["status_crm_board","crm_status"], color: "#2563eb" },
    { name: "Leads – Contact Center",     flag: "show_board_leads",    fields: ["status_leads"],                    color: "#16a34a" },
    { name: "Deals – Contact Center",     flag: "show_board_deals",    fields: ["status_deals"],                    color: "#ea580c" },
    { name: "Patients – Care Department", flag: "show_board_patients", fields: ["status_patients"],                 color: "#9333ea" },
  ];

  // ------- CSS (строго на этой форме) -------
  const CSS_ID = "ec-form-ux-css";
  function ensureCss() {
    if (document.getElementById(CSS_ID)) return;
    const s = document.createElement("style");
    s.id = CSS_ID;
    s.textContent = `
    .ec-suppress-title-indicator .page-head .indicator-pill { display:none !important; }

    .form-dashboard .ec-progress-section .section-head{
      font-weight:600;padding:8px 12px;border-bottom:1px solid var(--border-color,#e5e7eb);
    }
    .form-dashboard .ec-progress-section .section-body{ padding:12px; }
    .ec-pipes{ display:flex; flex-direction:column; gap:12px; }
    .ec-pipe{ border:1px solid var(--border-color,#e5e7eb); border-radius:10px; padding:10px; background:#fff; }
    .ec-pipe.-disabled{ opacity:.9; }
    .ec-pipe .head{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }
    .ec-pipe .dot{ width:10px; height:10px; border-radius:50%; flex:0 0 10px; }
    .ec-pipe .title{ font-weight:600; }

    .ec-steps{ display:flex; gap:6px; align-items:center; }
    .ec-step{
      position:relative; flex:1; height:10px; border-radius:999px; cursor:pointer;
      background:#eef2f7; outline:1px solid rgba(0,0,0,.03);
      transition: transform .12s ease, box-shadow .12s ease, opacity .12s ease;
    }
    .ec-step.-past{ opacity:.95 }
    .ec-step.-current{ transform: translateY(-1px); box-shadow: 0 1px 4px rgba(0,0,0,.08); }
    .ec-step.-future{ opacity:.6 }
    .ec-step.-disabled { background: transparent !important; border:1px dashed #d1d5db; outline:none; }
    .ec-step:hover{ box-shadow: 0 1px 6px rgba(0,0,0,.12); }

    .ec-names{ display:flex; gap:6px; margin-top:4px; font-size:11px; color:#6b7280; }
    .ec-name{ flex:1; text-align:center; white-space:nowrap; overflow:hidden; text-overflow:ellipsis }
    .ec-name.-current{ color:#111827; font-weight:600; }
    .ec-names.-disabled .ec-name{ color:#9ca3af; }

    /* Linked Cases — как в прежней версии */
    .ec-title-badges{display:flex;gap:6px;align-items:center;margin-left:8px}
    .crm-chip{font-size:10px;padding:2px 6px;border-radius:999px;border:1px solid #e5e7eb;background:transparent}
    .crm-chip.-ghost{background:#f8fafc}
    .crm-chip.-dashed{border-style:dashed;background:transparent}
    .crm-vsep{display:inline-block;width:0;border-left:1px dashed #d1d5db;margin:0 6px;align-self:stretch}
    .ec-linked-preview{margin-top:8px;border-top:1px solid #eef2f7;padding-top:6px}
    .ec-parents-preview{margin-top:8px;border-top:1px dashed #e5e7eb;padding-top:6px}
    .ec-linked-header{font-size:12px;color:#6b7280;margin-bottom:4px;display:flex;align-items:center;justify-content:space-between}
    .ec-card{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;padding:10px;border:1px solid #eef2f7;border-radius:10px;margin-top:8px;transition:background .15s}
    .ec-card:hover{background:#fafafa}
    .ec-card.-parent{border-style:dashed}
    .ec-left{display:flex;gap:10px;align-items:flex-start;min-width:0}
    .ec-avatar{width:28px;height:28px;border-radius:8px;background:#e5e7eb;flex:0 0 auto;overflow:hidden}
    .ec-avatar img{width:100%;height:100%;object-fit:cover;display:block}
    .ec-body{min-width:0}
    .ec-title{font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:flex;align-items:center;gap:6px}
    .ec-meta{color:#6b7280;font-size:11px;margin-top:2px;display:flex;gap:8px;flex-wrap:wrap}
    .ec-meta.-time .frappe-timestamp{opacity:.9}
    .ec-right{display:flex;align-items:center;gap:6px}
    .ec-open-kanban{margin-left:6px}
    .ec-grid-hidden .control-label,
    .ec-grid-hidden .grid-description,
    .ec-grid-hidden .grid-custom-buttons,
    .ec-grid-hidden .form-grid-container,
    .ec-grid-hidden .grid-heading-row,
    .ec-grid-hidden .grid-footer { display:none !important; }
    `;
    document.head.appendChild(s);
  }

  // ----------------- helpers -----------------
  function pageWrap(frm) { return frm?.page?.wrapper && frm.page.wrapper[0] || null; }
  function suppressTitleIndicator(frm, on) {
    const root = pageWrap(frm);
    if (!root) return;
    root.classList.toggle("ec-suppress-title-indicator", !!on);
  }
  function findFirstExistingField(frm, list) {
    for (const fn of list) if (frm.fields_dict[fn]) return fn;
    return null;
  }
  function getSelectOptions(frm, fieldname) {
    const df = frm.fields_dict[fieldname]?.df;
    if (!df) return [];
    return String(df.options || "").split("\n").map(s => s.trim()).filter(Boolean);
  }
  function getOrCreateDashSection(frm, id, title) {
    const host = frm?.page?.wrapper?.[0];
    if (!host) return null;
    const dash = host.querySelector(".form-dashboard");
    if (!dash) return null;
    let sec = dash.querySelector(`#${id}`);
    if (!sec) {
      const row = document.createElement("div");
      row.className = "row form-dashboard-section ec-progress-section";
      row.id = id;
      const head = document.createElement("div");
      head.className = "section-head collapsible";
      head.tabIndex = 0;
      head.textContent = title;
      const body = document.createElement("div");
      body.className = "section-body";
      row.appendChild(head); row.appendChild(body);
      dash.insertBefore(row, dash.firstChild);
      sec = row;
    }
    return sec;
  }
  function sectionBody(sec) { return sec?.querySelector(".section-body") || null; }
  function idxOf(steps, v) {
    const i = steps.findIndex(s => (s||"").toLowerCase() === (v||"").toLowerCase());
    return i >= 0 ? i : -1;
  }

  function clickableStep(frm, fieldname, label, i, currentIdx, color, enabled) {
    const div = document.createElement("div");
    // статус шага
    div.className = "ec-step " + (i < currentIdx ? "-past" : i === currentIdx ? "-current" : "-future");
    if (enabled) {
      div.style.background = i <= currentIdx ? (color + "22") : "#eef2f7";
      div.addEventListener("click", () => frm.set_value(fieldname, label));
    } else {
      div.classList.add("-disabled");
      div.style.background = "transparent";
      div.style.border = "1px dashed #d1d5db";
      div.style.cursor = "default";
    }
    div.title = label;
    return div;
  }

  function renderOnePipeline(frm, board, doc) {
    const fieldname = findFirstExistingField(frm, board.fields);
    if (!fieldname) return null;

    const steps = getSelectOptions(frm, fieldname);
    const current = (doc[fieldname] || "");
    const currentIdx = idxOf(steps, current);
    const enabled = parseInt(doc[board.flag] || 0) === 1;

    const card = document.createElement("div");
    card.className = "ec-pipe" + (enabled ? "" : " -disabled");

    const head = document.createElement("div");
    head.className = "head";
    const dot = document.createElement("span");
    dot.className = "dot"; dot.style.background = board.color;
    const ttl = document.createElement("div");
    ttl.className = "title"; ttl.textContent = board.name;
    head.appendChild(dot); head.appendChild(ttl);

    const stepsWrap = document.createElement("div");
    stepsWrap.className = "ec-steps";
    steps.forEach((lbl, i) => {
      stepsWrap.appendChild(
        clickableStep(frm, fieldname, lbl, i, Math.max(currentIdx, -0.5), board.color, enabled)
      );
    });

    const namesWrap = document.createElement("div");
    namesWrap.className = "ec-names" + (enabled ? "" : " -disabled");
    steps.forEach((lbl, i) => {
      const n = document.createElement("div");
      n.className = "ec-name" + (i === currentIdx && enabled ? " -current" : "");
      n.title = lbl; n.textContent = lbl;
      namesWrap.appendChild(n);
    });

    card.appendChild(head);
    card.appendChild(stepsWrap);
    card.appendChild(namesWrap);
    return card;
  }

  function renderProgress(frm) {
    ensureCss();
    const sec = getOrCreateDashSection(frm, "ec-progress-area", "Workflow");
    const body = sectionBody(sec);
    if (!body) return;

    let list = body.querySelector(".ec-pipes");
    if (!list) {
      list = document.createElement("div");
      list.className = "ec-pipes";
      body.appendChild(list);
    }
    list.innerHTML = "";

    const doc = frm.doc || {};
    BOARDS.forEach(b => {
      const ui = renderOnePipeline(frm, b, doc);
      if (ui) list.appendChild(ui);
    });
  }

  // ---------------- Linked Cases (как было) ----------------
  const fullPath  = (p)=> p ? (p.startsWith("/") ? p : `/${p}`) : "";
  const pickAvatar= (row)=> fullPath(row.avatar || "/assets/frappe/images/ui/user-avatar.svg");
  function chipTag(bucket, val, dashed=false) {
    if (!val) return "";
    if (typeof window.tagChip === "function") return window.tagChip(bucket, val, dashed);
    const cls = "crm-chip" + (dashed ? " -dashed" : "");
    return `<span class="${cls}">${esc(val)}</span>`;
  }
  function chipBoard(boardName, status, dashed=false) {
    if (!status) return "";
    if (typeof window.boardChip === "function") return window.boardChip(boardName, status, dashed);
    const extra = dashed ? "border-style:dashed;background:transparent" : "";
    return `<span class="crm-chip" style="${extra}">${esc(status)}</span>`;
  }
  const timeChip  = (label, dt)=> dt ? `<span class="crm-chip -ghost"><span class="lbl">${esc(label)}:</span> ${frappe.datetime.comment_when(dt)}</span>` : "";
  const sepChip   = `<span class="crm-vsep" aria-hidden="true"></span>`;

  function ensureLinkedContainer(frm) {
    const fld = frm.get_field("linked_engagements");
    if (!fld?.wrapper) return null;
    fld.wrapper.classList.add("ec-grid-hidden");

    let wrap = fld.wrapper.querySelector(".ec-linked-preview");
    if (!wrap) {
      const div = document.createElement("div");
      div.className = "ec-linked-preview";
      div.innerHTML = `
        <div class="ec-linked-header">
          Linked engagements
          <span class="ec-actions">
            <button class="btn btn-xs btn-default" data-ec-act="search-link">Search & Link</button>
          </span>
        </div>
        <div class="ec-linked-list"></div>`;
      fld.wrapper.appendChild(div);
      wrap = div;

      wrap.querySelector("[data-ec-act='search-link']")?.addEventListener("click", ()=> addLinkExistingDialog(frm));
    }
    return wrap.querySelector(".ec-linked-list");
  }

  function kanbanChipsAll(row) {
    const list = [];
    for (const b of BOARDS) {
      const f = b.fields.find(fn => fn in row);
      const st = f ? row[f] : null;
      if (!st) continue;
      const dashed = !row[b.flag];
      list.push(chipBoard(b.name, st, dashed));
    }
    return list.join("");
  }

  function renderMiniCard(row, opts={}) {
    const title  = row.title || row.display_name || row.name;
    const avatar = pickAvatar(row);
    const common = [
      row.channel_platform ? chipTag("platform", row.channel_platform) : "",
      row.priority         ? chipTag("priority", row.priority) : "",
    ].filter(Boolean).join("");
    const kchips = kanbanChipsAll(row);
    const chips  = [common, kchips ? sepChip + kchips : ""].join("");
    const times  = [
      timeChip("Last", row.last_event_at),
      timeChip("First", row.first_event_at)
    ].filter(Boolean).join(" ");
    const right = [
      `<button class="btn btn-xs btn-default" data-act="open"   data-name="${esc(row.name)}">Open</button>`,
      opts.show_unlink   ? `<button class="btn btn-xs btn-danger"  data-act="unlink" data-name="${esc(row.name)}">Unlink</button>` : "",
      opts.can_edit_link ? `<button class="btn btn-xs btn-primary" data-act="edit-link" data-name="${esc(row.name)}" title="Edit link row">✎</button>` : ""
    ].filter(Boolean).join(" ");

    return `
      <div class="ec-card${opts.is_parent ? " -parent" : ""}" data-name="${esc(row.name)}">
        <div class="ec-left">
          <div class="ec-avatar"><img src="${esc(avatar)}" alt=""></div>
          <div class="ec-body">
            <div class="ec-title">${esc(title)}</div>
            <div class="ec-meta">${chips}</div>
            <div class="ec-meta -time">${times}</div>
          </div>
        </div>
        <div class="ec-right">${right}</div>
      </div>
    `;
  }

  function hideLinkedGrid(frm) {
    const fld = frm.get_field("linked_engagements");
    if (fld?.wrapper) fld.wrapper.classList.add("ec-grid-hidden");
  }

  async function loadLinkedPreviews(frm) {
    const listWrap = ensureLinkedContainer(frm);
    if (!listWrap) return;
    listWrap.innerHTML = `<div class="text-muted small">Loading…</div>`;

    const linkRows = (frm.doc.linked_engagements || []).filter(r => r.engagement);
    const names = linkRows.map(r => r.engagement);
    const hiddenByName = {};
    linkRows.forEach(r => { hiddenByName[r.engagement] = !!r.hide_in_lists; });

    if (!names.length) { listWrap.innerHTML = `<div class="text-muted small">No linked engagements yet.</div>`; return; }

    try {
      const { message: rows = [] } = await frappe.call({
        method: "frappe.client.get_list",
        args: {
          doctype: "Engagement Case",
          fields: [
            "name","title","display_name","avatar","channel_platform","priority",
            // ВАЖНО: БЕЗ crm_status, чтобы не ловить DataError
            "status_crm_board","status_leads","status_deals","status_patients",
            "show_board_crm","show_board_leads","show_board_deals","show_board_patients",
            "first_event_at","last_event_at"
          ],
          filters: [["name","in",names]],
          limit_page_length: names.length
        }
      });

      listWrap.innerHTML = (rows||[]).map(r => renderMiniCard(r, {
        show_unlink: true,
        can_edit_link: true,
        hidden: !!hiddenByName[r.name]
      })).join("") || `<div class="text-muted small">No data.</div>`;

      listWrap.querySelectorAll("[data-act]").forEach(btn => {
        btn.addEventListener("click", (ev) => {
          ev.preventDefault();
          const act  = btn.getAttribute("data-act");
          const name = btn.getAttribute("data-name");
          if (act === "open") {
            frappe.set_route("Form", "Engagement Case", name);
          } else if (act === "unlink") {
            frappe.confirm(__("Unlink this case?"), () => {
              const idx = (frm.doc.linked_engagements || []).findIndex(r => r.engagement === name);
              if (idx >= 0) {
                frm.doc.linked_engagements.splice(idx, 1);
                frm.refresh_field("linked_engagements");
                loadLinkedPreviews(frm);
                loadParentPreviews(frm);
                frappe.show_alert({ message: `Unlinked ${name}`, indicator: "orange" });
              }
            });
          } else if (act === "edit-link") {
            openLinkRowEditor(frm, name);
          }
        });
      });
    } catch (e) {
      console.error(e);
      listWrap.innerHTML = `<div class="text-danger small">Failed to load linked previews.</div>`;
    }
  }

  function ensureParentsContainer(frm) {
    const fld = frm.get_field("linked_engagements");
    if (!fld?.wrapper) return null;
    let wrap = fld.wrapper.querySelector(".ec-parents-preview");
    if (!wrap) {
      const div = document.createElement("div");
      div.className = "ec-parents-preview";
      div.innerHTML = `<div class="ec-linked-header">Parents (where this case is linked)</div><div class="ec-parents-list"></div>`;
      fld.wrapper.appendChild(div);
      wrap = div;
    }
    return wrap.querySelector(".ec-parents-list");
  }

  async function loadParentPreviews(frm) {
    const listWrap = ensureParentsContainer(frm);
    if (!listWrap || frm.is_new()) { if (listWrap) listWrap.innerHTML = ""; return; }
    listWrap.innerHTML = `<div class="text-muted small">Loading…</div>`;
    try {
      const { message: rows = [] } = await frappe.call({
        method: "dantist_app.api.engagement.handlers.parents_of_engagement",
        args: { name: frm.doc.name }
      });
      listWrap.innerHTML = (rows||[]).map(r => renderMiniCard(r, { is_parent:true })).join("") || `<div class="text-muted small">No parents.</div>`;
      listWrap.querySelectorAll("[data-act='open']").forEach(btn =>
        btn.addEventListener("click", ()=> frappe.set_route("Form", "Engagement Case", btn.getAttribute("data-name")))
      );
    } catch (e) {
      console.error(e);
      listWrap.innerHTML = `<div class="text-danger small">Failed to load parent previews.</div>`;
    }
  }

  // ---- ✎: надёжно открываем редактор строки child-таблицы ----
  function openLinkRowEditor(frm, engagementName) {
    const grid = frm.get_field("linked_engagements")?.grid;
    if (!grid) return;

    const tryOpen = () => {
      const docRow = (frm.doc.linked_engagements || []).find(r => r.engagement === engagementName);
      if (!docRow) return false;

      if (!grid.grid_rows || !grid.grid_rows.length) grid.refresh();

      let rowObj =
        (grid.grid_rows || []).find(r => r.doc && (r.doc.name === docRow.name)) ||
        (grid.grid_rows || []).find(r => r.doc && (r.doc.engagement === engagementName));

      if (!rowObj) {
        grid.refresh();
        rowObj =
          (grid.grid_rows || []).find(r => r.doc && (r.doc.name === docRow.name)) ||
          (grid.grid_rows || []).find(r => r.doc && (r.doc.engagement === engagementName));
      }

      if (rowObj && typeof rowObj.toggle_view === "function") {
        rowObj.toggle_view(true);
        return true;
      }

      if (typeof grid.open_grid_row === "function") {
        try {
          grid.open_grid_row(docRow.name || ((docRow.idx || 1) - 1));
          return true;
        } catch {}
      }
      return false;
    };

    if (!tryOpen()) setTimeout(() => { if (!tryOpen()) grid.refresh(); }, 30);
  }

  // ---- диалог поиска/линковки (как было, без crm_status в полях) ----
  function addLinkExistingDialog(frm) {
    const already = new Set((frm.doc.linked_engagements || []).map(r => r.engagement).filter(Boolean));

    const d = new frappe.ui.Dialog({
      title: "Link existing case",
      fields: [
        { fieldtype: "Data", fieldname: "q", label: "Search", description: "name, title, display name, phone, email" },
        { fieldtype: "Section Break" },
        { fieldtype: "HTML", fieldname: "results" },
      ],
      primary_action_label: "Close",
      primary_action() { d.hide(); }
    });
    const $res = ()=> d.get_field("results").$wrapper;

    async function runSearch() {
      const q = (d.get_value("q") || "").trim();
      $res().html(`<div class="text-muted small">Searching…</div>`);
      const like = `%${q}%`;
      const or_filters = q ? [
        ["Engagement Case","name","like",like],
        ["Engagement Case","title","like",like],
        ["Engagement Case","display_name","like",like],
        ["Engagement Case","phone","like",like],
        ["Engagement Case","email","like",like],
      ] : null;

      try {
        const { message: items = [] } = await frappe.call({
          method: "frappe.client.get_list",
          args: {
            doctype: "Engagement Case",
            fields: [
              "name","title","display_name","avatar","channel_platform","priority",
              "status_crm_board","status_leads","status_deals","status_patients",
              "show_board_crm","show_board_leads","show_board_deals","show_board_patients",
              "first_event_at","last_event_at"
            ],
            filters: [["name","!=", frm.doc.name]],
            or_filters,
            order_by: "ifnull(last_event_at, modified) desc, modified desc",
            limit_page_length: 20
          }
        });

        const filtered = (items || []).filter(it => !already.has(it.name));
        if (!filtered.length) { $res().html(`<div class="text-muted small">Nothing found</div>`); return; }

        const html = filtered.map(r => {
          const common = [
            r.channel_platform ? chipTag("platform", r.channel_platform) : "",
            r.priority         ? chipTag("priority", r.priority) : "",
          ].filter(Boolean).join("");
          const kchips = kanbanChipsAll(r);
          const chips  = [common, kchips ? sepChip + kchips : ""].join("");

          return `
            <div class="ec-card" data-name="${esc(r.name)}">
              <div class="ec-left">
                <div class="ec-avatar"><img src="${esc(pickAvatar(r))}" alt=""></div>
                <div class="ec-body">
                  <div class="ec-title">${esc(r.title || r.display_name || r.name)}</div>
                  <div class="ec-meta">${chips}</div>
                  <div class="ec-meta -time">
                    ${timeChip("Last", r.last_event_at)} ${timeChip("First", r.first_event_at)}
                  </div>
                </div>
              </div>
              <div class="ec-right">
                <button class="btn btn-xs btn-default" data-act="open" data-name="${esc(r.name)}">Open</button>
                <button class="btn btn-xs btn-primary" data-act="link" data-name="${esc(r.name)}">Link</button>
              </div>
            </div>
          `;
        }).join("");

        $res().html(html);
        $res().find("[data-act]").on("click", (e)=>{
          const btn = e.target.closest("[data-act]");
          if (!btn) return;
          const act = btn.getAttribute("data-act");
          const name = btn.getAttribute("data-name");
          if (act === "open") {
            frappe.set_route("Form", "Engagement Case", name);
          } else if (act === "link") {
            if (already.has(name)) {
              frappe.msgprint(__("This case is already linked."), __("Duplicate link"));
              return;
            }
            frm.add_child("linked_engagements", { engagement: name, hide_in_lists: 1 });
            already.add(name);
            frm.refresh_field("linked_engagements");
            loadLinkedPreviews(frm);
            loadParentPreviews(frm);
            frappe.show_alert({ message: `Linked ${name}`, indicator: "green" });
          }
        });
      } catch (e) {
        console.error(e);
        $res().html(`<div class="text-danger small">Search failed</div>`);
      }
    }

    d.get_field("q").$input.on("input", frappe.utils.debounce(runSearch, 250));
    d.show();
    runSearch();
  }

  // ---------------- Hooks ----------------
  frappe.ui.form.on(DOCTYPE, {
    onload_post_render(frm) {
      ensureCss();
      suppressTitleIndicator(frm, true);
      renderProgress(frm);
      hideLinkedGrid(frm);
      loadLinkedPreviews(frm);
      loadParentPreviews(frm);
    },
    refresh(frm) {
      ensureCss();
      suppressTitleIndicator(frm, true);
      renderProgress(frm);
      hideLinkedGrid(frm);
      loadLinkedPreviews(frm);
      loadParentPreviews(frm);

      requestAnimationFrame(() => { renderProgress(frm); });
      setTimeout(() => { renderProgress(frm); }, 60);
    },
    // слушаем все изменения статусов/флагов
    status_crm_board:   (frm)=> renderProgress(frm),
    crm_status:         (frm)=> renderProgress(frm),
    status_leads:       (frm)=> renderProgress(frm),
    status_deals:       (frm)=> renderProgress(frm),
    status_patients:    (frm)=> renderProgress(frm),
    show_board_crm:     (frm)=> renderProgress(frm),
    show_board_leads:   (frm)=> renderProgress(frm),
    show_board_deals:   (frm)=> renderProgress(frm),
    show_board_patients:(frm)=> renderProgress(frm),

    linked_engagements_add(frm){ loadLinkedPreviews(frm); },
    linked_engagements_remove(frm){ loadLinkedPreviews(frm); loadParentPreviews(frm); },

    on_close(frm){ suppressTitleIndicator(frm, false); }
  });

})();