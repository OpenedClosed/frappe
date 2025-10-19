// Engagement Case — form UX
// - Шапка: все статусы по 4 доскам (Show-on=1 → сплошной, Show-on=0 → пунктир БЕЗ заливки)
//   + справа от статусов при необходимости отдельный чип "Hidden" (СПЛОШНОЙ, как в карточках)
// - Linked preview: скрываем нативную grid, только "Search & Link", без дублей; unlink — с подтверждением
// - ✎ открывает child-row; мини-карточки детей и родителей показывают ВСЕ доски (цвета из Kanban)
// - Между обычными тегами (platform/priority/…) и канбан-статусами — узкий вертикальный пунктир
(function () {
  const esc = frappe.utils.escape_html;

  const BOARDS = [
    { name: "CRM Board",                  flag: "show_board_crm",      field: "status_crm_board" },
    { name: "Leads – Contact Center",     flag: "show_board_leads",    field: "status_leads" },
    { name: "Deals – Contact Center",     flag: "show_board_deals",    field: "status_deals" },
    { name: "Patients – Care Department", flag: "show_board_patients", field: "status_patients" },
  ];

  const fullPath  = (p)=> p ? (p.startsWith("/") ? p : `/${p}`) : "";
  const pickAvatar= (row)=> fullPath(row.avatar || "/assets/frappe/images/ui/user-avatar.svg");

  // ----- helpers: chips -----
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

  async function ensureAllBoardColors() {
    if (typeof window.getBoardColors === "function") {
      await Promise.all(BOARDS.map(b => window.getBoardColors(b.name)));
    }
  }

  // ----- hidden-mark for current doc (если он скрыт где-то как child) -----
  let HIDDEN_SET = null;
  async function isCurrentHidden(name) {
    try {
      if (!name) return false;
      if (!HIDDEN_SET) {
        const { message: hiddenList = [] } = await frappe.call({
          method: "dantist_app.api.engagement.handlers.engagement_hidden_children"
        });
        HIDDEN_SET = new Set(hiddenList || []);
      }
      return HIDDEN_SET.has(name);
    } catch (e) {
      console.warn("[EC Form] hidden check failed", e);
      return false;
    }
  }

  // ---------- title badges ----------
  async function updateTitleBadges(frm) {
    try {
      const titleArea = document.querySelector(".page-head .title-area .flex");
      if (!titleArea) return;

      let wrap = titleArea.querySelector(".ec-title-badges");
      if (!wrap) {
        wrap = document.createElement("div");
        wrap.className = "ec-title-badges";
        titleArea.appendChild(wrap);
      }

      const chips = [];
      for (const b of BOARDS) {
        const st = frm.doc[b.field];
        if (!st) continue;
        const dashed = !frm.doc[b.flag];
        chips.push(chipBoard(b.name, st, dashed));
      }

      // если текущий кейс скрыт в каком-то родителе — покажем чип "Hidden" (СПЛОШНОЙ!)
      const hiddenNow = await isCurrentHidden(frm.doc.name);
      const hiddenChip = hiddenNow ? chipTag("badge", "Hidden", /*dashed*/ false) : "";

      wrap.innerHTML = chips.join("") + (hiddenChip ? sepChip + hiddenChip : "");

      // спрячем стандартный одинокий индикатор
      const std = titleArea.querySelector(".indicator-pill");
      if (std) std.style.display = "none";
    } catch (e) { console.warn("updateTitleBadges failed", e); }
  }

  // ---------- открыть редактирование строки child table по ✎ ----------
  function openLinkRowEditor(frm, engagementName) {
    const grid = frm.get_field("linked_engagements")?.grid;
    if (!grid) return;
    const row = (grid.grid_rows || []).find(r => (r.doc && r.doc.engagement === engagementName));
    if (row && row.toggle_view) { row.toggle_view(true); return; }
    const docRow = (frm.doc.linked_engagements || []).find(r => r.engagement === engagementName);
    if (docRow && typeof grid.row_open === "function") grid.row_open((docRow.idx || 1) - 1);
  }

  // ---------- linked preview ----------
  function ensureLinkedContainer(frm) {
    const fld = frm.get_field("linked_engagements");
    if (!fld?.wrapper) return null;

    // скрываем стандартную grid (DOM остаётся для редакторов строк)
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
    const out = [];
    for (const b of BOARDS) {
      const st = row[b.field];
      if (!st) continue;
      const dashed = !row[b.flag];
      out.push(chipBoard(b.name, st, dashed));
    }
    return out.join("");
  }

  function renderMiniCard(row, opts={}) {
    const title  = row.title || row.display_name || row.name;
    const avatar = pickAvatar(row);

    // обычные теги (цветные из EC_TAG_COLORS)
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

  // ---------- parents ----------
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

  // ---------- диалог поиска/линковки (без дублей) ----------
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

  // ---------- кнопки Open Kanban (только текст) ----------
  function addOpenKanbanButtons(frm) {
    BOARDS.forEach(meta => {
      const fld = frm.get_field(meta.field);
      if (!fld || !fld.$wrapper || fld.$wrapper[0]?.$open_kb_btn) return;
      const btn = $(`
        <button class="btn btn-xs btn-default ec-open-kanban" type="button">
          Open Kanban
        </button>
      `).on("click", () => frappe.set_route("List", "Engagement Case", "Kanban", meta.name));
      fld.$wrapper.find(".control-input").append(btn);
      fld.$wrapper[0].$open_kb_btn = btn;
    });
  }

  // ---------- hooks ----------
  frappe.ui.form.on("Engagement Case", {
    async refresh(frm) {
      await ensureAllBoardColors();
      await updateTitleBadges(frm);
      addOpenKanbanButtons(frm);
      loadLinkedPreviews(frm);
      loadParentPreviews(frm);
    },
    linked_engagements_add(frm)    { loadLinkedPreviews(frm); },
    linked_engagements_remove(frm) { loadLinkedPreviews(frm); loadParentPreviews(frm); }
  });

  // ---------- styles ----------
  const style = document.createElement("style");
  style.innerHTML = `
  .ec-title-badges{display:flex;gap:6px;align-items:center;margin-left:8px}

  /* База для всех чипов */
  .crm-chip{font-size:10px;padding:2px 6px;border-radius:999px;border:1px solid #e5e7eb;background:transparent}
  .crm-chip.-ghost{background:#f8fafc}
  .crm-chip.-dashed{border-style:dashed;background:transparent}

  /* Узкая вертикальная пунктирная черта (разделитель) */
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

  /* Скрыть стандартную grid Linked Engagements целиком */
  .ec-grid-hidden .control-label,
  .ec-grid-hidden .grid-description,
  .ec-grid-hidden .grid-custom-buttons,
  .ec-grid-hidden .form-grid-container,
  .ec-grid-hidden .grid-heading-row,
  .ec-grid-hidden .grid-footer { display:none !important; }
  `;
  document.head.appendChild(style);
})();