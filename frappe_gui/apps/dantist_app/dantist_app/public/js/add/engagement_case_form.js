// === FILE 1 (final, patched) ===
// Engagement Case — Form UX (i18n + Kanban colors + one-line header chips + dark-ready)
// Ничего не ломаем, только нейтральные цвета и мелкие правки отображения.

(function () {
  const DOCTYPE = "Engagement Case";
  const esc = frappe.utils.escape_html;

  // ---------- LS ----------
  const LS = {
    get(key, def = null) { try { const v = localStorage.getItem(key); return v === null ? def : v; } catch { return def; } },
    set(key, val) { try { localStorage.setItem(key, String(val)); } catch {} },
  };
  const WORKFLOW_LS_KEY = "ec_workflow_collapsed";

  // --- Boards meta ---
  const BOARDS = [
    { name: "CRM Board",                  flag: "show_board_crm",      fields: ["status_crm_board","crm_status"], color: "#2563eb" },
    { name: "Leads – Contact Center",     flag: "show_board_leads",    fields: ["status_leads"],                    color: "#16a34a" },
    { name: "Deals – Contact Center",     flag: "show_board_deals",    fields: ["status_deals"],                    color: "#ea580c" },
    { name: "Patients – Care Department", flag: "show_board_patients", fields: ["status_patients"],                 color: "#9333ea" },
  ];

  // ---------- Route-scoped cleanup ----------
  function isOnThisForm() {
    try { const r = frappe.get_route ? frappe.get_route() : []; return r && r[0] === "Form" && r[1] === DOCTYPE; }
    catch { return false; }
  }
  function clearBadgesEverywhere() {
    document.querySelectorAll(".ec-title-badges").forEach(n => n.remove());
    document.querySelectorAll(".ec-title-layout").forEach(n => n.classList.remove("ec-title-layout"));
    document.querySelectorAll(".ec-suppress-title-indicator").forEach(n => n.classList.remove("ec-suppress-title-indicator"));
  }
  try { if (frappe.router?.on) frappe.router.on("change", () => { if (!isOnThisForm()) clearBadgesEverywhere(); }); } catch {}
  window.addEventListener("hashchange", () => { if (!isOnThisForm()) clearBadgesEverywhere(); });

  // ---------- Colors (Kanban) ----------
  async function ensureAllBoardColors() {
    if (typeof window.getBoardColors === "function") {
      await Promise.all(BOARDS.map(b => window.getBoardColors(b.name)));
    }
  }
  function colorMetaFor(board, status) {
    const map = (window.EC_BOARD_COLORS && window.EC_BOARD_COLORS[board]) || {};
    const key = status || "";
    const v = map[key] ?? map[key?.toLowerCase?.()] ?? null;
    if (!v) return { bd: "#2563eb" };
    if (typeof v === "string") return { bd: v };
    const bd = v.bd || v.bg || v.tx || "#2563eb";
    const bg = v.bg || null;
    const tx = v.tx || null;
    return { bd, bg, tx };
  }
  function rgba(hex, a){
    const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex||"");
    if (!m) return `rgba(37,99,235,${a})`;
    const r=parseInt(m[1],16), g=parseInt(m[2],16), b=parseInt(m[3],16);
    return `rgba(${r},${g},${b},${a})`;
  }

  // ---------- Chips (переводимый текст; lookup цвета — по raw status) ----------
  const TEXT_DARK = "var(--text-color,#111827)"; // контрастный текст — читабелен и в дарке, и в лайте

  // Аккуратная замена текста внутри готового HTML чипа (не трогаем иконки/атрибуты)
  function translateValueInChipHTML(html, rawVal) {
    const disp = __(String(rawVal)) || String(rawVal);
    try {
      const tmp = document.createElement("div");
      tmp.innerHTML = html || "";
      const root = tmp.firstElementChild || tmp;

      // если есть явный контейнер чипа — работаем в нём
      const scope = root.querySelector?.(".crm-chip") || root;

      // пройтись по всем текстовым узлам и заменить точные совпадения
      const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, null);
      const texts = [];
      while (walker.nextNode()) texts.push(walker.currentNode);

      const raw = String(rawVal).trim();
      texts.forEach(node => {
        const curTrim = node.nodeValue.trim();
        if (!curTrim) return;

        if (curTrim === raw) {
          node.nodeValue = node.nodeValue.replace(raw, disp);
        } else {
          const re = new RegExp(`\\b${raw.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "g");
          if (re.test(node.nodeValue)) node.nodeValue = node.nodeValue.replace(re, disp);
        }
      });

      return (root.outerHTML || tmp.innerHTML || html);
    } catch {
      // Фолбэк: простой чип
      return `<span class="crm-chip">${esc(disp)}</span>`;
    }
  }

  function chipTag(bucket, val, dashed=false){
    if (!val) return "";
    if (typeof window.tagChip === "function") {
      const html = window.tagChip(bucket, String(val), dashed);
      return translateValueInChipHTML(html, val);
    }
    return `<span class="crm-chip${dashed?" -dashed":""}">${esc(__(String(val)))}</span>`;
  }

  function chipBoard(boardName, rawStatus, dashed=false){
    if (!rawStatus) return "";
    const { bd } = colorMetaFor(boardName, rawStatus);
    if (dashed) {
      const st = `border-color:${bd};border-style:dashed;background:transparent;color:${TEXT_DARK}`;
      return `<span class="crm-chip" style="${st}">${esc(__(rawStatus))}</span>`;
    }
    const st = `background:${rgba(bd,.15)};border-color:${rgba(bd,.25)};color:${TEXT_DARK}`;
    return `<span class="crm-chip" style="${st}">${esc(__(rawStatus))}</span>`;
  }

  const timeChip  = (lbl, dt)=> dt ? `<span class="crm-chip -ghost"><span class="lbl">${esc(__(lbl))}:</span> ${frappe.datetime.comment_when(dt)}</span>` : "";
  const sepChip   = `<span class="crm-vsep" aria-hidden="true"></span>`;
  const fullPath  = (p)=> p ? (p.startsWith("/") ? p : `/${p}`) : "";
  const pickAvatar = (row) => fullPath(row.avatar || "/assets/dantist_app/files/egg.png");

  // ---------- Hidden mark ----------
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

  // ---------- CSS ----------
  const CSS_ID = "ec-form-ux-css";
  function ensureCss() {
    if (document.getElementById(CSS_ID)) return;
    const s = document.createElement("style");
    s.id = CSS_ID;
    s.textContent = `
    /* === Engagement Case Form UX === */
    .ec-suppress-title-indicator .page-head .indicator-pill { display:none !important; }
    .ec-title-layout .page-head .title-area { display:flex; align-items:center; gap:8px; flex-wrap:nowrap; }
    .ec-title-layout .page-head .title-area .title-text{ display:flex; align-items:center; gap:8px; min-width:0; }
    .ec-title-badges{ display:flex; gap:6px; flex-wrap:nowrap; white-space:nowrap; margin-left:8px; overflow:hidden; }
    .ec-title-badges .crm-chip{ white-space:nowrap; }

    .form-dashboard .ec-progress-section .section-head{
      font-weight:600;padding:8px 12px;
      border-bottom:1px solid var(--border-color,#e5e7eb);
      display:flex; align-items:center; gap:6px; cursor:pointer;
      color:var(--text-color,#111827);
    }
    .form-dashboard .ec-progress-section .section-body{ padding:12px; }

    .ec-pipes{ display:flex; flex-direction:column; gap:12px; }
    .ec-pipe{ border:1px solid var(--border-color,#e5e7eb); border-radius:10px; padding:10px;
      background:var(--card-bg,#fff); transition:background .15s ease,border-color .15s ease; }
    .ec-pipe.-disabled{ opacity:.9; }
    .ec-pipe .head{ display:flex; align-items:center; gap:8px; margin-bottom:8px; justify-content:space-between; }
    .ec-pipe .head .l{display:flex;align-items:center;gap:8px}
    .ec-pipe .dot{ width:10px; height:10px; border-radius:50%; flex:0 0 10px; }
    .ec-pipe .title{ font-weight:600; }

    .ec-steps{ display:flex; gap:6px; align-items:center; }
    .ec-step{ position:relative; flex:1; height:10px; border-radius:999px; cursor:pointer;
      background:var(--control-bg,#eef2f7); outline:1px solid rgba(0,0,0,.03);
      transition: transform .12s ease, box-shadow .12s ease, opacity .12s ease;
    }
    .ec-step.-past{ opacity:.95 }
    .ec-step.-current{ transform: translateY(-1px); box-shadow: 0 1px 4px rgba(0,0,0,.08); }
    .ec-step.-future{ opacity:.6 }
    .ec-step.-disabled { background: transparent !important; border:1px dashed var(--border-color,#d1d5db); outline:none; cursor:default; }
    .ec-step:hover{ box-shadow: 0 1px 6px rgba(0,0,0,.12); }

    .ec-names{ display:flex; gap:6px; margin-top:4px; font-size:11px; color:var(--text-muted,#6b7280); }
    .ec-name{ flex:1; text-align:center; white-space:nowrap; overflow:hidden; text-overflow:ellipsis }
    .ec-name.-current{ color:var(--text-color,#111827); font-weight:600; }
    .ec-names.-disabled .ec-name{ color:#9ca3af; }

    .crm-chip{font-size:10px;padding:2px 6px;border-radius:999px;
      border:1px solid var(--border-color,#e5e7eb);
      background:var(--control-bg,#f8fafc);color:var(--text-color,#111827);}
    .crm-chip.-ghost{background:var(--control-bg,#f8fafc)}
    .crm-chip.-dashed{border-style:dashed;background:transparent}
    .crm-vsep{display:inline-block;width:0;border-left:1px dashed var(--border-color,#d1d5db);margin:0 6px;align-self:stretch}

    .ec-linked-preview{margin-top:8px;border-top:1px solid var(--border-color,#eef2f7);padding-top:6px}
    .ec-parents-preview{margin-top:8px;border-top:1px dashed var(--border-color,#e5e7eb);padding-top:6px}
    .ec-linked-header{font-size:12px;color:var(--text-muted,#6b7280);margin-bottom:4px;display:flex;align-items:center;justify-content:space-between}
    .ec-card{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;padding:10px;border:1px solid var(--border-color,#eef2f7);border-radius:10px;margin-top:8px;transition:background .15s}
    .ec-card:hover{background:var(--fg-hover-color,#fafafa)}
    .ec-card.-parent{border-style:dashed}
    .ec-left{display:flex;gap:10px;align-items:flex-start;min-width:0}
    .ec-avatar{width:28px;height:28px;border-radius:8px;background:var(--bg-light-gray,#e5e7eb);flex:0 0 auto;overflow:hidden}
    .ec-avatar img{width:100%;height:100%;object-fit:cover;display:block}
    .ec-body{min-width:0}
    .ec-title{font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:flex;align-items:center;gap:6px;color:var(--text-color,#111827)}
    .ec-meta{color:var(--text-muted,#6b7280);font-size:11px;margin-top:2px;display:flex;gap:8px;flex-wrap:wrap;max-width:100%}
    .ec-meta.-time .frappe-timestamp{opacity:.9}
    .ec-right{display:flex;align-items:center;gap:6px}

    .ec-grid-hidden .control-label,
    .ec-grid-hidden .grid-description,
    .ec-grid-hidden .grid-custom-buttons,
    .ec-grid-hidden .form-grid-container,
    .ec-grid-hidden .grid-heading-row,
    .ec-grid-hidden .grid-footer { display:none !important; }

    /* Темная тема — мягкие подложки */
    [data-theme="dark"] .ec-pipe{background:var(--card-bg,#1d2f33);}
    [data-theme="dark"] .ec-step{background:var(--control-bg,#243a3f);outline:none;}
    [data-theme="dark"] .ec-card{background:var(--card-bg,#1d2f33);border-color:var(--border-color,#3e555a);}
    [data-theme="dark"] .ec-card:hover{background:var(--fg-hover-color,#2b4349);}
    `;
    document.head.appendChild(s);
  }

  // ---------- helpers ----------
  function pageWrap(frm) { return frm?.page?.wrapper && frm.page.wrapper[0] || null; }
  function suppressTitleIndicator(frm, on) {
    const root = pageWrap(frm);
    if (!root) return;
    root.classList.toggle("ec-suppress-title-indicator", !!on);
    root.classList.toggle("ec-title-layout", !!on); // наш layout заголовка (одна строка)
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

  // ---------- collapsible ----------
  function wireCollapsible(sec, lsKey, defCollapsed=false){
    if (!sec) return;
    const head = sec.querySelector(".section-head");
    const body = sec.querySelector(".section-body");
    if (!head || !body) return;

    if (!head.querySelector(".collapse-indicator")){
      const ind = document.createElement("span");
      ind.className = "ml-2 collapse-indicator mb-1";
      ind.setAttribute("tabindex","0");
      ind.innerHTML = `<svg class="es-icon es-line icon-sm" aria-hidden="true"><use href="#es-line-down"></use></svg>`;
      head.appendChild(ind);
    }

    const apply = (collapsed) => {
      head.classList.toggle("collapsed", collapsed);
      body.classList.toggle("hide", collapsed);
      LS.set(lsKey, collapsed ? "1" : "0");
    };

    const ls = LS.get(lsKey, defCollapsed ? "1" : "0");
    apply(ls === "1");

    const toggle = (e) => {
      if (e && e.type === "keydown" && e.key !== "Enter" && e.key !== " ") return;
      const now = !head.classList.contains("collapsed");
      apply(now);
    };

    if (!head.__ecBound){
      head.addEventListener("click", toggle);
      head.addEventListener("keydown", toggle);
      head.__ecBound = true;
    }
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
      head.textContent = __(title);

      const body = document.createElement("div");
      body.className = "section-body";

      row.appendChild(head); row.appendChild(body);
      dash.insertBefore(row, dash.firstChild);
      sec = row;
    }
    wireCollapsible(sec, WORKFLOW_LS_KEY, false);
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
      div.style.background = i <= currentIdx ? (rgba(color,.2)) : "var(--control-bg,#eef2f7)";
      div.addEventListener("click", () => frm.set_value(fieldname, label));
    } else {
      div.classList.add("-disabled");
      div.style.background = "transparent";
      div.style.border = "1px dashed var(--border-color,#d1d5db)";
      div.style.cursor = "default";
    }
    div.title = __(label);
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
    const left = document.createElement("div");
    left.className = "l";
    const dot = document.createElement("span");
    dot.className = "dot"; dot.style.background = board.color;
    const ttl = document.createElement("div");
    ttl.className = "title"; ttl.textContent = __(board.name);
    left.appendChild(dot); left.appendChild(ttl);

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-xs btn-default ec-open-kanban";
    btn.textContent = __("Open Kanban");
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
      n.title = __(lbl); n.textContent = __(lbl);
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

    wireCollapsible(sec, WORKFLOW_LS_KEY, false);
  }

  // ---------- Title badges ----------
  async function updateTitleBadges(frm){
    if (!isOnThisForm()) return;

    const root = pageWrap(frm);
    if (!root) return;
    root.classList.add("ec-title-layout");
    root.classList.add("ec-suppress-title-indicator");

    const titleArea = root.querySelector(".page-head .title-area");
    const titleText = titleArea?.querySelector(".title-text");
    if (!titleArea || !titleText) return;

    // убрать прошлые
    titleArea.querySelectorAll(".ec-title-badges").forEach(n => n.remove());

    // вставляем СЛЕДОМ за .title-text — одна линия, без overlay
    const wrap = document.createElement("div");
    wrap.className = "ec-title-badges";
    titleText.insertAdjacentElement("afterend", wrap);

    const chips=[];
    for (const b of BOARDS){
      const fieldname = findFirstExistingField(frm, b.fields);
      const st = fieldname ? frm.doc[fieldname] : null;
      if (!st) continue;
      const dashed = !frm.doc[b.flag];
      chips.push(chipBoard(b.name, st, dashed));
    }
    const hidden = await isCurrentHidden(frm.doc.name);
    wrap.innerHTML = chips.join("") + (hidden ? sepChip + chipTag("badge", "Hidden", false) : "");
  }

  // ---------- Linked UI ----------
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
          ${esc(__("Linked engagements"))}
          <span class="ec-actions">
            <button class="btn btn-xs btn-default" data-ec-act="search-link">${esc(__("Search & Link"))}</button>
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
      `<button class="btn btn-xs btn-default" data-act="open"   data-name="${esc(row.name)}">${esc(__("Open"))}</button>`,
      opts.show_unlink   ? `<button class="btn btn-xs btn-danger"  data-act="unlink" data-name="${esc(row.name)}">${esc(__("Unlink"))}</button>` : "",
      opts.can_edit_link ? `<button class="btn btn-xs btn-primary" data-act="edit-link" data-name="${esc(row.name)}" title="${esc(__("Edit link row"))}">✎</button>` : ""
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
      bits.forEach((el,i) => el.style.display = prevDisplay[i] ?? "");
      if (wasHidden) wrap.classList.add("ec-grid-hidden");
    };

    return { shown:true, wrap, cleanup };
  }

  async function loadLinkedPreviews(frm) {
    const listWrap = ensureLinkedContainer(frm);
    if (!listWrap) return;
    listWrap.innerHTML = `<div class="text-muted small">${esc(__("Loading…"))}</div>`;

    const linkRows = (frm.doc.linked_engagements || []).filter(r => r.engagement);
    const names = linkRows.map(r => r.engagement);
    const hiddenByName = {};
    linkRows.forEach(r => { hiddenByName[r.engagement] = !!r.hide_in_lists; });

    if (!names.length) { listWrap.innerHTML = `<div class="text-muted small">${esc(__("No linked engagements yet."))}</div>`; return; }

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
      })).join("") || `<div class="text-muted small">${esc(__("No data."))}</div>`;

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
                frappe.show_alert({ message: `${esc(__("Unlinked"))} ${esc(name)}`, indicator: "orange" });
              }
            });
          } else if (act === "edit-link") {
            openLinkRowEditor(frm, name);
          }
        });
      });
    } catch (e) {
      console.error(e);
      listWrap.innerHTML = `<div class="text-danger small">${esc(__("Failed to load linked previews."))}</div>`;
    }
  }

  function ensureParentsContainer(frm) {
    const fld = frm.get_field("linked_engagements");
    if (!fld?.wrapper) return null;
    let wrap = fld.wrapper.querySelector(".ec-parents-preview");
    if (!wrap) {
      const div = document.createElement("div");
      div.className = "ec-parents-preview";
      div.innerHTML = `<div class="ec-linked-header">${esc(__("Parents (where this case is linked)"))}</div><div class="ec-parents-list"></div>`;
      fld.wrapper.appendChild(div);
      wrap = div;
    }
    return wrap.querySelector(".ec-parents-list");
  }

  async function loadParentPreviews(frm) {
    const listWrap = ensureParentsContainer(frm);
    if (!listWrap || frm.is_new()) { if (listWrap) listWrap.innerHTML = ""; return; }
    listWrap.innerHTML = `<div class="text-muted small">${esc(__("Loading…"))}</div>`;
    try {
      const { message: rows = [] } = await frappe.call({
        method: "dantist_app.api.engagement.handlers.parents_of_engagement",
        args: { name: frm.doc.name }
      });
      listWrap.innerHTML = (rows||[]).map(r => renderMiniCard(r, { is_parent:true })).join("") || `<div class="text-muted small">${esc(__("No parents."))}</div>`;
      listWrap.querySelectorAll("[data-act='open']").forEach(btn =>
        btn.addEventListener("click", ()=> frappe.set_route("Form", DOCTYPE, btn.getAttribute("data-name")))
      );
    } catch (e) {
      console.error(e);
      listWrap.innerHTML = `<div class="text-danger small">${esc(__("Failed to load parent previews."))}</div>`;
    }
  }

  // ---------- Row editor ----------
  function openLinkRowEditor(frm, engagementName) {
    const grid = frm.get_field("linked_engagements")?.grid;
    if (!grid) return;

    const rowDoc = (frm.doc.linked_engagements || []).find(r => r.engagement === engagementName);
    if (!rowDoc) return;

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

        rowEl?.querySelector(".grid-row-close")?.addEventListener("click", () => { setTimeout(cleanup, 40); }, { once: true });

        if (rowEl) {
          const mo = new MutationObserver(() => {
            if (!rowEl.classList.contains("grid-row-open")) {
              mo.disconnect();
              setTimeout(cleanup, 10);
            }
          });
          mo.observe(rowEl, { attributes: true, attributeFilter: ["class"] });
        }
        setTimeout(cleanup, 120000);
      } catch (_) {
        setTimeout(ensureVisible.cleanup, 3000);
      }
    };

    const openInline = () => {
      try {
        const gRow = getGridRow();
        if (!gRow) return false;
        if (typeof gRow.open_form === "function") {
          gRow.open_form();
        } else if (typeof gRow.toggle_view === "function") {
          gRow.toggle_view(true);
        } else {
          return false;
        }
        try {
          const el = grid.wrapper && grid.wrapper[0] && grid.wrapper[0].querySelector(`.grid-row[data-name="${rowDoc.name}"]`);
          el?.scrollIntoView({ behavior: "smooth", block: "center" });
        } catch (_){}
        attachAutoHide();
        return true;
      } catch { return false; }
    };

    try { grid.refresh?.(); } catch (_) {}

    if (typeof grid.edit_row === "function") {
      grid.edit_row(rowDoc.name); setTimeout(ensureVisible.cleanup, 10); return;
    }
    if (typeof grid.open_grid_row === "function") {
      grid.open_grid_row(rowDoc.name); setTimeout(ensureVisible.cleanup, 10); return;
    }
    if (openInline()) return;

    setTimeout(() => {
      try { grid.refresh?.(); } catch (_) {}
      if (typeof grid.edit_row === "function") { grid.edit_row(rowDoc.name); setTimeout(ensureVisible.cleanup, 10); return; }
      if (typeof grid.open_grid_row === "function") { grid.open_grid_row(rowDoc.name); setTimeout(ensureVisible.cleanup, 10); return; }
      if (openInline()) return;
      ensureVisible.cleanup();
    }, 40);
  }

  // ---------- Search & Link ----------
  function addLinkExistingDialog(frm) {
    const already = new Set((frm.doc.linked_engagements || []).map(r => r.engagement).filter(Boolean));

    const d = new frappe.ui.Dialog({
      title: __("Link existing case"),
      fields: [
        { fieldtype: "Data", fieldname: "q", label: __("Search"), description: __("name, title, display name, phone, email") },
        { fieldtype: "Section Break" },
        { fieldtype: "HTML", fieldname: "results" },
      ],
      primary_action_label: __("Close"),
      primary_action() { d.hide(); }
    });
    const $res = ()=> d.get_field("results").$wrapper;

    async function runSearch() {
      const q = (d.get_value("q") || "").trim();
      $res().html(`<div class="text-muted small">${esc(__("Searching…"))}</div>`);
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
        if (!filtered.length) { $res().html(`<div class="text-muted small">${esc(__("Nothing found"))}</div>`); return; }

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
                <button class="btn btn-xs btn-default" data-act="open" data-name="${esc(r.name)}">${esc(__("Open"))}</button>
                <button class="btn btn-xs btn-primary" data-act="link" data-name="${esc(r.name)}">${esc(__("Link"))}</button>
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
            frappe.show_alert({ message: `${esc(__("Linked"))} ${esc(name)}`, indicator: "green" });
          }
        });
      } catch (e) {
        console.error(e);
        $res().html(`<div class="text-danger small">${esc(__("Search failed"))}</div>`);
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
      await ensureAllBoardColors();
      suppressTitleIndicator(frm, true);
      await updateTitleBadges(frm);
      renderProgress(frm);
      hideLinkedGrid(frm);
      loadLinkedPreviews(frm);
      loadParentPreviews(frm);
    },
    async refresh(frm) {
      ensureCss();
      await ensureAllBoardColors();
      suppressTitleIndicator(frm, true);
      await updateTitleBadges(frm);
      renderProgress(frm);
      hideLinkedGrid(frm);
      loadLinkedPreviews(frm);
      loadParentPreviews(frm);

      requestAnimationFrame(renderProgress.bind(null, frm));
      setTimeout(renderProgress.bind(null, frm), 60);
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

    on_close(frm){
      suppressTitleIndicator(frm, false);
      clearBadgesEverywhere();
    }
  });

})();