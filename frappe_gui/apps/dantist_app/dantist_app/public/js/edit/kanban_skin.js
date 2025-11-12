(() => {
  if (window.__DNT_KANBAN_S) return; window.__DNT_KANBAN_S = true;

  const CFG = {
    cssId: "dantist-kanban-skin-css",
    htmlClass: "dantist-kanban-skin",
    rolesSettings: ["AIHub Super Admin", "System Manager"],
    rolesCreateOnly: ["System Manager"],
    rolesCanColor: ["AIHub Super Admin", "System Manager"],
    rolesColumnMenu:["AIHub Super Admin", "System Manager"],
    settingsBtnId: "dnt-kanban-settings",
    modeToggleId: "dnt-mode-toggle",
    openListBtnId: "dnt-open-list",
    minCardW: 240,
    maxCardW: 720,
    compactChars: 26,
    comfyChars: 44,
    compactDefault: true,

    caseDoctype: "Engagement Case",
    tasksMethod: "dantist_app.api.tasks.handlers.ec_tasks_for_case",
    tasksLimit: 5,

    debug: true,
    log_prefix: "[DNT-KANBAN]",

    boardFieldByTitle:{
      "CRM Board": "show_board_crm",
      "Leads – Contact Center": "show_board_leads",
      "Deals – Contact Center": "show_board_deals",
      "Patients – Care Department": "show_board_patients"
    }
  };

  const ICONS = {
    modeCompact:  '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M7 9h6M7 13h4"/></svg>',
    modeComfy:    '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="4" width="18" height="16" rx="4"/><path d="M7 10h10M7 14h8"/></svg>',
    resizerGrip:  '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="square" shape-rendering="crispEdges"><path d="M6 15L15 6M9 15L15 9M12 15L15 12"/></svg>',
    listIcon:     '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/></svg>',
    plus:         '<svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/></svg>',
    settings:     '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="6" x2="20" y2="6"/><circle cx="9" cy="6" r="2"/><line x1="4" y1="12" x2="20" y2="12"/><circle cx="15" cy="12" r="2"/><line x1="4" y1="18" x2="20" y2="18"/><circle cx="7" cy="18" r="2"/></svg>'
  };

  // ===== Utils
  const CLEAN = s => (s||"").replace(/\u00A0/g," ").replace(/\s+/g," ").trim();
  const STRIP_COLON = s => CLEAN(s).replace(/:\s*$/,"");
  const LBL_KEY = s => STRIP_COLON(s).toLowerCase();
  const t = (s)=>{ if (typeof __ === "function") return __(s); const d=frappe&&frappe._messages; return (d&&typeof d[s]==="string"&&d[s].length)?d[s]:s; };
  const hasAny = (roles)=>{ try{ return roles.some(r=>frappe.user.has_role?.(r)); }catch{ return false; } };
  const json_hash = (o)=>{ try{ return JSON.stringify(o); }catch{ return ""; } };
  const dbg = (...args)=> { if (CFG.debug) try{ console.log(CFG.log_prefix, ...args); }catch{} };
  const ls_get = (k)=>{ try{ return localStorage.getItem(k); }catch{ return null; } };
  const ls_set = (k,v)=>{ try{ localStorage.setItem(k,v); }catch{} };

  async function ensure_messages(timeout_ms = 2000) {
    const start = Date.now();
    while (Date.now() - start < timeout_ms) {
      if (typeof __ === "function") return true;
      if (frappe && frappe._messages && Object.keys(frappe._messages).length) return true;
      await new Promise(r => setTimeout(r, 50));
    }
    return false;
  }

  const isKanbanRoute = () => {
    const r = frappe.get_route?.() || [];
    if (r[0] === "List" && (r[2] === "Kanban" || r[2] === "Kanban Board")) return true;
    return (location.pathname||"").includes("/view/kanban/");
  };
  const getDoctype   = () => window.cur_list?.doctype || window.cur_list?.board?.reference_doctype || CFG.caseDoctype;
  const getBoardName = () => {
    try { const r = frappe.get_route?.(); return r?.[3] ? decodeURIComponent(r[3]) : (window.cur_list?.board?.name || window.cur_list?.kanban_board?.name || ""); }
    catch { return ""; }
  };
  const getColumnField = () => {
    const b = window.cur_list?.board || window.cur_list?.kanban_board || {};
    return b.field_name || b.field || b.kanban_field || "status";
  };

  // ===== View flags
  const getShowLabelsFlag = () => {
    const b = window.cur_list?.board || window.cur_list?.kanban_board;
    return !!(b && (b.show_labels === 1 || b.show_labels === true || b.show_labels === "1" || b.show_labels === "true"));
  };

  // ===== Width persistence per column + mode
  const currentMode = () => document.documentElement.classList.contains("dnt-compact-on") ? "compact" : "comfy";
  const colKey = (col, mode) => {
    const board = getBoardName() || "__";
    const val = col?.getAttribute?.("data-column-value") || "__col__";
    return `dntKanbanColW::${board}::${val}::${mode}`;
  };
  const loadColW = (col, mode) => { try{ const v = localStorage.getItem(colKey(col, mode)); return v? +v : null; }catch{ return null; } };
  const saveColW = (col, mode, w) => { try{ localStorage.setItem(colKey(col,mode), String(w)); }catch{} };
  const sessionColW = new Map();
  const sessKey = (col, mode) => colKey(col, mode) + "::session";
  const setSessW = (col, mode, px) => sessionColW.set(sessKey(col,mode), px);
  const getSessW = (col, mode) => sessionColW.get(sessKey(col,mode));
  const clearSessAll = () => sessionColW.clear();
  function resetColumnInlineWidth(col){
    if (!col) return;
    col.style.removeProperty("--dnt-card-w");
    col.style.minWidth = `calc(var(--dnt-card-w-default) + 24px)`;
  }
  function getColumnsEl(){ return Array.from(document.querySelectorAll(".kanban-column")); }
  function normalizeColumns(){
    const mode = currentMode();
    getColumnsEl().forEach(col=>{
      const hasCards = !!col.querySelector(".kanban-card, .kanban-card-wrapper");
      if (!hasCards){
        resetColumnInlineWidth(col);
        sessionColW.delete(sessKey(col, mode));
      }
    });
  }
  function applyWidthsForMode(mode){
    getColumnsEl().forEach(resetColumnInlineWidth);
    getColumnsEl().forEach(col=>{
      const saved = loadColW(col, mode);
      const sessionW = getSessW(col, mode);
      const w = (sessionW ?? saved);
      if (w){
        col.style.setProperty("--dnt-card-w", w + "px");
        col.style.minWidth = `calc(${w}px + 24px)`;
      }
    });
    normalizeColumns();
  }
  function clearSavedColWidthsForBoard(board){
    try{
      const prefix = `dntKanbanColW::${board||"__"}::`;
      const keys = [];
      for (let i=0;i<localStorage.length;i++){ const k = localStorage.key(i); if (k && k.startsWith(prefix)) keys.push(k); }
      keys.forEach(k => localStorage.removeItem(k));
    }catch{}
  }

  // ===== CSS
  function injectCSS(){
    if(document.getElementById(CFG.cssId)) return;
    const s=document.createElement("style"); s.id=CFG.cssId;
    s.textContent = `
      :root{
        --dnt-card-ch-compact: ${CFG.compactChars};
        --dnt-card-ch-comfy:   ${CFG.comfyChars};
        --dnt-h-head-compact: 36px;
        --dnt-h-head-comfy:   52px;
        --dnt-assign-h-compact: 22px;
        --dnt-assign-h-comfy:   32px;
        --dnt-tasks-h-compact: 72px;
        --dnt-tasks-h-comfy:   100px;
      }
      html.${CFG.htmlClass}{ --dnt-card-w: var(--dnt-card-w-default); }
      html.${CFG.htmlClass}.dnt-compact-on { --dnt-card-w-default: calc(var(--dnt-card-ch-compact) * 1ch + 48px); }
      html.${CFG.htmlClass}:not(.dnt-compact-on) { --dnt-card-w-default: calc(var(--dnt-card-ch-comfy) * 1ch + 48px); }

      .kanban-board{ contain:layout style; }
      html.${CFG.htmlClass} .kanban-column{ padding:8px; min-width: calc(var(--dnt-card-w) + 24px); }
      html.${CFG.htmlClass} .kanban-cards{ display:block !important; }
      html.${CFG.htmlClass} .kanban-card-wrapper{ position:relative; margin:0 !important; width:100%; will-change: transform; }

      html.${CFG.htmlClass} .dnt-col-count{ margin-left:6px; font-weight:600; opacity:.8; font-size:.9em; }

      html.${CFG.htmlClass} .kanban-card.content{
        border-radius:14px; border:1px solid var(--border-color);
        background: var(--card-bg); padding:12px;
        box-shadow: var(--shadow-base, 0 1px 2px rgba(0,0,0,.06));
        transition:transform .12s, box-shadow .12s;
        display:flex !important; flex-direction:column; gap:0;
        color: var(--text-color); width: var(--dnt-card-w); margin-inline:auto;
      }
      html.${CFG.htmlClass} .kanban-card.content:hover{
        transform:translateY(-1px); box-shadow: var(--shadow-lg, 0 8px 22px rgba(0,0,0,.12));
      }

      html.${CFG.htmlClass} .dnt-softfade { transition: opacity .16s ease, filter .16s ease; }
      html.${CFG.htmlClass} .dnt-softfade.dim { opacity:.35; filter: blur(.4px) saturate(.9); }
      @media (prefers-reduced-motion: reduce){
        html.${CFG.htmlClass} .dnt-softfade { transition: none !important; }
      }
      html.${CFG.htmlClass}.dnt-resizing *{ transition: none !important; }

      html.${CFG.htmlClass} .dnt-head{
        display:flex; align-items:center; justify-content:space-between; gap:12px; min-width:0; margin-bottom:10px;
        min-height: var(--dnt-h-head-comfy);
      }
      html.${CFG.htmlClass}.dnt-compact-on .dnt-head{ min-height: var(--dnt-h-head-compact); }

      html.${CFG.htmlClass} .dnt-head-left{ display:flex; align-items:center; gap:10px; min-width:0; flex:1 1 auto; }
      html.${CFG.htmlClass} .kanban-title-area{ margin:0 !important; min-width:0; }
      html.${CFG.htmlClass} .kanban-card-title{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color: var(--text-color); }
      html.${CFG.htmlClass} .dnt-title{ font-weight:600; line-height:1.25; display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; cursor:text; }
      html.${CFG.htmlClass} .dnt-title.is-edit{ outline:none; border-radius:6px; padding:0 2px; background: var(--fg-hover-color); }

      html.${CFG.htmlClass} .kanban-image{
        width:40px !important; height:40px !important; border-radius:10px; overflow:hidden;
        background: var(--bg-color);
        display:flex; align-items:center; justify-content:center; margin:0 !important; flex:0 0 40px;
        box-sizing:border-box; padding:2px;
      }
      html.${CFG.htmlClass} .kanban-image img{ width:100% !important; height:100% !important; object-fit:contain !important; object-position:center; display:block !important; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-image{ width:22px !important; height:22px !important; border-radius:6px; padding:1px; }

      html.${CFG.htmlClass} .kanban-card-meta{ display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin:4px 0 0; }

      html.${CFG.htmlClass} .kanban-card-doc{ padding:0; overflow:visible; }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-kv{
        display:flex; align-items:center; gap:6px;
        background: var(--control-bg);
        border:1px solid var(--border-color);
        border-radius:10px; padding:4px 8px; font-size:12px; min-height:24px; color: var(--text-color);
        white-space:nowrap; overflow:visible; text-overflow:clip;
      }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-kv + .dnt-kv { margin-top:6px; }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-k{ flex:0 0 auto; color: var(--text-muted); }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-v{ flex:1 1 auto; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-weight:600; color: var(--text-color); }

      html.${CFG.htmlClass} .dnt-assign-slot{
        height: var(--dnt-assign-h-comfy);
        min-height: var(--dnt-assign-h-comfy);
        max-height: var(--dnt-assign-h-comfy);
        line-height: var(--dnt-assign-h-comfy);
        margin-top:8px;
        display:flex; align-items:center; justify-content:space-between; gap:8px; overflow:hidden;
      }
      html.${CFG.htmlClass}.dnt-compact-on .dnt-assign-slot{
        height: var(--dnt-assign-h-compact);
        min-height: var(--dnt-assign-h-compact);
        max-height: var(--dnt-assign-h-compact);
        line-height: var(--dnt-assign-h-compact);
      }
      html.${CFG.htmlClass} .dnt-assign-left{ display:flex; align-items:center; gap:6px; flex:1 1 auto; min-width:0; overflow:hidden; }
      html.${CFG.htmlClass} .dnt-assign-right{ display:inline-flex; align-items:center; gap:8px; flex:0 0 auto; white-space:nowrap; }

      html.${CFG.htmlClass} .kanban-assignments{ display:flex; align-items:center; height:100%; max-height:100%; overflow:hidden; }
      html.${CFG.htmlClass} .kanban-assignments .avatar-group{ display:flex; align-items:center; height:100%; }
      html.${CFG.htmlClass} .kanban-assignments .avatar.avatar-small{ width:22px; height:22px; }
      html.${CFG.htmlClass} .kanban-assignments .avatar .avatar-frame.avatar-action{
        width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center;
      }
      html.${CFG.htmlClass} .kanban-assignments .avatar .avatar-frame.avatar-action svg{ width:14px; height:14px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-assignments .avatar.avatar-small{ width:18px; height:18px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-assignments .avatar .avatar-frame.avatar-action{ width:18px; height:18px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-assignments .avatar .avatar-frame.avatar-action svg{ width:12px; height:12px; }

      html.${CFG.htmlClass} .document-star,
      html.${CFG.htmlClass} .star-action,
      html.${CFG.htmlClass} .favorite-action{ display:none !important; }

      html.${CFG.htmlClass} .dnt-assign-right .like-action,
      html.${CFG.htmlClass} .dnt-assign-right [data-action="like"],
      html.${CFG.htmlClass} .dnt-assign-right .btn-like{
        display:inline-flex !important; align-items:center; gap:4px; opacity:1 !important; visibility:visible !important; cursor:pointer;
      }
      html.${CFG.htmlClass} .dnt-like-fallback .es-icon{ width:16px; height:16px; }

      html.${CFG.htmlClass} .dnt-tasks-mini{
        margin-top:6px; width:100%; overflow-y:auto; padding-right:4px;
        border-top:1px solid var(--border-color); padding-top:6px; scrollbar-gutter: stable;
        min-height: var(--dnt-tasks-h-comfy); max-height: var(--dnt-tasks-h-comfy);
      }
      html.${CFG.htmlClass}.dnt-compact-on .dnt-tasks-mini{
        min-height: var(--dnt-tasks-h-compact); max-height: var(--dnt-tasks-h-compact);
      }
      html.${CFG.htmlClass} .dnt-taskline{ display:flex; gap:6px; align-items:center; font-size:11px; color: var(--text-muted); padding:2px 0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; cursor:pointer; }
      html.${CFG.htmlClass} .dnt-taskline .ttl{ font-weight:600; color: var(--text-color); overflow:hidden; text-overflow:ellipsis; }
      html.${CFG.htmlClass} .dnt-chip{ border:1px solid var(--border-color); border-radius:999px; padding:1px 6px; background: var(--control-bg); font-size:10px; color: var(--text-color); }
      html.${CFG.htmlClass} .dnt-overdue{ background: var(--alert-bg-danger); border-color: color-mix(in oklab, var(--alert-bg-danger) 60%, transparent); color: var(--alert-text-danger); }
      html.${CFG.htmlClass} .dnt-task-add{ margin-left:auto; display:inline-flex; align-items:center; gap:4px; padding:0 6px; border-radius:999px; border:1px solid var(--border-color); background: var(--control-bg); text-decoration:none; cursor:pointer; }

      html.${CFG.htmlClass} .kanban-card-meta,
      html.${CFG.htmlClass} .kanban-card-doc,
      html.${CFG.htmlClass} .dnt-assign-slot,
      html.${CFG.htmlClass} .dnt-tasks-mini{
        -webkit-user-drag: none; user-select: none; cursor: grab;
      }

      html.${CFG.htmlClass} .dnt-card-actions{ position:absolute; top:12px; right:12px; display:flex; gap:6px; opacity:0; pointer-events:none; transition:opacity .12s; z-index:5; }
      html.${CFG.htmlClass} .kanban-card-wrapper:hover .dnt-card-actions{ opacity:1; pointer-events:auto; }

      html.${CFG.htmlClass} .dnt-resizer{
        position:absolute; right:4px; bottom:4px; width:16px; height:16px; cursor:nwse-resize;
        opacity:.9; border-radius:4px; display:flex; align-items:center; justify-content:center;
        color: var(--border-color); background: transparent; z-index:6;
      }
      html.${CFG.htmlClass} .kanban-card-wrapper:hover .dnt-resizer{ opacity:1; }

      html.${CFG.htmlClass}.dnt-compact-on .kanban-card.content{ padding:8px; border-radius:12px; gap:6px; }
      html.${CFG.htmlClass}.dnt-compact-on .dnt-head{ margin-bottom:6px; gap:8px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card-title{ font-size:12px; line-height:1.2; }

      @keyframes dnt-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
      html.${CFG.htmlClass} .dnt-skel{ display:grid; gap:6px; }
      html.${CFG.htmlClass} .dnt-skel-line{
        height:12px; border-radius:6px;
        background: linear-gradient(90deg, var(--control-bg) 25%, color-mix(in oklab, var(--control-bg) 70%, white) 50%, var(--control-bg) 75%);
        background-size:200% 100%;
        animation:dnt-shimmer 1.1s linear infinite;
      }
      html.${CFG.htmlClass} .dnt-skel-line.h16{ height:16px; border-radius:8px; }
      html.${CFG.htmlClass} .w20{ width:20%; } .w30{ width:30%; } .w40{ width:40%; } .w50{ width:50%; }
      html.${CFG.htmlClass} .w60{ width:60%; } .w70{ width:70%; } .w80{ width:80%; } .w100{ width:100%; }
      @media (prefers-reduced-motion: reduce){ html.${CFG.htmlClass} .dnt-skel-line{ animation:none; } }

      html.${CFG.htmlClass} .btn.icon-btn svg{ display:block; }
      html.${CFG.htmlClass} .dnt-toggle-labels-text{ display:inline-block; min-width: 120px; }
    `;
    document.head.appendChild(s);
  }

  // ===== Meta helpers, dates, caches
  const LABEL_ALIASES = { display_name: new Set(["display name","display_name","displayname","отображаемое имя","имя профиля","full name","name","фио","имя / фио","имя и фамилия","имя, фамилия"]) };
  const isDisplayName = (s)=> LABEL_ALIASES.display_name.has(LBL_KEY(s));
  function buildMetaMaps(doctype){
    const meta = frappe.get_meta(doctype);
    const label2fn = {}, fn2label = {}, fn2df = {};
    (meta?.fields||[]).forEach(f=>{ const lbl = CLEAN(f?.label||""); if (lbl){ label2fn[LBL_KEY(lbl)] = f.fieldname; fn2label[f.fieldname] = lbl; fn2df[f.fieldname] = f; }});
    (frappe.model.std_fields||[]).forEach(f=>{ const lbl = CLEAN(f?.label||""); if (lbl){ label2fn[LBL_KEY(lbl)] = f.fieldname; fn2label[f.fieldname] = lbl; fn2df[f.fieldname] = fn2df[f.fieldname] || f; }});
    LABEL_ALIASES.display_name.forEach(a=> label2fn[a] = "display_name");
    return { label2fn, fn2label, fn2df };
  }
  function coerceFieldsList(dt, any){
    let arr=[];
    if(Array.isArray(any)) arr=any;
    else if(typeof any==="string" && any.trim()){
      try{ const j=JSON.parse(any); if(Array.isArray(j)) arr=j; } catch{ arr=any.split(/[,\s]+/).filter(Boolean); }
    }
    const meta = frappe.get_meta(dt);
    const fns = new Set((meta?.fields||[]).map(f=>f.fieldname).concat((frappe.model.std_fields||[]).map(f=>f.fieldname), ["name"]));
    const label2fn = {};
    (meta?.fields||[]).forEach(f=>{ if (f?.label) label2fn[LBL_KEY(f.label)] = f.fieldname; });
    (frappe.model.std_fields||[]).forEach(f=>{ if (f?.label) label2fn[LBL_KEY(f.label)] = f.fieldname; });
    const out=[]; arr.forEach(x=>{ const raw=(""+x).trim(); if(!raw) return; if (fns.has(raw)) out.push(raw); else { const g = label2fn[LBL_KEY(raw)]; if (g && fns.has(g)) out.push(g); }});
    return [...new Set(out)];
  }
  const gvCache = new Map();
  const DOC_CACHE = new Map();
  const miniCacheHtml = new Map();
  const miniCacheMeta = new Map();
  const docKey = (dt, name) => `${dt}::${name}`;
  function readFromDocCache(dt, name, fields){
    const key = docKey(dt, name);
    const stored = DOC_CACHE.get(key) || {};
    const out = {}; const missing = [];
    (fields||[]).forEach(f=>{ if (Object.prototype.hasOwnProperty.call(stored, f)) out[f] = stored[f]; else missing.push(f); });
    return { out, missing, stored };
  }
  function mergeDocCache(dt, name, obj){
    const key = docKey(dt, name);
    const prev = DOC_CACHE.get(key) || {};
    const next = Object.assign({}, prev, obj||{});
    DOC_CACHE.set(key, next);
    return next;
  }
  async function getValuesBatch(doctype, name, fields){
    const need = Array.from(new Set((fields||[]).slice()));
    const k = `${doctype}:${name}::${need.slice().sort().join(",")}`;
    if (gvCache.has(k)) return gvCache.get(k);
    let { out, missing } = readFromDocCache(doctype, name, need);
    if (missing.length){
      try{
        const { message } = await frappe.call({ method: "frappe.client.get_value", args: { doctype, filters:{ name }, fieldname: missing }});
        const obj = message || {};
        mergeDocCache(doctype, name, obj);
        out = Object.assign({}, out, obj);
        dbg("🧩 Fields refreshed ↻", name);
      }catch{ dbg("🧩 Fields refresh failed ⚠️", name); }
    } else {
      dbg("✅ Fields from cache", name);
    }
    gvCache.set(k, out);
    return out;
  }
  function composeDisplayName(v){
    const f = CLEAN(v.first_name), m = CLEAN(v.middle_name), l = CLEAN(v.last_name);
    const parts = [f,m,l].filter(Boolean);
    return parts.length ? parts.join(" ") : (CLEAN(v.title) || "");
  }

  // ==== Robust date detection
  const DATE_ISO = /^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?$/;
  const DATE_DOTS = /^\d{2}[./-]\d{2}[./-]\d{4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?$/;
  const HAS_TIME = /\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?/;
  function looksDateLike(v){
    if (!v || typeof v !== "string") return false;
    const s = CLEAN(v);
    if (!s) return false;
    return DATE_ISO.test(s) || DATE_DOTS.test(s) || s.includes("T");
  }
  function normalizeDateish(raw){
    let v = CLEAN(raw || "");
    if (!v) return v;
    if (!looksDateLike(v)) return v;
    try{
      const m = moment(frappe.datetime.convert_to_user_tz(v));
      if (m.isValid()) return HAS_TIME.test(v) || DATE_ISO.test(v) ? m.format("DD-MM-YYYY HH:mm:ss") : m.format("DD-MM-YYYY");
    }catch{}
    return v;
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
    const v = CLEAN(val); if (!v) return v;
    if (/\b\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?\b/.test(v)) return v;
    if (isTranslatableField(fn, df)) { try { return t(v); } catch { return v; } }
    if (/^(Yes|No|Open|Closed)$/i.test(v)) { try { return t(v); } catch {} }
    return v;
  }
  function getBoardOrderMap(doctype){
    try{
      const board = window.cur_list?.board || window.cur_list?.kanban_board;
      const fields = coerceFieldsList(doctype, board?.fields || []);
      const map = new Map(); fields.forEach((fn,i)=> map.set(fn,i));
      return map;
    }catch{ return new Map(); }
  }

  // ===== Skeleton helpers + anti-jank
  function showDocSkeleton(docEl, labelsOn){
    const sk = document.createElement("div"); sk.className = "dnt-skel";
    const rows = labelsOn ? [ "w80","w60","w70","w50","w40" ] : [ "w70","w60","w50" ];
    for (let i=0;i<Math.max(3, rows.length); i++){
      const r = document.createElement("div"); r.className = "dnt-skel-line " + rows[i % rows.length]; sk.appendChild(r);
    }
    docEl.innerHTML=""; docEl.appendChild(sk);
  }
  function showTasksSkeleton(container){
    const sk = document.createElement("div"); sk.className = "dnt-skel";
    const arr = ["w50 h16","w80","w60"];
    arr.forEach(cls => { const d=document.createElement("div"); d.className = "dnt-skel-line " + cls; sk.appendChild(d); });
    container.innerHTML = sk.outerHTML;
  }
  function lockCardHeight(el){
    const wrap = el.closest(".kanban-card-wrapper") || el.closest(".kanban-card") || null;
    if (!wrap) return ()=>{};
    const h = wrap.getBoundingClientRect().height;
    wrap.style.minHeight = Math.max(48, Math.round(h)) + "px";
    const fades = wrap.querySelectorAll(".kanban-card-doc, .kanban-card-meta, .dnt-assign-slot, .dnt-tasks-mini");
    fades.forEach(n => n.classList.add("dnt-softfade","dim"));
    let undone = false;
    return ()=>{
      if (undone) return; undone = true;
      requestAnimationFrame(()=>{
        fades.forEach(n => n.classList.remove("dim"));
        setTimeout(()=>{ wrap.style.removeProperty("min-height"); }, 160);
      });
    };
  }
  function ensure_dashes(container){
    if (!getShowLabelsFlag()) return;
    container.querySelectorAll?.(".dnt-kv .dnt-v")?.forEach(sv=>{
      if (!CLEAN(sv.textContent)) sv.textContent = "—";
    });
  }

  // ===== Build chips (ON/OFF)
  function buildChipsFromCache(ctx){
    const orderMap = getBoardOrderMap(ctx.doctype);
    const labelsOn = getShowLabelsFlag();
    const { fn2label, fn2df } = buildMetaMaps(ctx.doctype);
    const boardFields = [...orderMap.keys()];
    const { out } = readFromDocCache(ctx.doctype, ctx.docName, boardFields);

    const frag = document.createDocumentFragment();
    boardFields.forEach(fn=>{
      const human = fn2label[fn] || (fn==="display_name" ? "Display Name" : fn);
      let val = CLEAN(normalizeDateish(out[fn]));
      if (fn==="display_name" && !val){
        const pseudo = (readFromDocCache(ctx.doctype, ctx.docName, ["first_name","middle_name","last_name","title"]).out);
        val = composeDisplayName(pseudo);
      }
      const locVal = translateValue(ctx.doctype, fn, val, fn2df[fn]) || "";
      if (!labelsOn && !locVal) return;
      const kv = document.createElement("div"); kv.className="dnt-kv text-truncate"; kv.dataset.dntLabel = labelsOn ? human : "";
      if (labelsOn && CLEAN(human)){
        const sk=document.createElement("span"); sk.className="dnt-k"; sk.textContent = t(STRIP_COLON(human))+":";
        kv.appendChild(sk);
      }
      const sv=document.createElement("span"); sv.className="dnt-v"; sv.textContent = labelsOn ? (locVal||"") : locVal; kv.appendChild(sv);
      insertChipAtIndex(frag, kv, orderMap.get(fn) ?? 0);
    });
    if (labelsOn){
      queueMicrotask(()=> {
        Array.from(frag.querySelectorAll?.(":scope > .dnt-kv .dnt-v") || []).forEach(sv=>{
          if (!CLEAN(sv.textContent)) sv.textContent = "—";
        });
      });
    }
    return frag;
  }
  function insertChipAtIndex(container, chip, idx){
    const nodes = Array.from(container.querySelectorAll(":scope > .dnt-kv"));
    const target = nodes[idx];
    if (target) container.insertBefore(chip, target); else container.appendChild(chip);
  }

  // ===== Backfill / normalize (исключаем поле статуса из сравнения)
  function getExcludedSnapshotFields(){
    const f = getColumnField();
    return new Set([CLEAN(f).toLowerCase()]);
  }

  function normalizeDocFields(docEl, ctx, opts={}){
    if (!docEl) return;
    const orderMap = getBoardOrderMap(ctx.doctype);
    const boardFields = [...orderMap.keys()];
    const { out, missing } = readFromDocCache(ctx.doctype, ctx.docName, boardFields);

    const labelsOn = getShowLabelsFlag();
    const tasksMeta = miniCacheMeta.get(ctx.docName);
    const tasksVer  = (opts.tasksVersion != null ? opts.tasksVersion : (tasksMeta?.versionKey || "")) || "";

    const excluded = getExcludedSnapshotFields();
    const snapshot = {};
    boardFields.forEach(fn => {
      if (!excluded.has(CLEAN(fn).toLowerCase())) snapshot[fn] = CLEAN(out[fn] ?? "");
    });
    const card_hash_if_ready = json_hash({ labelsOn, snapshot, tasksVer });

    if (!missing.length){
      if (docEl.dataset.dntCardHash !== card_hash_if_ready){
        const unlock = lockCardHeight(docEl);
        const frag = buildChipsFromCache(ctx);
        docEl.innerHTML = "";
        docEl.appendChild(frag);
        ensure_dashes(docEl);
        docEl.dataset.dntCardHash = card_hash_if_ready;

        if (opts.cause !== "tasks"){
          const mini = docEl.parentElement?.querySelector(".dnt-tasks-mini");
          if (mini && mini.dataset.dntMiniInit!=="1") {
            if (miniCacheHtml.has(ctx.docName)){
              mini.innerHTML = miniCacheHtml.get(ctx.docName);
              bindMini(mini, ctx.docName);
              mini.dataset.dntMiniInit = "1";
              dbg("✅ Tasks from cache (init)", ctx.docName);
            } else {
              setTimeout(()=> loadMini(mini, ctx.docName, { soft:true }), 0);
            }
          }
        }
        unlock();
      } else {
        dbg("✅ Fields up-to-date (hash match)", ctx.docName);
      }
      return;
    }

    if (docEl.dataset.dntCardHash !== "loading"){
      const unlock = lockCardHeight(docEl);
      showDocSkeleton(docEl, labelsOn);
      docEl.dataset.dntCardHash = "loading";
      setTimeout(unlock, 160);
    }

    queueMicrotask(async ()=>{
      const holder = document.createElement("div");
      await backfillAll(holder, ctx, labelsOn, orderMap);

      const v = await getValuesBatch(ctx.doctype, ctx.docName, boardFields);
      const snapshot2 = {};
      boardFields.forEach(fn => {
        if (!excluded.has(CLEAN(fn).toLowerCase())) snapshot2[fn] = CLEAN(v[fn] ?? "");
      });
      const done_hash = json_hash({ labelsOn, snapshot: snapshot2, tasksVer });

      if (docEl.dataset.dntCardHash !== done_hash){
        const unlock = lockCardHeight(docEl);
        docEl.innerHTML = "";
        Array.from(holder.childNodes).forEach(n => docEl.appendChild(n));
        ensure_dashes(docEl);
        docEl.dataset.dntCardHash = done_hash;

        if (opts.cause !== "tasks"){
          const mini = docEl.parentElement?.querySelector(".dnt-tasks-mini");
          if (mini && mini.dataset.dntMiniInit!=="1") {
            if (miniCacheHtml.has(ctx.docName)){
              mini.innerHTML = miniCacheHtml.get(ctx.docName);
              bindMini(mini, ctx.docName);
              mini.dataset.dntMiniInit = "1";
              dbg("✅ Tasks from cache (init)", ctx.docName);
            } else {
              setTimeout(()=> loadMini(mini, ctx.docName, { soft:true }), 0);
            }
          }
        }
        unlock();
      }
    });
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

    const v = await getValuesBatch(ctx.doctype, ctx.docName, boardFields);
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
          chip = document.createElement("div"); chip.className="dnt-kv text-truncate"; chip.dataset.dntLabel = human;
          const sk=document.createElement("span"); sk.className="dnt-k"; sk.textContent = t(STRIP_COLON(human))+":";
          const sv=document.createElement("span"); sv.className="dnt-v"; sv.textContent = locVal || "—";
          chip.appendChild(sk); chip.appendChild(sv);
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
      ensure_dashes(container);
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

    const { fn2df: fn2df2 } = buildMetaMaps(ctx.doctype);
    boardFields.forEach(fn=>{
      const raw = v[fn];
      const norm = CLEAN(normalizeDateish(raw));
      const locVal = translateValue(ctx.doctype, fn, norm, fn2df2[fn]);
      if (!locVal) return;
      const pool = valueIndex.get(norm) || valueIndex.get(locVal) || [];
      const pick = pool.shift?.();
      if (pick){
        const sv = pick.querySelector(".dnt-v"); if (sv) sv.textContent = locVal;
        insertChipAtIndex(container, pick, orderMap.get(fn) ?? 0);
        assignedValues.add(locVal);
      } else {
        const chip = document.createElement("div"); chip.className="dnt-kv text-truncate";
        const sv=document.createElement("span"); sv.className="dnt-v"; sv.textContent = locVal;
        chip.appendChild(sv);
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
  }

  // ===== Mini-tasks
  const fmtDT = (dt) => { try { return moment(frappe.datetime.convert_to_user_tz(dt)).format("DD-MM-YYYY HH:mm:ss"); } catch { return dt; } };
  function planLabel(kind){ return kind==="target" ? t("Target at") : t("Planned"); }
  function pickPlan(t){ if (t.custom_target_datetime) return { dt: t.custom_target_datetime, kind: "target" }; return { dt: null, kind: null }; }
  function plain_text(html_like){ const div=document.createElement("div"); div.innerHTML = html_like || ""; return CLEAN(div.textContent || div.innerText || ""); }
  function truncate_text(s, max_len=40){ const str = s || ""; return str.length<=max_len?str:(str.slice(0,max_len).trimEnd()+"…"); }

  function miniHeader(total, caseName){
    const cnt = typeof total === "number" ? ` (${total})` : "";
    return `<div class="dnt-taskline" data-act="noop" style="cursor:default">
      <span class="dnt-chip">${frappe.utils.escape_html(t("Tasks")+cnt)}</span>
      <a href="#" class="dnt-task-add" data-act="create-task" data-case="${frappe.utils.escape_html(caseName||"")}" title="${frappe.utils.escape_html(t("New task"))}">
        ${ICONS.plus}<span>${frappe.utils.escape_html(t("New"))}</span>
      </a>
    </div>`;
  }
  function miniHtml(rows, total, caseName){
    const totalCount = typeof total === "number" ? total : (rows?.length || 0);
    const showOpenAll = totalCount > 1 || (rows?.length || 0) > 1;
    if (!rows?.length) return miniHeader(totalCount, caseName) + `<div class="dnt-taskline"><span class="ttl">${t("No open tasks")}</span></div>`;
    const lines = rows.map(ti=>{
      const pick = pickPlan(ti); const p = pick.dt;
      const open = (ti.status||"Open")==="Open";
      const overdue = p && open && moment(p).isBefore(moment());
      const val = p ? fmtDT(p) : "—";
      const cls = p && overdue ? "dnt-chip dnt-overdue" : "dnt-chip";
      const ttl  = frappe.utils.escape_html(truncate_text(plain_text(ti.description || ti.name), 40));
      return `<div class="dnt-taskline" data-open="${frappe.utils.escape_html(ti.name)}"><span class="${cls}" title="${frappe.utils.escape_html(planLabel(pick.kind))}">${frappe.utils.escape_html(val)}</span><span class="ttl" title="${ttl}">${ttl}</span></div>`;
    }).join("");
    const more = showOpenAll ? `<div class="dnt-taskline" data-act="open-all"><span class="ttl">${frappe.utils.escape_html(t("Open all tasks") + " →")}</span></div>` : ``;
    return miniHeader(totalCount, caseName) + lines + more;
  }

  // === NEW: версия задач только по count и макс. custom_target_datetime + кэш между перезагрузками
  async function tasks_version(caseName){
    const [cntResp, lastTargetResp] = await Promise.all([
      frappe.call({ method: "frappe.client.get_count", args: {
        doctype: "ToDo",
        filters: { reference_type: CFG.caseDoctype, reference_name: caseName, status: "Open" }
      }}),
      frappe.call({ method: "frappe.client.get_list", args: {
        doctype: "ToDo",
        filters: { reference_type: CFG.caseDoctype, reference_name: caseName, status: "Open", custom_target_datetime: ["is", "set"] },
        fields: ["custom_target_datetime"],
        limit_page_length: 1,
        order_by: "custom_target_datetime desc"
      }})
    ]);
    const total = +((cntResp?.message)||0);
    const lastTarget = ((lastTargetResp?.message||[])[0]?.custom_target_datetime) || "";
    return { versionKey: `${total}|${lastTarget||"__no_target__"}`, total };
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
          fields: ["name","description","status","date","custom_due_datetime","custom_target_datetime","modified"],
          limit_page_length: CFG.tasksLimit,
          order_by: "modified desc"
        }
      });
      return { rows, total: rows.length };
    } catch { return { rows: [], total: 0 }; }
  }

  async function loadMini(container, caseName, opts={}){
    const soft = !!opts.soft;
    const lsHtmlKey = `dntMiniHtml::${caseName}`;
    const lsMetaKey = `dntMiniMeta::${caseName}`;
    const metaPrev = miniCacheMeta.get(caseName);
    try{
      if (!soft) showTasksSkeleton(container);

      const metaNow = await tasks_version(caseName);

      // 1) Проверяем кэш из localStorage (живёт между перезагрузками)
      const lsMetaRaw = ls_get(lsMetaKey);
      const lsHtml = ls_get(lsHtmlKey);
      let lsMeta = null;
      try{ lsMeta = lsMetaRaw ? JSON.parse(lsMetaRaw) : null; }catch{ lsMeta = null; }

      if (lsMeta && lsMeta.versionKey === metaNow.versionKey && lsHtml){
        miniCacheHtml.set(caseName, lsHtml);
        miniCacheMeta.set(caseName, { versionKey: metaNow.versionKey });
        container.innerHTML = lsHtml;
        bindMini(container, caseName);
        container.dataset.dntMiniInit = "1";
        dbg("✅ Tasks from localStorage cache", caseName);
        container.dispatchEvent(new CustomEvent("dnt:tasks-version", { detail: { versionKey: metaNow.versionKey }}));
        return;
      }

      // 2) Проверяем кэш в памяти текущей сессии
      if (metaPrev && metaPrev.versionKey === metaNow.versionKey && miniCacheHtml.has(caseName)){
        const html = miniCacheHtml.get(caseName);
        container.innerHTML = html;
        bindMini(container, caseName);
        container.dataset.dntMiniInit = "1";
        // синхронизируем localStorage
        ls_set(lsHtmlKey, html);
        ls_set(lsMetaKey, JSON.stringify({ versionKey: metaNow.versionKey }));
        dbg("✅ Tasks from cache", caseName);
        container.dispatchEvent(new CustomEvent("dnt:tasks-version", { detail: { versionKey: metaNow.versionKey }}));
        return;
      }

      // 3) Тянем список только если версия изменилась/кэша нет
      let data = await fetchMiniPrimary(caseName);
      if ((!data.rows || !data.rows.length) && (!data.total || data.total === 0)) data = await fetchMiniFallback(caseName);
      const html  = miniHtml(data.rows || [], data.total || 0, caseName);
      miniCacheHtml.set(caseName, html);
      miniCacheMeta.set(caseName, { versionKey: metaNow.versionKey });
      ls_set(lsHtmlKey, html);
      ls_set(lsMetaKey, JSON.stringify({ versionKey: metaNow.versionKey }));

      const unlock = lockCardHeight(container);
      container.innerHTML = html;
      bindMini(container, caseName);
      container.dataset.dntMiniInit = "1";
      unlock();

      dbg(metaPrev ? "♻️ Tasks refreshed" : "🆕 Tasks first load", caseName);
      container.dispatchEvent(new CustomEvent("dnt:tasks-version", { detail: { versionKey: metaNow.versionKey }}));
    } catch {
      if (miniCacheHtml.has(caseName)){
        const unlock = lockCardHeight(container);
        const html = miniCacheHtml.get(caseName);
        container.innerHTML = html;
        bindMini(container, caseName);
        container.dataset.dntMiniInit = "1";
        unlock();
        dbg("✅ Tasks from cache (fallback)", caseName);
        container.dispatchEvent(new CustomEvent("dnt:tasks-version", { detail: { versionKey: (miniCacheMeta.get(caseName)?.versionKey || "") }}));
        return;
      }
      const lsHtml = ls_get(lsHtmlKey);
      const lsMetaRaw = ls_get(lsMetaKey);
      if (lsHtml && lsMetaRaw){
        let parsed=null; try{ parsed = JSON.parse(lsMetaRaw); }catch{}
        miniCacheHtml.set(caseName, lsHtml);
        if (parsed?.versionKey) miniCacheMeta.set(caseName, { versionKey: parsed.versionKey });
        const unlock = lockCardHeight(container);
        container.innerHTML = lsHtml;
        bindMini(container, caseName);
        container.dataset.dntMiniInit = "1";
        unlock();
        dbg("✅ Tasks from localStorage (fallback)", caseName);
        container.dispatchEvent(new CustomEvent("dnt:tasks-version", { detail: { versionKey: (parsed?.versionKey || "") }}));
        return;
      }
      try{
        const data = await fetchMiniFallback(caseName);
        const html  = miniHtml(data.rows || [], data.total || 0, caseName);
        miniCacheHtml.set(caseName, html);
        const metaNow = await tasks_version(caseName).catch(()=>({versionKey:""}));
        miniCacheMeta.set(caseName, { versionKey: metaNow.versionKey||"" });
        ls_set(lsHtmlKey, html);
        ls_set(lsMetaKey, JSON.stringify({ versionKey: metaNow.versionKey||"" }));

        const unlock = lockCardHeight(container);
        container.innerHTML = html;
        bindMini(container, caseName);
        container.dataset.dntMiniInit = "1";
        unlock();

        dbg("♻️ Tasks refreshed (fallback)", caseName);
        container.dispatchEvent(new CustomEvent("dnt:tasks-version", { detail: { versionKey: (metaNow.versionKey || "") }}));
      }catch{
        container.innerHTML = miniHeader(0, caseName) + `<div class="dnt-taskline"><span class="ttl">${t("No open tasks")}</span></div>`;
        dbg("⚠️ Tasks empty / error", caseName);
        container.dispatchEvent(new CustomEvent("dnt:tasks-version", { detail: { versionKey: "" }}));
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
    container.querySelector('[data-act="create-task"]')?.addEventListener("click",(e)=>{
      e.preventDefault(); e.stopPropagation();
      const cName = e.currentTarget.getAttribute("data-case") || caseName;
      try {
        frappe.new_doc("ToDo", { reference_type: CFG.caseDoctype, reference_name: cName, status: "Open" });
      } catch {
        frappe.set_route("Form","ToDo","new-to-do-1");
        setTimeout(()=> {
          try {
            cur_frm?.set_value("reference_type", CFG.caseDoctype);
            cur_frm?.set_value("reference_name", cName);
            cur_frm?.set_value("status","Open");
          } catch {}
        }, 200);
      }
    });
  }

  // ===== Like
  function ensureVisibleAction(el){
    try{
      el.classList.remove("hidden","hide"); el.style.removeProperty("display"); el.removeAttribute("aria-hidden");
      el.style.opacity = "1"; el.style.visibility = "visible"; el.style.cursor = "pointer";
      el.classList.add("dnt-softfade");
    }catch{}
  }
  function detectLikeFrom(root){ return root.querySelector(".like-action, .list-row-like, .liked-by, [data-action='like'], .btn-like"); }
  function createFallbackLike(doctype, name){
    const span = document.createElement("span");
    span.className = "like-action not-liked dnt-like-fallback dnt-softfade";
    span.setAttribute("data-doctype", doctype);
    span.setAttribute("data-name", name);
    span.setAttribute("title", t("Like"));
    span.innerHTML = `<svg class="es-icon es-line icon-sm" aria-hidden="true"><use class="like-icon" href="#es-solid-heart"></use></svg>`;
    let busy = false;
    span.addEventListener("click", async (e)=>{
      e.preventDefault(); e.stopPropagation();
      if (busy) return; busy = true;
      try{
        await frappe.call("frappe.desk.like.toggle_like", { doctype, name });
        span.classList.toggle("liked");
        span.classList.toggle("not-liked");
      } finally { busy = false; }
    });
    return span;
  }

  // ===== Drag из динамических зон
  function enableDragFromDynamicAreas(body){
    const areas = [ body.querySelector(".kanban-card-meta"), body.querySelector(".kanban-card-doc"), body.querySelector(".dnt-assign-slot"), body.querySelector(".dnt-tasks-mini") ].filter(Boolean);
    areas.forEach(area=>{
      if (area.__dntDragFixApplied) return;
      area.__dntDragFixApplied = true;
      area.addEventListener("mousedown", (e)=>{
        if (e.button !== 0) return;
        const tag = (e.target?.tagName||"").toLowerCase();
        if (/^(a|button|input|textarea|select|svg|path|use)$/i.test(tag)) return;
        e.preventDefault();
      }, true);
      area.addEventListener("touchstart", ()=>{
        try{ area.style.touchAction = "none"; setTimeout(()=> area.style.touchAction = "", 500); }catch{}
      }, { passive: true });
    });
  }

  // ===== Title inline-edit
  function makeTitleEditable(titleArea, name, doctype){
    if (!titleArea || titleArea.__dntEditable) return;
    titleArea.__dntEditable = true;
    const anchor = titleArea.querySelector("a");
    const currentText = (titleArea.querySelector(".kanban-card-title")?.textContent || anchor?.textContent || name || "").trim();
    const holder = titleArea.querySelector(".kanban-card-title") || document.createElement("div");
    holder.classList.add("kanban-card-title"); holder.innerHTML = "";
    const span = document.createElement("span");
    span.className = "dnt-title dnt-softfade"; span.textContent = currentText;
    holder.appendChild(span);
    if (anchor) anchor.replaceWith(holder); else titleArea.appendChild(holder);
    let beforeEdit = currentText;
    function toEdit(){ if (span.isContentEditable) return; beforeEdit = span.textContent || ""; span.classList.add("is-edit"); span.setAttribute("contenteditable","true"); span.focus();
      const sel = window.getSelection?.(); if (sel && document.createRange){ const r = document.createRange(); r.selectNodeContents(span); r.collapse(false); sel.removeAllRanges(); sel.addRange(r); } }
    function saveEdit(){
      if (!span.isContentEditable) return;
      const val = CLEAN(span.textContent || "");
      const done = ()=>{ span.classList.remove("is-edit"); span.removeAttribute("contenteditable"); };
      if (!val || val === beforeEdit){ done(); return; }
      frappe.call({ method:"frappe.client.set_value", args:{ doctype, name, fieldname:"title", value: val } })
        .then(()=>{ frappe.show_alert({ message: t("Title updated"), indicator:"green" }); beforeEdit = val; done(); })
        .catch(()=>{ frappe.msgprint({ message: t("Failed to update title"), indicator:"red" }); span.textContent = beforeEdit; done(); });
    }
    function cancelEdit(){ if (!span.isContentEditable) return; span.textContent = beforeEdit; span.classList.remove("is-edit"); span.removeAttribute("contenteditable"); }
    span.addEventListener("dblclick", (e)=>{ e.preventDefault(); e.stopPropagation(); toEdit(); });
    span.addEventListener("click", (e)=> e.stopPropagation());
    span.addEventListener("keydown", (e)=>{ if (e.key==="Enter"){ e.preventDefault(); saveEdit(); span.blur(); } if (e.key==="Escape"){ e.preventDefault(); cancelEdit(); span.blur(); }});
    span.addEventListener("blur", saveEdit);
  }

  // ===== Lazy observe
  const visibleCards = new WeakSet();
  let lazyIO = null;
  function ensureLazyIO(){
    if (lazyIO) return lazyIO;
    try{
      lazyIO = new IntersectionObserver(entries=>{
        entries.forEach(entry=>{
          const wrap = entry.target;
          if (entry.isIntersecting){
            visibleCards.add(wrap);
            upgradeCard(wrap);
            refreshCardDocForWrap(wrap);
            lazyIO.unobserve(wrap);
          }
        });
      }, { root:null, rootMargin:"200px", threshold:0.01 });
    }catch{ lazyIO = null; }
    return lazyIO;
  }
  function observeForLazy(wrap){
    const io = ensureLazyIO();
    if (io) io.observe(wrap);
  }
  function isWrapVisible(wrap){
    if (visibleCards.has(wrap)) return true;
    try{
      const r = wrap.getBoundingClientRect();
      const vh = window.innerHeight || document.documentElement.clientHeight;
      const vw = window.innerWidth  || document.documentElement.clientWidth;
      return r.bottom >= -180 && r.top <= vh + 180 && r.right >= -50 && r.left <= vw + 50;
    }catch{ return true; }
  }
  function refreshCardDocForWrap(wrap){
    const dt = getDoctype();
    const body = wrap.querySelector(".kanban-card-body") || wrap;
    const docEl = body?.querySelector(".kanban-card-doc");
    const name = wrap.getAttribute("data-name") || wrap.dataset?.name || body?.querySelector?.(".kanban-card")?.getAttribute?.("data-name") || "";
    if (dt && name && docEl) normalizeDocFields(docEl, { doctype: dt, docName: name });
  }

  // ===== Positions map
  const POS_MAP = new Map();
  function getCardColumnValue(wrap){
    return wrap?.closest(".kanban-column")?.getAttribute("data-column-value") || "";
  }
  function forceReloadTasksForWrap(wrap){
    const body = wrap.querySelector(".kanban-card-body") || wrap;
    const name = wrap.getAttribute("data-name") || wrap.dataset?.name || body?.querySelector?.(".kanban-card")?.getAttribute?.("data-name") || "";
    const mini = body?.querySelector(".dnt-tasks-mini");
    if (name && mini){ loadMini(mini, name, { soft:true }); }
  }

  // ===== Card upgrade
  function attachResizer(wrapper){
    if (!wrapper || wrapper.querySelector(".dnt-resizer")) return;
    const card = wrapper.querySelector(".kanban-card.content") || wrapper.querySelector(".kanban-card");
    const col = wrapper.closest(".kanban-column");
    if (!card || !col) return;
    const handle = document.createElement("div");
    handle.className = "dnt-resizer"; handle.title = t("Resize width"); handle.innerHTML = ICONS.resizerGrip;
    wrapper.appendChild(handle);
    let currentW = null;
    const startResize = (evStart)=>{
      if (!(evStart instanceof PointerEvent)) return;
      evStart.preventDefault(); evStart.stopPropagation(); evStart.stopImmediatePropagation();
      handle.setPointerCapture?.(evStart.pointerId);
      const startX = evStart.clientX;
      const startRect = card.getBoundingClientRect();
      const mode = currentMode();
      document.documentElement.classList.add("dnt-resizing");
      const stopper = (ev)=>{ ev.preventDefault(); ev.stopPropagation(); ev.stopImmediatePropagation(); };
      const cutDown = (ev)=>{ if (!ev.target?.closest(".dnt-resizer")) { ev.preventDefault(); ev.stopPropagation(); ev.stopImmediatePropagation(); } };
      document.addEventListener("dragstart", stopper, true);
      document.addEventListener("selectstart", stopper, true);
      document.addEventListener("mousedown", cutDown, true);
      document.addEventListener("touchstart", cutDown, true);
      document.addEventListener("pointerdown", cutDown, true);
      const onMove = (ev)=>{
        if (!(ev instanceof PointerEvent)) return;
        const dx = ev.clientX - startX;
        let w = Math.round(startRect.width + dx);
        w = Math.max(CFG.minCardW, Math.min(CFG.maxCardW, w));
        currentW = w;
        col.style.setProperty("--dnt-card-w", w + "px");
        col.style.minWidth = `calc(${w}px + 24px)`;
        card.style.width = w + "px";
        setSessW(col, mode, w);
        ev.preventDefault(); ev.stopPropagation(); ev.stopImmediatePropagation();
      };
      const endResize = (ev)=>{
        document.removeEventListener("pointermove", onMove, true);
        document.removeEventListener("pointerup", endResize, true);
        document.removeEventListener("pointercancel", endResize, true);
        document.removeEventListener("dragstart", stopper, true);
        document.removeEventListener("selectstart", stopper, true);
        document.removeEventListener("mousedown", cutDown, true);
        document.removeEventListener("touchstart", cutDown, true);
        document.removeEventListener("pointerdown", cutDown, true);
        handle.releasePointerCapture?.(evStart.pointerId);
        if (currentW != null){ saveColW(col, mode, currentW); }
        card.style.removeProperty("width");
        document.documentElement.classList.remove("dnt-resizing");
        normalizeColumns();
      };
      document.addEventListener("pointermove", onMove, true);
      document.addEventListener("pointerup", endResize, true);
      document.addEventListener("pointercancel", endResize, true);
    };
    handle.addEventListener("pointerdown", startResize, { passive:false, capture:true });
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

    [meta, doc, body.querySelector(".dnt-assign-slot"), body.querySelector(".dnt-tasks-mini")]
      .filter(Boolean).forEach(n => n.classList.add("dnt-softfade"));

    let head = body.querySelector(".dnt-head"); if(!head){ head = document.createElement("div"); head.className = "dnt-head"; body.prepend(head); }
    let left = head.querySelector(".dnt-head-left"); if(!left){ left = document.createElement("div"); left.className = "dnt-head-left"; head.prepend(left); }
    if (img && !left.contains(img)) left.prepend(img);
    if (title) { title.querySelectorAll("br").forEach(br=>br.remove()); if(!left.contains(title)) left.appendChild(title); }
    if (meta && meta.parentElement !== head) head.appendChild(meta);
    if (doc && doc.previousElementSibling !== head) body.insertBefore(doc, head.nextSibling);

    const name = wrapper.getAttribute("data-name") || wrapper.dataset.name || card.getAttribute("data-name") || "";
    const doctype = getDoctype();

    if (doc && isWrapVisible(wrapper)) normalizeDocFields(doc, { doctype, docName: name });

    let assignSlot = body.querySelector(".dnt-assign-slot"); if (!assignSlot){ assignSlot = document.createElement("div"); assignSlot.className = "dnt-assign-slot dnt-softfade"; body.appendChild(assignSlot); }
    let assignLeft = assignSlot.querySelector(".dnt-assign-left"); if (!assignLeft){ assignLeft = document.createElement("div"); assignLeft.className = "dnt-assign-left"; assignSlot.appendChild(assignLeft); }
    let assignRight = assignSlot.querySelector(".dnt-assign-right"); if (!assignRight){ assignRight = document.createElement("div"); assignRight.className = "dnt-assign-right"; assignSlot.appendChild(assignRight); }

    const assignments = (meta || body).querySelector(".kanban-assignments");
    if (assignments && assignments.parentElement !== assignLeft) assignLeft.appendChild(assignments);

    body.querySelectorAll(".document-star, .star-action, .favorite-action").forEach(el=> el.remove());

    let like = detectLikeFrom(body) || detectLikeFrom(card);
    if (like){ ensureVisibleAction(like); if (like.parentElement !== assignRight) assignRight.appendChild(like); }
    else if (doctype && name){ assignRight.appendChild(createFallbackLike(doctype, name)); }

    let mini = body.querySelector(".dnt-tasks-mini");
    if (!mini){ mini = document.createElement("div"); mini.className = "dnt-tasks-mini dnt-softfade"; body.appendChild(mini); }

    // Мгновенный показ из localStorage, затем лёгкая проверка версии
    if (doctype === CFG.caseDoctype && name) {
      const lsHtml = ls_get(`dntMiniHtml::${name}`);
      const lsMetaRaw = ls_get(`dntMiniMeta::${name}`);
      if (lsHtml && lsMetaRaw){
        let parsed=null; try{ parsed = JSON.parse(lsMetaRaw); }catch{}
        if (parsed?.versionKey){
          mini.innerHTML = lsHtml;
          bindMini(mini, name);
          mini.dataset.dntMiniInit = "1";
          miniCacheHtml.set(name, lsHtml);
          miniCacheMeta.set(name, { versionKey: parsed.versionKey });
          dbg("✅ Prime tasks from localStorage (upgrade)", name);
        }
      }
      mini.addEventListener("dnt:tasks-version", (e)=>{
        normalizeDocFields(doc, { doctype, docName: name }, { cause: "tasks", tasksVersion: e.detail?.versionKey });
      });
      setTimeout(()=> loadMini(mini, name, { soft:true }), 0);
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
        const bname = getBoardName();
        const flag = CFG.boardFieldByTitle[bname];
        const canSoft = !!flag;
        const d = new frappe.ui.Dialog({
          title: t("Card actions"),
          primary_action_label: canSoft ? t("Remove from this board") : t("Delete"),
          primary_action: ()=> {
            if (canSoft) {
              frappe.call({ method:"frappe.client.set_value", args:{ doctype, name, fieldname: flag, value: 0 } })
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

    makeTitleEditable(title, name, doctype);
    attachResizer(wrapper);
    enableDragFromDynamicAreas(body);

    POS_MAP.set(name, getCardColumnValue(wrapper));

    card.dataset.dntUpgraded = "1";
  }

  function enhanceCards(){
    document.querySelectorAll(".kanban-card-wrapper, .kanban-column .kanban-card:not(.content)").forEach(w => {
      const wrap = w.classList.contains?.("kanban-card") ? w.closest(".kanban-card-wrapper") || w : w;
      if (isWrapVisible(wrap)) upgradeCard(wrap); else observeForLazy(wrap);
    });
  }
  function refreshVisibleCardsDocs(){
    document.querySelectorAll(".kanban-card-wrapper, .kanban-column .kanban-card").forEach(w => {
      const wrap = w.classList.contains?.("kanban-card") ? w.closest(".kanban-card-wrapper") || w : w;
      if (!isWrapVisible(wrap)) return;
      refreshCardDocForWrap(wrap);
    });
  }

  // ===== Column header counters
  function headerOfColumn(col){
    return col.querySelector(".kanban-column-title, .kanban-title, .kanban-title-area, .kanban-column .title, .kanban-card-title-area") || null;
  }
  function countCards(col){
    return col.querySelectorAll(".kanban-card-wrapper, .kanban-cards > .kanban-card").length;
  }
  function updateColumnCounts(){
    getColumnsEl().forEach(col=>{
      const head = headerOfColumn(col);
      if (!head) return;
      let badge = head.querySelector(".dnt-col-count");
      const n = countCards(col);
      if (!badge){
        badge = document.createElement("span");
        badge.className = "dnt-col-count";
        head.appendChild(badge);
      }
      badge.textContent = ` (${n})`;
    });
  }

  // ===== Header controls (settings icon fix)
  function findSettingsAnchor(){
    return (
      document.querySelector(".page-actions .page-icon-group") ||
      document.querySelector(".page-actions") ||
      document.querySelector(".standard-actions .page-icon-group") ||
      document.querySelector(".standard-actions") ||
      document.querySelector(".page-head-content") ||
      document.querySelector(".page-title")
    );
  }
  function hideViewSwitcher(){
    const candidates = Array.from(document.querySelectorAll(".standard-actions .menu-btn-group, .page-actions .menu-btn-group, .page-actions .btn-group, .standard-actions .btn-group"));
    candidates.forEach(g=>{
      const txt = CLEAN(g.textContent||"").toLowerCase();
      const hasViewWords = /view|вид/i.test(g.querySelector("[title]")?.getAttribute("title")||"") || /list|report|kanban|calendar|вид|список|отчет/i.test(txt);
      const looksSwitcher = g.querySelector("button.dropdown-toggle, .view-switcher, .btn-view-switcher");
      if (looksSwitcher && hasViewWords){ g.style.display = "none"; }
    });
  }
  function slugDoctype(dt){ return (frappe?.router?.slug?.(dt)) || (dt||"").toLowerCase().replace(/\s+/g,"-"); }
  function routeToListWithBoardFilter(){
    const dt = getDoctype();
    const boardTitle = getBoardName();
    if (!dt) return;
    const field = CFG.boardFieldByTitle[boardTitle] || "";
    if (field){
      try{ frappe.route_options = Object.assign({}, frappe.route_options, { [field]: 1 }); }catch{}
      const path = `/app/${slugDoctype(dt)}/view/list?${encodeURIComponent(field)}=1`;
      window.location.assign(path);
      return;
    }
    frappe.set_route("List", dt, "List");
  }
  function resolveSettingsIcon(){
    try{
      const tries = ["settings","settings-2","setup","preferences","sliders","cog","gear","sliders-horizontal"];
      for (const key of tries){
        const svg = (frappe.utils?.icon && frappe.utils.icon(key,"sm")) || (frappe.ui?.icon && frappe.ui.icon(key,"sm")) || "";
        if (svg && typeof svg === "string" && svg.indexOf("<svg") !== -1) return svg;
      }
    }catch{}
    return ICONS.settings;
  }
  function buildSettingsDropdown(){
    const wrap = document.createElement("div");
    wrap.id = CFG.settingsBtnId;
    wrap.className = "btn-group btn-group-sm";
    const btn = document.createElement("button");
    btn.className = "btn btn-default icon-btn btn-sm dropdown-toggle";
    btn.setAttribute("data-toggle","dropdown");
    btn.setAttribute("aria-expanded","false");
    btn.setAttribute("title", t("Kanban options"));
    btn.innerHTML = ICONS.settings; // или ICONS.listIcon
    wrap.appendChild(btn);
    const menu = document.createElement("ul");
    menu.className = "dropdown-menu";
    menu.innerHTML = `
      <li><a class="grey-link dropdown-item dnt-open-board-settings" href="#" onclick="return false;">${frappe.utils.icon("edit","sm")} <span class="menu-item-label">${t("Board Settings")}</span></a></li>
      <li class="dropdown-divider"></li>
      <li><a class="grey-link dropdown-item dnt-toggle-labels" href="#" onclick="return false;">${frappe.utils.icon("tag","sm")} <span class="menu-item-label dnt-toggle-labels-text"></span></a></li>
    `;
    wrap.appendChild(menu);
    const labelsText = menu.querySelector(".dnt-toggle-labels-text");
    const isLabelsOn = () => getShowLabelsFlag();
    const refreshLabelsText = () => { labelsText.textContent = isLabelsOn() ? t("Hide labels") : t("Show labels"); };
    refreshLabelsText();
    btn.addEventListener("show.bs.dropdown", refreshLabelsText);
    btn.addEventListener("shown.bs.dropdown", refreshLabelsText);
    btn.addEventListener("hidden.bs.dropdown", refreshLabelsText);
    btn.addEventListener("click", () => setTimeout(refreshLabelsText, 0));

    menu.querySelector(".dnt-open-board-settings").addEventListener("click",(e)=>{
      e.preventDefault(); e.stopPropagation();
      const bname = getBoardName();
      if (bname) frappe.set_route(`/app/kanban-board/${encodeURIComponent(bname)}`);
    });
    menu.querySelector(".dnt-toggle-labels").addEventListener("click", async (e)=>{
      e.preventDefault(); e.stopPropagation();
      const bname = getBoardName(); if (!bname) return;
      const want = !isLabelsOn();
      try{
        await frappe.call({ method: "frappe.client.set_value", args: { doctype: "Kanban Board", name: bname, fieldname: "show_labels", value: want ? 1 : 0 }});
        if (window.cur_list?.board) window.cur_list.board.show_labels = want;
        if (window.cur_list?.kanban_board) window.cur_list.kanban_board.show_labels = want;
        refreshLabelsText();
        refreshVisibleCardsDocs();
        dbg(want ? "🔖 Labels shown" : "🔖 Labels hidden");
        frappe.show_alert({ message: want ? t("Labels shown") : t("Labels hidden"), indicator: "green" });
      } catch {
        frappe.msgprint?.({ message: t("Failed to toggle labels"), indicator: "red" });
      }
    });
    return wrap;
  }
  function exposeSelectKanban(){
    document.querySelectorAll(".custom-actions").forEach(el=>{
      el.classList.remove("hide","hidden-xs","hidden-sm","hidden-md","hidden-lg");
      el.style.display = ""; el.style.visibility = "";
    });
    const groups = Array.from(document.querySelectorAll(".custom-actions .custom-btn-group"));
    const selectGrp = groups.find(g => /Select\s+Kanban/i.test(g.textContent||"") || /Выбрать\s+Канбан/i.test(g.textContent||""));
    if (selectGrp){
      selectGrp.classList.remove("hide","hidden-xs","hidden-sm","hidden-md","hidden-lg");
      selectGrp.style.display = "";
      const btn = selectGrp.querySelector("button");
      if (btn){
        btn.addEventListener("click", ()=>{
          setTimeout(()=>{
            const menu = selectGrp.querySelector(".dropdown-menu") || document.querySelector(".dropdown-menu.show");
            if (!menu) return;
            const allowCreate = hasAny(CFG.rolesCreateOnly);
            Array.from(menu.querySelectorAll("li")).forEach(li=>{
              const lbl = (li.textContent||"").trim();
              const isCreate = /Create\s+New\s+Kanban\s+Board/i.test(lbl) || /Создать\s+Канбан/i.test(lbl) || /Создать.*доску/i.test(lbl);
              if (isCreate) li.style.display = allowCreate ? "" : "none";
              if (!allowCreate && (isCreate || li.classList.contains("divider") || /(^|\s)(dropdown-divider|divider)(\s|$)/.test(li.className))) { li.style.display = "none"; }
            });
            Array.from(menu.querySelectorAll("li.user-action a.dropdown-item")).forEach(a=>{
              const labNode = a.querySelector(".menu-item-label");
              const rawEnc = labNode?.getAttribute("data-label") || "";
              const rawTxt = (labNode?.textContent || a.textContent || "").trim();
              const boardTitle = rawEnc ? decodeURIComponent(rawEnc) : rawTxt;
              a.onclick = (e)=>{ e.preventDefault(); e.stopPropagation();
                const dt = getDoctype();
                frappe.set_route("List", dt, "Kanban", boardTitle);
              };
            });
          }, 0);
        });
      }
    }
  }

  // ==== Прогрев кэша полей доков
  async function prime_doc_fields_cache_for_visible_cards(){
    const dt = getDoctype(); if (!dt) return;
    const orderMap = getBoardOrderMap(dt);
    const boardFields = [...orderMap.keys()]; if (!boardFields.length) return;
    const nodes = Array.from(document.querySelectorAll(".kanban-card-wrapper, .kanban-column .kanban-card"));
    const names = nodes
      .filter(w => isWrapVisible(w.classList?.contains?.("kanban-card") ? (w.closest(".kanban-card-wrapper") || w) : w))
      .map(el => el.getAttribute("data-name") || el.dataset?.name || el.querySelector?.(".kanban-card")?.getAttribute?.("data-name"))
      .filter(Boolean);
    const unique = Array.from(new Set(names)); if (!unique.length) return;

    let versionRows = [];
    try{
      const { message: rows = [] } = await frappe.call({
        method: "frappe.client.get_list",
        args: { doctype: dt, filters: [["name","in", unique]], fields: ["name","modified"], limit_page_length: unique.length }
      });
      versionRows = rows;
    }catch{}

    const changed = [];
    for (const r of versionRows){
      const key = docKey(dt, r.name);
      const cached = DOC_CACHE.get(key) || {};
      if (!cached.__modified || cached.__modified !== r.modified){ changed.push(r.name); }
    }
    unique.forEach(n => { if (!DOC_CACHE.has(docKey(dt,n))) changed.push(n); });

    if (!changed.length) return;

    try{
      const { message: rows = [] } = await frappe.call({
        method: "frappe.client.get_list",
        args: {
          doctype: dt,
          filters: [["name","in", Array.from(new Set(changed))]],
          fields: ["name","modified", ...boardFields, "first_name","middle_name","last_name","title"],
          limit_page_length: changed.length
        }
      });
      rows.forEach(r => {
        const { name, modified, ...rest } = r || {};
        if (name){ mergeDocCache(dt, name, Object.assign({}, rest, { __modified: modified })); }
      });
    }catch{}
  }

  // ===== Controls & run
  function injectControls(){
    document.querySelectorAll(`#${CFG.settingsBtnId}, #${CFG.modeToggleId}, #${CFG.openListBtnId}`).forEach(el => el.remove());
    if(!isKanbanRoute()) return;
    hideViewSwitcher();
    const anchorIcons = document.querySelector(".standard-actions .page-icon-group") || findSettingsAnchor();
    const actionsBar  = document.querySelector(".standard-actions") || document.querySelector(".page-actions") || anchorIcons?.parentElement;
    const settingsDropdown = buildSettingsDropdown();

    const wrap = document.createElement("div");
    wrap.id = CFG.modeToggleId;
    wrap.className = "btn-group btn-group-sm dnt-mode-toggle";
    const btnCompact = document.createElement("button");
    btnCompact.className = "btn btn-default";
    btnCompact.innerHTML = `${ICONS.modeCompact} <span>${t("Compact")}</span>`;
    const btnComfy = document.createElement("button");
    btnComfy.className = "btn btn-default";
    btnComfy.innerHTML = `${ICONS.modeComfy} <span>${t("Comfort")}</span>`;
    const setActive = ()=>{
      const on = document.documentElement.classList.contains("dnt-compact-on");
      btnCompact.classList.toggle("active", on);
      btnComfy.classList.toggle("active", !on);
    };
    btnCompact.addEventListener("click", ()=>{
      if (!document.documentElement.classList.contains("dnt-compact-on")){
        document.documentElement.classList.add("dnt-compact-on");
        try{ localStorage.setItem(`dntKanbanCompact::${getBoardName()||"__all__"}`, "1"); }catch{}
        clearSavedColWidthsForBoard(getBoardName());
        clearSessAll(); getColumnsEl().forEach(resetColumnInlineWidth);
        requestAnimationFrame(()=>{ applyWidthsForMode("compact"); setActive(); updateColumnCounts(); });
      }
    });
    btnComfy.addEventListener("click", ()=>{
      if (document.documentElement.classList.contains("dnt-compact-on")){
        document.documentElement.classList.remove("dnt-compact-on");
        try{ localStorage.setItem(`dntKanbanCompact::${getBoardName()||"__all__"}`, "0"); }catch{}
        clearSavedColWidthsForBoard(getBoardName());
        clearSessAll(); getColumnsEl().forEach(resetColumnInlineWidth);
        requestAnimationFrame(()=>{ applyWidthsForMode("comfy"); setActive(); updateColumnCounts(); });
      }
    });
    wrap.appendChild(btnCompact); wrap.appendChild(btnComfy); setActive();

    const btnList = document.createElement("button");
    btnList.id = CFG.openListBtnId;
    btnList.className = "btn btn-default btn-sm";
    btnList.setAttribute("title", t("Open List with board filter"));
    btnList.innerHTML = `${ICONS.listIcon} <span>${t("List")}</span>`;
    btnList.addEventListener("click", (e)=>{ e.preventDefault(); e.stopPropagation(); routeToListWithBoardFilter(); });

    const menuGroup   = document.querySelector(".standard-actions .menu-btn-group");
    const filterGroup = document.querySelector(".custom-actions .filter-section") || document.querySelector(".filter-section");
    if (filterGroup?.parentElement) filterGroup.parentElement.insertAdjacentElement("afterend", settingsDropdown);
    else if (menuGroup) menuGroup.insertAdjacentElement("afterend", settingsDropdown);
    else (anchorIcons || actionsBar)?.insertAdjacentElement("afterbegin", settingsDropdown);

    (anchorIcons || actionsBar)?.appendChild(wrap);
    (anchorIcons || actionsBar)?.appendChild(btnList);

    const mo = new MutationObserver(()=> {
      if (!document.getElementById(CFG.settingsBtnId) || !document.getElementById(CFG.modeToggleId) || !document.getElementById(CFG.openListBtnId)) injectControls();
      exposeSelectKanban();
      hideViewSwitcher();
    });
    mo.observe(actionsBar || document.body, { childList:true, subtree:true });
    window.__dntActionsMO = mo;
  }

  async function run(){
    await ensure_messages();
    if(!isKanbanRoute()){
      document.documentElement.classList.remove(CFG.htmlClass,"dnt-compact-on","dnt-resizing");
      document.querySelectorAll(`#${CFG.settingsBtnId}, #${CFG.modeToggleId}, #${CFG.openListBtnId}`).forEach(el => el.remove());
      return;
    }
    injectCSS();
    document.documentElement.classList.add(CFG.htmlClass);

    try{
      const preferRaw = localStorage.getItem(`dntKanbanCompact::${getBoardName()||"__all__"}`);
      const prefer = preferRaw === null ? CFG.compactDefault : preferRaw === "1";
      document.documentElement.classList.toggle("dnt-compact-on", !!prefer);
    }catch{
      document.documentElement.classList.toggle("dnt-compact-on", !!CFG.compactDefault);
    }

    applyWidthsForMode(currentMode());

    await prime_doc_fields_cache_for_visible_cards();
    enhanceCards();
    refreshVisibleCardsDocs();
    injectControls();
    exposeSelectKanban();
    updateColumnCounts();

    const colMO = new MutationObserver(()=>{ normalizeColumns(); updateColumnCounts(); });
    getColumnsEl().forEach(col=> colMO.observe(col, { childList:true, subtree:true }));

    let attempts = 0;
    const pump = () => {
      if (!isKanbanRoute()) return;
      attempts += 1;
      requestAnimationFrame(()=>{
        applyWidthsForMode(currentMode());
        enhanceCards();
        refreshVisibleCardsDocs();
        normalizeColumns();
        exposeSelectKanban();
        hideViewSwitcher();
        updateColumnCounts();
      });
      if (attempts < 12) setTimeout(pump, 80);
    };
    pump();

    if (window.__dntKanbanMO) window.__dntKanbanMO.disconnect();
    const mo = new MutationObserver(async (muts)=>{
      if(!isKanbanRoute()) return;
      const touchedCards = new Set();
      const touchedColumns = new Set();

      const collect = (node) => {
        if (!node || node.nodeType !== 1) return;
        if (node.classList.contains("kanban-card-wrapper") || node.classList.contains("kanban-card")) {
          const wrap = node.classList.contains("kanban-card") ? (node.closest(".kanban-card-wrapper") || node) : node;
          touchedCards.add(wrap);
        }
        if (node.classList.contains("kanban-column")) touchedColumns.add(node);
        node.querySelectorAll?.(".kanban-card-wrapper, .kanban-card, .kanban-column")?.forEach(collect);
      };

      muts.forEach(m=>{
        m.addedNodes && m.addedNodes.forEach(collect);
        m.removedNodes && m.removedNodes.forEach(collect);
        if (m.target && m.target.classList?.contains("kanban-column")) touchedColumns.add(m.target);
      });

      touchedCards.forEach(w=>{
        const wrap = w.classList?.contains?.("kanban-card") ? (w.closest(".kanban-card-wrapper") || w) : w;
        if (!wrap.isConnected) return;
        const body = wrap.querySelector(".kanban-card-body") || wrap;
        const name = wrap.getAttribute("data-name") || wrap.dataset?.name || body?.querySelector?.(".kanban-card")?.getAttribute?.("data-name") || "";
        if (!name) return;

        const prevCol = POS_MAP.get(name);
        const nowCol  = getCardColumnValue(wrap);
        if (prevCol !== undefined && nowCol !== prevCol){
          POS_MAP.set(name, nowCol);
          dbg("🔁 Card moved → reload tasks only", name, ":", prevCol, "→", nowCol);
          forceReloadTasksForWrap(wrap);
        } else {
          if (isWrapVisible(wrap)) { upgradeCard(wrap); refreshCardDocForWrap(wrap); }
          else observeForLazy(wrap);
          if (prevCol === undefined) POS_MAP.set(name, nowCol);
        }
      });

      if (touchedColumns.size || touchedCards.size) updateColumnCounts();
    });
    mo.observe(document.body||document.documentElement,{ childList:true, subtree:true });
    window.__dntKanbanMO = mo;
  }

  if (frappe?.after_ajax) frappe.after_ajax(run); else document.addEventListener("DOMContentLoaded", run);
  window.addEventListener("load", run);
  frappe?.router?.on && frappe.router.on("change", run);
})();