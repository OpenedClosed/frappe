/* Dantist Kanban skin — v25.4 (universal backfill)
   — Порядок = Kanban Settings (board.fields)
     * Labels ON: сортируем по board.fields
     * Labels OFF: нативный порядок + чипы из БД вставляем в позиции по board.fields
   — Универсальный backfill: для ВСЕХ полей из board.fields
     * batch get_value по всем полям и подстановка в пустые чипы
     * если чипа нет, но в БД есть значение — создаём чип (в правильном месте)
   — Display Name: доп. синонимы + сборка из First/Middle/Last/Title как особый случай
   — Labels ON: пустые → "—"; Labels OFF: пустые не рисуем
   — Фикс действий (open/delete), «карандаш» настроек
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
    BOARD: {
      "CRM Board":                  { flag: "show_board_crm",      status: "status_crm_board" },
      "Leads – Contact Center":     { flag: "show_board_leads",    status: "status_leads" },
      "Deals – Contact Center":     { flag: "show_board_deals",    status: "status_deals" },
      "Patients – Care Department": { flag: "show_board_patients", status: "status_patients" },
    },
    debug: { enableStats:false }
  };

  /* ===== helpers ===== */
  const isKanbanRoute = () => {
    const r = frappe.get_route?.() || [];
    if (r[0] === "List" && (r[2] === "Kanban" || r[2] === "Kanban Board")) return true;
    return (location.pathname||"").includes("/view/kanban/");
  };
  const userHasAny = (roles) => { try { return roles.some((r)=>frappe.user.has_role(r)); } catch { return false; } };
  const CLEAN = s => (s||"").replace(/\u00A0/g," ").replace(/\s+/g," ").trim();
  const STRIP_COLON = s => CLEAN(s).replace(/:\s*$/,"");
  const LBL_KEY = s => STRIP_COLON(s).toLowerCase();
  const getShowLabelsFlag = () => {
    const b = window.cur_list?.board || window.cur_list?.kanban_board;
    return !!(b && (b.show_labels === 1 || b.show_labels === true));
  };

  const LABEL_ALIASES = {
    display_name: new Set([
      "display name","display_name","displayname",
      "отображаемое имя","имя профиля","full name","name","фио",
      "имя / фио","имя и фамилия","имя, фамилия"
    ])
  };
  const isDisplayName = (s)=> LABEL_ALIASES.display_name.has(LBL_KEY(s));

  /* ===== CSS ===== */
  function injectCSS(){
    if(document.getElementById(CFG.cssId)) return;
    const s=document.createElement("style"); s.id=CFG.cssId;
    s.textContent = `
      html.${CFG.htmlClass} .kanban-card.content{
        border-radius:14px; border:1px solid var(--border-color,rgba(0,0,0,.06));
        background:#fff; padding:12px; box-shadow:0 1px 2px rgba(0,0,0,.06);
        display:flex !important; flex-direction:column; gap:0; transition:transform .12s, box-shadow .12s;
      }
      html.${CFG.htmlClass} .kanban-card.content:hover{ transform:translateY(-1px); box-shadow:0 8px 22px rgba(0,0,0,.08); }
      html.${CFG.htmlClass} .dnt-head{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:10px; }
      html.${CFG.htmlClass} .dnt-head-left{ display:flex; align-items:center; gap:10px; min-width:0; flex:1 1 auto; }
      html.${CFG.htmlClass} .kanban-image{ width:40px !important; height:40px !important; border-radius:10px; overflow:hidden; background:#eef2f7; flex:0 0 40px; }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-kv{
        display:flex; align-items:center; gap:6px; background:#f3f4f6; border:1px solid #e5e7eb;
        border-radius:10px; padding:4px 8px; font-size:12px; min-height:24px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
      }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-kv + .dnt-kv { margin-top:6px; }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-k{ opacity:.7; }
      html.${CFG.htmlClass} .kanban-card-doc .dnt-v{ font-weight:600; min-width:0; overflow:hidden; text-overflow:ellipsis; }
      html.${CFG.htmlClass} .dnt-card-actions{ position:absolute; top:12px; right:12px; display:flex; gap:6px; z-index:3; }
      html.${CFG.htmlClass} .dnt-icon-btn{ height:28px; min-width:28px; padding:0 6px; display:grid; place-items:center; border-radius:8px; border:1px solid rgba(0,0,0,.12); background:#f8f9fa; cursor:pointer; }
    `;
    document.head.appendChild(s);
  }

  /* ===== board fields & meta ===== */
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
    if (!out.includes("display_name")) out.unshift("display_name");
    return [...new Set(out)];
  }
  function getBoardOrderMap(doctype){
    try{
      const board = window.cur_list?.board || window.cur_list?.kanban_board;
      const fields = coerceFieldsList(doctype, board?.fields || []);
      const map = new Map(); fields.forEach((fn,i)=> map.set(fn,i));
      if (!map.has("display_name")) map.set("display_name", 0);
      return map;
    }catch{ return new Map([["display_name",0]]); }
  }
  function buildMetaMaps(doctype){
    const meta = frappe.get_meta(doctype);
    const label2fn = {}, fn2label = {};
    (meta?.fields||[]).forEach(f=>{
      const lbl = CLEAN(f?.label||"");
      if (lbl){ label2fn[LBL_KEY(lbl)] = f.fieldname; fn2label[f.fieldname] = lbl; }
    });
    (frappe.model.std_fields||[]).forEach(f=>{
      const lbl = CLEAN(f?.label||"");
      if (lbl){ label2fn[LBL_KEY(lbl)] = f.fieldname; fn2label[f.fieldname] = lbl; }
    });
    LABEL_ALIASES.display_name.forEach(a=> label2fn[a] = "display_name");
    return { label2fn, fn2label };
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

  /* ===== parse native rows ===== */
  function collectPairsFromNative(docEl, doctype){
    const rows = Array.from(docEl.querySelectorAll(":scope > .text-truncate, :scope > .ellipsis"));
    const pairs = [];
    const labelsOn = getShowLabelsFlag();
    const { label2fn } = buildMetaMaps(doctype);

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
        if (value) pairs.push({ k:"", v:value, row, fieldname:null });
        return;
      }

      let label = STRIP_COLON(nonEmpty[0] || "");
      let value = "";
      for (let i=1; i<nonEmpty.length; i++){
        const t = STRIP_COLON(nonEmpty[i]);
        if (t && LBL_KEY(t) !== LBL_KEY(label)) { value = t; break; }
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
      const fn = label2fn[LBL_KEY(label)] || (isDisplayName(label) ? "display_name" : null);
      pairs.push({ k: label, v: value || "", row, fieldname: fn });
    });

    // dedupe по fieldname/label
    const seen = new Set(), out=[];
    for (const o of pairs){
      const key = (o.fieldname || o.k || "").toLowerCase();
      if (key && seen.has(key)) continue;
      if (key) seen.add(key);
      out.push(o);
    }
    return out;
  }

  /* ===== DB values (batch) ===== */
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

  /* ===== chips ===== */
  function makeChip(label, value, showLabel){
    const kv = document.createElement("div");
    kv.className = "dnt-kv text-truncate";
    kv.dataset.dntLabel = CLEAN(label||"");
    if (showLabel && CLEAN(label)){
      const sk = document.createElement("span");
      sk.className = "dnt-k";
      sk.textContent = STRIP_COLON(label) + ":";
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
  function moveChipToIndex(container, chip, idx){
    const nodes = Array.from(container.querySelectorAll(":scope > .dnt-kv")).filter(n=>n!==chip);
    const target = nodes[idx];
    if (target) container.insertBefore(chip, target);
    else container.appendChild(chip);
  }

  /* ===== универсальный backfill ===== */
  async function backfillAll(container, ctx, labelsOn, orderMap){
    const { fn2label } = buildMetaMaps(ctx.doctype);
    const boardFields = [...orderMap.keys()];

    // 1) Батч: берём все поля борда + компоненты для ДН
    const need = [...new Set(boardFields.concat(["display_name","first_name","middle_name","last_name","title"]))];
    const v = await getValuesBatch(ctx.doctype, ctx.docName, need);

    // 2) Если ДН пуст в БД — соберём
    if (!CLEAN(v.display_name)) v.display_name = composeDisplayName(v);

    // 3) для существующих чипов — дозаполнение пустых
    Array.from(container.querySelectorAll(":scope > .dnt-kv")).forEach(chip=>{
      const labelText = CLEAN(chip.dataset.dntLabel || chip.querySelector(".dnt-k")?.textContent || "");
      const lbl = STRIP_COLON(labelText);
      const sv = chip.querySelector(".dnt-v");
      const current = CLEAN(sv?.textContent || "");
      const fnGuess = Object.entries(fn2label).find(([fn,lab]) => LBL_KEY(lab)===LBL_KEY(lbl))?.[0]
        || (isDisplayName(lbl) ? "display_name" : null);

      if (!current && fnGuess && CLEAN(v[fnGuess])) {
        sv.textContent = CLEAN(v[fnGuess]);
      }
    });

    // 4) создать недостающие чипы (есть значение в БД, но нет чипа)
    boardFields.forEach(fn=>{
      const value = CLEAN(v[fn]);
      if (!value) return; // не засоряем пустыми
      const human = fn2label[fn] || (fn==="display_name" ? "Display Name" : fn);
      const have = Array.from(container.querySelectorAll(":scope > .dnt-kv")).some(ch=>{
        const lbl = CLEAN(ch.dataset.dntLabel || ch.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
        return (LBL_KEY(lbl) === LBL_KEY(human)) || (fn==="display_name" && isDisplayName(lbl));
      });
      if (have) return;

      const chip = makeChip(human, value, labelsOn);
      insertChipAtIndex(container, chip, orderMap.get(fn) ?? 0);
    });

    // 5) специальные правила отображения
    if (!labelsOn){
      // при labels OFF скрываем чипы, у которых пустое значение
      Array.from(container.querySelectorAll(":scope > .dnt-kv")).forEach(ch=>{
        const val = CLEAN(ch.querySelector(".dnt-v")?.textContent || "");
        if (!val) ch.remove();
      });
    } else {
      // при labels ON ставим «—» в пустых
      Array.from(container.querySelectorAll(":scope > .dnt-kv .dnt-v")).forEach(sv=>{
        if (!CLEAN(sv.textContent)) sv.textContent = "—";
      });
    }

    // 6) привести порядок к orderMap (только если labels ON)
    if (labelsOn){
      const chips = Array.from(container.querySelectorAll(":scope > .dnt-kv"));
      chips.sort((a,b)=>{
        const la = CLEAN(a.dataset.dntLabel || a.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
        const lb = CLEAN(b.dataset.dntLabel || b.querySelector(".dnt-k")?.textContent || "").replace(/:$/,"");
        const fna = (Object.entries(fn2label).find(([fn,lab])=> LBL_KEY(lab)===LBL_KEY(la))||[])[0] || (isDisplayName(la)?"display_name":null);
        const fnb = (Object.entries(fn2label).find(([fn,lab])=> LBL_KEY(lab)===LBL_KEY(lb))||[])[0] || (isDisplayName(lb)?"display_name":null);
        const ia = orderMap.has(fna||"") ? orderMap.get(fna||"") : 9999;
        const ib = orderMap.has(fnb||"") ? orderMap.get(fnb||"") : 9999;
        return ia-ib;
      });
      chips.forEach(ch => container.appendChild(ch));
    }
  }

  function buildChipsHTML(pairs, ctx){
    const labelsOn = getShowLabelsFlag();
    const orderMap = getBoardOrderMap(ctx.doctype);
    const { fn2label } = buildMetaMaps(ctx.doctype);

    let items = pairs.slice();
    if (labelsOn){
      items.sort((a,b)=>{
        const ia = orderMap.has(a.fieldname||"") ? orderMap.get(a.fieldname||"") : 9999;
        const ib = orderMap.has(b.fieldname||"") ? orderMap.get(b.fieldname||"") : 9999;
        return ia - ib;
      });
    }

    const frag = document.createDocumentFragment();
    items.forEach(o=>{
      const k = o.k || (o.fieldname ? fn2label[o.fieldname]||"" : "");
      const v = (o.v || "").trim();
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

  /* ===== карточка и окружение ===== */
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

    // footer
    let foot = body.querySelector(".dnt-foot");
    if(!foot){ foot = document.createElement("div"); foot.className = "dnt-foot"; body.appendChild(foot); }
    const assign = (meta || body).querySelector(".kanban-assignments");
    const like   = (meta || body).querySelector(".like-action");
    if(assign && !foot.contains(assign)) foot.appendChild(assign);
    if(like   && !foot.contains(like))   foot.appendChild(like);
    if(meta && !meta.children.length) meta.remove();

    // actions
    if (!wrapper.querySelector(".dnt-card-actions")){
      const row = document.createElement("div"); row.className="dnt-card-actions";
      const bOpen = document.createElement("div"); bOpen.className="dnt-icon-btn"; bOpen.title=__("Open");
      bOpen.innerHTML = frappe.utils.icon("external-link","sm"); bOpen.addEventListener("click",(e)=>{ e.stopPropagation(); if (doctype && name) frappe.set_route("Form", doctype, name); });
      row.appendChild(bOpen);

      const bDel = document.createElement("div"); bDel.className="dnt-icon-btn"; bDel.title=__("Delete / Remove from board");
      bDel.innerHTML = frappe.utils.icon("delete","sm");
      bDel.addEventListener("click",(e)=>{
        e.stopPropagation();
        const getBoardName=()=>{ try { const r = frappe.get_route(); if (r?.[3]) return decodeURIComponent(r[3]); } catch {} return window.cur_list?.board?.name || null; };
        const board = CFG.BOARD[getBoardName()];
        const canSoft = !!(board && board.flag);
        const d = new frappe.ui.Dialog({
          title: __("Card actions"),
          primary_action_label: canSoft ? __("Remove from this board") : __("Delete"),
          primary_action: ()=> {
            if (canSoft) {
              frappe.call({ method:"frappe.client.set_value", args:{ doctype, name, fieldname: board.flag, value: 0 } })
                .then(()=>{ frappe.show_alert(__("Removed from board")); try{window.cur_list?.refresh();}catch{}; d.hide(); });
            } else {
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
    const anchor = findSettingsAnchor(); if(!anchor) return;
    const btn=document.createElement("button");
    btn.id=CFG.settingsBtnId; btn.className="btn btn-default icon-btn";
    btn.setAttribute("title", __("Kanban settings"));
    btn.innerHTML = frappe.utils.icon("edit","sm");
    btn.addEventListener("click",()=> {
      const r = frappe.get_route(); const bname = r?.[3] ? decodeURIComponent(r[3]) : (window.cur_list?.board?.name||"");
      if (bname) frappe.set_route(`/app/kanban-board/${encodeURIComponent(bname)}`);
    });
    (document.querySelector(".page-icon-group") || anchor).insertAdjacentElement("beforeend", btn);
  }
  function ensureSettingsBtnSticky(){
    let tries=0, max=120;
    const tick=()=>{ if(!isKanbanRoute()) return;
      injectSettingsBtn(); tries+=1;
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
  }

  /* ===== boot ===== */
  function run(){
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

    // несколько прогонов для поздней догрузки
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