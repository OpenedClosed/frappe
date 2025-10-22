/* Dantist Kanban skin — v25.0
   — Labels ON: пустые → "—"; Labels OFF: пустые скрываем
   — Усиленный парсер значений (+ data-* и split по :)
   — Если "Display Name" пуст в DOM — добираем через get_value и подставляем
   — Кнопки действий закреплены; Delete = «убрать с доски» ИЛИ жёстко удалить
   — Карандаш настроек закреплён и не отваливается при переключении досок
*/
(() => {
  const CFG = {
    cssId: "dantist-kanban-skin-css",
    htmlClass: "dantist-kanban-skin",
    rolesSettings: ["AIHub Super Admin", "System Manager"],
    rolesCanColor: ["AIHub Super Admin", "System Manager"],
    rolesColumnMenu:["AIHub Super Admin", "System Manager"],
    settingsBtnId: "dnt-kanban-settings",
    caseDoctype: "Engagement Case",
    // для «убрать с доски» по текущей доске:
    BOARD: {
      "CRM Board":                  { flag: "show_board_crm",      status: "status_crm_board" },
      "Leads – Contact Center":     { flag: "show_board_leads",    status: "status_leads" },
      "Deals – Contact Center":     { flag: "show_board_deals",    status: "status_deals" },
      "Patients – Care Department": { flag: "show_board_patients", status: "status_patients" },
    },
    debug: {
      targetId: "INSTAGRAM_797099196357045", // docname/visible title/external id — любой
      enableStats: true
    }
  };

  /* ===== helpers ===== */
  const isKanbanRoute = () => {
    const r = frappe.get_route?.() || [];
    if (r[0] === "List" && (r[2] === "Kanban" || r[2] === "Kanban Board")) return true;
    return (location.pathname||"").includes("/view/kanban/");
  };
  const userHasAny = (roles) => { try { return roles.some((r)=>frappe.user.has_role(r)); } catch { return false; } };
  const getBoardName = () => {
    try { const r = frappe.get_route(); if (r?.[3]) return decodeURIComponent(r[3]); } catch {}
    try { const seg=(location.pathname||"").split("/").filter(Boolean); if(seg[1]==="kanban"&&seg[3]) return decodeURIComponent(seg[3]); } catch {}
    const h = document.querySelector(".page-head-content .title-text, .page-title .title-text");
    if (h?.textContent?.trim()) return h.textContent.trim();
    return window.cur_list?.kanban_board?.name || window.cur_list?.board?.name || null;
  };
  function stdIcon(name, size="sm") {
    try {
      const html = frappe.utils.icon(name, size);
      const span = document.createElement("span");
      span.innerHTML = html;
      return span.firstElementChild || span;
    } catch {}
    const svg = document.createElementNS("http://www.w3.org/2000/svg","svg");
    svg.setAttribute("class",`icon icon-${size}`);
    const use = document.createElementNS("http://www.w3.org/2000/svg","use");
    use.setAttribute("href",`#icon-${name}`);
    svg.appendChild(use);
    return svg;
  }
  const CLEAN = s => (s||"").replace(/\u00A0/g," ").replace(/\s+/g," ").trim();
  const STRIP_COLON = s => CLEAN(s).replace(/:\s*$/,"");
  const LBL_MATCH = s => STRIP_COLON(s).toLowerCase();
  const isDisplayNameKey = (k) => ["display name","display_name","displayname"].includes(LBL_MATCH(k));
  const getShowLabelsFlag = () => {
    const b = window.cur_list?.board || window.cur_list?.kanban_board;
    return !!(b && (b.show_labels === 1 || b.show_labels === true));
  };

  /* ===== CSS ===== */
  function injectCSS(){
    if(document.getElementById(CFG.cssId)) return;
    const s=document.createElement("style"); s.id=CFG.cssId;
    s.textContent = `
      html.${CFG.htmlClass} .kanban-column{ padding:8px; }
      html.${CFG.htmlClass} .kanban-cards{ display:block !important; }
      html.${CFG.htmlClass} .kanban-card-wrapper{ position:relative; margin:0 !important; }
      html.${CFG.htmlClass} .kanban-cards > .kanban-card-wrapper + .kanban-card-wrapper{ margin-top:8px !important; }
      html.${CFG.htmlClass} .kanban-card{ position:relative; }
      html.${CFG.htmlClass} .kanban-card.content{
        border-radius:14px; border:1px solid var(--border-color,rgba(0,0,0,.06));
        background:#fff; padding:12px; box-shadow:0 1px 2px rgba(0,0,0,.06);
        transition:transform .12s, box-shadow .12s;
        display:flex !important; flex-direction:column; gap:0;
      }
      html.${CFG.htmlClass} .kanban-card.content:hover{ transform:translateY(-1px); box-shadow:0 8px 22px rgba(0,0,0,.08); }
      html.${CFG.htmlClass} .dnt-head{ display:flex; align-items:center; justify-content:space-between; gap:12px; min-width:0; margin-bottom:10px; }
      html.${CFG.htmlClass} .dnt-head-left{ display:flex; align-items:center; gap:10px; min-width:0; flex:1 1 auto; }
      html.${CFG.htmlClass} .kanban-image{
        width:40px !important; height:40px !important; border-radius:10px; overflow:hidden; background:#eef2f7;
        display:flex; align-items:center; justify-content:center; float:none !important; margin:0 !important; flex:0 0 40px; position:static !important;
      }
      html.${CFG.htmlClass} .kanban-image img{ display:block !important; width:100% !important; height:100% !important; max-width:none !important; object-fit:cover !important; object-position:center; }
      html.${CFG.htmlClass} .kanban-title-area{ margin:0 !important; min-width:0; }
      html.${CFG.htmlClass} .kanban-title-area a{ display:none !important; }
      html.${CFG.htmlClass} .dnt-title{ font-weight:600; line-height:1.25; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; cursor:text; }
      html.${CFG.htmlClass} .kanban-card-meta{ margin-left:auto; display:flex; align-items:center; gap:8px; flex-shrink:0; }
      html.${CFG.htmlClass} .kanban-card-doc{ padding:0; }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-kv{ 
        display:flex; align-items:center; gap:6px; 
        background:#f3f4f6; border:1px solid #e5e7eb; border-radius:10px; padding:4px 8px; 
        font-size:12px; min-height:24px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
      }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-kv + .dnt-kv { margin-top:6px; }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-k{ opacity:.7; }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-v{ font-weight:600; min-width:0; overflow:hidden; text-overflow:ellipsis; }
      html.${CFG.htmlClass} .dnt-foot{ margin-top:10px; display:flex; align-items:flex-start; justify-content:space-between; gap:10px; }
      /* плавающие действия — фикс в правом верхнем (как раньше, но без мерцаний) */
      html.${CFG.htmlClass} .dnt-card-actions{ position:absolute; top:12px; right:12px; display:flex; gap:6px; z-index:3; }
      html.${CFG.htmlClass} .dnt-icon-btn{ height:28px; min-width:28px; padding:0 6px; display:grid; place-items:center; border-radius:8px; border:1px solid rgba(0,0,0,.12); background:#f8f9fa; cursor:pointer; }
      html.${CFG.htmlClass} .dnt-icon-btn:hover{ background:#fff; box-shadow:0 2px 8px rgba(0,0,0,.08); }
      html.${CFG.htmlClass}.no-color .column-options .button-group{ display:none !important; }
      html.${CFG.htmlClass}.no-column-menu .kanban-column-header .menu,
      html.${CFG.htmlClass}.no-column-menu .kanban-column-header .dropdown,
      html.${CFG.htmlClass}.no-column-menu .kanban-column-header .kanban-column-actions{ display:none !important; }
    `;
    document.head.appendChild(s);
  }

  /* ===== статистика (минимум логов) ===== */
  const STATS = {
    enabled: !!CFG.debug.enableStats, printed:false,
    totalCards:0, labelsOnCards:0, totalPairs:0,
    displayNameRows:0, displayNameRendered:0, displayNameDashed:0, displayNameMissing:0
  };
  function printStatsOnce(){
    if (!STATS.enabled || STATS.printed) return;
    if (STATS.totalCards === 0) return;
    STATS.printed = true;
    try {
      console.table([{
        totalCards: STATS.totalCards,
        labelsOnCards: STATS.labelsOnCards,
        totalPairs: STATS.totalPairs,
        displayNameRows: STATS.displayNameRows,
        displayNameRendered: STATS.displayNameRendered,
        displayNameDashed: STATS.displayNameDashed,
        displayNameMissing: STATS.displayNameMissing
      }]);
    } catch {}
  }

  /* ===== value extractors ===== */
  function tryParseDataFilter(el){
    const raw = el?.getAttribute?.("data-filter") || "";
    if (!raw) return "";
    try {
      const j = JSON.parse(raw);
      if (Array.isArray(j) && j.length >= 3) return CLEAN(j[2]);
    } catch {}
    const csv = raw.split(",").map(CLEAN).filter(Boolean);
    if (csv.length >= 3) return CLEAN(csv.slice(2).join(","));
    return CLEAN(raw);
  }
  function extractFromAttrs(el){
    if (!el) return "";
    const attrs = ["title","aria-label","data-original-title","data-label","data-value"];
    for (const a of attrs){
      const v = el.getAttribute?.(a);
      if (v && CLEAN(v)) return CLEAN(v);
    }
    const df = tryParseDataFilter(el);
    if (df) return df;
    const img = el.querySelector?.("img[alt]"); if (img && CLEAN(img.alt)) return CLEAN(img.alt);
    const svg = el.querySelector?.("svg[aria-label]"); if (svg){ const v=svg.getAttribute("aria-label"); if (CLEAN(v)) return CLEAN(v); }
    const dv = el.querySelector?.("[data-value]"); if (dv){ const v=dv.getAttribute("data-value"); if (CLEAN(v)) return CLEAN(v); }
    const df2 = el.querySelector?.("[data-filter]"); if (df2){ const v = tryParseDataFilter(df2); if (CLEAN(v)) return CLEAN(v); }
    return "";
  }
  function splitByFirstColon(text){
    const t = CLEAN(text);
    const i = t.indexOf(":");
    if (i === -1) return [t, ""];
    return [CLEAN(t.slice(0,i)), CLEAN(t.slice(i+1))];
  }

  /* ===== сбор k/v из нативной разметки ===== */
  function collectPairsFromNative(docEl){
    const rows = Array.from(docEl.querySelectorAll(":scope > .text-truncate, :scope > .ellipsis"));
    const pairs = [];
    const labelsOn = getShowLabelsFlag();

    rows.forEach(row=>{
      const fullText = row.textContent || "";
      const spans = Array.from(row.querySelectorAll(":scope > span"));
      const tokens = spans.length ? spans.map(s => CLEAN(s.textContent)) : [CLEAN(fullText)];
      const nonEmpty = tokens.filter(Boolean);

      if (!nonEmpty.length && !CLEAN(fullText) && !extractFromAttrs(row)) return;

      if (!labelsOn) {
        let value = STRIP_COLON(nonEmpty[nonEmpty.length - 1] || CLEAN(fullText));
        if (!value) value = CLEAN(row.innerText || "");
        if (!value) value = extractFromAttrs(row);
        if (value) pairs.push({ k:"", v:value, row, tokens, reason:"labels_off" });
        return;
      }

      let label = STRIP_COLON(nonEmpty[0] || "");
      let value = "";
      let reason = "";

      for (let i=1; i<nonEmpty.length; i++){
        const t = STRIP_COLON(nonEmpty[i]);
        if (t && LBL_MATCH(t) !== LBL_MATCH(label)) { value = t; reason = "next_token"; break; }
      }
      if (!value && fullText) {
        const [lbl, tail] = splitByFirstColon(fullText);
        if (LBL_MATCH(lbl)) label = STRIP_COLON(lbl);
        if (tail) { value = tail; reason = "split_fulltext"; }
      }
      if (!value) {
        const it = CLEAN(row.innerText || "");
        if (it){
          const [lbl2, tail2] = splitByFirstColon(it);
          if (LBL_MATCH(lbl2)) { if (tail2){ value = tail2; reason = "split_innerText"; } }
        }
      }
      if (!value) {
        const a = extractFromAttrs(row);
        if (a){ value = a; reason = "attrs_fallback"; }
      }

      const pair = { k: label, v: value || "", row, tokens, reason };
      pairs.push(pair);

      if (STATS.enabled && isDisplayNameKey(label)) STATS.displayNameRows += 1;
    });

    const seen = new Set();
    const out = [];
    for (const o of pairs){
      const key = (o.k || "").toLowerCase();
      if (o.k && seen.has(key)) continue;
      if (o.k) seen.add(key);
      out.push(o);
    }
    return out;
  }

  /* ===== дозагрузка пустых значений из БД (точечно) ===== */
  const gvCache = new Map(); // key: `${doctype}:${name}:${field}`
  async function fetchField(doctype, name, field){
    const key = `${doctype}:${name}:${field}`;
    if (gvCache.has(key)) return gvCache.get(key);
    try{
      const { message } = await frappe.call({
        method: "frappe.client.get_value",
        args: { doctype, filters:{ name }, fieldname: field }
      });
      const val = message?.[field] || "";
      gvCache.set(key, val);
      return val;
    }catch{ gvCache.set(key, ""); return ""; }
  }

  function matchTarget(ctx){
    const wanted = (CFG.debug.targetId || "").trim();
    if (!wanted) return false;
    const s = (x)=> (x||"").trim();
    return (
      s(ctx.docName) === wanted ||
      s(ctx.titleText) === wanted ||
      s(ctx.mongoId) === wanted ||
      s(ctx.externalId) === wanted
    );
  }

  function buildChipsHTML(pairs, ctx){
    const labelsOn = getShowLabelsFlag();
    const frag = document.createDocumentFragment();

    const sawDisplayName = pairs.some(p => isDisplayNameKey(p.k));
    if (STATS.enabled && labelsOn && !sawDisplayName) STATS.displayNameMissing += 1;

    pairs.forEach(o=>{
      const k = o.k || "";
      const v = (o.v || "").trim();
      const hasVal = !!v;
      const isDisplay = isDisplayNameKey(k);

      if (!labelsOn && !hasVal) return;

      const kv = document.createElement("div");
      kv.className = "dnt-kv text-truncate";
      if (k) {
        const sk = document.createElement("span");
        sk.className = "dnt-k";
        sk.textContent = k + ":";
        kv.appendChild(sk);
      }

      const sv = document.createElement("span");
      sv.className = "dnt-v";
      sv.textContent = hasVal ? v : "—";
      kv.appendChild(sv);

      // точечная диагностика — только для целевой карточки и только для Display Name
      if (isDisplay && matchTarget(ctx)) {
        try {
          console.info("[DNT Kanban · DisplayName]", {
            target: CFG.debug.targetId,
            board: getBoardName(),
            showLabels: labelsOn,
            parsed: { label: k, value: hasVal ? v : null, reason: o.reason || null },
            textContent: CLEAN(o.row?.textContent || ""),
            innerText: CLEAN(o.row?.innerText || ""),
            dataValue: o.row?.getAttribute?.("data-value") || null,
            dataFilter: o.row?.getAttribute?.("data-filter") || null,
            deepAttrs: extractFromAttrs(o.row) || null,
            rowHTML: o.row?.outerHTML || null
          });
        } catch {}
      }

      // если это Display Name и значения нет — дозакачиваем из БД и подставляем
      if (isDisplay && !hasVal && ctx?.doctype && ctx?.docName) {
        fetchField(ctx.doctype, ctx.docName, "display_name").then(val=>{
          const finalVal = CLEAN(val);
          if (finalVal) {
            sv.textContent = finalVal;
            if (STATS.enabled){ STATS.displayNameDashed = Math.max(0, STATS.displayNameDashed - 1); STATS.displayNameRendered += 1; }
          }
        });
      }

      if (STATS.enabled && isDisplay) {
        if (hasVal) STATS.displayNameRendered += 1; else STATS.displayNameDashed += 1;
      }

      frag.appendChild(kv);
    });
    return frag;
  }

  function normalizeDocFields(docEl, ctx){
    if (!docEl || docEl.__dnt_locked) return;
    docEl.__dnt_locked = true;

    const pairs = collectPairsFromNative(docEl);
    STATS.totalPairs += pairs.length;

    docEl.innerHTML = "";
    docEl.appendChild(buildChipsHTML(pairs, ctx));

    let raf = null;
    const mo = new MutationObserver((muts)=>{
      for (const m of muts){
        for (const n of m.addedNodes||[]){
          if (n instanceof HTMLElement && !n.classList.contains("dnt-kv")) {
            if (raf) cancelAnimationFrame(raf);
            raf = requestAnimationFrame(()=>{
              docEl.__dnt_locked = false;
              normalizeDocFields(docEl, ctx);
            });
            return;
          }
        }
      }
    });
    mo.observe(docEl, { childList:true });
    docEl.__dnt_mo = mo;
  }

  function upgradeCard(wrapper){
    const card = wrapper?.querySelector?.(".kanban-card.content, .kanban-card");
    if(!card || card.dataset.dntUpgraded==="1") return;

    const body  = card.querySelector(".kanban-card-body") || card;
    const img   = card.querySelector(":scope > .kanban-image, .kanban-image");
    const title = body?.querySelector(".kanban-title-area, .kanban-card-title-area");
    const meta  = body?.querySelector(".kanban-card-meta");
    const doc   = body?.querySelector(".kanban-card-doc");
    if(!body) { card.dataset.dntUpgraded="1"; return; }

    let head = body.querySelector(".dnt-head");
    if(!head){ head = document.createElement("div"); head.className = "dnt-head"; body.prepend(head); }
    let left = head.querySelector(".dnt-head-left");
    if(!left){ left = document.createElement("div"); left.className = "dnt-head-left"; head.prepend(left); }

    if (img && !left.contains(img)) left.prepend(img);
    if (title) {
      title.querySelectorAll("br").forEach(br=>br.remove());
      if(!left.contains(title)) left.appendChild(title);
    }
    if (meta && meta.parentElement !== head) head.appendChild(meta);
    if (doc && doc.previousElementSibling !== head) body.insertBefore(doc, head.nextSibling);

    const name = wrapper.getAttribute("data-name") || wrapper.dataset.name || card.getAttribute("data-name") || "";
    const titleText = CLEAN(title?.textContent || "");
    const doctype = window.cur_list?.doctype || window.cur_list?.board?.reference_doctype || CFG.caseDoctype;

    if (doc) {
      STATS.totalCards += 1;
      if (getShowLabelsFlag()) STATS.labelsOnCards += 1;

      // для диагностики цели
      let externalId = "", mongoId = "";
      const rawRows = Array.from(doc.querySelectorAll(":scope > .text-truncate, :scope > .ellipsis"));
      rawRows.forEach(r=>{
        const t = CLEAN(r.textContent || "");
        if (!externalId && /external user id/i.test(t)) externalId = t.split(":").slice(1).join(":").trim();
        if (!mongoId && /(mongo (client )?id)/i.test(t)) mongoId = t.split(":").slice(1).join(":").trim();
        if (!externalId) externalId = r.getAttribute("data-external-id") || "";
        if (!mongoId) mongoId = r.getAttribute("data-mongo-id") || "";
      });

      normalizeDocFields(doc, { doctype, docName: name, titleText, externalId, mongoId });
    }

    let foot = body.querySelector(".dnt-foot");
    if(!foot){ foot = document.createElement("div"); foot.className = "dnt-foot"; body.appendChild(foot); }
    const assign = (meta || body).querySelector(".kanban-assignments");
    const like   = (meta || body).querySelector(".like-action");
    if(assign && !foot.contains(assign)) foot.appendChild(assign);
    if(like   && !foot.contains(like))   foot.appendChild(like);
    if(meta && !meta.children.length) meta.remove();

    // плавающие действия
    if (!wrapper.querySelector(".dnt-card-actions")){
      const row = document.createElement("div"); row.className="dnt-card-actions";
      const bOpen = document.createElement("div"); bOpen.className="dnt-icon-btn"; bOpen.title=__("Open");
      bOpen.appendChild(stdIcon("external-link","sm"));
      bOpen.addEventListener("click",(e)=>{ e.stopPropagation(); if (doctype && name) frappe.set_route("Form", doctype, name); });
      row.appendChild(bOpen);

      const bDel = document.createElement("div"); bDel.className="dnt-icon-btn"; bDel.title=__("Delete / Remove from board");
      bDel.appendChild(stdIcon("delete","sm"));
      bDel.addEventListener("click",(e)=>{
        e.stopPropagation();
        const board = CFG.BOARD[getBoardName()];
        const canSoft = !!(board && board.flag);
        const d = new frappe.ui.Dialog({
          title: __("Card actions"),
          primary_action_label: canSoft ? __("Remove from this board") : __("Delete"),
          primary_action: ()=> {
            if (canSoft) {
              // мягко убираем с текущей доски
              frappe.call({ method:"frappe.client.set_value", args:{ doctype, name, fieldname: board.flag, value: 0 } })
                .then(()=>{ frappe.show_alert(__("Removed from board")); try{window.cur_list?.refresh();}catch{}; d.hide(); });
            } else {
              // жёсткое удаление
              frappe.call({ method:"frappe.client.delete", args:{ doctype, name } })
                .then(()=>{ frappe.show_alert(__("Deleted")); try{window.cur_list?.refresh();}catch{}; d.hide(); });
            }
          }
        });
        if (canSoft){
          d.set_secondary_action_label(__("Delete document"));
          d.set_secondary_action(()=> {
            frappe.confirm(__("Delete this document?"),()=>{
              frappe.call({ method:"frappe.client.delete", args:{ doctype, name } })
                .then(()=>{ frappe.show_alert(__("Deleted")); try{window.cur_list?.refresh();}catch{}; d.hide(); });
            });
          });
        }
        d.show();
      });
      row.appendChild(bDel);
      wrapper.appendChild(row);
    }

    card.dataset.dntUpgraded = "1";
  }

  function enhanceCards(){
    document.querySelectorAll(".kanban-card-wrapper, .kanban-column .kanban-card:not(.content)").forEach(w => {
      const wrap = w.classList.contains?.("kanban-card") ? w.closest(".kanban-card-wrapper") || w : w;
      upgradeCard(wrap);
    });
  }

  /* ===== settings button (sticky) ===== */
  function findSettingsAnchor(){
    return (
      document.querySelector(".page-actions .page-icon-group") ||
      document.querySelector(".standard-actions .page-icon-group") ||
      document.querySelector(".page-actions") ||
      document.querySelector(".standard-actions") ||
      document.querySelector(".page-head-content") ||
      document.querySelector(".page-title")
    );
  }
  function injectSettingsBtn(){
    document.querySelectorAll(`#${CFG.settingsBtnId}`).forEach(el => el.remove());
    if(!isKanbanRoute() || !userHasAny(CFG.rolesSettings)) return;
    const anchor = findSettingsAnchor();
    if(!anchor) return;

    const btn=document.createElement("button");
    btn.id=CFG.settingsBtnId; btn.className="btn btn-default icon-btn";
    btn.setAttribute("title", __("Kanban settings"));
    btn.appendChild(stdIcon("edit","sm"));
    btn.addEventListener("click",()=> {
      const bname = getBoardName();
      if (bname) frappe.set_route(`/app/kanban-board/${encodeURIComponent(bname)}`);
    });

    (document.querySelector(".page-icon-group") || anchor).insertAdjacentElement("beforeend", btn);
  }
  function ensureSettingsBtnSticky(){
    let tries=0, max=120;
    const tick=()=>{ if(!isKanbanRoute()) return;
      injectSettingsBtn();
      tries+=1;
      if (document.getElementById(CFG.settingsBtnId)) return;
      if (tries<max) setTimeout(tick, 50);
    };
    tick();

    const head = document.querySelector(".page-head-content") || document.querySelector(".page-title") || document.body;
    try{
      const mo = new MutationObserver(()=> {
        if (!isKanbanRoute()) return;
        if (!document.getElementById(CFG.settingsBtnId)) injectSettingsBtn();
      });
      mo.observe(head, { childList:true, subtree:true });
      window.__dntKanbanHeadMO = mo;
    }catch{}

    if (window.__dntSettingsInt) clearInterval(window.__dntSettingsInt);
    window.__dntSettingsInt = setInterval(()=>{
      if (!isKanbanRoute()) return;
      if (!document.getElementById(CFG.settingsBtnId)) injectSettingsBtn();
    }, 800);
    setTimeout(()=> clearInterval(window.__dntSettingsInt), 30_000);
  }

  /* ===== boot ===== */
  function run(){
    Object.assign(STATS, { printed:false, totalCards:0, labelsOnCards:0, totalPairs:0, displayNameRows:0, displayNameRendered:0, displayNameDashed:0, displayNameMissing:0 });

    if(!isKanbanRoute()){
      document.documentElement.classList.remove(CFG.htmlClass,"no-color","no-column-menu");
      document.querySelectorAll(`#${CFG.settingsBtnId}`).forEach(el => el.remove());
      return;
    }
    injectCSS();
    document.documentElement.classList.add(CFG.htmlClass);

    const allowColor = userHasAny(CFG.rolesCanColor);
    const allowMenu  = userHasAny(CFG.rolesColumnMenu);
    document.documentElement.classList.toggle("no-color", !allowColor);
    document.documentElement.classList.toggle("no-column-menu", !allowMenu);

    enhanceCards();
    ensureSettingsBtnSticky();

    let attempts = 0;
    const pump = () => {
      if (!isKanbanRoute()) return;
      attempts += 1;
      enhanceCards();
      if (attempts < 30) setTimeout(pump, 60);
      else setTimeout(printStatsOnce, 0);
    };
    pump();

    if (window.__dntKanbanMO) window.__dntKanbanMO.disconnect();
    const mo = new MutationObserver(()=>{ if(isKanbanRoute()) { enhanceCards(); printStatsOnce(); } });
    mo.observe(document.body||document.documentElement,{ childList:true, subtree:true });
    window.__dntKanbanMO = mo;
  }

  if (frappe?.after_ajax) frappe.after_ajax(run); else document.addEventListener("DOMContentLoaded", run);
  window.addEventListener("load", run);
  frappe?.router?.on && frappe.router.on("change", run);
})();