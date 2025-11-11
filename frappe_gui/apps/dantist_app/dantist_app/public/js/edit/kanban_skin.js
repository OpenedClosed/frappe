/* Dantist Kanban skin — v25.23.0
 * Fix: DnD вернулся, ресайз запускается только по mousedown/touchstart, DnD глушится ТОЛЬКО во время ресайза.
 * UI: комфортная аватарка крупнее, в Compact уменьшен add-assign; корректные отступы хедера.
 */
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
    modeToggleId: "dnt-mode-toggle",
    minCardW: 240,
    maxCardW: 720,
    compactChars: 26,
    comfyChars: 44,
    compactDefault: true,
    caseDoctype: "Engagement Case",
    tasksMethod: "dantist_app.api.tasks.handlers.ec_tasks_for_case",
    tasksLimit: 5
  };

  const ICONS = {
    openSettings: '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06A2 2 0 1 1 7.04 3.2l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V2a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c0 .66.26 1.3.73 1.77.47.47 1.11.73 1.77.73h.09a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/></svg>',
    modeCompact:  '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M7 9h6M7 13h4"/></svg>',
    modeComfy:    '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="4" width="18" height="16" rx="4"/><path d="M7 10h10M7 14h8"/></svg>',
    resizerGrip:  '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="square" shape-rendering="crispEdges"><path d="M6 15L15 6M9 15L15 9M12 15L15 12"/></svg>'
  };

  const CLEAN = s => (s||"").replace(/\u00A0/g," ").replace(/\s+/g," ").trim();
  const STRIP_COLON = s => CLEAN(s).replace(/:\s*$/,"");
  const LBL_KEY = s => STRIP_COLON(s).toLowerCase();
  const t = (s) => { if (typeof __ === "function") return __(s); const d=frappe&&frappe._messages; return (d&&typeof d[s]==="string"&&d[s].length)?d[s]:s; };
  const isKanbanRoute = () => {
    const r = frappe.get_route?.() || [];
    if (r[0] === "List" && (r[2] === "Kanban" || r[2] === "Kanban Board")) return true;
    return (location.pathname||"").includes("/view/kanban/");
  };
  const getBoardName = () => {
    try {
      const r = frappe.get_route?.();
      return r?.[3] ? decodeURIComponent(r[3]) : (window.cur_list?.board?.name || window.cur_list?.kanban_board?.name || "");
    } catch { return ""; }
  };
  const currentMode = () => document.documentElement.classList.contains("dnt-compact-on") ? "compact" : "comfy";
  const getColumns = () => Array.from(document.querySelectorAll(".kanban-column"));

  const colKey = (col, mode) => {
    const board = getBoardName() || "__";
    const val = col?.getAttribute?.("data-column-value") || "__col__";
    return `dntKanbanColW::${board}::${val}::${mode}`;
  };
  const loadColW = (col, mode) => { try{ const v = localStorage.getItem(colKey(col, mode)); return v? +v : null; }catch{ return null; } };
  const clearSavedMode = (mode) => { getColumns().forEach(col=>{ try{ localStorage.removeItem(colKey(col, mode)); }catch{} }); };
  const purgeLegacySaved = () => { try{ Object.keys(localStorage).forEach(k=>{ if(k.startsWith("dntKanbanColW::")) localStorage.removeItem(k); }); }catch{} };

  const sessionColW = new Map();
  const sessKey = (col, mode) => colKey(col, mode) + "::session";
  const setSessW = (col, mode, px) => sessionColW.set(sessKey(col,mode), px);
  const getSessW = (col, mode) => sessionColW.get(sessKey(col,mode));
  const clearSessAll = () => sessionColW.clear();

  const FULL_DT = /\b\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?\b/;
  const DATE_LIKE = /\b(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}|\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})\b/;
  const HAS_TIME = /\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?/;

  function injectCSS(){
    if(document.getElementById(CFG.cssId)) return;
    const s=document.createElement("style"); s.id=CFG.cssId;
    s.textContent = `
      :root{
        --dnt-card-ch-compact: ${CFG.compactChars};
        --dnt-card-ch-comfy:   ${CFG.comfyChars};
      }
      html.${CFG.htmlClass}{ --dnt-card-w: var(--dnt-card-w-default); }

      html.${CFG.htmlClass}.dnt-compact-on { --dnt-card-w-default: calc(var(--dnt-card-ch-compact) * 1ch + 48px); }
      html.${CFG.htmlClass}:not(.dnt-compact-on) { --dnt-card-w-default: calc(var(--dnt-card-ch-comfy) * 1ch + 48px); }

      /* Header spacing — возвращаем как было */
      html.${CFG.htmlClass} .page-head{ margin-top: 0 !important; margin-bottom: 14px !important; }
      html.${CFG.htmlClass} .page-actions, html.${CFG.htmlClass} .page-icon-group{ display:flex; align-items:center; gap:8px; }
      html.${CFG.htmlClass} #${CFG.modeToggleId}{ margin-left: 8px; align-self:center; }

      .kanban-board{ contain:layout style; }

      html.${CFG.htmlClass} .kanban-column{ padding:8px; min-width: calc(var(--dnt-card-w) + 24px); }
      html.${CFG.htmlClass} .kanban-cards{ display:block !important; }
      html.${CFG.htmlClass} .kanban-card-wrapper{ position:relative; margin:0 !important; width:100%; }

      html.${CFG.htmlClass} .kanban-card.content{
        border-radius:14px;
        border:1px solid var(--border-color, rgba(0,0,0,.06));
        background: var(--card-bg, #ffffff);
        padding:12px;
        box-shadow: var(--shadow-base, 0 1px 2px rgba(0,0,0,.06));
        transition:transform .12s, box-shadow .12s, width .06s ease-out;
        display:flex !important; flex-direction:column; gap:0;
        color: var(--text-color, #111827);
        width: var(--dnt-card-w);
        margin-inline:auto;
      }
      html.${CFG.htmlClass} .kanban-card.content:hover{
        transform:translateY(-1px);
        box-shadow: 0 8px 22px color-mix(in oklab, var(--shadow-color, rgba(0,0,0,.16)) 70%, transparent);
      }

      /* Title */
      html.${CFG.htmlClass} .dnt-head{ display:flex; align-items:center; justify-content:space-between; gap:12px; min-width:0; margin-bottom:10px; }
      html.${CFG.htmlClass} .dnt-head-left{ display:flex; align-items:center; gap:10px; min-width:0; flex:1 1 auto; }
      html.${CFG.htmlClass} .kanban-title-area{ margin:0 !important; min-width:0; }
      html.${CFG.htmlClass} .kanban-card-title{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color: var(--text-color, #111827); }
      html.${CFG.htmlClass} .dnt-title{ font-weight:600; line-height:1.25; cursor:text; display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      html.${CFG.htmlClass} .dnt-title[contenteditable="true"]{ outline:none; border-radius:6px; padding:0 2px; }
      html.${CFG.htmlClass} .dnt-title[contenteditable="true"]:focus{ background: var(--fg-hover-color, #f3f4f6); }

      /* Avatar — комфорт = больше, компакт = меньше */
      html.${CFG.htmlClass} .kanban-image{
        width:40px !important; height:40px !important; border-radius:10px; overflow:hidden;
        background: var(--bg-light-gray, #eef2f7);
        display:flex; align-items:center; justify-content:center; margin:0 !important; flex:0 0 40px;
        box-sizing:border-box; padding:2px;
      }
      html.${CFG.htmlClass} .kanban-image img{ width:100% !important; height:100% !important; object-fit:contain !important; object-position:center; display:block !important; }

      html.${CFG.htmlClass}.dnt-compact-on .kanban-image{ width:22px !important; height:22px !important; border-radius:6px; padding:1px; }

      /* Chips */
      html.${CFG.htmlClass} .kanban-card-doc{ padding:0; }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-kv{
        display:flex; align-items:center; gap:6px;
        background: var(--control-bg, #f3f4f6);
        border:1px solid var(--border-color, #e5e7eb);
        border-radius:10px; padding:4px 8px; font-size:12px; min-height:24px; color: var(--text-color, #111827);
      }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-kv + .dnt-kv { margin-top:6px; }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-k{ flex:0 1 auto; max-width:45%; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color: var(--text-muted, #6b7280); }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-v{ flex:1 1 auto; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-weight:600; color: var(--text-color, #111827); }

      /* Footer + Tasks */
      html.${CFG.htmlClass} .dnt-foot{ margin-top:10px; display:flex; align-items:center; justify-content:space-between; gap:10px; }
      html.${CFG.htmlClass} .dnt-tasks-mini{
        margin-top:6px; width:100%; max-height:72px; overflow-y:auto; padding-right:4px;
        border-top:1px solid var(--table-border-color, var(--border-color, #eef2f7)); padding-top:6px; scrollbar-gutter: stable;
      }
      html.${CFG.htmlClass} .dnt-taskline{ display:flex; gap:6px; align-items:center; font-size:11px; color: var(--text-muted, #4b5563); padding:2px 0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; cursor:pointer; }
      html.${CFG.htmlClass} .dnt-taskline .ttl{ font-weight:600; color: var(--text-color, #111827); overflow:hidden; text-overflow:ellipsis; }
      html.${CFG.htmlClass} .dnt-chip{ border:1px solid var(--border-color, #e5e7eb); border-radius:999px; padding:1px 6px; background: var(--control-bg, #f8fafc); font-size:10px; color: var(--text-color, #111827); }

      /* Просрочка — корректно в темной теме */
      html.${CFG.htmlClass} .dnt-overdue{ background: var(--alert-bg-danger, #fee2e2); border-color: color-mix(in oklab, var(--alert-bg-danger, #fee2e2) 60%, transparent); color: var(--alert-text-danger, #991b1b); }
      @media (prefers-color-scheme: dark){
        html.${CFG.htmlClass} .dnt-overdue{ background: color-mix(in oklab, #ef4444 20%, transparent); border-color: color-mix(in oklab, #ef4444 65%, transparent); color: #fecaca; }
      }

      /* Actions */
      html.${CFG.htmlClass} .dnt-card-actions{
        position:absolute; top:12px; right:12px; display:flex; gap:6px;
        opacity:0; pointer-events:none; transition:opacity .12s; z-index:5;
      }
      html.${CFG.htmlClass} .kanban-card-wrapper:hover .dnt-card-actions{ opacity:1; pointer-events:auto; }

      /* Compact tweaks: плотнее всё, маленький Assign '+' */
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card.content{ padding:8px; border-radius:12px; gap:6px; }
      html.${CFG.htmlClass}.dnt-compact-on .dnt-head{ margin-bottom:6px; gap:8px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card-title{ font-size:12px; line-height:1.2; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-card-meta{ display:none; }
      html.${CFG.htmlClass}.dnt-compact-on .dnt-foot{ margin-top:6px; }
      html.${CFG.htmlClass}.dnt-compact-on .dnt-foot .like-action{ display:none !important; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-assignments .avatar-group .avatar.avatar-small{ width:18px; height:18px; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-assignments .avatar-group .avatar.avatar-small .avatar-frame{ width:100%; height:100%; border-radius:9999px; background-size:cover; background-position:center; }
      html.${CFG.htmlClass}.dnt-compact-on .kanban-assignments .avatar .avatar-frame.avatar-action svg{ width:12px; height:12px; }

      /* В обычном режиме — нормальный '+' */
      html.${CFG.htmlClass} .kanban-assignments .avatar .avatar-frame.avatar-action svg{ width:14px; height:14px; }

      /* Resizer — аккуратно в углу */
      html.${CFG.htmlClass} .dnt-resizer{
        position:absolute; right:4px; bottom:4px; width:16px; height:16px; cursor:nwse-resize;
        opacity:.85; border-radius:4px; display:flex; align-items:center; justify-content:center;
        color: var(--border-color, #94a3b8);
        background: transparent; z-index:6;
      }
      html.${CFG.htmlClass} .kanban-card-wrapper:hover .dnt-resizer{ opacity:1; }

      /* Во время ресайза — без выделения текста */
      html.${CFG.htmlClass}.dnt-resizing * { user-select: none !important; }

      /* Drag ghost/selected — ширина по колонке */
      html.${CFG.htmlClass} .sortable-ghost .kanban-card.content,
      html.${CFG.htmlClass} .sortable-chosen .kanban-card.content,
      html.${CFG.htmlClass} .kanban-card.sortable-ghost,
      html.${CFG.htmlClass} .kanban-card.sortable-chosen{
        width: var(--dnt-card-w) !important;
      }
    `;
    document.head.appendChild(s);
  }

  const fmtDT = (dt) => { try { return moment(frappe.datetime.convert_to_user_tz(dt)).format("DD-MM-YYYY HH:mm:ss"); } catch { return dt; } };
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

  function getBoardOrderMap(doctype){
    try{
      const board = window.cur_list?.board || window.cur_list?.kanban_board;
      const fieldsRaw = board?.fields || [];
      let arr=[];
      if(Array.isArray(fieldsRaw)) arr=fieldsRaw;
      else if(typeof fieldsRaw==="string" && fieldsRaw.trim()){
        try{ const j=JSON.parse(fieldsRaw); if(Array.isArray(j)) arr=j; }
        catch{ arr=fieldsRaw.split(/[,\s]+/).filter(Boolean); }
      }
      const map = new Map(); arr.forEach((fn,i)=> map.set(fn,i));
      return map;
    }catch{ return new Map(); }
  }

  function buildMetaMaps(doctype){
    const meta = frappe.get_meta(doctype);
    const label2fn = {}, fn2label = {}, fn2df = {};
    (meta?.fields||[]).forEach(f=>{ const lbl=CLEAN(f?.label||""); if (lbl){ label2fn[LBL_KEY(lbl)] = f.fieldname; fn2label[f.fieldname] = lbl; } });
    (frappe.model.std_fields||[]).forEach(f=>{ const lbl=CLEAN(f?.label||""); if (lbl){ label2fn[LBL_KEY(lbl)] = f.fieldname; fn2label[f.fieldname] = lbl; } });
    (meta?.fields||[]).forEach(f=> fn2df[f.fieldname] = f);
    (frappe.model.std_fields||[]).forEach(f=> fn2df[f.fieldname] = fn2df[f.fieldname] || f);
    ["display name","display_name","displayname","отображаемое имя","имя профиля","full name","name","фио","имя / фио","имя и фамилия","имя, фамилия"]
      .forEach(a=> label2fn[LBL_KEY(a)] = "display_name");
    return { label2fn, fn2label, fn2df };
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
    sv.textContent = CLEAN(value || "");
    kv.appendChild(sv);
    return kv;
  }
  function insertChipAtIndex(container, chip, idx){
    const nodes = Array.from(container.querySelectorAll(":scope > .dnt-kv"));
    const target = nodes[idx];
    if (target) container.insertBefore(chip, target);
    else container.appendChild(chip);
  }

  async function backfillAll(container, ctx, labelsOn, orderMap){
    const { fn2label, label2fn, fn2df } = buildMetaMaps(ctx.doctype);
    const boardFields = [...orderMap.keys()];
    Array.from(container.querySelectorAll(":scope > .dnt-kv")).forEach(ch=>{
      const lbl = CLEAN(ch.dataset.dntLabel || ch.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
      if (!lbl) return;
      const fn = label2fn[LBL_KEY(lbl)] || (LBL_KEY(lbl)==="display_name" ? "display_name" : null);
      if (!fn || !boardFields.includes(fn)) ch.remove();
    });

    const need = boardFields.slice();
    const v = await frappe.call({
      method: "frappe.client.get_value",
      args: { doctype: ctx.doctype, filters:{ name: ctx.docName }, fieldname: need }
    }).then(r=> r.message || {}).catch(()=> ({}));

    if (boardFields.includes("display_name") && !CLEAN(v.display_name)) {
      const pseudo = await frappe.call({
        method: "frappe.client.get_value",
        args: { doctype: ctx.doctype, filters:{ name: ctx.docName }, fieldname: ["first_name","middle_name","last_name","title"] }
      }).then(r=> r.message || {}).catch(()=> ({}));
      const parts=[CLEAN(pseudo.first_name),CLEAN(pseudo.middle_name),CLEAN(pseudo.last_name)].filter(Boolean);
      v.display_name = parts.length ? parts.join(" ") : (CLEAN(pseudo.title)||"");
    }

    if (labelsOn){
      boardFields.forEach(fn=>{
        const human = fn2label[fn] || (fn==="display_name" ? "Display Name" : fn);
        const rawVal = CLEAN(normalizeDateish(v[fn])) || "";
        const shown = CLEAN(rawVal) ? rawVal : "—";
        let chip = Array.from(container.querySelectorAll(":scope > .dnt-kv")).find(ch=>{
          const lbl = CLEAN(ch.dataset.dntLabel || ch.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
          const f = label2fn[LBL_KEY(lbl)] || (LBL_KEY(lbl)==="display_name" ? "display_name" : null);
          return f === fn;
        });
        if (!chip){
          chip = makeChip(human, shown, true);
          insertChipAtIndex(container, chip, orderMap.get(fn) ?? 0);
        } else {
          chip.querySelector(".dnt-v").textContent = shown;
          chip.querySelector(".dnt-k").textContent = t(STRIP_COLON(human)) + ":";
        }
      });
      const chips = Array.from(container.querySelectorAll(":scope > .dnt-kv"));
      chips.sort((a,b)=>{
        const la = CLEAN(a.dataset.dntLabel || a.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
        const lb = CLEAN(b.dataset.dntLabel || b.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
        const fna = label2fn[LBL_KEY(la)] || (LBL_KEY(la)==="display_name" ? "display_name" : null);
        const fnb = label2fn[LBL_KEY(lb)] || (LBL_KEY(lb)==="display_name" ? "display_name" : null);
        const ia = orderMap.has(fna||"") ? orderMap.get(fna||"") : 9999;
        const ib = orderMap.has(fnb||"") ? orderMap.get(fnb||"") : 9999;
        return ia - ib;
      });
      chips.forEach(ch => container.appendChild(ch));
      return;
    }

    const assigned = new Set();
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
      const norm = CLEAN(normalizeDateish(v[fn]));
      if (!norm) return;
      const pool = valueIndex.get(norm) || [];
      const pick = pool.shift?.();
      if (pick){
        pick.querySelector(".dnt-v").textContent = norm;
        const idx = orderMap.get(fn) ?? 0;
        const siblings = Array.from(container.querySelectorAll(":scope > .dnt-kv"));
        if (siblings[idx]) container.insertBefore(pick, siblings[idx]); else container.appendChild(pick);
        assigned.add(norm);
      } else {
        const chip = makeChip("", norm, false);
        insertChipAtIndex(container, chip, orderMap.get(fn) ?? 0);
        assigned.add(norm);
      }
    });
    Array.from(container.querySelectorAll(":scope > .dnt-kv")).forEach(ch=>{
      const lbl = CLEAN(ch.dataset.dntLabel || ch.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
      if (!lbl){
        const val = CLEAN(ch.querySelector(".dnt-v")?.textContent || "");
        if (!val || !assigned.has(val)) ch.remove();
      }
    });
  }

  function buildChipsHTML(docEl, ctx){
    const labelsOn = !!(window.cur_list?.board?.show_labels || window.cur_list?.kanban_board?.show_labels);
    const orderMap = getBoardOrderMap(ctx.doctype);
    const rows = Array.from(docEl.querySelectorAll(":scope > .text-truncate, :scope > .ellipsis"));
    const frag = document.createDocumentFragment();
    rows.forEach(row=>{
      const fullText = CLEAN(row.textContent || "");
      const spans = Array.from(row.querySelectorAll(":scope > span"));
      const tokens = (spans.length ? spans.map(s => CLEAN(s.textContent)) : [fullText]).filter(Boolean);
      if (!tokens.length) return;
      if (!labelsOn){
        let value = "";
        if (FULL_DT.test(fullText)) {
          const matches = [...fullText.matchAll(FULL_DT)].map(m=>m[0]);
          value = matches.sort((a,b)=>b.length - a.length)[0] || "";
        }
        if (!value) {
          if (fullText.includes(":")){ const i=fullText.indexOf(":"); value = CLEAN(fullText.slice(i+1)); }
          if (!value) value = CLEAN(tokens[tokens.length-1] || "");
        }
        frag.appendChild(makeChip("", normalizeDateish(value || ""), false));
        return;
      }
      let label = STRIP_COLON(tokens[0] || "");
      let value = "";
      for (let i=1; i<tokens.length; i++){
        const tkn = STRIP_COLON(tokens[i]);
        if (tkn && LBL_KEY(tkn) !== LBL_KEY(label)) { value = tkn; break; }
      }
      if (!value && fullText) {
        const j=fullText.indexOf(":");
        if (j>-1){ const lbl=STRIP_COLON(fullText.slice(0,j)); if (LBL_KEY(lbl)) label = lbl; value = CLEAN(fullText.slice(j+1)); }
      }
      frag.appendChild(makeChip(label, normalizeDateish(value || ""), true));
    });

    queueMicrotask(async ()=>{
      if (frag.__dntMount) await backfillAll(frag.__dntMount, ctx, labelsOn, orderMap);
    });

    return frag;
  }

  function normalizeDocFields(docEl, ctx){
    if (!docEl || docEl.__dnt_locked) return;
    docEl.__dnt_locked = true;
    const frag = buildChipsHTML(docEl, ctx);
    docEl.innerHTML = "";
    frag.__dntMount = docEl;
    docEl.appendChild(frag);

    const mo = new MutationObserver((muts)=>{
      for (const m of muts){
        for (const n of (m.addedNodes||[])){
          if (n instanceof HTMLElement && !n.classList.contains("dnt-kv")) {
            docEl.__dnt_locked = false;
            normalizeDocFields(docEl, ctx);
            return;
          }
        }
      }
    });
    mo.observe(docEl, { childList:true });
    docEl.__dnt_mo = mo;
  }

  // mini-tasks (сокращённо)
  const miniCache = new Map();
  function pickPlan(t){ if (t.custom_target_datetime) return { dt: t.custom_target_datetime, kind: "target" }; return { dt: null, kind: null }; }
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
      const val = p ? fmtDT(p) : "—";
      const cls = p && overdue ? "dnt-chip dnt-overdue" : "dnt-chip";
      const div=document.createElement("div"); div.innerHTML = ti.description || ti.name || "";
      const ttl  = frappe.utils.escape_html(CLEAN(div.textContent || div.innerText || ""));
      return `<div class="dnt-taskline" data-open="${frappe.utils.escape_html(ti.name)}"><span class="${cls}" title="${frappe.utils.escape_html(pick.kind==="target"?t("Target at"):t("Planned"))}">${frappe.utils.escape_html(val)}</span><span class="ttl" title="${ttl}">${ttl}</span></div>`;
    }).join("");
    const more = showOpenAll ? `<div class="dnt-taskline" data-act="open-all"><span class="ttl">${frappe.utils.escape_html(t("Open all tasks") + " →")}</span></div>` : ``;
    return header + lines + more;
  }
  async function fetchMiniPrimary(caseName){
    const { message } = await frappe.call({ method: CFG.tasksMethod, args: { name: caseName, status: "Open", limit_start: 0, limit_page_length: CFG.tasksLimit, order: "desc" } });
    return { rows: (message && message.rows) || [], total: (message && message.total) || 0 };
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

  // === Резайзер: только по mousedown/touchstart на handle; DnD вырубаем на время ===
  function attachResizer(wrapper){
    if (!wrapper || wrapper.querySelector(".dnt-resizer")) return;
    const card = wrapper.querySelector(".kanban-card.content") || wrapper.querySelector(".kanban-card");
    const col = wrapper.closest(".kanban-column");
    if (!card || !col) return;

    const handle = document.createElement("div");
    handle.className = "dnt-resizer";
    handle.title = t("Resize width");
    handle.innerHTML = ICONS.resizerGrip;
    wrapper.appendChild(handle);

    const startResize = (evStart)=>{
      evStart.preventDefault(); evStart.stopPropagation();
      const isTouch = evStart.type === "touchstart";
      const getX = (ev)=> (isTouch ? (ev.touches?.[0]?.clientX||0) : (ev.clientX||0));
      const startX = getX(evStart);
      const startRect = card.getBoundingClientRect();
      const mode = currentMode();
      document.documentElement.classList.add("dnt-resizing");

      // глушим DnD/selection ТОЛЬКО пока тянем
      const stopper = (ev)=>{ ev.preventDefault(); ev.stopPropagation(); ev.stopImmediatePropagation(); };
      document.addEventListener("dragstart", stopper, true);
      document.addEventListener("selectstart", stopper, true);
      // сортировки часто слушают mousedown/mousemove — подрежем тоже, но СНИМАЕМ на окончании
      const cutDown = (ev)=>{ if (ev.target && !ev.target.closest(".dnt-resizer")) { ev.preventDefault(); ev.stopPropagation(); ev.stopImmediatePropagation(); } };
      document.addEventListener("mousedown", cutDown, true);
      document.addEventListener("touchstart", cutDown, true);

      const onMove = (ev)=>{
        const dx = getX(ev) - startX;
        let w = Math.round(startRect.width + dx);
        w = Math.max(CFG.minCardW, Math.min(CFG.maxCardW, w));
        col.style.setProperty("--dnt-card-w", w + "px");
        col.style.minWidth = `calc(${w}px + 24px)`;
        setSessW(col, mode, w);
        ev.preventDefault(); ev.stopPropagation();
      };
      const endResize = ()=>{
        ["mousemove","touchmove"].forEach(t => document.removeEventListener(t, onMove, true));
        ["mouseup","touchend","mouseleave"].forEach(t => document.removeEventListener(t, endResize, true));
        document.removeEventListener("dragstart", stopper, true);
        document.removeEventListener("selectstart", stopper, true);
        document.removeEventListener("mousedown", cutDown, true);
        document.removeEventListener("touchstart", cutDown, true);
        document.documentElement.classList.remove("dnt-resizing");
        normalizeColumns();
      };
      ["mousemove","touchmove"].forEach(t => document.addEventListener(t, onMove, true));
      ["mouseup","touchend","mouseleave"].forEach(t => document.addEventListener(t, endResize, true));
    };

    handle.addEventListener("mousedown", startResize, { passive:false });
    handle.addEventListener("touchstart", startResize, { passive:false });
  }

  function resetColumnInlineWidth(col){
    if (!col) return;
    col.style.removeProperty("--dnt-card-w");
    col.style.minWidth = `calc(var(--dnt-card-w-default) + 24px)`;
  }
  function normalizeColumns(){
    const mode = currentMode();
    getColumns().forEach(col=>{
      const hasCards = !!col.querySelector(".kanban-card, .kanban-card-wrapper");
      if (!hasCards){
        resetColumnInlineWidth(col);
        sessionColW.delete(sessKey(col, mode));
      }
    });
  }
  function applyWidthsForMode(mode){
    getColumns().forEach(resetColumnInlineWidth);
    getColumns().forEach(col=>{
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
  function resetInlineCardWidths(){
    document.querySelectorAll(".kanban-card, .kanban-card-wrapper").forEach(el=>{
      el.style.removeProperty("--dnt-card-w");
      el.style.removeProperty("width");
    });
  }

  // редактирование заголовка
  function makeTitleEditable(titleArea, name, doctype){
    if (!titleArea || titleArea.__dntEditable) return;
    titleArea.__dntEditable = true;
    const anchor = titleArea.querySelector("a");
    const currentText = (titleArea.querySelector(".kanban-card-title")?.textContent || anchor?.textContent || name || "").trim();
    const holder = titleArea.querySelector(".kanban-card-title") || document.createElement("div");
    holder.classList.add("kanban-card-title"); holder.innerHTML = "";
    const span = document.createElement("span");
    span.className = "dnt-title"; span.setAttribute("contenteditable","true"); span.textContent = currentText;
    holder.appendChild(span);
    if (anchor) anchor.replaceWith(holder); else titleArea.appendChild(holder);
    const save = async () => {
      const val = (span.textContent || "").trim();
      if (!val || val === currentText) return;
      try{ await frappe.call({ method:"frappe.client.set_value", args:{ doctype, name, fieldname:"title", value: val } });
        frappe.show_alert({ message: t("Title updated"), indicator:"green" });
      }catch{
        frappe.msgprint({ message: t("Failed to update title"), indicator:"red" });
        span.textContent = currentText;
      }
    };
    span.addEventListener("keydown", (e)=>{ if (e.key==="Enter"){ e.preventDefault(); span.blur(); } else if (e.key==="Escape"){ e.preventDefault(); span.textContent=currentText; span.blur(); }});
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

    let head = body.querySelector(".dnt-head"); if(!head){ head = document.createElement("div"); head.className = "dnt-head"; body.prepend(head); }
    let left = head.querySelector(".dnt-head-left"); if(!left){ left = document.createElement("div"); left.className = "dnt-head-left"; head.prepend(left); }
    if (img && !left.contains(img)) left.prepend(img);
    if (title) { title.querySelectorAll("br").forEach(br=>br.remove()); if(!left.contains(title)) left.appendChild(title); }
    if (meta && meta.parentElement !== head) head.appendChild(meta);
    if (doc && doc.previousElementSibling !== head) body.insertBefore(doc, head.nextSibling);

    const name = wrapper.getAttribute("data-name") || wrapper.dataset.name || card.getAttribute("data-name") || "";
    const doctype = window.cur_list?.doctype || window.cur_list?.board?.reference_doctype || CFG.caseDoctype;

    if (doc) normalizeDocFields(doc, { doctype, docName: name });

    let foot = body.querySelector(".dnt-foot"); if(!foot){ foot = document.createElement("div"); foot.className = "dnt-foot"; body.appendChild(foot); }
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
        const r = frappe.get_route?.();
        const bname = r?.[3] ? decodeURIComponent(r[3]) : (window.cur_list?.board?.name||"");
        const board = bname && { "Leads – Contact Center":"show_board_leads","CRM Board":"show_board_crm","Deals – Contact Center":"show_board_deals","Patients – Care Department":"show_board_patients" }[bname];
        const canSoft = !!board;
        const d = new frappe.ui.Dialog({
          title: t("Card actions"),
          primary_action_label: canSoft ? t("Remove from this board") : t("Delete"),
          primary_action: ()=> {
            if (canSoft) {
              frappe.call({ method:"frappe.client.set_value", args:{ doctype, name, fieldname: board, value: 0 } })
                .then(()=>{ frappe.show_alert(t("Removed from board")); setTimeout(()=> location.reload(), 50); });
            } else {
              frappe.call({ method:"frappe.client.delete", args:{ doctype, name } })
                .then(()=>{ frappe.show_alert(t("Deleted")); setTimeout(()=> location.reload(), 50); });
            }
          }
        });
        if (canSoft){
          d.set_secondary_action_label(t("Delete document"));
          d.set_secondary_action(()=> {
            frappe.confirm(t("Delete this document?"),()=>{
              frappe.call({ method:"frappe.client.delete", args:{ doctype, name } })
                .then(()=>{ frappe.show_alert(t("Deleted")); setTimeout(()=> location.reload(), 50); });
            });
          });
        }
        d.show();
      });
      row.appendChild(bDel);
      wrapper.appendChild(row);
    }

    attachResizer(wrapper);
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
      document.querySelector(".page-actions") ||
      document.querySelector(".standard-actions .page-icon-group") ||
      document.querySelector(".standard-actions") ||
      document.querySelector(".page-head-content") ||
      document.querySelector(".page-title")
    );
  }
  function injectControls(){
    document.querySelectorAll(`#${CFG.settingsBtnId}, #${CFG.modeToggleId}`).forEach(el => el.remove());
    if(!isKanbanRoute()) return;
    const anchor = findSettingsAnchor(); if(!anchor) return;

    // settings
    const btn=document.createElement("button");
    btn.id=CFG.settingsBtnId; btn.className="btn btn-default icon-btn";
    btn.setAttribute("title", t("Kanban settings"));
    btn.innerHTML = ICONS.openSettings;
    btn.addEventListener("click",()=> {
      const r = frappe.get_route(); const bname = r?.[3] ? decodeURIComponent(r[3]) : (window.cur_list?.board?.name||"");
      if (bname) frappe.set_route(`/app/kanban-board/${encodeURIComponent(bname)}`);
    });
    (document.querySelector(".page-icon-group") || anchor).insertAdjacentElement("beforeend", btn);

    // mode toggle
    const wrap = document.createElement("div");
    wrap.id = CFG.modeToggleId;
    wrap.className = "dnt-mode-toggle";
    wrap.style.marginLeft = "8px";

    const btnCompact = document.createElement("button");
    btnCompact.innerHTML = `${ICONS.modeCompact} <span>${t("Compact")}</span>`;
    const btnComfy = document.createElement("button");
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
        clearSessAll(); resetInlineCardWidths(); getColumns().forEach(resetColumnInlineWidth);
        applyWidthsForMode("compact"); setActive();
      }
    });
    btnComfy.addEventListener("click", ()=>{
      if (document.documentElement.classList.contains("dnt-compact-on")){
        document.documentElement.classList.remove("dnt-compact-on");
        try{ localStorage.setItem(`dntKanbanCompact::${getBoardName()||"__all__"}`, "0"); }catch{}
        clearSessAll(); resetInlineCardWidths(); getColumns().forEach(resetColumnInlineWidth);
        applyWidthsForMode("comfy"); setActive();
      }
    });

    // двойной клик по активной кнопке — очистка сохранённых ширин данного режима
    btnCompact.addEventListener("dblclick", ()=>{ if (document.documentElement.classList.contains("dnt-compact-on")){ clearSavedMode("compact"); clearSessAll(); resetInlineCardWidths(); getColumns().forEach(resetColumnInlineWidth); applyWidthsForMode("compact"); }});
    btnComfy  .addEventListener("dblclick", ()=>{ if (!document.documentElement.classList.contains("dnt-compact-on")){ clearSavedMode("comfy");   clearSessAll(); resetInlineCardWidths(); getColumns().forEach(resetColumnInlineWidth); applyWidthsForMode("comfy");   }});

    setActive();
    (document.querySelector(".page-icon-group") || anchor).insertAdjacentElement("beforeend", wrap);
    wrap.appendChild(btnCompact);
    wrap.appendChild(btnComfy);
  }

  async function ensure_messages(timeout_ms = 2000) {
    const start = Date.now();
    while (Date.now() - start < timeout_ms) {
      if (typeof __ === "function") return true;
      if (frappe && frappe._messages && Object.keys(frappe._messages).length) return true;
      await new Promise(r => setTimeout(r, 50));
    }
    return false;
  }

  async function run(){
    await ensure_messages();
    if(!isKanbanRoute()){
      document.documentElement.classList.remove(CFG.htmlClass,"no-color","no-column-menu","dnt-compact-on","dnt-resizing");
      document.querySelectorAll(`#${CFG.settingsBtnId}, #${CFG.modeToggleId}`).forEach(el => el.remove());
      return;
    }
    injectCSS();
    document.documentElement.classList.add(CFG.htmlClass);

    purgeLegacySaved();

    const allowColor = ["AIHub Super Admin","System Manager"].some(r=>frappe.user.has_role?.(r));
    const allowMenu  = ["AIHub Super Admin","System Manager"].some(r=>frappe.user.has_role?.(r));
    document.documentElement.classList.toggle("no-color", !allowColor);
    document.documentElement.classList.toggle("no-column-menu", !allowMenu);

    try{
      const preferRaw = localStorage.getItem(`dntKanbanCompact::${getBoardName()||"__all__"}`);
      const prefer = preferRaw === null ? CFG.compactDefault : preferRaw === "1";
      document.documentElement.classList.toggle("dnt-compact-on", !!prefer);
    }catch{
      document.documentElement.classList.toggle("dnt-compact-on", !!CFG.compactDefault);
    }

    applyWidthsForMode(currentMode());
    enhanceCards();
    injectControls();

    // наблюдаем колонки — сбрасываем ширину если опустели
    const colMO = new MutationObserver(normalizeColumns);
    getColumns().forEach(col=> colMO.observe(col, { childList:true, subtree:true }));

    let attempts = 0;
    const pump = () => {
      if (!isKanbanRoute()) return;
      attempts += 1;
      applyWidthsForMode(currentMode());
      enhanceCards();
      normalizeColumns();
      if (attempts < 30) setTimeout(pump, 60);
    };
    pump();

    if (window.__dntKanbanMO) window.__dntKanbanMO.disconnect();
    const mo = new MutationObserver(()=>{ if(isKanbanRoute()) { applyWidthsForMode(currentMode()); enhanceCards(); normalizeColumns(); } });
    mo.observe(document.body||document.documentElement,{ childList:true, subtree:true });
    window.__dntKanbanMO = mo;
  }

  if (frappe?.after_ajax) frappe.after_ajax(run); else document.addEventListener("DOMContentLoaded", run);
  window.addEventListener("load", run);
  frappe?.router?.on && frappe.router.on("change", run);
})();