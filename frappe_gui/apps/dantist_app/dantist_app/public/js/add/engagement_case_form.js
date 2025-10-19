// Engagement Case — header indicators + link-existing UX + pretty previews (linked & parents)
(function () {
  const C = window.EC_COLORS || {};
  const esc = frappe.utils.escape_html;

  // ---------- small utils ----------
  function color(bucket, key) { return bucket && bucket[key]; }
  function addIndicator(frm, label, val, colr) {
    if (!val || !frm.dashboard || !frm.dashboard.add_indicator) return;
    frm.dashboard.add_indicator(__("{0}: {1}", [label, val]), colr || "gray");
  }
  function fullPath(p) { if (!p) return ""; return p.startsWith("/") ? p : `/${p}`; }

  // ---------- pills / chips ----------
  function chip(txt) { return `<span class="indicator-pill gray">${esc(txt||"")}</span>`; }

  // ВАЖНО: не экранируем innerHTML из comment_when, чтобы .frappe-timestamp корректно отрисовывался
  function timeChip(label, dt) {
    if (!dt) return "";
    return `<span class="indicator-pill light"><span class="lbl">${esc(label)}:</span> ${frappe.datetime.comment_when(dt)}</span>`;
  }

  // только личный аватар; если нет — дефолтный плейсхолдер
  function pickAvatar(row) {
    const fallback = "/assets/frappe/images/ui/user-avatar.svg";
    return fullPath(row.avatar || fallback);
  }

  // ---------- pretty mini card ----------
  function renderMiniCard(row, opts = {}) {
    const title = row.title || row.display_name || row.name;
    const avatar = pickAvatar(row);
    const statusChip =
      row.status_crm_board ? chip(row.status_crm_board) : "";
    const chips = [
      row.channel_platform ? chip(row.channel_platform) : "",
      row.priority ? chip(`P: ${row.priority}`) : "",
      statusChip,
    ].join("");

    const times = [
      timeChip("Last", row.last_event_at),
      timeChip("First", row.first_event_at)
    ].join(" ");

    const rightParts = [];
    if (opts.showUnlink) {
      rightParts.push(`<button class="btn btn-xs btn-danger" data-act="unlink" data-name="${esc(row.name)}">Unlink</button>`);
    }
    rightParts.push(`<button class="btn btn-xs btn-default" data-act="open" data-name="${esc(row.name)}">Open</button>`);
    const right = rightParts.join(" ");

    // визуальный маркер «родитель»
    const parentBadge = opts.parent ? `<span class="ec-badge -parent">Parent</span>` : "";

    return `
      <div class="ec-card${opts.parent ? " -parent" : ""}" data-name="${esc(row.name)}">
        <div class="ec-left">
          <div class="ec-avatar"><img src="${esc(avatar)}" alt=""></div>
          <div class="ec-body">
            <div class="ec-title">
              ${esc(title)}
              ${parentBadge}
            </div>
            <div class="ec-meta">${chips}</div>
            <div class="ec-meta -time">${times}</div>
          </div>
        </div>
        <div class="ec-right">${right}</div>
      </div>
    `;
  }

  // ---------- linked preview (children this case links to) ----------
  function ensureLinkedContainer(frm) {
    const fld = frm.get_field("linked_engagements");
    if (!fld || !fld.wrapper) return null;
    let wrap = fld.wrapper.querySelector(".ec-linked-preview");
    if (!wrap) {
      const div = document.createElement("div");
      div.className = "ec-linked-preview";
      div.innerHTML = `<div class="ec-linked-header">Linked engagements</div><div class="ec-linked-list"></div>`;
      fld.wrapper.appendChild(div);
      wrap = div;
    }
    return wrap.querySelector(".ec-linked-list");
  }

  async function loadLinkedPreviews(frm) {
    const listWrap = ensureLinkedContainer(frm);
    if (!listWrap) return;
    listWrap.innerHTML = `<div class="text-muted small">Loading…</div>`;

    const names = (frm.doc.linked_engagements || [])
      .map(r => r.engagement)
      .filter(Boolean);

    if (!names.length) {
      listWrap.innerHTML = `<div class="text-muted small">No linked engagements yet.</div>`;
      return;
    }

    try {
      const { message: rows = [] } = await frappe.call({
        method: "frappe.client.get_list",
        args: {
          doctype: "Engagement Case",
          fields: [
            "name","title","display_name","avatar","channel_platform","priority",
            "status_crm_board","first_event_at","last_event_at"
          ],
          filters: [["name","in",names]],
          limit_page_length: names.length
        }
      });

      if (!rows.length) {
        listWrap.innerHTML = `<div class="text-muted small">No data.</div>`;
        return;
      }

      listWrap.innerHTML = rows.map(r => renderMiniCard(r, { showUnlink: true })).join("");

      // actions
      listWrap.querySelectorAll("[data-act]").forEach(btn => {
        btn.addEventListener("click", () => {
          const act = btn.getAttribute("data-act");
          const name = btn.getAttribute("data-name");
          if (act === "open") {
            frappe.set_route("Form", "Engagement Case", name);
          } else if (act === "unlink") {
            const idx = (frm.doc.linked_engagements || []).findIndex(r => r.engagement === name);
            if (idx >= 0) {
              frm.doc.linked_engagements.splice(idx, 1);
              frm.refresh_field("linked_engagements");
              loadLinkedPreviews(frm);
              loadParentPreviews(frm); // родители могли измениться
              frappe.show_alert({ message: `Unlinked ${name}`, indicator: "orange" });
            }
          }
        });
      });
    } catch (e) {
      console.error(e);
      listWrap.innerHTML = `<div class="text-danger small">Failed to load linked previews.</div>`;
    }
  }

  // ---------- parents preview (where this case is linked) ----------
  function ensureParentsContainer(frm) {
    const fld = frm.get_field("linked_engagements");
    if (!fld || !fld.wrapper) return null;
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

      if (!rows.length) {
        listWrap.innerHTML = `<div class="text-muted small">No parents.</div>`;
        return;
      }

      listWrap.innerHTML = rows.map(r => renderMiniCard(r, { parent: true, showUnlink: false })).join("");

      listWrap.querySelectorAll("[data-act='open']").forEach(btn => {
        btn.addEventListener("click", () =>
          frappe.set_route("Form", "Engagement Case", btn.getAttribute("data-name"))
        );
      });
    } catch (e) {
      console.error(e);
      listWrap.innerHTML = `<div class="text-danger small">Failed to load parent previews.</div>`;
    }
  }

  // ---------- search & link dialog ----------
  function addLinkExistingButton(frm) {
    frm.add_custom_button("Link existing case", async () => {
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

      const $res = () => d.get_field("results").$wrapper;

      async function runSearch() {
        const q = (d.get_value("q") || "").trim();
        $res().html(`<div class="text-muted small">Searching…</div>`);

        const like = `%${q}%`;
        const or_filters = q ? [
          ["Engagement Case", "name", "like", like],
          ["Engagement Case", "title", "like", like],
          ["Engagement Case", "display_name", "like", like],
          ["Engagement Case", "phone", "like", like],
          ["Engagement Case", "email", "like", like],
        ] : null;

        try {
          const { message: items = [] } = await frappe.call({
            method: "frappe.client.get_list",
            args: {
              doctype: "Engagement Case",
              fields: [
                "name","title","display_name","avatar","channel_platform","priority",
                "status_crm_board","first_event_at","last_event_at"
              ],
              filters: [["name","!=", frm.doc.name]],
              or_filters,
              order_by: "ifnull(last_event_at, modified) desc, modified desc",
              limit_page_length: 20
            }
          });

          if (!items.length) {
            $res().html(`<div class="text-muted small">Nothing found</div>`);
            return;
          }

          const html = items.map(r => `
            <div class="ec-card" data-name="${esc(r.name)}">
              <div class="ec-left">
                <div class="ec-avatar"><img src="${esc(pickAvatar(r))}" alt=""></div>
                <div class="ec-body">
                  <div class="ec-title">${esc(r.title || r.display_name || r.name)}</div>
                  <div class="ec-meta">
                    ${r.channel_platform ? chip(r.channel_platform) : ""}
                    ${r.priority ? chip("P: " + r.priority) : ""}
                    ${r.status_crm_board ? chip(r.status_crm_board) : ""}
                  </div>
                  <div class="ec-meta -time">
                    ${timeChip("Last", r.last_event_at)}
                    ${timeChip("First", r.first_event_at)}
                  </div>
                </div>
              </div>
              <div class="ec-right">
                <button class="btn btn-xs btn-default" data-act="open" data-name="${esc(r.name)}">Open</button>
                <button class="btn btn-xs btn-primary" data-act="link" data-name="${esc(r.name)}">Link</button>
              </div>
            </div>
          `).join("");

          $res().html(html);

          $res().find("[data-act]").on("click", (e) => {
            const btn = e.target.closest("[data-act]");
            if (!btn) return;
            const act = btn.getAttribute("data-act");
            const name = btn.getAttribute("data-name");
            if (act === "open") {
              frappe.set_route("Form", "Engagement Case", name);
            } else if (act === "link") {
              frm.add_child("linked_engagements", { engagement: name, hide_in_lists: 1 });
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
    }, "Actions");
  }

  // ---------- decorate child-table row actions ----------
  function decorateChildTableActions(frm) {
    const grid = frm.get_field("linked_engagements") && frm.get_field("linked_engagements").grid;
    if (!grid) return;
    grid.wrapper.find(".grid-body .rows .grid-row").each((_, el) => {
      const row = $(el).data("grid_row");
      if (!row || !row.doc) return;
      if (row.$custom_open_btn) return;
      row.$custom_open_btn = $('<button class="btn btn-xs btn-default" style="margin-left:6px">Open</button>')
        .on("click", () => {
          const dst = row.doc.engagement;
          if (dst) frappe.set_route("Form", "Engagement Case", dst);
        });
      $(el).find(".row-actions").append(row.$custom_open_btn);
    });
  }

  // ---------- hooks ----------
  frappe.ui.form.on("Engagement Case", {
    refresh(frm) {
      if (frm.dashboard && frm.dashboard.clear_headline) frm.dashboard.clear_headline();

      // борды
      if (frm.doc.show_board_crm)      addIndicator(frm, "CRM Board",       frm.doc.status_crm_board, color(C.crm_status, frm.doc.status_crm_board));
      if (frm.doc.show_board_leads)    addIndicator(frm, "Leads – CC",      frm.doc.status_leads,     color(C.crm_status, frm.doc.status_leads));
      if (frm.doc.show_board_deals)    addIndicator(frm, "Deals – CC",      frm.doc.status_deals,     color(C.crm_status, frm.doc.status_deals));
      if (frm.doc.show_board_patients) addIndicator(frm, "Patients – Care", frm.doc.status_patients,  color(C.crm_status, frm.doc.status_patients));

      // прочее
      addIndicator(frm, "Runtime",  frm.doc.runtime_status, color(C.runtime_status, frm.doc.runtime_status));
      addIndicator(frm, "Priority", frm.doc.priority,       color(C.priority,       frm.doc.priority));
      addIndicator(frm, "Channel",  frm.doc.channel_platform, color(C.platform,     frm.doc.channel_platform));
      addIndicator(frm, "Transport",frm.doc.channel_type,   color(C.channel_type,   frm.doc.channel_type));

      if (!frm.is_new()) addLinkExistingButton(frm);
      decorateChildTableActions(frm);

      loadLinkedPreviews(frm);
      loadParentPreviews(frm);
    },

    linked_engagements_add(frm)    { loadLinkedPreviews(frm); loadParentPreviews(frm); },
    linked_engagements_remove(frm) { loadLinkedPreviews(frm); loadParentPreviews(frm); }
  });

  // ---------- styles ----------
  const style = document.createElement("style");
  style.innerHTML = `
  .ec-linked-preview{margin-top:8px;border-top:1px solid #eef2f7;padding-top:6px}
  .ec-parents-preview{margin-top:8px;border-top:1px dashed #e5e7eb;padding-top:6px}
  .ec-linked-header{font-size:12px;color:#6b7280;margin-bottom:4px}
  .ec-card{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;padding:10px;border:1px solid #eef2f7;border-radius:10px;margin-top:8px;transition:background .15s}
  .ec-card:hover{background:#fafafa}
  .ec-card.-parent{border-style:dashed}
  .ec-left{display:flex;gap:10px;align-items:flex-start;min-width:0}
  .ec-avatar{width:28px;height:28px;border-radius:8px;background:#e5e7eb;flex:0 0 auto;overflow:hidden}
  .ec-avatar img{width:100%;height:100%;object-fit:cover;display:block}
  .ec-body{min-width:0}
  .ec-title{font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:flex;align-items:center;gap:6px}
  .ec-badge{-parent}{}
  .ec-badge{font-size:10px;padding:2px 6px;border-radius:999px;border:1px solid #e5e7eb;background:#f3f4f6;color:#374151}
  .ec-badge.-parent{border-color:#c7d2fe;background:#eef2ff}
  .ec-meta{color:#6b7280;font-size:11px;margin-top:2px;display:flex;gap:6px;flex-wrap:wrap}
  .ec-meta.-time .frappe-timestamp{opacity:.9}
  .ec-right{display:flex;align-items:center;gap:6px}
  `;
  document.head.appendChild(style);
})();