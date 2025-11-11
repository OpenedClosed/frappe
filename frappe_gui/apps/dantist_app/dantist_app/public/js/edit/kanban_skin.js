/* Dantist Kanban skin — v25.29.2  (v25.29.0 + field caching from old + LS width cleanup on mode switch)
 *
 * Что внутри:
 * - Чипы/поля как в v25.18.5: корректный парсинг, одинаковые даты в обоих режимах, прочерки "—" при ВКЛ лейблах.
 * - OFF (без лейблов): чипы строятся по полям доски; пустые поля не выводятся (как раньше).
 * - Фиксированный слот ассайни + лайк справа (если нет — появляется fallback-сердечко).
 * - Ширина карточек меняется резайзером, помним ширину per-board/per-column и per-mode (compact/comfy).
 * - Кнопка "Выбор вида" скрыта; оставлен "Select Kanban" (для не-SM скрыт Create New Kanban Board).
 * - Кнопка "List" открывает список с флагом текущей доски.
 * - Тоггл компакт/комфорт (с сохранением per-board).
 * - Мини-задачи ToDo под карточкой (как раньше).
 *
 * Дополнительно:
 * - КЭШ ПОЛЕЙ ДОКУМЕНТОВ как в старой версии: батч-прогрев по видимым карточкам через get_list + общий DOC_CACHE.
 *   getValuesBatch теперь сначала читает из DOC_CACHE и только для недостающих полей делает get_value.
 * - При переключении compact/comfy чистятся сохранённые вручную размеры карточек из localStorage для текущей доски.
 */

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

    // Заголовок доски → флаг на доке (для "List")
    boardFieldByTitle:{
      "CRM Board": "show_board_crm",
      "Leads – Contact Center": "show_board_leads",
      "Deals – Contact Center": "show_board_deals",
      "Patients – Care Department": "show_board_patients"
    }
  };

  const ICONS = {
    openSettings: '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06A2 2 0 1 1 7.04 3.2l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V2a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c0 .66.26 1.3.73 1.77.47.47 1.11.73 1.77.73h.09a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/></svg>',
    modeCompact:  '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M7 9h6M7 13h4"/></svg>',
    modeComfy:    '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="4" width="18" height="16" rx="4"/><path d="M7 10h10M7 14h8"/></svg>',
    resizerGrip:  '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="square" shape-rendering="crispEdges"><path d="M6 15L15 6M9 15L15 9M12 15L15 12"/></svg>',
    listIcon:     '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/></svg>'
  };

  // ===== Utils
  const CLEAN = s => (s||"").replace(/\u00A0/g," ").replace(/\s+/g," ").trim();
  const STRIP_COLON = s => CLEAN(s).replace(/:\s*$/,"");
  const LBL_KEY = s => STRIP_COLON(s).toLowerCase();
  const t = (s)=>{ if (typeof __ === "function") return __(s); const d=frappe&&frappe._messages; return (d&&typeof d[s]==="string"&&d[s].length)?d[s]:s; };
  const hasAny = (roles)=>{ try{ return roles.some(r=>frappe.user.has_role?.(r)); }catch{ return false; } };

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
  // Удаление сохранённых ручных ширин при смене режима
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
        --dnt-assign-h-comfy:   28px;
        --dnt-tasks-h-compact: 72px;
        --dnt-tasks-h-comfy:   88px;
      }
      html.${CFG.htmlClass}{ --dnt-card-w: var(--dnt-card-w-default); }
      html.${CFG.htmlClass}.dnt-compact-on { --dnt-card-w-default: calc(var(--dnt-card-ch-compact) * 1ch + 48px); }
      html.${CFG.htmlClass}:not(.dnt-compact-on) { --dnt-card-w-default: calc(var(--dnt-card-ch-comfy) * 1ch + 48px); }

      .kanban-board{ contain:layout style; }
      html.${CFG.htmlClass} .kanban-column{ padding:8px; min-width: calc(var(--dnt-card-w) + 24px); }
      html.${CFG.htmlClass} .kanban-cards{ display:block !important; }
      html.${CFG.htmlClass} .kanban-card-wrapper{ position:relative; margin:0 !important; width:100%; }

      html.${CFG.htmlClass} .kanban-card.content{
        border-radius:14px; border:1px solid var(--border-color);
        background: var(--card-bg); padding:12px;
        box-shadow: var(--shadow-base, 0 1px 2px rgba(0,0,0,.06));
        transition:transform .12s, box-shadow .12s, width .06s ease-out;
        display:flex !important; flex-direction:column; gap:0;
        color: var(--text-color); width: var(--dnt-card-w); margin-inline:auto;
      }
      html.${CFG.htmlClass} .kanban-card.content:hover{
        transform:translateY(-1px); box-shadow: var(--shadow-lg, 0 8px 22px rgba(0,0,0,.12));
      }

      /* Header */
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

      /* Avatar */
      html.${CFG.htmlClass} .kanban-image{
        width:40px !important; height:40px !important; border-radius:10px; overflow:hidden;
        background: var(--bg-color);
        display:flex; align-items:center; justify-content:center; margin:0 !important; flex:0 0 40px;
        box-sizing:border-box; padding:2px;
      }
      html.${CFG.htmlClass} .kanban-image img{ width:100% !important; height:100% !important; object-fit:contain !important; object-position:center; display:block !important; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-image{ width:22px !important; height:22px !important; border-radius:6px; padding:1px; }

      /* Meta & tags */
      html.${CFG.htmlClass} .kanban-card-meta{ display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin:4px 0 0; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card-meta{ gap:4px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card-meta .label,
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card-meta .tag-pill{ transform:scale(.92); transform-origin:left center; }

      /* Doc fields */
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

      /* Assignees — фиксированный слот; Like справа */
      html.${CFG.htmlClass} .dnt-assign-slot{
        height: var(--dnt-assign-h-comfy);
        min-height: var(--dnt-assign-h-comfy);
        max-height: var(--dnt-assign-h-comfy);
        line-height: var(--dnt-assign-h-comfy);
        margin-top:8px;
        display:flex; align-items:center; justify-content:space-between; gap:8px;
        overflow:hidden;
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
      html.${CFG.htmlClass} .kanban-assignments .avatar .avatar-frame.avatar-action{ width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; }
      html.${CFG.htmlClass} .kanban-assignments .avatar .avatar-frame.avatar-action svg{ width:14px; height:14px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-assignments .avatar.avatar-small{ width:18px; height:18px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-assignments .avatar .avatar-frame.avatar-action{ width:18px; height:18px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-assignments .avatar .avatar-frame.avatar-action svg{ width:12px; height:12px; }

      /* Скрыть звёзды */
      html.${CFG.htmlClass} .document-star,
      html.${CFG.htmlClass} .star-action,
      html.${CFG.htmlClass} .favorite-action{ display:none !important; }

      /* Like в правом слоте */
      html.${CFG.htmlClass} .dnt-assign-right .like-action,
      html.${CFG.htmlClass} .dnt-assign-right [data-action="like"],
      html.${CFG.htmlClass} .dnt-assign-right .btn-like{
        display:inline-flex !important; align-items:center; gap:4px; opacity:1 !important; visibility:visible !important; cursor:pointer;
      }
      html.${CFG.htmlClass} .dnt-like-fallback .es-icon{ width:16px; height:16px; }

      /* Tasks mini */
      html.${CFG.htmlClass} .dnt-tasks-mini{
        margin-top:6px; width:100%; overflow-y:auto; padding-right:4px;
        border-top:1px solid var(--border-color); padding-top:6px; scrollbar-gutter: stable;
        min-height: var(--dnt-tasks-h-comfy); max-height: var(--dnt-tasks-h-comfy);
      }
      html.${CFG.htmlClass}.dnt-compact-on .dnt-tasks-mini{
        min-height: var(--dnt-tasks-h-compact); max-height: var(--dnt-tasks-h-compact);
      }
      html.${CFG.htmlClass} .dnt-taskline{
        display:flex; gap:6px; align-items:center; font-size:11px;
        color: var(--text-muted); padding:2px 0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; cursor:pointer;
      }
      html.${CFG.htmlClass} .dnt-taskline .ttl{ font-weight:600; color: var(--text-color); overflow:hidden; text-overflow:ellipsis; }
      html.${CFG.htmlClass} .dnt-chip{
        border:1px solid var(--border-color); border-radius:999px; padding:1px 6px;
        background: var(--control-bg); font-size:10px; color: var(--text-color);
      }
      html.${CFG.htmlClass} .dnt-overdue{ background: var(--alert-bg-danger); border-color: color-mix(in oklab, var(--alert-bg-danger) 60%, transparent); color: var(--alert-text-danger); }

      /* Hover actions */
      html.${CFG.htmlClass} .dnt-card-actions{
        position:absolute; top:12px; right:12px; display:flex; gap:6px; opacity:0; pointer-events:none; transition:opacity .12s; z-index:5;
      }
      html.${CFG.htmlClass} .kanban-card-wrapper:hover .dnt-card-actions{ opacity:1; pointer-events:auto; }

      /* Resizer */
      html.${CFG.htmlClass} .dnt-resizer{
        position:absolute; right:4px; bottom:4px; width:16px; height:16px; cursor:nwse-resize;
        opacity:.9; border-radius:4px; display:flex; align-items:center; justify-content:center;
        color: var(--border-color); background: transparent; z-index:6;
      }
      html.${CFG.htmlClass} .kanban-card-wrapper:hover .dnt-resizer{ opacity:1; }

      /* Compact tweaks */
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card.content{ padding:8px; border-radius:12px; gap:6px; }
      html.${CFG.htmlClass}.dnt-compact-on .dnt-head{ margin-bottom:6px; gap:8px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card-title{ font-size:12px; line-height:1.2; }
    `;
    document.head.appendChild(s);
  }

  // ===== Board fields order mapping
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

  // ===== Meta & translate
  const LABEL_ALIASES = {
    display_name: new Set([
      "display name","display_name","displayname",
      "отображаемое имя","имя профиля","full name","name","фио",
      "имя / фио","имя и фамилия","имя, фамилия"
    ])
  };
  const isDisplayName = (s)=> LABEL_ALIASES.display_name.has(LBL_KEY(s));
  function buildMetaMaps(doctype){
    const meta = frappe.get_meta(doctype);
    const label2fn = {}, fn2label = {}, fn2df = {};
    (meta?.fields||[]).forEach(f=>{
      const lbl = CLEAN(f?.label||"");
      if (lbl){ label2fn[LBL_KEY(lbl)] = f.fieldname; fn2label[f.fieldname] = lbl; fn2df[f.fieldname] = f; }
    });
    (frappe.model.std_fields||[]).forEach(f=>{
      const lbl = CLEAN(f?.label||"");
      if (lbl){ label2fn[LBL_KEY(lbl)] = f.fieldname; fn2label[f.fieldname] = lbl; fn2df[f.fieldname] = fn2df[f.fieldname] || f; }
    });
    LABEL_ALIASES.display_name.forEach(a=> label2fn[a] = "display_name");
    return { label2fn, fn2label, fn2df };
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
    if (/\b\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?\b/.test(v)) return v;
    if (isTranslatableField(fn, df)) {
      try { return t(v); } catch { return v; }
    }
    if (/^(Yes|No|Open|Closed)$/i.test(v)) { try { return t(v); } catch {} }
    return v;
  }

  // ===== Dates (как в v25.18.5)
  const FULL_DT = /\b\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?\b/;
  const DATE_LIKE = /\b(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}|\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})\b/;
  const TIME_TAIL = /^(?:\d{1,2}:\d{2})(?::\d{2})?$/;
  const HAS_TIME = /\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?/;
  function normalizeDateish(raw){
    let v = CLEAN(raw || "");
    v = v.replace(/(\d{2}:\d{2}:\d{2})\.\d+$/, "$1");
    if (!v) return v;
    if (FULL_DT.test(v) || DATE_LIKE.test(v)) {
      try {
        const m = moment(frappe.datetime.convert_to_user_tz(v));
        if (m.isValid()) return HAS_TIME.test(v) ? m.format("DD-MM-YYYY HH:mm:ss") : m.format("DD-MM-YYYY");
      } catch {}
    }
    return v;
  }

  // ===== Values cache & helpers (добавлен батч-кэш старого типа)
  const gvCache = new Map(); // прежний кэш запросов get_value по комбинации полей
  const DOC_CACHE = new Map(); // ключ: `${doctype}::${name}` -> объект полей

  const docKey = (dt, name) => `${dt}::${name}`;
  function readFromDocCache(dt, name, fields){
    const key = docKey(dt, name);
    const stored = DOC_CACHE.get(key) || {};
    const out = {};
    const missing = [];
    (fields||[]).forEach(f=>{
      if (Object.prototype.hasOwnProperty.call(stored, f)) out[f] = stored[f];
      else missing.push(f);
    });
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

    // Сначала пробуем DOC_CACHE (батч-кэш)
    let { out, missing } = readFromDocCache(doctype, name, need);

    if (missing.length){
      try{
        const { message } = await frappe.call({
          method: "frappe.client.get_value",
          args: { doctype, filters:{ name }, fieldname: missing }
        });
        const obj = message || {};
        mergeDocCache(doctype, name, obj);
        out = Object.assign({}, out, obj);
      }catch{}
    }

    gvCache.set(k, out);
    return out;
  }

  function composeDisplayName(v){
    const f = CLEAN(v.first_name), m = CLEAN(v.middle_name), l = CLEAN(v.last_name);
    const parts = [f,m,l].filter(Boolean);
    return parts.length ? parts.join(" ") : (CLEAN(v.title) || "");
  }

  // ===== Build chips (логика v25.18.5)
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

  // ===== Chips DOM helpers
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

  // ===== Backfill (v25.18.5, с переводами и прочерками) — ЛОГИКА НЕ МЕНЯЛАСЬ
  async function backfillAll(container, ctx, labelsOn, orderMap){
    const { fn2label, label2fn, fn2df } = buildMetaMaps(ctx.doctype);
    const boardFields = [...orderMap.keys()];

    // Сносим чужие лейблы (не из набора доски)
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

      // Отсортировать по порядку доски
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

      // Проставить прочерки — как в старой версии
      Array.from(container.querySelectorAll(":scope > .dnt-kv .dnt-v")).forEach(sv=>{
        if (!CLEAN(sv.textContent)) sv.textContent = "—";
      });
      return;
    }

    // OFF (без лейблов): чипы только из значений полей доски, пустые не выводим
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

  function normalizeDocFields(docEl, ctx){
    if (!docEl || docEl.__dnt_locked) return;
    docEl.__dnt_locked = true;

    const pairs = collectPairsFromNative(docEl, ctx.doctype);
    docEl.innerHTML = "";
    const frag = buildChipsHTML(pairs, ctx);
    frag.__dntMount = docEl;
    docEl.appendChild(frag);

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

  // ===== Mini-tasks
  const miniCache = new Map();
  const fmtDT = (dt) => { try { return moment(frappe.datetime.convert_to_user_tz(dt)).format("DD-MM-YYYY HH:mm:ss"); } catch { return dt; } };
  function planLabel(kind){ return kind==="target" ? t("Target at") : t("Planned"); }
  function pickPlan(t){
    if (t.custom_target_datetime) return { dt: t.custom_target_datetime, kind: "target" };
    return { dt: null, kind: null };
  }
  function plain_text(html_like){ const div=document.createElement("div"); div.innerHTML = html_like || ""; return CLEAN(div.textContent || div.innerText || ""); }
  function truncate_text(s, max_len=40){ const str = s || ""; return str.length<=max_len?str:(str.slice(0,max_len).trimEnd()+"…"); }
  function miniHeader(){ return `<div class="dnt-taskline" data-act="noop"><span class="dnt-chip">${t("Tasks")}</span></div>`; }
  function miniHtml(rows, total){
    const totalCount = typeof total === "number" ? total : (rows?.length || 0);
    const showOpenAll = totalCount > 1 || (rows?.length || 0) > 1;
    if (!rows?.length) return miniHeader() + `<div class="dnt-taskline"><span class="ttl">${t("No open tasks")}</span></div>`;

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
    return miniHeader() + lines + more;
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
    } catch { return { rows: [], total: 0 }; }
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
        container.innerHTML = miniHeader() + `<div class="dnt-taskline"><span class="ttl">${t("No open tasks")}</span></div>`;
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

  // ===== Like helpers
  function ensureVisibleAction(el){
    try{
      el.classList.remove("hidden","hide"); el.style.removeProperty("display"); el.removeAttribute("aria-hidden");
      el.style.opacity = "1"; el.style.visibility = "visible"; el.style.cursor = "pointer";
    }catch{}
  }
  function detectLikeFrom(root){
    return root.querySelector(".like-action, .list-row-like, .liked-by, [data-action='like'], .btn-like");
  }
  function createFallbackLike(doctype, name){
    const span = document.createElement("span");
    span.className = "like-action not-liked dnt-like-fallback";
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

  // ===== Title inline-edit
  function makeTitleEditable(titleArea, name, doctype){
    if (!titleArea || titleArea.__dntEditable) return;
    titleArea.__dntEditable = true;

    const anchor = titleArea.querySelector("a");
    const currentText = (titleArea.querySelector(".kanban-card-title")?.textContent || anchor?.textContent || name || "").trim();

    const holder = titleArea.querySelector(".kanban-card-title") || document.createElement("div");
    holder.classList.add("kanban-card-title"); holder.innerHTML = "";

    const span = document.createElement("span");
    span.className = "dnt-title"; span.textContent = currentText;
    holder.appendChild(span);
    if (anchor) anchor.replaceWith(holder); else titleArea.appendChild(holder);

    let beforeEdit = currentText;

    function toEdit(){
      if (span.isContentEditable) return;
      beforeEdit = span.textContent || "";
      span.classList.add("is-edit");
      span.setAttribute("contenteditable","true");
      span.focus();
      const sel = window.getSelection?.();
      if (sel && document.createRange){
        const r = document.createRange();
        r.selectNodeContents(span); r.collapse(false);
        sel.removeAllRanges(); sel.addRange(r);
      }
    }
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
    span.addEventListener("keydown", (e)=>{
      if (e.key==="Enter"){ e.preventDefault(); saveEdit(); span.blur(); }
      if (e.key==="Escape"){ e.preventDefault(); cancelEdit(); span.blur(); }
    });
    span.addEventListener("blur", saveEdit);
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

    // Header layout
    let head = body.querySelector(".dnt-head"); if(!head){ head = document.createElement("div"); head.className = "dnt-head"; body.prepend(head); }
    let left = head.querySelector(".dnt-head-left"); if(!left){ left = document.createElement("div"); left.className = "dnt-head-left"; head.prepend(left); }
    if (img && !left.contains(img)) left.prepend(img);
    if (title) { title.querySelectorAll("br").forEach(br=>br.remove()); if(!left.contains(title)) left.appendChild(title); }
    if (meta && meta.parentElement !== head) head.appendChild(meta);
    if (doc && doc.previousElementSibling !== head) body.insertBefore(doc, head.nextSibling);

    const name = wrapper.getAttribute("data-name") || wrapper.dataset.name || card.getAttribute("data-name") || "";
    const doctype = getDoctype();

    if (doc) normalizeDocFields(doc, { doctype, docName: name });

    // Assignees + Like (фикс. слот)
    let assignSlot = body.querySelector(".dnt-assign-slot"); if (!assignSlot){ assignSlot = document.createElement("div"); assignSlot.className = "dnt-assign-slot"; body.appendChild(assignSlot); }
    let assignLeft = assignSlot.querySelector(".dnt-assign-left"); if (!assignLeft){ assignLeft = document.createElement("div"); assignLeft.className = "dnt-assign-left"; assignSlot.appendChild(assignLeft); }
    let assignRight = assignSlot.querySelector(".dnt-assign-right"); if (!assignRight){ assignRight = document.createElement("div"); assignRight.className = "dnt-assign-right"; assignSlot.appendChild(assignRight); }

    const assignments = (meta || body).querySelector(".kanban-assignments");
    if (assignments && assignments.parentElement !== assignLeft) assignLeft.appendChild(assignments);

    body.querySelectorAll(".document-star, .star-action, .favorite-action").forEach(el=> el.remove());

    let like = detectLikeFrom(body) || detectLikeFrom(card);
    if (like){ ensureVisibleAction(like); if (like.parentElement !== assignRight) assignRight.appendChild(like); }
    else if (doctype && name){ assignRight.appendChild(createFallbackLike(doctype, name)); }

    // Tasks mini
    let mini = body.querySelector(".dnt-tasks-mini");
    if (!mini){ mini = document.createElement("div"); mini.className = "dnt-tasks-mini"; body.appendChild(mini); }
    if (doctype === CFG.caseDoctype && name) {
      setTimeout(()=> loadMini(mini, name), 0);
    }

    // Quick actions
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
    card.dataset.dntUpgraded = "1";
  }

  function enhanceCards(){
    document.querySelectorAll(".kanban-card-wrapper, .kanban-column .kanban-card:not(.content)").forEach(w => {
      const wrap = w.classList.contains?.("kanban-card") ? w.closest(".kanban-card-wrapper") || w : w;
      upgradeCard(wrap);
    });
  }

  // ===== Header controls: Settings/Labels, Compact/Comfy, List, Select Kanban, Hide View
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
    // Прячет кнопку "Выбор вида" (View) — эвристически
    const candidates = Array.from(document.querySelectorAll(".standard-actions .menu-btn-group, .page-actions .menu-btn-group, .page-actions .btn-group, .standard-actions .btn-group"));
    candidates.forEach(g=>{
      const txt = CLEAN(g.textContent||"").toLowerCase();
      const hasViewWords = /view|вид/i.test(g.querySelector("[title]")?.getAttribute("title")||"") || /list|report|kanban|calendar|вид|список|отчет/i.test(txt);
      const looksSwitcher = g.querySelector("button.dropdown-toggle, .view-switcher, .btn-view-switcher");
      if (looksSwitcher && hasViewWords){
        g.style.display = "none";
      }
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

  function buildSettingsDropdown(){
    const wrap = document.createElement("div");
    wrap.id = CFG.settingsBtnId;
    wrap.className = "btn-group btn-group-sm";

    const btn = document.createElement("button");
    btn.className = "btn btn-default icon-btn btn-sm dropdown-toggle";
    btn.setAttribute("data-toggle","dropdown");
    btn.setAttribute("aria-expanded","false");
    btn.setAttribute("title", t("Kanban options"));
    btn.innerHTML = ICONS.openSettings;
    wrap.appendChild(btn);

    const menu = document.createElement("ul");
    menu.className = "dropdown-menu";
    menu.innerHTML = `
      <li>
        <a class="grey-link dropdown-item dnt-open-board-settings" href="#" onclick="return false;">
          ${frappe.utils.icon("edit","sm")} <span class="menu-item-label">${t("Board Settings")}</span>
        </a>
      </li>
      <li class="dropdown-divider"></li>
      <li>
        <a class="grey-link dropdown-item dnt-toggle-labels" href="#" onclick="return false;">
          ${frappe.utils.icon("tag","sm")} <span class="menu-item-label dnt-toggle-labels-text"></span>
        </a>
      </li>
    `;
    wrap.appendChild(menu);

    const labelsText = menu.querySelector(".dnt-toggle-labels-text");
    const isLabelsOn = () => getShowLabelsFlag();
    const refreshLabelsText = () => { labelsText.textContent = isLabelsOn() ? t("Hide labels") : t("Show labels"); };

    refreshLabelsText();
    btn.addEventListener("show.bs.dropdown", refreshLabelsText);
    btn.addEventListener("shown.bs.dropdown", refreshLabelsText);
    btn.addEventListener("click", () => setTimeout(refreshLabelsText, 0));

    menu.querySelector(".dnt-open-board-settings").addEventListener("click",(e)=>{
      e.preventDefault(); e.stopPropagation();
      const bname = getBoardName();
      if (bname) frappe.set_route(`/app/kanban-board/${encodeURIComponent(bname)}`);
    });

    menu.querySelector(".dnt-toggle-labels").addEventListener("click", async (e)=>{
      e.preventDefault(); e.stopPropagation();
      const bname = getBoardName();
      if (!bname) return;
      const want = !isLabelsOn();
      try{
        await frappe.call({
          method: "frappe.client.set_value",
          args: { doctype: "Kanban Board", name: bname, fieldname: "show_labels", value: want ? 1 : 0 }
        });
        if (window.cur_list?.board) window.cur_list.board.show_labels = want;
        if (window.cur_list?.kanban_board) window.cur_list.kanban_board.show_labels = want;
        refreshLabelsText();
        frappe.show_alert({ message: want ? t("Labels shown") : t("Labels hidden"), indicator: "green" });
        setTimeout(()=> location.reload(), 50);
      } catch {
        frappe.msgprint?.({ message: t("Failed to toggle labels"), indicator: "red" });
      }
    });

    return wrap;
  }

  function exposeSelectKanban(){
    // показать "Select Kanban", скрыть "Create…" для не-SM
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
              if (!allowCreate && (isCreate || li.classList.contains("divider") || /(^|\s)(dropdown-divider|divider)(\s|$)/.test(li.className))) {
                li.style.display = "none";
              }
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

  // ==== Батч-прогрев кэша полей для видимых карточек (как в старой)
  async function prime_doc_fields_cache_for_visible_cards(){
    const dt = getDoctype();
    if (!dt) return;
    const orderMap = getBoardOrderMap(dt);
    const boardFields = [...orderMap.keys()];
    if (!boardFields.length) return;

    // names всех видимых карточек
    const names = Array.from(document.querySelectorAll(".kanban-card-wrapper, .kanban-column .kanban-card"))
      .map(el => el.getAttribute("data-name") || el.dataset?.name || el.querySelector?.(".kanban-card")?.getAttribute?.("data-name"))
      .filter(Boolean);

    const unique = Array.from(new Set(names)).filter(n => !DOC_CACHE.has(docKey(dt, n)));
    if (!unique.length) return;

    try{
      const { message: rows = [] } = await frappe.call({
        method: "frappe.client.get_list",
        args: {
          doctype: dt,
          filters: [["name","in", unique]],
          fields: ["name", ...boardFields],
          limit_page_length: unique.length
        }
      });
      rows.forEach(r => {
        const { name, ...rest } = r || {};
        if (name) mergeDocCache(dt, name, rest);
      });
    }catch{}
  }

  function injectControls(){
    // Удалим прошлые
    document.querySelectorAll(`#${CFG.settingsBtnId}, #${CFG.modeToggleId}, #${CFG.openListBtnId}`).forEach(el => el.remove());
    if(!isKanbanRoute()) return;

    // Спрятать View switcher
    hideViewSwitcher();

    const anchorIcons = document.querySelector(".standard-actions .page-icon-group") || findSettingsAnchor();
    const actionsBar  = document.querySelector(".standard-actions") || document.querySelector(".page-actions") || anchorIcons?.parentElement;

    // Settings dropdown (labels toggle)
    const settingsDropdown = buildSettingsDropdown();

    // Compact/Comfy
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
        // Чистим сохранённые ручные ширины при смене режима
        clearSavedColWidthsForBoard(getBoardName());
        clearSessAll(); getColumnsEl().forEach(resetColumnInlineWidth);
        applyWidthsForMode("compact"); setActive();
      }
    });
    btnComfy.addEventListener("click", ()=>{
      if (document.documentElement.classList.contains("dnt-compact-on")){
        document.documentElement.classList.remove("dnt-compact-on");
        try{ localStorage.setItem(`dntKanbanCompact::${getBoardName()||"__all__"}`, "0"); }catch{}
        // Чистим сохранённые ручные ширины при смене режима
        clearSavedColWidthsForBoard(getBoardName());
        clearSessAll(); getColumnsEl().forEach(resetColumnInlineWidth);
        applyWidthsForMode("comfy"); setActive();
      }
    });
    wrap.appendChild(btnCompact); wrap.appendChild(btnComfy); setActive();

    // List btn
    const btnList = document.createElement("button");
    btnList.id = CFG.openListBtnId;
    btnList.className = "btn btn-default btn-sm";
    btnList.setAttribute("title", t("Open List with board filter"));
    btnList.innerHTML = `${ICONS.listIcon} <span>${t("List")}</span>`;
    btnList.addEventListener("click", (e)=>{ e.preventDefault(); e.stopPropagation(); routeToListWithBoardFilter(); });

    // Вставка
    const menuGroup   = document.querySelector(".standard-actions .menu-btn-group");
    const filterGroup = document.querySelector(".custom-actions .filter-section") || document.querySelector(".filter-section");
    if (filterGroup?.parentElement) filterGroup.parentElement.insertAdjacentElement("afterend", settingsDropdown);
    else if (menuGroup) menuGroup.insertAdjacentElement("afterend", settingsDropdown);
    else (anchorIcons || actionsBar)?.insertAdjacentElement("afterbegin", settingsDropdown);

    (anchorIcons || actionsBar)?.appendChild(wrap);
    (anchorIcons || actionsBar)?.appendChild(btnList);

    // Следим за мутациями шапки, держим кнопки видимыми; и Select Kanban — доступен
    const mo = new MutationObserver(()=> {
      if (!document.getElementById(CFG.settingsBtnId) || !document.getElementById(CFG.modeToggleId) || !document.getElementById(CFG.openListBtnId)) injectControls();
      exposeSelectKanban();
      hideViewSwitcher();
    });
    mo.observe(actionsBar || document.body, { childList:true, subtree:true });
    window.__dntActionsMO = mo;
  }

  // ===== Run
  async function run(){
    await ensure_messages();
    if(!isKanbanRoute()){
      document.documentElement.classList.remove(CFG.htmlClass,"dnt-compact-on","dnt-resizing");
      document.querySelectorAll(`#${CFG.settingsBtnId}, #${CFG.modeToggleId}, #${CFG.openListBtnId}`).forEach(el => el.remove());
      return;
    }
    injectCSS();
    document.documentElement.classList.add(CFG.htmlClass);

    // Начальный режим (per-board)
    try{
      const preferRaw = localStorage.getItem(`dntKanbanCompact::${getBoardName()||"__all__"}`);
      const prefer = preferRaw === null ? CFG.compactDefault : preferRaw === "1";
      document.documentElement.classList.toggle("dnt-compact-on", !!prefer);
    }catch{
      document.documentElement.classList.toggle("dnt-compact-on", !!CFG.compactDefault);
    }

    applyWidthsForMode(currentMode());

    // ВАЖНО: сперва прогреваем кэш полей видимых карточек (как в старой), затем апгрейд
    await prime_doc_fields_cache_for_visible_cards();
    enhanceCards();
    injectControls();
    exposeSelectKanban();

    // Колонки могут исчезать — нормализуем
    const colMO = new MutationObserver(normalizeColumns);
    getColumnsEl().forEach(col=> colMO.observe(col, { childList:true, subtree:true }));

    // Памп старта (несколько тикoв)
    let attempts = 0;
    const pump = () => {
      if (!isKanbanRoute()) return;
      attempts += 1;
      applyWidthsForMode(currentMode());
      enhanceCards();
      normalizeColumns();
      exposeSelectKanban();
      hideViewSwitcher();
      if (attempts < 12) setTimeout(pump, 80);
    };
    pump();

    if (window.__dntKanbanMO) window.__dntKanbanMO.disconnect();
    const mo = new MutationObserver(async ()=>{ 
      if(isKanbanRoute()) { 
        await prime_doc_fields_cache_for_visible_cards();
        applyWidthsForMode(currentMode()); 
        enhanceCards(); 
        normalizeColumns(); 
        exposeSelectKanban(); 
        hideViewSwitcher(); 
      } 
    });
    mo.observe(document.body||document.documentElement,{ childList:true, subtree:true });
    window.__dntKanbanMO = mo;
  }

  if (frappe?.after_ajax) frappe.after_ajax(run); else document.addEventListener("DOMContentLoaded", run);
  window.addEventListener("load", run);
  frappe?.router?.on && frappe.router.on("change", run);
})();