/* Dantist Kanban skin — v25.18.12 • Compact + char-budget (tighter) + assignees in compact + safe avatar fit */
(() => {
  if (window.__DNT_KANBAN_SKIN_LOCK) return;
  window.__DNT_KANBAN_SKIN_LOCK = true;

  const CFG = {
    cssId: "dantist-kanban-skin-css",
    htmlClass: "dantist-kanban-skin",
    rolesSettings: ["AIHub Super Admin", "System Manager"],
    rolesCanColor: ["AIHub Super Admin", "System Manager"],
    rolesColumnMenu:["AIHub Super Admin", "System Manager"],
    settingsBtnId: "dnt-kanban-settings",

    // === Compact mode ===
    compactBtnId: "dnt-kanban-compact",
    compactDefault: true,
    compactTitleClamp: 24,        // было 28 → ещё компактнее
    compactFieldClamp: 18,        // для legacy кейсов без label
    compactMaxFields: 4,

    // === Единый символьный бюджет (ужат) ===
    pairClamp: 36,                // было 40 → −4 символа
    taskLineBudget: 36,           // было 40 → −4 символа

    caseDoctype: "Engagement Case",
    tasksMethod: "dantist_app.api.tasks.handlers.ec_tasks_for_case",
    tasksLimit: 5,
    BOARD: {
      "CRM Board":                  { flag: "show_board_crm",      status: "status_crm_board" },
      "Leads – Contact Center":     { flag: "show_board_leads",    status: "status_leads" },
      "Deals – Contact Center":     { flag: "show_board_deals",    status: "status_deals" },
      "Patients – Care Department": { flag: "show_board_patients", status: "status_patients" },
    }
  };

  // Позволяем быстро переопределить бюджет через глобалки (по желанию)
  if (!Number.isNaN(+window.DNT_KANBAN_PAIR_CLAMP)) CFG.pairClamp = +window.DNT_KANBAN_PAIR_CLAMP;
  if (!Number.isNaN(+window.DNT_KANBAN_TASK_BUDGET)) CFG.taskLineBudget = +window.DNT_KANBAN_TASK_BUDGET;
  if (!Number.isNaN(+window.DNT_KANBAN_TITLE_CLAMP)) CFG.compactTitleClamp = +window.DNT_KANBAN_TITLE_CLAMP;

  const ICONS = {
    compactOn:
      '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h10M4 17h7"/></svg>',
    compactOff:
      '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M7 9h10M7 13h10M7 17h6"/></svg>',
  };

  async function ensure_messages(timeout_ms = 2000) {
    const start = Date.now();
    while (Date.now() - start < timeout_ms) {
      if (typeof __ === "function") return true;
      if (frappe && frappe._messages && Object.keys(frappe._messages).length) return true;
      await new Promise(r => setTimeout(r, 50));
    }
    return false;
  }
  const t = (s) => {
    if (typeof __ === "function") return __(s);
    const dict = (frappe && frappe._messages) ? frappe._messages : null;
    return (dict && typeof dict[s] === "string" && dict[s].length) ? dict[s] : s;
  };
  const CLEAN = s => (s||"").replace(/\u00A0/g," ").replace(/\s+/g," ").trim();
  const STRIP_COLON = s => CLEAN(s).replace(/:\s*$/,"");
  const LBL_KEY = s => STRIP_COLON(s).toLowerCase();
  const userHasAny = (roles) => { try { return roles.some((r)=>frappe.user.has_role(r)); } catch { return false; } };
  const isKanbanRoute = () => {
    const r = frappe.get_route?.() || [];
    if (r[0] === "List" && (r[2] === "Kanban" || r[2] === "Kanban Board")) return true;
    return (location.pathname||"").includes("/view/kanban/");
  };
  const getShowLabelsFlag = () => {
    const b = window.cur_list?.board || window.cur_list?.kanban_board;
    return !!(b && (b.show_labels === 1 || b.show_labels === true));
  };
  const getBoardName = () => {
    try {
      const r = frappe.get_route?.();
      return r?.[3] ? decodeURIComponent(r[3]) : (window.cur_list?.board?.name || window.cur_list?.kanban_board?.name || "");
    } catch { return ""; }
  };

  const isCompactOn = () => document.documentElement.classList.contains("dnt-compact-on");
  const compactKey = (board) => `dntKanbanCompact::${board||"__all__"}`;
  const loadCompactPref = (board) => {
    try {
      const raw = localStorage.getItem(compactKey(board));
      return raw === null ? CFG.compactDefault : raw === "1";
    } catch { return CFG.compactDefault; }
  };
  const saveCompactPref = (board, on) => { try{ localStorage.setItem(compactKey(board), on ? "1":"0"); }catch{} };

  const LABEL_ALIASES = {
    display_name: new Set([
      "display name","display_name","displayname",
      "отображаемое имя","имя профиля","full name","name","фио",
      "имя / фио","имя и фамилия","имя, фамилия"
    ])
  };
  const isDisplayName = (s)=> LABEL_ALIASES.display_name.has(LBL_KEY(s));

  function injectCSS(){
    if(document.getElementById(CFG.cssId)) return;
    const s=document.createElement("style"); s.id=CFG.cssId;
    s.textContent = `
      :root{ --dnt-chars: ${CFG.pairClamp}; }
      html.${CFG.htmlClass} .kanban-column{ padding:8px; }
      html.${CFG.htmlClass} .kanban-cards{ display:block !important; }
      html.${CFG.htmlClass} .kanban-card-wrapper{ position:relative; margin:0 !important; }

      html.${CFG.htmlClass} .kanban-card.content{
        border-radius:14px;
        border:1px solid var(--border-color, rgba(0,0,0,.06));
        background: var(--card-bg, #ffffff);
        padding:12px;
        box-shadow: var(--shadow-base, 0 1px 2px rgba(0,0,0,.06));
        transition:transform .12s, box-shadow .12s;
        display:flex !important; flex-direction:column; gap:0;
        color: var(--text-color, #111827);
        /* ширина «под символы»: ~36ch + запас на паддинги/иконки */
        width: min(100%, calc(var(--dnt-chars, ${CFG.pairClamp}) * 1ch + 48px));
        margin-inline:auto;
      }
      html.${CFG.htmlClass} .kanban-card.content:hover{
        transform:translateY(-1px);
        box-shadow: 0 8px 22px color-mix(in oklab, var(--shadow-color, rgba(0,0,0,.16)) 70%, transparent);
      }

      html.${CFG.htmlClass} .dnt-head{ display:flex; align-items:center; justify-content:space-between; gap:12px; min-width:0; margin-bottom:10px; }
      html.${CFG.htmlClass} .dnt-head-left{ display:flex; align-items:center; gap:10px; min-width:0; flex:1 1 auto; }

      /* Аватар слева от названия: делаем меньше и не кропаем */
      html.${CFG.htmlClass} .kanban-image{
        width:30px !important; height:30px !important; border-radius:8px; overflow:hidden;
        background: var(--bg-light-gray, #eef2f7);
        display:flex; align-items:center; justify-content:center; float:none !important; margin:0 !important; flex:0 0 30px; position:static !important;
        box-sizing: border-box; padding:2px; /* чуть воздуха вокруг */
      }
      html.${CFG.htmlClass} .kanban-image img{
        display:block !important; width:100% !important; height:100% !important;
        object-fit:contain !important; object-position:center;
      }

      html.${CFG.htmlClass} .kanban-title-area{ margin:0 !important; min-width:0; }
      html.${CFG.htmlClass} .kanban-card-title{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color: var(--text-color, #111827); }
      html.${CFG.htmlClass} .dnt-title{ font-weight:600; line-height:1.25; cursor:text; }
      html.${CFG.htmlClass} .dnt-title[contenteditable="true"]{ outline:none; border-radius:6px; padding:0 2px; }
      html.${CFG.htmlClass} .dnt-title[contenteditable="true"]:focus{ background: var(--fg-hover-color, #f3f4f6); }

      html.${CFG.htmlClass} .kanban-card-meta{ margin-left:auto; display:flex; align-items:center; gap:8px; flex-shrink:0; color: var(--text-muted, #6b7280); }

      html.${CFG.htmlClass} .kanban-card-doc{ padding:0; }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-kv{
        display:flex; align-items:center; gap:6px;
        background: var(--control-bg, #f3f4f6);
        border:1px solid var(--border-color, #e5e7eb);
        border-radius:10px; padding:4px 8px;
        font-size:12px; min-height:24px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
        color: var(--text-color, #111827);
      }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-kv + .dnt-kv { margin-top:6px; }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-k{ opacity:.72; color: var(--text-muted, #6b7280); }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-v{ font-weight:600; min-width:0; overflow:hidden; text-overflow:ellipsis; color: var(--text-color, #111827); }

      html.${CFG.htmlClass} .dnt-foot{ margin-top:10px; display:flex; align-items:center; justify-content:space-between; gap:10px; }
      html.${CFG.htmlClass} .dnt-tasks-mini{
        margin-top:6px; width:100%; max-height:72px; overflow-y: scroll; padding-right:4px;
        border-top:1px solid var(--table-border-color, var(--border-color, #eef2f7));
        padding-top:6px; scrollbar-gutter: stable;
      }
      html.${CFG.htmlClass} .dnt-taskline{
        display:flex; gap:6px; align-items:center; font-size:11px;
        color: var(--text-muted, #4b5563); padding:2px 0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; cursor:pointer;
      }
      html.${CFG.htmlClass} .dnt-taskline .ttl{ font-weight:600; color: var(--text-color, #111827); overflow:hidden; text-overflow:ellipsis; }
      html.${CFG.htmlClass} .dnt-chip{
        border:1px solid var(--border-color, #e5e7eb);
        border-radius:999px; padding:1px 6px;
        background: var(--control-bg, #f8fafc);
        font-size:10px; color: var(--text-color, #111827);
      }
      html.${CFG.htmlClass} .dnt-overdue{
        background: var(--alert-bg-danger, #fee2e2);
        border-color: color-mix(in oklab, var(--alert-bg-danger, #fee2e2) 60%, #ffffff);
        color: var(--alert-text-danger, #991b1b);
      }

      html.${CFG.htmlClass} .dnt-card-actions{
        position:absolute; top:12px; right:12px; display:flex; gap:6px;
        opacity:0; pointer-events:none; transition:opacity .12s;
      }
      html.${CFG.htmlClass} .kanban-card-wrapper:hover .dnt-card-actions{ opacity:1; pointer-events:auto; }

      html.${CFG.htmlClass}.no-color .kanban-column .column-options .button-group{ display:none !important; }
      html.${CFG.htmlClass}.no-column-menu .kanban-column .kanban-column-header .menu,
      html.${CFG.htmlClass}.no-column-menu .kanban-column .kanban-column-header .dropdown,
      html.${CFG.htmlClass}.no-column-menu .kanban-column .kanban-column-header .kanban-column-actions{ display:none !important; }

      /* === Compact mode tweaks === */
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card.content{ padding:8px; border-radius:12px; gap:6px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-image{
        width:22px !important; height:22px !important; border-radius:6px; padding:1px;
      }
      html.${CFG.htmlClass}.dnt-compact-on .dnt-head{ margin-bottom:6px; gap:8px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card-title{ font-size:12px; line-height:1.2; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card-meta{ display:none; }
      /* ВЕРНУЛ ассайни в compact, но лайк скрыли и сделали меньший размер аватаров */
      html.${CFG.htmlClass}.dnt-compact-on .dnt-foot{ display:flex; margin-top:6px; }
      html.${CFG.htmlClass}.dnt-compact-on .dnt-foot .like-action{ display:none !important; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-assignments .avatar-group .avatar.avatar-small{
        width:18px; height:18px;
      }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-assignments .avatar-group .avatar.avatar-small .avatar-frame{
        width:100%; height:100%; border-radius:9999px; background-size:cover; background-position:center;
      }

      html.${CFG.htmlClass}.dnt-compact-on .kanban-card-doc{ display:block; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card-doc .dnt-kv{ padding:3px 6px; font-size:11px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card-doc .dnt-kv:nth-child(n+${CFG.compactMaxFields + 1}){ display:none; }
    `;
    document.head.appendChild(s);
  }

  const FULL_DT = /\b\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?\b/;
  const DATE_LIKE = /\b(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}|\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})\b/;
  const TIME_TAIL = /^(?:\d{1,2}:\d{2})(?::\d{2})?$/;
  const HAS_TIME = /\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?/;

  function normalizeDateish(raw){
    const v0 = CLEAN(raw || "").replace(/(\d{2}:\d{2}:\d{2})\.\d+$/, "$1");
    if (!v0) return v0;
    const isoLike = /^\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}(?:[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?$/;
    const humanLike = /^\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?$/;
    try{
      let m=null;
      if (isoLike.test(v0)) m = moment(frappe.datetime.convert_to_user_tz(v0));
      else if (humanLike.test(v0)){
        const fmts=["DD-MM-YYYY HH:mm:ss","DD.MM.YYYY HH:mm:ss","DD/MM/YYYY HH:mm:ss","DD-MM-YYYY","DD.MM.YYYY","DD/MM/YYYY"];
        m = moment(v0, fmts, true);
      }
      if (m && m.isValid()){
        const hasTime = HAS_TIME.test(v0);
        return hasTime ? m.format("DD-MM-YYYY HH:mm:ss") : m.format("DD-MM-YYYY");
      }
    }catch{}
    return v0;
  }

  function coerceFieldsList(dt, any){
    let arr=[];
    if(Array.isArray(any)) arr=any;
    else if(typeof any==="string" && any.trim()){
      try{ const j=JSON.parse(any); if(Array.isArray(j)) arr=j; }
      catch{ arr=any.split(/[,\s]+/).filter(Boolean); }
    }
    const meta = frappe.get_meta(dt);
    const fns = new Set((meta?.fields||[]).map(f=>f.fieldname)
      .concat((frappe.model.std_fields||[]).map(f=>f.fieldname), ["name"]));
    const label2fn = {};
    (meta?.fields||[]).forEach(f=>{ if (f?.label) label2fn[LBL_KEY(f.label)] = f.fieldname; });
    (frappe.model.std_fields||[]).forEach(f=>{ if (f?.label) label2fn[LBL_KEY(f.label)] = f.fieldname; });
    const out=[];
    arr.forEach(x=>{
      const raw = (""+x).trim(); if(!raw) return;
      if (fns.has(raw)) out.push(raw);
      else { const g = label2fn[LBL_KEY(raw)]; if (g && fns.has(g)) out.push(g); }
    });
    return [...new Set(out)];
  }

  function getBoardOrderMap(doctype){
    try{
      const board = window.cur_list?.board || window.cur_list?.kanban_board;
      const fields = coerceFieldsList(doctype, board?.fields || []);
      const map = new Map(); fields.forEach((fn,i)=> map.set(fn,i));
      return map;
    }catch{ return new Map(); }
  }

  function buildMetaMaps(doctype){
    const meta = frappe.get_meta(doctype);
    const label2fn = {}, fn2label = {}, fn2df = {};
    (meta?.fields||[]).forEach(f=>{ const lbl=CLEAN(f?.label||""); if (lbl){ label2fn[LBL_KEY(lbl)] = f.fieldname; fn2label[f.fieldname] = lbl; } });
    (frappe.model.std_fields||[]).forEach(f=>{ const lbl=CLEAN(f?.label||""); if (lbl){ label2fn[LBL_KEY(lbl)] = f.fieldname; fn2label[f.fieldname] = lbl; } });
    LABEL_ALIASES.display_name.forEach(a=> label2fn[a] = "display_name");
    (meta?.fields||[]).forEach(f=> fn2df[f.fieldname] = f);
    (frappe.model.std_fields||[]).forEach(f=> fn2df[f.fieldname] = fn2df[f.fieldname] || f);
    return { label2fn, fn2label, fn2df };
  }

  function tryParseDataFilter(el){
    const raw = el?.getAttribute?.("data-filter") || "";
    if (!raw) return "";
    try{
      const j=JSON.parse(raw);
      if (Array.isArray(j) && j.length>=3) return CLEAN(j[2]);
    }catch{}
    const csv = raw.split(",").map(CLEAN).filter(Boolean);
    if (csv.length>=3) return CLEAN(csv.slice(2).join(","));
    return CLEAN(raw);
  }
  function extractFromAttrs(el){
    if (!el) return "";
    const attrs=["title","aria-label","data-original-title","data-label","data-value"];
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
    const t = CLEAN(text); const i=t.indexOf(":"); if (i===-1) return [t,""]; return [CLEAN(t.slice(0,i)), CLEAN(t.slice(i+1))];
  }

  function collectPairsFromNative(docEl, doctype){
    const rows = Array.from(docEl.querySelectorAll(":scope > .text-truncate, :scope > .ellipsis"));
    const pairs = [], seenValuesOff=[];
    const labelsOn = getShowLabelsFlag();
    const { label2fn } = buildMetaMaps(doctype);

    rows.forEach(row=>{
      const fullText = CLEAN(row.textContent || "");
      const spans = Array.from(row.querySelectorAll(":scope > span"));
      const tokens = (spans.length ? spans.map(s => CLEAN(s.textContent)) : [fullText]).filter(Boolean);
      if (!tokens.length && !extractFromAttrs(row)) return;

      if (!labelsOn){
        let value = "";
        if (FULL_DT.test(fullText)) {
          const matches = [...fullText.matchAll(FULL_DT)].map(m=>m[0]);
          value = matches.sort((a,b)=>b.length - a.length)[0] || "";
        }
        if (!value) {
          if (fullText.includes(":")){ const [,tail]=splitByFirstColon(fullText); value = CLEAN(tail); }
          if (!value) value = STRIP_COLON(tokens[tokens.length-1] || "");
          if (!value) value = CLEAN(row.innerText || "");
          if (!value) value = extractFromAttrs(row);
        }
        value = normalizeDateish(value);

        if (!value || value.length<=2) return;
        if (TIME_TAIL.test(value) && tokens.some(t=>t.length>value.length && t.endsWith(value))) return;
        if (TIME_TAIL.test(value) && seenValuesOff.some(v=>v.length>value.length && v.endsWith(value))) return;
        if (seenValuesOff.includes(value)) return;

        pairs.push({ k:"", v:value, row, fieldname:null });
        seenValuesOff.push(value);
        return;
      }

      let label = STRIP_COLON(tokens[0] || "");
      let value = "";
      for (let i=1; i<tokens.length; i++){
        const tkn = STRIP_COLON(tokens[i]);
        if (tkn && LBL_KEY(tkn) !== LBL_KEY(label)) { value = tkn; break; }
      }
      if (!value && fullText) {
        const [lbl, tail] = splitByFirstColon(fullText);
        if (LBL_KEY(lbl)) label = STRIP_COLON(lbl);
        if (tail) value = tail;
      }
      if (!value) {
        const it = CLEAN(row.innerText || "");
        if (it){
          const [lbl2, tail2] = splitByFirstColon(it);
          if (LBL_KEY(lbl2) && tail2) value = tail2;
        }
      }
      if (!value) {
        const a = extractFromAttrs(row);
        if (a) value = a;
      }

      value = normalizeDateish(value);
      const fn = label2fn[LBL_KEY(label)] || (isDisplayName(label) ? "display_name" : null);
      pairs.push({ k: label, v: value || "", row, fieldname: fn });
    });

    const seen = new Set(), out=[];
    for (const o of pairs){
      const key = (o.fieldname || o.k || "").toLowerCase();
      if (key && seen.has(key)) continue;
      if (key) seen.add(key);
      out.push(o);
    }
    return out;
  }

  const gvCache = new Map();
  async function getValuesBatch(doctype, name, fields){
    const key = `${doctype}:${name}::${fields.slice().sort().join(",")}`;
    if (gvCache.has(key)) return gvCache.get(key);
    try{
      const { message } = await frappe.call({
        method: "frappe.client.get_value",
        args: { doctype, filters:{ name }, fieldname: fields }
      });
      const obj = message || {};
      gvCache.set(key, obj);
      return obj;
    }catch{ gvCache.set(key, {}); return {}; }
  }
  function composeDisplayName(v){
    const f = CLEAN(v.first_name), m = CLEAN(v.middle_name), l = CLEAN(v.last_name);
    const parts = [f,m,l].filter(Boolean);
    return parts.length ? parts.join(" ") : (CLEAN(v.title) || "");
  }

  function isTranslatableField(fn, df){
    if (!fn) return false;
    if (/^status_/.test(fn)) return true;
    if (fn === "channel_platform" || fn === "channel_type" || fn === "priority") return true;
    const ty = (df?.fieldtype || "").toLowerCase();
    if (ty === "select") return true;
    return false;
  }
  function translateValue(dt, fn, val, df){
    const v = CLEAN(val);
    if (!v) return v;
    if (FULL_DT.test(v) || DATE_LIKE.test(v)) return v;
    if (isTranslatableField(fn, df)) { try { return t(v); } catch { return v; } }
    if (/^(Yes|No|Open|Closed)$/i.test(v)) { try { return t(v); } catch {} }
    return v;
  }

  function makeChip(label, value, showLabel){
    const kv = document.createElement("div");
    kv.className = "dnt-kv text-truncate";
    kv.dataset.dntLabel = showLabel ? CLEAN(label||"") : "";
    if (showLabel && CLEAN(label)){
      const sk = document.createElement("span");
      sk.className = "dnt-k";
      sk.textContent = t(STRIP_COLON(label)) + ":";
      kv.appendChild(sk);
    }
    const sv = document.createElement("span");
    sv.className = "dnt-v";
    sv.textContent = CLEAN(value);
    kv.appendChild(sv);
    return kv;
  }
  function insertChipAtIndex(container, chip, idx){
    const nodes = Array.from(container.querySelectorAll(":scope > .dnt-kv"));
    const target = nodes[idx];
    if (target) container.insertBefore(chip, target);
    else container.appendChild(chip);
  }

  function clampStr(s, n){
    const str = s || "";
    if (n <= 0) return "…";
    if (str.length <= n) return str;
    return str.slice(0, Math.max(0, n-1)).trimEnd() + "…";
  }
  const isLikelyDate = (s)=> FULL_DT.test(CLEAN(s||"")) || DATE_LIKE.test(CLEAN(s||""));

  // Режем ПАРОЙ «Label: Value» под общий бюджет
  function clampKVPair(kvEl){
    if (!kvEl) return;
    const sv = kvEl.querySelector(".dnt-v");
    const sk = kvEl.querySelector(".dnt-k");
    if (!sv) return;

    const fullV = sv.getAttribute("data-full") || CLEAN(sv.textContent || "");
    const fullK = sk ? (sk.getAttribute("data-full") || CLEAN(sk.textContent || "")) : "";
    sv.setAttribute("data-full", fullV);
    if (sk) sk.setAttribute("data-full", fullK);

    if (!isCompactOn()){
      sv.textContent = fullV;
      if (sk) sk.textContent = fullK;
      sv.removeAttribute("title");
      sk?.removeAttribute("title");
      return;
    }

    const budget = Math.max(1, CFG.pairClamp|0);

    if (sk){
      const labelText = STRIP_COLON(fullK).replace(/:$/,"");
      const labelShown = (labelText ? t(labelText) : "").trim();
      const labelWithColon = labelShown ? (labelShown + ":") : "";
      const valueBudget = Math.max(1, budget - labelWithColon.length - 1); // минус пробел
      const vShown = isLikelyDate(fullV) ? fullV : clampStr(fullV, valueBudget);
      sv.textContent = vShown; sv.setAttribute("title", fullV);
      sk.textContent = labelWithColon; sk.setAttribute("title", labelWithColon);
    } else {
      const vShown = isLikelyDate(fullV) ? fullV : clampStr(fullV, budget);
      sv.textContent = vShown; sv.setAttribute("title", fullV);
    }
  }
  function clampChips(container){
    if (!container) return;
    container.querySelectorAll(":scope > .dnt-kv").forEach(clampKVPair);
  }

  async function backfillAll(container, ctx, labelsOn, orderMap){
    const { fn2label, label2fn, fn2df } = buildMetaMaps(ctx.doctype);
    const boardFields = [...orderMap.keys()];

    Array.from(container.querySelectorAll(":scope > .dnt-kv")).forEach(ch=>{
      const lbl = CLEAN(ch.dataset.dntLabel || ch.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
      if (!lbl) return;
      const fn = label2fn[LBL_KEY(lbl)] || (isDisplayName(lbl) ? "display_name" : null);
      if (!fn || !boardFields.includes(fn)) ch.remove();
    });

    const need = boardFields.slice();
    const v = await getValuesBatch(ctx.doctype, ctx.docName, need);
    if (boardFields.includes("display_name") && !CLEAN(v.display_name)) {
      const pseudo = await getValuesBatch(ctx.doctype, ctx.docName, ["first_name","middle_name","last_name","title"]);
      v.display_name = composeDisplayName(pseudo);
    }

    if (labelsOn){
      boardFields.forEach(fn=>{
        const human = fn2label[fn] || (fn==="display_name" ? "Display Name" : fn);
        const rawVal = CLEAN(normalizeDateish(v[fn])) || "";
        const locVal = translateValue(ctx.doctype, fn, rawVal, fn2df[fn]) || "";
        let chip = Array.from(container.querySelectorAll(":scope > .dnt-kv")).find(ch=>{
          const lbl = CLEAN(ch.dataset.dntLabel || ch.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
          const f = label2fn[LBL_KEY(lbl)] || (isDisplayName(lbl) ? "display_name" : null);
          return f === fn;
        });
        if (!chip){
          chip = makeChip(human, locVal, true);
          insertChipAtIndex(container, chip, orderMap.get(fn) ?? 0);
        } else {
          const sv = chip.querySelector(".dnt-v"); if (sv) sv.textContent = locVal || "—";
          const sk = chip.querySelector(".dnt-k"); if (sk) sk.textContent = t(STRIP_COLON(human)) + ":";
        }
      });

      const chips = Array.from(container.querySelectorAll(":scope > .dnt-kv"));
      chips.sort((a,b)=>{
        const la = CLEAN(a.dataset.dntLabel || a.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
        const lb = CLEAN(b.dataset.dntLabel || b.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
        const fna = label2fn[LBL_KEY(la)] || (isDisplayName(la) ? "display_name" : null);
        const fnb = label2fn[LBL_KEY(lb)] || (isDisplayName(lb) ? "display_name" : null);
        const ia = orderMap.has(fna||"") ? orderMap.get(fna||"") : 9999;
        const ib = orderMap.has(fnb||"") ? orderMap.get(fnb||"") : 9999;
        return ia - ib;
      });
      chips.forEach(ch => container.appendChild(ch));

      Array.from(container.querySelectorAll(":scope > .dnt-kv .dnt-v")).forEach(sv=>{
        if (!CLEAN(sv.textContent)) sv.textContent = "—";
      });

      clampChips(container);
      return;
    }

    const assignedValues = new Set();
    const valueIndex = new Map();
    Array.from(container.querySelectorAll(":scope > .dnt-kv")).forEach(ch=>{
      const lbl = CLEAN(ch.dataset.dntLabel || ch.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
      if (lbl) return;
      const val = CLEAN(ch.querySelector(".dnt-v")?.textContent || "");
      if (!val) return;
      if (!valueIndex.has(val)) valueIndex.set(val, []);
      valueIndex.get(val).push(ch);
    });

    boardFields.forEach(fn=>{
      const raw = v[fn];
      const norm = CLEAN(normalizeDateish(raw));
      const locVal = translateValue(ctx.doctype, fn, norm, fn2df[fn]);
      if (!locVal) return;
      const pool = valueIndex.get(norm) || valueIndex.get(locVal) || [];
      const pick = pool.shift?.();
      if (pick){
        const sv = pick.querySelector(".dnt-v"); if (sv) sv.textContent = locVal;
        insertChipAtIndex(container, pick, orderMap.get(fn) ?? 0);
        assignedValues.add(locVal);
      } else {
        const chip = makeChip("", locVal, false);
        insertChipAtIndex(container, chip, orderMap.get(fn) ?? 0);
        assignedValues.add(locVal);
      }
    });

    Array.from(container.querySelectorAll(":scope > .dnt-kv")).forEach(ch=>{
      const lbl = CLEAN(ch.dataset.dntLabel || ch.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
      if (lbl){
        const fn = label2fn[LBL_KEY(lbl)] || (isDisplayName(lbl) ? "display_name" : null);
        if (!fn || !boardFields.includes(fn)) ch.remove();
        return;
      }
      const val = CLEAN(ch.querySelector(".dnt-v")?.textContent || "");
      if (!val || !assignedValues.has(val)) ch.remove();
    });

    clampChips(container);
  }

  function buildChipsHTML(pairs, ctx){
    const labelsOn = getShowLabelsFlag();
    const orderMap = getBoardOrderMap(ctx.doctype);
    const { fn2label } = buildMetaMaps(ctx.doctype);
    const boardFields = [...orderMap.keys()];

    let items = pairs.slice();

    if (labelsOn){
      items = items.filter(o => o.fieldname && boardFields.includes(o.fieldname));
      items.sort((a,b)=>{
        const ia = orderMap.has(a.fieldname||"") ? orderMap.get(a.fieldname||"") : 9999;
        const ib = orderMap.has(b.fieldname||"") ? orderMap.get(b.fieldname||"") : 9999;
        return ia - ib;
      });
    } else {
      items = items.filter(o => !o.fieldname || boardFields.includes(o.fieldname));
    }

    const frag = document.createDocumentFragment();
    items.forEach(o=>{
      const k = o.k || (o.fieldname ? fn2label[o.fieldname]||"" : "");
      const v = CLEAN(o.v || "");
      if (!labelsOn && !v) return;
      const chip = makeChip(k, labelsOn ? (v||"") : v, labelsOn && CLEAN(k));
      frag.appendChild(chip);
    });

    queueMicrotask(async ()=>{
      if (frag.__dntMount) await backfillAll(frag.__dntMount, ctx, labelsOn, orderMap);
    });

    return frag;
  }

  function clampTitleSpan(span){
    if (!span) return;
    const full = span.getAttribute("data-title-full") || CLEAN(span.textContent || "");
    if (isCompactOn()){
      const n = Math.max(1, CFG.compactTitleClamp|0);
      span.textContent = full.length <= n ? full : (full.slice(0, Math.max(0,n-1)).trimEnd()+"…");
      span.setAttribute("title", full);
    } else {
      span.textContent = full;
      span.removeAttribute("title");
    }
  }

  function normalizeDocFields(docEl, ctx){
    if (!docEl || docEl.__dnt_locked) return;
    docEl.__dnt_locked = true;

    const pairs = collectPairsFromNative(docEl, ctx.doctype);
    docEl.innerHTML = "";
    const frag = buildChipsHTML(pairs, ctx);
    frag.__dntMount = docEl;
    docEl.appendChild(frag);

    clampChips(docEl);

    let raf = null;
    const mo = new MutationObserver((muts)=>{
      for (const m of muts){
        for (const n of (m.addedNodes||[])){
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

  const miniCache = new Map();
  const fmtDT = (dt) => { try { return moment(frappe.datetime.convert_to_user_tz(dt)).format("DD-MM-YYYY HH:mm:ss"); } catch { return dt; } };

  function pickPlan(t){
    if (t.custom_target_datetime)   return { dt: t.custom_target_datetime, kind: "target" };
    return { dt: null, kind: null };
  }
  function planLabel(kind){ return kind==="target" ? t("Target at") : t("Planned"); }

  function plain_text(html_like){
    const div = document.createElement("div"); div.innerHTML = html_like || "";
    return CLEAN(div.textContent || div.innerText || "");
  }
  function truncate_text(s, max_len=40){
    const str = s || "";
    if (max_len <= 0) return "…";
    if (str.length <= max_len) return str;
    return str.slice(0, Math.max(0, max_len-1)).trimEnd() + "…";
  }

  function miniHtml(rows, total){
    const totalCount = typeof total === "number" ? total : (rows?.length || 0);
    const showOpenAll = totalCount > 1 || (rows?.length || 0) > 1;
    const header = `<div class="dnt-taskline" data-act="noop"><span class="dnt-chip">${t("Tasks")}</span></div>`;

    if (!rows?.length) return header + `<div class="dnt-taskline"><span class="ttl">${t("No open tasks")}</span></div>`;

    const lines = rows.map(ti=>{
      const pick = pickPlan(ti);
      const p = pick.dt;
      const open = (ti.status||"Open")==="Open";
      const overdue = p && open && moment(p).isBefore(moment());
      const label = planLabel(pick.kind);
      const val = p ? fmtDT(p) : "—";
      const chipText = val;
      const cls = p && overdue ? "dnt-chip dnt-overdue" : "dnt-chip";

      const chipLen = (chipText || "").length;
      const ttlBudget = Math.max(1, (CFG.taskLineBudget|0) - chipLen - 1); // минус пробел
      const raw = plain_text(ti.description || ti.name);
      const ttlShown = truncate_text(raw, ttlBudget);

      const chip = `<span class="${cls}" title="${frappe.utils.escape_html(label)}">${frappe.utils.escape_html(chipText)}</span>`;
      const ttl  = frappe.utils.escape_html(ttlShown);
      return `<div class="dnt-taskline" data-open="${frappe.utils.escape_html(ti.name)}">${chip}<span class="ttl" title="${frappe.utils.escape_html(raw)}">${ttl}</span></div>`;
    }).join("");

    const more = showOpenAll ? `<div class="dnt-taskline" data-act="open-all"><span class="ttl">${frappe.utils.escape_html(t("Open all tasks") + " →")}</span></div>` : ``;
    return header + lines + more;
  }

  async function fetchMiniPrimary(caseName){
    const { message } = await frappe.call({
      method: CFG.tasksMethod,
      args: { name: caseName, status: "Open", limit_start: 0, limit_page_length: CFG.tasksLimit, order: "desc" }
    });
    const rows  = (message && message.rows) || [];
    const total = (message && message.total) || rows.length;
    return { rows, total };
  }
  async function fetchMiniFallback(caseName){
    try{
      const { message: rows=[] } = await frappe.call({
        method: "frappe.client.get_list",
        args: {
          doctype: "ToDo",
          filters: { reference_type: CFG.caseDoctype, reference_name: caseName, status: "Open" },
          fields: ["name","description","status","date","custom_due_datetime","custom_target_datetime"],
          limit_page_length: CFG.tasksLimit,
          order_by: "modified desc"
        }
      });
      return { rows, total: rows.length };
    } catch {
      return { rows: [], total: 0 };
    }
  }

  async function loadMini(container, caseName){
    if (miniCache.has(caseName)) { container.innerHTML = miniCache.get(caseName); return bindMini(container, caseName); }
    container.innerHTML = `<div class="dnt-taskline"><span class="ttl">${t("Loading…")}</span></div>`;
    try{
      let data = await fetchMiniPrimary(caseName);
      if ((!data.rows || !data.rows.length) && (!data.total || data.total === 0)) data = await fetchMiniFallback(caseName);
      const html  = miniHtml(data.rows || [], data.total || 0);
      miniCache.set(caseName, html);
      container.innerHTML = html;
      bindMini(container, caseName);
    } catch {
      try{
        const data = await fetchMiniFallback(caseName);
        const html  = miniHtml(data.rows || [], data.total || 0);
        miniCache.set(caseName, html);
        container.innerHTML = html;
        bindMini(container, caseName);
      }catch{
        container.innerHTML = `<div class="dnt-taskline"><span class="dnt-chip">${t("Tasks")}</span></div><div class="dnt-taskline"><span class="ttl">${t("No open tasks")}</span></div>`;
      }
    }
  }
  function bindMini(container, caseName){
    container.querySelectorAll("[data-open]").forEach(el=>{
      el.addEventListener("click",(e)=>{ e.preventDefault(); e.stopPropagation(); frappe.set_route("Form","ToDo", el.getAttribute("data-open")); });
    });
    container.querySelector('[data-act="open-all"]')?.addEventListener("click",(e)=>{
      e.preventDefault(); e.stopPropagation();
      frappe.set_route("List","ToDo",{ reference_type: CFG.caseDoctype, reference_name: caseName, status: "Open" });
    });
  }

  function makeTitleEditable(titleArea, name, doctype){
    if (!titleArea || titleArea.__dntEditable) return;
    titleArea.__dntEditable = true;

    const anchor = titleArea.querySelector("a");
    const currentText = (titleArea.querySelector(".kanban-card-title")?.textContent || anchor?.textContent || name || "").trim();

    const holder = titleArea.querySelector(".kanban-card-title") || document.createElement("div");
    holder.classList.add("kanban-card-title"); holder.innerHTML = "";

    const span = document.createElement("span");
    span.className = "dnt-title"; span.setAttribute("contenteditable","true"); span.textContent = currentText;
    span.setAttribute("data-title-full", currentText);
    holder.appendChild(span);

    if (anchor) anchor.replaceWith(holder); else titleArea.appendChild(holder);

    clampTitleSpan(span);

    const save = async () => {
      const full = span.getAttribute("data-title-full") || currentText;
      let val = (span.textContent || "").trim();
      if (isCompactOn() && full && val.endsWith("…") && full.startsWith(val.slice(0, Math.max(0,val.length-1)))) val = full;
      if (!val || val === currentText) { clampTitleSpan(span); return; }
      try{
        await frappe.call({ method:"frappe.client.set_value", args:{ doctype, name, fieldname:"title", value: val } });
        frappe.show_alert({ message: t("Title updated"), indicator:"green" });
        span.setAttribute("data-title-full", val);
        clampTitleSpan(span);
      }catch{
        frappe.msgprint({ message: t("Failed to update title"), indicator:"red" });
        span.textContent = currentText;
        span.setAttribute("data-title-full", currentText);
        clampTitleSpan(span);
      }
    };
    span.addEventListener("keydown", (e)=>{
      if (e.key==="Enter"){ e.preventDefault(); span.blur(); }
      else if (e.key==="Escape"){ e.preventDefault(); span.textContent=currentText; span.setAttribute("data-title-full", currentText); span.blur(); }
    });
    span.addEventListener("click", e=> e.stopPropagation());
    span.addEventListener("blur", save);
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
    const doctype = window.cur_list?.doctype || window.cur_list?.board?.reference_doctype || CFG.caseDoctype;

    if (doc) normalizeDocFields(doc, { doctype, docName: name });

    let foot = body.querySelector(".dnt-foot");
    if(!foot){ foot = document.createElement("div"); foot.className = "dnt-foot"; body.appendChild(foot); }
    const assign = (meta || body).querySelector(".kanban-assignments");
    const like   = (meta || body).querySelector(".like-action");
    if(assign && !foot.contains(assign)) foot.appendChild(assign);
    if(like   && !foot.contains(like))   foot.appendChild(like);
    if(meta && !meta.children.length) meta.remove();

    if (doctype === CFG.caseDoctype && name) {
      if (!body.querySelector(".dnt-tasks-mini")) {
        const mini = document.createElement("div");
        mini.className = "dnt-tasks-mini";
        body.appendChild(mini);
        setTimeout(()=> loadMini(mini, name), 0);
      }
      makeTitleEditable(title, name, doctype);
    }

    if (!wrapper.querySelector(".dnt-card-actions")){
      const row = document.createElement("div"); row.className="dnt-card-actions";

      const bOpen = document.createElement("div"); bOpen.className="dnt-icon-btn"; bOpen.title=t("Open");
      bOpen.innerHTML = frappe.utils.icon("external-link","sm");
      bOpen.addEventListener("click",(e)=>{ e.stopPropagation(); if (doctype && name) frappe.set_route("Form", doctype, name); });
      row.appendChild(bOpen);

      const bDel = document.createElement("div"); bDel.className="dnt-icon-btn"; bDel.title=t("Delete / Remove from board");
      bDel.innerHTML = frappe.utils.icon("delete","sm");
      bDel.addEventListener("click",(e)=>{
        e.stopPropagation();
        const getBoardName=()=>{ try { const r = frappe.get_route(); if (r?.[3]) return decodeURIComponent(r[3]); } catch {} return window.cur_list?.board?.name || null; };
        const board = CFG.BOARD[getBoardName()];
        const canSoft = !!(board && board.flag);
        const d = new frappe.ui.Dialog({
          title: t("Card actions"),
          primary_action_label: canSoft ? t("Remove from this board") : t("Delete"),
          primary_action: ()=> {
            if (canSoft) {
              frappe.call({ method:"frappe.client.set_value", args:{ doctype, name, fieldname: board.flag, value: 0 } })
                .then(()=>{ frappe.show_alert(t("Removed from board")); try{window.cur_list?.refresh();}catch{}; d.hide(); });
            } else {
              frappe.call({ method:"frappe.client.delete", args:{ doctype, name } })
                .then(()=>{ frappe.show_alert(t("Deleted")); try{window.cur_list?.refresh();}catch{}; d.hide(); });
            }
          }
        });
        if (canSoft){
          d.set_secondary_action_label(t("Delete document"));
          d.set_secondary_action(()=> {
            frappe.confirm(t("Delete this document?"),()=>{
              frappe.call({ method:"frappe.client.delete", args:{ doctype, name } })
                .then(()=>{ frappe.show_alert(t("Deleted")); try{window.cur_list?.refresh();}catch{}; d.hide(); });
            });
          });
        }
        d.show();
      });
      row.appendChild(bDel);
      wrapper.appendChild(row);
    }

    clampTitleSpan(wrapper.querySelector(".dnt-title"));
    clampChips(body.querySelector(".kanban-card-doc"));

    card.dataset.dntUpgraded = "1";
  }

  function enhanceCards(){
    document.querySelectorAll(".kanban-card-wrapper, .kanban-column .kanban-card:not(.content)").forEach(w => {
      const wrap = w.classList.contains?.("kanban-card") ? w.closest(".kanban-card-wrapper") || w : w;
      upgradeCard(wrap);
    });
  }

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
    document.querySelectorAll(`#${CFG.settingsBtnId}, #${CFG.compactBtnId}`).forEach(el => el.remove());
    if(!isKanbanRoute()) return;
    const anchor = findSettingsAnchor(); if(!anchor) return;

    if (userHasAny(CFG.rolesSettings)) {
      const btn=document.createElement("button");
      btn.id=CFG.settingsBtnId; btn.className="btn btn-default icon-btn";
      btn.setAttribute("title", t("Kanban settings"));
      btn.innerHTML = frappe.utils.icon("edit","sm");
      btn.addEventListener("click",()=> {
        const r = frappe.get_route(); const bname = r?.[3] ? decodeURIComponent(r[3]) : (window.cur_list?.board?.name||"");
        if (bname) frappe.set_route(`/app/kanban-board/${encodeURIComponent(bname)}`);
      });
      (document.querySelector(".page-icon-group") || anchor).insertAdjacentElement("beforeend", btn);
    }

    const cBtn=document.createElement("button");
    cBtn.id=CFG.compactBtnId; cBtn.className="btn btn-default icon-btn";
    const board = getBoardName();
    const prefOn = loadCompactPref(board);
    const setFace = (on) => {
      cBtn.setAttribute("title", on ? t("Compact mode: ON") : t("Compact mode: OFF"));
      cBtn.innerHTML = on ? ICONS.compactOn : ICONS.compactOff;
    };
    setFace(prefOn);
    cBtn.addEventListener("click",()=>{
      const next = !isCompactOn();
      document.documentElement.classList.toggle("dnt-compact-on", next);
      saveCompactPref(getBoardName(), next);
      setFace(next);
      document.querySelectorAll(".kanban-card-wrapper .dnt-title").forEach(clampTitleSpan);
      document.querySelectorAll(".kanban-card-wrapper .kanban-card-doc").forEach(clampChips);
    });
    (document.querySelector(".page-icon-group") || anchor).insertAdjacentElement("beforeend", cBtn);
  }

  function ensureSettingsBtnSticky(){
    let tries=0, max=120;
    const tick=()=>{ if(!isKanbanRoute()) return;
      injectSettingsBtn(); tries+=1;
      if (document.getElementById(CFG.settingsBtnId) || document.getElementById(CFG.compactBtnId)) return;
      if (tries<max) setTimeout(tick, 50);
    };
    tick();
    const head = document.querySelector(".page-head-content") || document.querySelector(".page-title") || document.body;
    try{
      const mo = new MutationObserver(()=> {
        if (!isKanbanRoute()) return;
        if (!document.getElementById(CFG.settingsBtnId) || !document.getElementById(CFG.compactBtnId)) injectSettingsBtn();
      });
      mo.observe(head, { childList:true, subtree:true });
      window.__dntKanbanHeadMO = mo;
    }catch{}
  }

  async function run(){
    await ensure_messages();
    if(!isKanbanRoute()){
      document.documentElement.classList.remove(CFG.htmlClass,"no-color","no-column-menu","dnt-compact-on");
      document.querySelectorAll(`#${CFG.settingsBtnId}, #${CFG.compactBtnId}`).forEach(el => el.remove());
      return;
    }
    injectCSS();
    document.documentElement.classList.add(CFG.htmlClass);

    const allowColor = userHasAny(CFG.rolesCanColor);
    const allowMenu  = userHasAny(CFG.rolesColumnMenu);
    document.documentElement.classList.toggle("no-color", !allowColor);
    document.documentElement.classList.toggle("no-column-menu", !allowMenu);

    const prefer = loadCompactPref(getBoardName());
    document.documentElement.classList.toggle("dnt-compact-on", !!prefer);

    enhanceCards();
    ensureSettingsBtnSticky();

    let attempts = 0;
    const pump = () => {
      if (!isKanbanRoute()) return;
      attempts += 1;
      enhanceCards();
      if (attempts < 30) setTimeout(pump, 60);
    };
    pump();

    if (window.__dntKanbanMO) window.__dntKanbanMO.disconnect();
    const mo = new MutationObserver(()=>{ if(isKanbanRoute()) enhanceCards(); });
    mo.observe(document.body||document.documentElement,{ childList:true, subtree:true });
    window.__dntKanbanMO = mo;
  }

  if (frappe?.after_ajax) frappe.after_ajax(run); else document.addEventListener("DOMContentLoaded", run);
  window.addEventListener("load", run);
  frappe?.router?.on && frappe.router.on("change", run);
})();