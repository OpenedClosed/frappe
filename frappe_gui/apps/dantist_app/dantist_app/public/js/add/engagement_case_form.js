// Engagement Case — Form UX (final: your original + stacked pipelines progress)
// - Progress: Пайплайны по одной доске в строку; шаги тянутся из df.options;
//   классы ec-steps/ec-step/-past/-current/-future/-disabled — как в "stacked pipelines" + кнопка Open Kanban.
// - Скрываем title-indicator ТОЛЬКО на Engagement Case (через ec-suppress-title-indicator).
// - Title badges: цветные чипы по всем доскам + "Hidden" при необходимости.
// - Linked Cases: «как было» (цветные чипы всех досок, Search & Link, Unlink).
// - ✎: надёжно открывает нативный редактор строки (если только inline-режим — временно раскрывает грид, потом снова прячет).
// - В get_list НЕТ crm_status (исправляет DataError).

(function () {
  const DOCTYPE = "Engagement Case";
  const esc = frappe.utils.escape_html;

  // --- Boards meta ---
  const BOARDS = [
    { name: "CRM Board",                  flag: "show_board_crm",      fields: ["status_crm_board","crm_status"], color: "#2563eb" },
    { name: "Leads – Contact Center",     flag: "show_board_leads",    fields: ["status_leads"],                    color: "#16a34a" },
    { name: "Deals – Contact Center",     flag: "show_board_deals",    fields: ["status_deals"],                    color: "#ea580c" },
    { name: "Patients – Care Department", flag: "show_board_patients", fields: ["status_patients"],                 color: "#9333ea" },
  ];

  // ---------- colors ----------
  async function ensureAllBoardColors() {
    if (typeof window.getBoardColors === "function") {
      await Promise.all(BOARDS.map(b => window.getBoardColors(b.name)));
    }
  }
  function colorFor(board, status) {
    const map = (window.EC_BOARD_COLORS && window.EC_BOARD_COLORS[board]) || {};
    return map[status] || map[(status||"").toLowerCase?.()] || "#2563eb";
  }
  function rgba(hex, a){
    const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex||"");
    if (!m) return `rgba(37,99,235,${a})`;
    const r=parseInt(m[1],16), g=parseInt(m[2],16), b=parseInt(m[3],16);
    return `rgba(${r},${g},${b},${a})`;
  }

  // ---------- chips ----------
  function chipTag(bucket, val, dashed=false){
    if (!val) return "";
    if (typeof window.tagChip === "function") return window.tagChip(bucket,val,dashed);
    return `<span class="crm-chip${dashed?" -dashed":""}">${esc(val)}</span>`;
  }
  function chipBoard(boardName, status, dashed=false){
    if (!status) return "";
    if (typeof window.boardChip === "function") return window.boardChip(boardName,status,dashed);
    const c = colorFor(boardName, status);
    const st = dashed
      ? `border-color:${c};border-style:dashed;background:transparent;color:${c}`
      : `background:${rgba(c,.18)};border-color:${rgba(c,.25)};color:#111827`;
    return `<span class="crm-chip" style="${st}">${esc(status)}</span>`;
  }
  const timeChip  = (lbl, dt)=> dt ? `<span class="crm-chip -ghost"><span class="lbl">${esc(lbl)}:</span> ${frappe.datetime.comment_when(dt)}</span>` : "";
  const sepChip   = `<span class="crm-vsep" aria-hidden="true"></span>`;
  const fullPath  = (p)=> p ? (p.startsWith("/") ? p : `/${p}`) : "";
  const pickAvatar= (row)=> fullPath(row.avatar || "/assets/frappe/images/ui/user-avatar.svg");

  // ---------- hidden mark ----------
  let HIDDEN_SET=null;
  async function isCurrentHidden(name){
    try{
      if (!name) return false;
      if (!HIDDEN_SET){
        const { message:list=[] } = await frappe.call({ method:"dantist_app.api.engagement.handlers.engagement_hidden_children" });
        HIDDEN_SET = new Set(list||[]);
      }
      return HIDDEN_SET.has(name);
    } catch { return false; }
  }

  // ---------- scoping + css ----------
  const CSS_ID = "ec-form-ux-css";
  function ensureCss() {
    if (document.getElementById(CSS_ID)) return;
    const s = document.createElement("style");
    s.id = CSS_ID;
    s.textContent = `
    /* Скрываем стандартный title-indicator только здесь */
    .ec-suppress-title-indicator .page-head .indicator-pill { display:none !important; }

    /* Progress — СТРОГО как в "stacked pipelines" + кнопка Open Kanban */
    .form-dashboard .ec-progress-section .section-head{
      font-weight:600;padding:8px 12px;border-bottom:1px solid var(--border-color,#e5e7eb);
    }
    .form-dashboard .ec-progress-section .section-body{ padding:12px; }
    .ec-pipes{ display:flex; flex-direction:column; gap:12px; }
    .ec-pipe{ border:1px solid var(--border-color,#e5e7eb); border-radius:10px; padding:10px; background:#fff; }
    .ec-pipe.-disabled{ opacity:.9; }
    .ec-pipe .head{ display:flex; align-items:center; gap:8px; margin-bottom:8px; justify-content:space-between; }
    .ec-pipe .head .l{display:flex;align-items:center;gap:8px}
    .ec-pipe .dot{ width:10px; height:10px; border-radius:50%; flex:0 0 10px; }
    .ec-pipe .title{ font-weight:600; }
    .ec-open-kanban{ margin-left:auto }

    .ec-steps{ display:flex; gap:6px; align-items:center; }
    .ec-step{
      position:relative; flex:1; height:10px; border-radius:999px; cursor:pointer;
      background:#eef2f7; outline:1px solid rgba(0,0,0,.03);
      transition: transform .12s ease, box-shadow .12s ease, opacity .12s ease;
    }
    .ec-step.-past{ opacity:.95 }
    .ec-step.-current{ transform: translateY(-1px); box-shadow: 0 1px 4px rgba(0,0,0,.08); }
    .ec-step.-future{ opacity:.6 }
    .ec-step.-disabled { background: transparent !important; border:1px dashed #d1d5db; outline:none; cursor:default; }
    .ec-step:hover{ box-shadow: 0 1px 6px rgba(0,0,0,.12); }

    .ec-names{ display:flex; gap:6px; margin-top:4px; font-size:11px; color:#6b7280; }
    .ec-name{ flex:1; text-align:center; white-space:nowrap; overflow:hidden; text-overflow:ellipsis }
    .ec-name.-current{ color:#111827; font-weight:600; }
    .ec-names.-disabled .ec-name{ color:#9ca3af; }

    /* Title badges + Linked Cards — как было у тебя */
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

    /* Прячем нативную grid визуально, DOM остаётся для ✎ */
    .ec-grid-hidden .control-label,
    .ec-grid-hidden .grid-description,
    .ec-grid-hidden .grid-custom-buttons,
    .ec-grid-hidden .form-grid-container,
    .ec-grid-hidden .grid-heading-row,
    .ec-grid-hidden .grid-footer { display:none !important; }
    `;
    document.head.appendChild(s);
  }

  // ---------- helpers ----------
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

  // ---------- PROGRESS ----------
  function clickableStep(frm, fieldname, label, i, currentIdx, color, enabled) {
    const div = document.createElement("div");
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
    theCurrentIdx = idxOf(steps, current);
    const currentIdx = theCurrentIdx;
    const enabled = parseInt(doc[board.flag] || 0) === 1;

    const card = document.createElement("div");
    card.className = "ec-pipe" + (enabled ? "" : " -disabled");

    const head = document.createElement("div");
    head.className = "head";
    const left = document.createElement("div");
    left.className = "l";
    const dot = document.createElement("span");
    dot.className = "dot"; dot.style.background = board.color;
    const ttl = document.createElement("div");
    ttl.className = "title"; ttl.textContent = board.name;
    left.appendChild(dot); left.appendChild(ttl);

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-xs btn-default ec-open-kanban";
    btn.textContent = "Open Kanban";
    btn.addEventListener("click", () => frappe.set_route("List", DOCTYPE, "Kanban", board.name));

    head.appendChild(left);
    head.appendChild(btn);

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

  // ---------- Title badges ----------
  async function updateTitleBadges(frm){
    const titleArea = document.querySelector(".page-head .title-area .flex");
    if (!titleArea) return;
    let wrap = titleArea.querySelector(".ec-title-badges");
    if (!wrap){
      wrap = document.createElement("div");
      wrap.className = "ec-title-badges";
      titleArea.appendChild(wrap);
    }
    const chips=[];
    for (const b of BOARDS){
      const fieldname = findFirstExistingField(frm, b.fields);
      const st = fieldname ? frm.doc[fieldname] : null;
      if (!st) continue;
      const dashed = !frm.doc[b.flag];
      chips.push(chipBoard(b.name, st, dashed));
    }
    const hidden = await isCurrentHidden(frm.doc.name);
    wrap.innerHTML = chips.join("") + (hidden ? sepChip + chipTag("badge","Hidden",false) : "");
  }

  // ---------- Linked ----------
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
      const fieldname = (b.fields||[]).find(fn => fn in row);
      const st = fieldname ? row[fieldname] : null;
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
    const badges = [];
    if (opts.is_parent) badges.push(chipTag("badge", "Parent"));
    if (opts.hidden)    badges.push(chipTag("badge", "Hidden"));

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
            <div class="ec-title">${esc(title)} ${badges.join(" ")}</div>
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

  // === NEW: временно показываем грид на время редактирования inline ===
  function temporarilyShowLinkedGrid(frm) {
    const fld = frm.get_field("linked_engagements");
    const wrap = fld?.wrapper && fld.wrapper[0] ? fld.wrapper[0] : (fld?.wrapper || null);
    if (!wrap) return { shown:false, cleanup:()=>{} };

    const wasHidden = wrap.classList.contains("ec-grid-hidden");
    const bits = [
      ".control-label",".grid-description",".grid-custom-buttons",
      ".form-grid-container",".grid-heading-row",".grid-footer"
    ].map(sel => wrap.querySelector(sel)).filter(Boolean);

    const prevDisplay = bits.map(el => el.style.display);
    if (wasHidden) wrap.classList.remove("ec-grid-hidden");
    bits.forEach(el => el.style.display = "");

    const cleanup = () => {
      // возвращаем всё, как было
      bits.forEach((el,i) => el.style.display = prevDisplay[i] ?? "");
      if (wasHidden) wrap.classList.add("ec-grid-hidden");
    };

    return { shown:true, wrap, cleanup };
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
          doctype: DOCTYPE,
          fields: [
            "name","title","display_name","avatar","channel_platform","priority",
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
            frappe.set_route("Form", DOCTYPE, name);
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
        btn.addEventListener("click", ()=> frappe.set_route("Form", DOCTYPE, btn.getAttribute("data-name")))
      );
    } catch (e) {
      console.error(e);
      listWrap.innerHTML = `<div class="text-danger small">Failed to load parent previews.</div>`;
    }
  }

  // ---------- ✎: открыть нативный редактор строки (с логами вокруг кнопки/открытия) ----------
  function openLinkRowEditor(frm, engagementName) {
    const TAG = "[EC ✎]";
    const grid = frm.get_field("linked_engagements")?.grid;
    if (!grid) { console.warn(TAG, "grid not found for linked_engagements"); return; }

    const rowDoc = (frm.doc.linked_engagements || []).find(r => r.engagement === engagementName);
    if (!rowDoc) { console.warn(TAG, "rowDoc not found for engagement", engagementName); return; }

    try {
      console.debug(TAG, "rowDoc:", { name: rowDoc.name, idx: rowDoc.idx, engagement: rowDoc.engagement });
      console.debug(TAG, "grid methods:", {
        edit_row: typeof grid.edit_row,
        open_grid_row: typeof grid.open_grid_row,
        get_row: typeof grid.get_row,
        show_form: typeof grid.show_form,
        grid_rows_len: (grid.grid_rows && grid.grid_rows.length) || 0,
        grid_rows_by_docname: !!grid.grid_rows_by_docname,
        grid_form_type: typeof grid.grid_form
      });
    } catch (_) {}

    const getGridRow = () => {
      try {
        return (typeof grid.get_row === "function" && grid.get_row(rowDoc.name))
            || (grid.grid_rows_by_docname && grid.grid_rows_by_docname[rowDoc.name])
            || null;
      } catch { return null; }
    };

    const ensureVisible = temporarilyShowLinkedGrid(frm);

    const attachAutoHide = () => {
      try {
        const wrap = grid.wrapper && grid.wrapper[0];
        const rowEl = wrap && wrap.querySelector(`.grid-row[data-name="${rowDoc.name}"]`);
        const cleanup = ensureVisible.cleanup;

        // кнопка закрытия инлайна
        rowEl?.querySelector(".grid-row-close")?.addEventListener("click", () => {
          setTimeout(cleanup, 40);
        }, { once: true });

        // наблюдаем сворачивание (класс .grid-row-open исчезает)
        if (rowEl) {
          const mo = new MutationObserver(() => {
            if (!rowEl.classList.contains("grid-row-open")) {
              mo.disconnect();
              setTimeout(cleanup, 10);
            }
          });
          mo.observe(rowEl, { attributes: true, attributeFilter: ["class"] });
        }

        // жёсткий фолбэк: вернём скрытие через 2 минуты, если что-то пошло не так
        setTimeout(cleanup, 120000);
      } catch (_) {
        // на крайний случай — вернуть скрытие через 3с
        setTimeout(ensureVisible.cleanup, 3000);
      }
    };

    const openInline = () => {
      try {
        const gRow = getGridRow();
        if (!gRow) { console.debug(TAG, "no grid row by docname for inline path"); return false; }
        if (typeof gRow.open_form === "function") {
          console.info(TAG, "try open via gRow.open_form()");
          gRow.open_form();
          console.info(TAG, "opened via gRow.open_form()");
        } else if (typeof gRow.toggle_view === "function") {
          gRow.toggle_view(true);
          console.info(TAG, "opened via gRow.toggle_view(true) (inline)");
        } else {
          return false;
        }

        // скроллим к строке, чтобы пользователь её увидел
        try {
          const el = grid.wrapper && grid.wrapper[0] && grid.wrapper[0].querySelector(`.grid-row[data-name="${rowDoc.name}"]`);
          el?.scrollIntoView({ behavior: "smooth", block: "center" });
        } catch (_){}
        attachAutoHide();
        return true;
      } catch (e) {
        console.error(TAG, "inline path failed:", e);
        return false;
      }
    };

    try { console.debug(TAG, "grid.refresh() pre"); grid.refresh(); } catch (_) {}

    // 1) Если есть API модалки — пользуемся им
    if (typeof grid.edit_row === "function") {
      console.info(TAG, "try open via grid.edit_row(name)");
      grid.edit_row(rowDoc.name);
      console.info(TAG, "opened via edit_row");
      // модалка — грид можно обратно спрятать сразу
      setTimeout(ensureVisible.cleanup, 10);
      return;
    }
    if (typeof grid.open_grid_row === "function") {
      console.info(TAG, "try open via grid.open_grid_row(name)");
      grid.open_grid_row(rowDoc.name);
      console.info(TAG, "opened via open_grid_row");
      setTimeout(ensureVisible.cleanup, 10);
      return;
    }

    // 2) Иначе — инлайн
    if (openInline()) return;

    // 3) Повторная попытка после refresh
    setTimeout(() => {
      try { console.debug(TAG, "grid.refresh() retry"); grid.refresh(); } catch (_) {}
      if (typeof grid.edit_row === "function") {
        console.info(TAG, "retry via grid.edit_row(name)");
        grid.edit_row(rowDoc.name);
        console.info(TAG, "opened via edit_row");
        setTimeout(ensureVisible.cleanup, 10);
        return;
      }
      if (typeof grid.open_grid_row === "function") {
        console.info(TAG, "retry via grid.open_grid_row(name)");
        grid.open_grid_row(rowDoc.name);
        console.info(TAG, "opened via open_grid_row");
        setTimeout(ensureVisible.cleanup, 10);
        return;
      }
      if (openInline()) return;

      console.error(TAG, "all paths failed; editor did not open");
      ensureVisible.cleanup();
    }, 40);
  }

  // ---------- Search & Link ----------
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
        [DOCTYPE,"name","like",like],
        [DOCTYPE,"title","like",like],
        [DOCTYPE,"display_name","like",like],
        [DOCTYPE,"phone","like",like],
        [DOCTYPE,"email","like",like],
      ] : null;

      try {
        const { message: items = [] } = await frappe.call({
          method: "frappe.client.get_list",
          args: {
            doctype: DOCTYPE,
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
            frappe.set_route("Form", DOCTYPE, name);
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
    async onload_post_render(frm) {
      ensureCss();
      suppressTitleIndicator(frm, true);
      await ensureAllBoardColors();
      await updateTitleBadges(frm);
      renderProgress(frm);
      hideLinkedGrid(frm);
      loadLinkedPreviews(frm);
      loadParentPreviews(frm);
    },
    async refresh(frm) {
      ensureCss();
      suppressTitleIndicator(frm, true);
      await ensureAllBoardColors();
      await updateTitleBadges(frm);
      renderProgress(frm);
      hideLinkedGrid(frm);
      loadLinkedPreviews(frm);
      loadParentPreviews(frm);

      requestAnimationFrame(() => { renderProgress(frm); });
      setTimeout(() => { renderProgress(frm); }, 60);
    },

    // обновляем пайплайны при изменениях
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