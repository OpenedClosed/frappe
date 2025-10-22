/* Dantist Kanban skin — v24 (stable) + anti-flicker + vertical fields + new-card keep-show
   — Моментальная отрисовка без «дёрганья» (anti-flicker через visibility)
   — Динамические поля: вертикально друг под другом; у значения есть горизонтальный скролл
   — Чинит labels ON/OFF, пустой Display Name (добираем из db)
   — Анти-дубликаты хуков
   — Не даёт новым карточкам скрываться (show_* и статус, плюс временное исключение)
*/
(() => {
  const CFG = {
    cssId: "dantist-kanban-skin-css",
    htmlClass: "dantist-kanban-skin",
    rolesSettings: ["AIHub Super Admin", "System Manager"],
    rolesCanColor: ["AIHub Super Admin", "System Manager"],
    rolesColumnMenu:["AIHub Super Admin", "System Manager"],
    settingsBtnId: "dnt-kanban-settings",
    // tasks
    caseDoctype: "Engagement Case",
    tasksMethod: "dantist_app.api.tasks.handlers.ec_tasks_for_case",
    tasksLimit: 5,
    // сколько секунд держать новую карточку принудительно видимой
    keepShowSecs: 12
  };

  /* ====== [A] helpers ====== */
  const isKanbanRoute = () => {
    const r = frappe.get_route?.() || [];
    if (r[0] === "List" && (r[2] === "Kanban" || r[2] === "Kanban Board")) return true;
    return (location.pathname||"").includes("/view/kanban/");
  };
  const userHasAny = (roles) => { try { return roles.some((r)=>frappe.user.has_role(r)); } catch { return false; } };
  const getBoardName = () => {
    try { const r = frappe.get_route(); if (r?.[3]) return decodeURIComponent(r[3]); } catch {}
    try { const seg=(location.pathname||"").split("/").filter(Boolean); if(seg[1]==="kanban"&&seg[3]) return decodeURIComponent(seg[3]); } catch {}
    const h = document.querySelector(".page-head-content .title-text");
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
  const fmtDT = (dt) => { try { return moment(frappe.datetime.convert_to_user_tz(dt)).format("YYYY-MM-DD HH:mm"); } catch { return dt; } };
  const planDT = (t) => t.custom_target_datetime || t.due_datetime || t.custom_due_datetime || t.date || null;

  /* ====== [B] CSS (anti-flicker + верстка) ====== */
  function injectCSS(){
    if(document.getElementById(CFG.cssId)) return;
    const s=document.createElement("style"); s.id=CFG.cssId;
    s.textContent = `
      /* anti-flicker: прячем карточку до апгрейда, затем показываем */
      html.${CFG.htmlClass} .kanban-card.content{ visibility:hidden; }
      html.${CFG.htmlClass} .kanban-card.content[data-dntupgraded="1"]{ visibility:visible; }

      /* если мы пометили обёртку как keep-show — её не скрывать внешними правилами */
      html.${CFG.htmlClass} .kanban-card-wrapper[data-dnt-keep-show="1"]{ display:block !important; opacity:1 !important; }

      /* аккуратные отступы у колонок и стека карточек */
      html.${CFG.htmlClass} .kanban-column{ padding:8px; }
      html.${CFG.htmlClass} .kanban-cards{ display:block !important; }
      html.${CFG.htmlClass} .kanban-card-wrapper{ position:relative; margin:0 !important; }
      html.${CFG.htmlClass} .kanban-cards > .kanban-card-wrapper + .kanban-card-wrapper{ margin-top:8px !important; }

      /* убираем раздувание плейсхолдеров при сортировке */
      html.${CFG.htmlClass} .kanban-card-placeholder,
      html.${CFG.htmlClass} .sortable-placeholder,
      html.${CFG.htmlClass} .sortable-ghost,
      html.${CFG.htmlClass} .sortable-fallback{
        height:0 !important; min-height:0 !important; margin:0 !important; padding:0 !important;
        border:none !important; box-shadow:none !important; background:transparent !important;
      }

      /* каркас карточки */
      html.${CFG.htmlClass} .kanban-card.content{
        border-radius:14px; border:1px solid var(--border-color,rgba(0,0,0,.06));
        background:#fff; padding:12px; box-shadow:0 1px 2px rgba(0,0,0,.06);
        transition:transform .12s, box-shadow .12s;
        display:flex !important; flex-direction:column; gap:0;
      }
      html.${CFG.htmlClass} .kanban-card.content:hover{ transform:translateY(-1px); box-shadow:0 8px 22px rgba(0,0,0,.08); }

      /* шапка */
      html.${CFG.htmlClass} .kanban-card .dnt-head{
        display:flex; align-items:center; justify-content:space-between; gap:12px; min-width:0;
        margin-bottom:10px;
      }
      html.${CFG.htmlClass} .kanban-card .dnt-head-left{
        display:flex; align-items:center; gap:10px; min-width:0; flex:1 1 auto;
      }

      /* аватар */
      html.${CFG.htmlClass} .kanban-card .kanban-image{
        width:40px !important; height:40px !important;
        border-radius:10px; overflow:hidden; background:#eef2f7;
        display:flex; align-items:center; justify-content:center;
        float:none !important; margin:0 !important; flex:0 0 40px; position:static !important;
      }
      html.${CFG.htmlClass} .kanban-card .kanban-image img{
        display:block !important; width:100% !important; height:100% !important;
        max-width:none !important; object-fit:cover !important; object-position:center;
      }

      /* заголовок (editable) */
      html.${CFG.htmlClass} .kanban-card .kanban-title-area{ margin:0 !important; min-width:0; }
      html.${CFG.htmlClass} .kanban-card .kanban-title-area a{ display:none !important; }
      html.${CFG.htmlClass} .kanban-card .dnt-title{
        font-weight:600; line-height:1.25; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
        cursor:text;
      }
      html.${CFG.htmlClass} .kanban-card .dnt-title[contenteditable="true"]{ outline:none; border-radius:6px; padding:0 2px; }
      html.${CFG.htmlClass} .kanban-card .dnt-title[contenteditable="true"]:focus{ background:#f3f4f6; }

      /* «мета» в шапке (без assignments/like) */
      html.${CFG.htmlClass} .kanban-card .kanban-card-meta{
        margin-left:auto; display:flex; align-items:center; gap:8px; flex-shrink:0;
      }

      /* динамические поля — ВЕРТИКАЛЬНЫЙ СПИСОК + горизонтальный скролл у значения */
      html.${CFG.htmlClass} .kanban-card .kanban-card-doc{ padding:0; }
      html.${CFG.htmlClass} .kanban-card .dnt-kv-col{
        display:flex; flex-direction:column; gap:6px; max-height:none;
      }
      html.${CFG.htmlClass} .kanban-card .dnt-kv{
        display:flex; align-items:center; gap:6px;
        background:#f3f4f6; border:1px solid #e5e7eb; border-radius:10px; padding:4px 8px;
        font-size:12px; min-height:24px;
      }
      html.${CFG.htmlClass} .kanban-card .dnt-kv .k{ opacity:.7; flex:0 0 auto; }
      html.${CFG.htmlClass} .kanban-card .dnt-kv .v{
        font-weight:600; flex:1 1 auto; min-width:0;
        white-space:nowrap; overflow-x:auto; overflow-y:hidden; -webkit-overflow-scrolling:touch;
      }

      /* низ карточки: Assignments + Like + mini Tasks */
      html.${CFG.htmlClass} .kanban-card .dnt-foot{ margin-top:10px; display:flex; align-items:flex-start; justify-content:space-between; gap:10px; }
      html.${CFG.htmlClass} .kanban-card .dnt-tasks-mini{
        margin-top:6px; width:100%; max-height:72px; overflow-y:auto; padding-right:4px;
        border-top:1px solid #eef2f7; padding-top:6px;
      }
      html.${CFG.htmlClass} .kanban-card .dnt-taskline{
        display:flex; gap:6px; align-items:center; font-size:11px; color:#4b5563; padding:2px 0;
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis; cursor:pointer;
      }
      html.${CFG.htmlClass} .kanban-card .dnt-taskline .ttl{ font-weight:600; color:#111827; overflow:hidden; text-overflow:ellipsis; }
      html.${CFG.htmlClass} .kanban-card .dnt-chip{ border:1px solid #e5e7eb; border-radius:999px; padding:1px 6px; background:#f8fafc; font-size:10px; }
      html.${CFG.htmlClass} .kanban-card .dnt-overdue{ background:#fee2e2; border-color:#fecaca; }

      /* плавающие действия — Open + Delete */
      html.${CFG.htmlClass} .kanban-card-wrapper{ position:relative; }
      html.${CFG.htmlClass} .dnt-card-actions{
        position:absolute; top:12px; right:12px;
        display:flex; gap:6px; opacity:0; pointer-events:none; transition:opacity .12s;
      }
      html.${CFG.htmlClass} .kanban-card-wrapper:hover .dnt-card-actions{ opacity:1; pointer-events:auto; }
      html.${CFG.htmlClass} .dnt-icon-btn{
        height:28px; min-width:28px; padding:0 6px; display:grid; place-items:center;
        border-radius:8px; border:1px solid rgba(0,0,0,.12); background:#f8f9fa; cursor:pointer;
      }
      html.${CFG.htmlClass} .dnt-icon-btn:hover{ background:#fff; box-shadow:0 2px 8px rgba(0,0,0,.08); }

      /* права */
      html.${CFG.htmlClass}.no-color .kanban-column .column-options .button-group{ display:none !important; }
      html.${CFG.htmlClass}.no-column-menu .kanban-column .kanban-column-header .menu, 
      html.${CFG.htmlClass}.no-column-menu .kanban-column .kanban-column-header .dropdown,
      html.${CFG.htmlClass}.no-column-menu .kanban-column .kanban-column-header .kanban-column-actions{
        display:none !important;
      }

      /* одинаковое поведение колонок (чтобы "New" не отличалась) */
      html.${CFG.htmlClass} .kanban-board{ display:flex; gap:12px; }
      html.${CFG.htmlClass} .kanban-column{ flex:1 1 260px; min-width:240px; }
      html.${CFG.htmlClass} .kanban-column:first-child{ margin-left:0 !important; }
      html.${CFG.htmlClass} .kanban-column .kanban-title{ white-space:nowrap; }
    `;
    document.head.appendChild(s);
  }

  /* ====== [C] mini tasks ====== */
  const miniCache = new Map();
  function miniHtml(rows, total){
    if (!rows?.length) return `<div class="dnt-taskline"><span class="dnt-chip">Tasks</span> <span class="ttl">No open tasks</span></div>`;
    const lines = rows.map(t=>{
      const p = planDT(t);
      const open = (t.status||"Open")==="Open";
      const overdue = p && open && moment(p).isBefore(moment());
      const chip = p ? `<span class="dnt-chip ${overdue?'dnt-overdue':''}" title="Planned">${frappe.utils.escape_html(fmtDT(p))}</span>` : ``;
      const ttl  = frappe.utils.escape_html(t.description || t.name);
      return `<div class="dnt-taskline" data-open="${frappe.utils.escape_html(t.name)}">${chip}<span class="ttl" title="${ttl}">${ttl}</span></div>`;
    }).join("");
    const more = total>rows.length ? `<div class="dnt-taskline" data-act="open-all"><span class="ttl">Show all (${total}) →</span></div>` : ``;
    return lines + more;
  }
  async function loadMini(container, caseName){
    if (miniCache.has(caseName)) {
      container.innerHTML = miniCache.get(caseName);
      return bindMini(container, caseName);
    }
    container.innerHTML = `<div class="dnt-taskline"><span class="ttl">Loading…</span></div>`;
    try{
      const { message } = await frappe.call({
        method: CFG.tasksMethod,
        args: { name: caseName, status: "Open", limit_start: 0, limit_page_length: CFG.tasksLimit, order: "desc" }
      });
      const rows  = (message && message.rows) || [];
      const total = (message && message.total) || rows.length;
      const html  = miniHtml(rows, total);
      miniCache.set(caseName, html);
      container.innerHTML = html;
      bindMini(container, caseName);
    } catch {
      container.innerHTML = `<div class="dnt-taskline"><span class="ttl">Failed to load</span></div>`;
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

  /* ====== [D] inline title edit ====== */
  function makeTitleEditable(titleArea, name, doctype){
    if (!titleArea || titleArea.__dntEditable) return;
    titleArea.__dntEditable = true;

    const anchor = titleArea.querySelector("a");
    const currentText = (titleArea.querySelector(".kanban-card-title")?.textContent || anchor?.textContent || name || "").trim();

    const holder = titleArea.querySelector(".kanban-card-title") || document.createElement("div");
    holder.classList.add("kanban-card-title");
    holder.innerHTML = "";

    const span = document.createElement("span");
    span.className = "dnt-title";
    span.setAttribute("contenteditable","true");
    span.textContent = currentText;
    holder.appendChild(span);

    if (anchor) anchor.replaceWith(holder); else titleArea.appendChild(holder);

    const save = async () => {
      const val = (span.textContent || "").trim();
      if (!val || val === currentText) return;
      try{
        await frappe.call({ method:"frappe.client.set_value", args:{ doctype, name, fieldname:"title", value: val } });
        frappe.show_alert({ message: __("Title updated"), indicator:"green" });
      }catch{
        frappe.msgprint({ message: __("Failed to update title"), indicator:"red" });
        span.textContent = currentText;
      }
    };
    span.addEventListener("keydown", (e)=>{
      if (e.key==="Enter"){ e.preventDefault(); span.blur(); }
      else if (e.key==="Escape"){ e.preventDefault(); span.textContent=currentText; span.blur(); }
    });
    span.addEventListener("click", e=> e.stopPropagation());
    span.addEventListener("blur", save);
  }

  /* ====== [E] Метаданные/нормализация полей + реформа карточки ====== */
  function getFieldLabelMap(dt){
    const meta = frappe.get_meta(dt);
    const map = {};
    (meta?.fields || []).forEach(f=>{
      if (f?.fieldname) map[f.fieldname] = f.label || f.fieldname;
    });
    (frappe.model.std_fields || []).forEach(f=>{
      if (f?.fieldname && !map[f.fieldname]) map[f.fieldname] = f.label || f.fieldname;
    });
    map.name = map.name || "Name";
    return map;
  }

  function coerceFieldsList(dt, any){
    let arr=[];
    if(Array.isArray(any)) arr=any;
    else if(typeof any==="string" && any.trim()){
      try{ const j=JSON.parse(any); if(Array.isArray(j)) arr=j; }
      catch{ arr=any.split(/[,\s]+/).filter(Boolean); }
    }
    const meta = frappe.get_meta(dt);
    const fieldnames = new Set((meta?.fields||[]).map(f=>f.fieldname)
      .concat((frappe.model.std_fields||[]).map(f=>f.fieldname))
      .concat(["name"]));
    const label2fn = {};
    (meta?.fields||[]).forEach(f=>{
      if (f?.label) label2fn[f.label.trim().toLowerCase()] = f.fieldname;
    });
    (frappe.model.std_fields||[]).forEach(f=>{
      if (f?.label) label2fn[f.label.trim().toLowerCase()] = f.fieldname;
    });

    const out = [];
    arr.forEach(x=>{
      const raw = (""+x).trim(); if(!raw) return;
      if (fieldnames.has(raw)) { out.push(raw); return; }
      const guess = label2fn[raw.toLowerCase()];
      if (guess && fieldnames.has(guess)) out.push(guess);
    });
    return [...new Set(out)];
  }

  function patchSettingsDialog(){
    if(!frappe?.views?.KanbanView) return;
    const _show=frappe.views.KanbanView.prototype.show_kanban_settings;
    if(_show && !_show._dnt){
      frappe.views.KanbanView.prototype.show_kanban_settings=function(){
        try{ this.board.fields = coerceFieldsList(this.doctype, this.board?.fields); }catch{}
        return _show.apply(this, arguments);
      };
      frappe.views.KanbanView.prototype.show_kanban_settings._dnt=true;
    }
    const KS = window.frappe?.views?.KanbanSettings || window.KanbanSettings;
    if(KS && !KS.prototype._dnt){
      const orig=KS.prototype.get_fields;
      KS.prototype.get_fields=function(){
        try{ this.fields = coerceFieldsList(this.doctype, this.settings?.fields || this.fields); }catch{}
        return orig.call(this);
      };
      KS.prototype._dnt=true;
    }
  }

  // поддержка рендера полей при labels ON/OFF + подхват пустого display_name
  async function reformatCardDocFields(body){
    const docEl = body?.querySelector(".kanban-card-doc");
    if (!docEl) return;

    const board = window.cur_list?.board;
    const dt = window.cur_list?.doctype || board?.reference_doctype;
    const fieldsOrder = Array.isArray(board?.fields) ? board.fields : [];
    const labelMap = getFieldLabelMap(dt);

    const rows = Array.from(docEl.querySelectorAll(":scope > .text-truncate"));
    const pairs = [];

    rows.forEach((row, idx)=>{
      const spans = row.querySelectorAll(":scope > span");
      let label = "", value = "";
      if (spans.length >= 2) {
        label = (spans[0].textContent || "").replace(/:\s*$/,"").trim();
        value = (spans[1].textContent || "").trim();
      } else if (spans.length === 1) {
        value = (spans[0].textContent || "").trim();
        const fn = fieldsOrder[idx] || "";
        label = labelMap[fn] || fn || "";
      }
      if (label) pairs.push([label, value, idx]);
    });

    // если Display Name пустой — дочитаем одно поле
    try{
      const wrap = body.closest(".kanban-card-wrapper");
      const docname = wrap?.getAttribute("data-name");
      if (docname) {
        for (let i=0;i<pairs.length;i++){
          const [lbl, val] = pairs[i];
          if ((lbl || "").toLowerCase() === "display name" && !val) {
            const r = await frappe.db.get_value(dt, docname, "display_name");
            const vv = r?.message?.display_name || "";
            if (vv) pairs[i][1] = vv;
          }
        }
      }
    }catch(_){}

    // перерисовка в вертикальные «чипы»
    docEl.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "dnt-kv-col";
    pairs.forEach(([k,v])=>{
      const chip = document.createElement("div");
      chip.className = "dnt-kv";
      const sk = document.createElement("span"); sk.className = "k"; sk.textContent = k + ":";
      const sv = document.createElement("span"); sv.className = "v"; sv.textContent = v || "—";
      chip.appendChild(sk); chip.appendChild(sv);
      wrap.appendChild(chip);
    });
    docEl.appendChild(wrap);
  }

  /* ====== [F] перестройка DOM карточки ====== */
  function upgradeCard(wrapper){
    const card = wrapper?.querySelector?.(".kanban-card.content");
    if(!card || card.dataset.dntupgraded==="1") return;

    const body  = card.querySelector(".kanban-card-body");
    const img   = card.querySelector(":scope > .kanban-image");
    const title = body?.querySelector(".kanban-title-area");
    const meta  = body?.querySelector(".kanban-card-meta");
    const doc   = body?.querySelector(".kanban-card-doc");
    if(!body) { card.setAttribute("data-dntupgraded","1"); return; }

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

    // нормализуем поля
    reformatCardDocFields(body);

    let foot = body.querySelector(".dnt-foot");
    if(!foot){ foot = document.createElement("div"); foot.className = "dnt-foot"; body.appendChild(foot); }

    const assign = (meta || body).querySelector(".kanban-assignments");
    const like   = (meta || body).querySelector(".like-action");
    if(assign && !foot.contains(assign)) foot.appendChild(assign);
    if(like   && !foot.contains(like))   foot.appendChild(like);
    if(meta && !meta.children.length) meta.remove();

    const name = wrapper.getAttribute("data-name");
    const doctype = window.cur_list?.doctype || window.cur_list?.board?.reference_doctype;
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
      const bOpen = document.createElement("div"); bOpen.className="dnt-icon-btn"; bOpen.title=__("Open");
      bOpen.appendChild(stdIcon("external-link","sm"));
      bOpen.addEventListener("click",(e)=>{ e.stopPropagation(); if (doctype && name) frappe.set_route("Form", doctype, name); });
      row.appendChild(bOpen);

      const bDel = document.createElement("div"); bDel.className="dnt-icon-btn"; bDel.title=__("Delete");
      bDel.appendChild(stdIcon("delete","sm"));
      bDel.addEventListener("click",(e)=>{
        e.stopPropagation();
        if (!doctype || !name) return;
        frappe.confirm(__("Delete this document?"),()=>{
          frappe.call({ method:"frappe.client.delete", args:{ doctype, name } })
            .then(()=>{ frappe.show_alert(__("Deleted")); try{window.cur_list?.refresh();}catch{} });
        });
      });
      row.appendChild(bDel);

      wrapper.appendChild(row);
    }

    card.setAttribute("data-dntupgraded","1");
  }

  const enhanceCards = () => {
    // первый проход максимально рано
    document.querySelectorAll(".kanban-card-wrapper").forEach(upgradeCard);
    // второй проход в следующий кадр — добираем лениво дорисованные
    requestAnimationFrame(()=> {
      document.querySelectorAll(".kanban-card-wrapper").forEach(upgradeCard);
    });
  };

  /* ====== [G] settings button ====== */
  function injectSettingsBtn(){
    document.querySelectorAll(`#${CFG.settingsBtnId}`).forEach(el => el.remove());
    if(!isKanbanRoute() || !userHasAny(CFG.rolesSettings)) return;

    const anchor = document.querySelector(".standard-actions .page-icon-group") || document.querySelector(".standard-actions");
    if(!anchor) return;

    const btn=document.createElement("button");
    btn.id=CFG.settingsBtnId; btn.className="btn btn-default icon-btn";
    btn.setAttribute("title", __("Kanban settings"));
    btn.appendChild(stdIcon("edit","sm"));
    btn.addEventListener("click",()=> {
      const bname = getBoardName();
      if (bname) frappe.set_route(`/app/kanban-board/${encodeURIComponent(bname)}`);
    });
    anchor.insertAdjacentElement("afterend", btn);
  }
  function ensureSettingsBtnSticky(){
    let tries=0, max=40;
    const tick=()=>{ if(!isKanbanRoute()) return;
      injectSettingsBtn();
      tries+=1;
      if (document.getElementById(CFG.settingsBtnId)) return;
      if (tries<max) setTimeout(tick, 50);
    };
    tick();
    const head = document.querySelector(".page-head-content") || document.body;
    try{
      const mo = new MutationObserver(()=> {
        if (!isKanbanRoute()) return;
        if (!document.getElementById(CFG.settingsBtnId)) injectSettingsBtn();
      });
      mo.observe(head, { childList:true, subtree:true });
      window.__dntKanbanHeadMO = mo;
    }catch{}
  }

  /* ====== [H] fix settings dialog fields ====== */
  function patchSettingsDialogWrapper(){ patchSettingsDialog(); }

  /* ====== [I] не скрывать новые карточки: show/status + исключение ====== */
  const BOARD = {
    "CRM Board":                  { flag: "show_board_crm",      status: "status_crm_board" },
    "Leads – Contact Center":     { flag: "show_board_leads",    status: "status_leads" },
    "Deals – Contact Center":     { flag: "show_board_deals",    status: "status_deals" },
    "Patients – Care Department": { flag: "show_board_patients", status: "status_patients" },
  };

  // одноразовый сниффер "+ Add Card" (анти-дубликат)
  function bindKanbanAddClickSniffer(){
    if (window.__DNT_BOUND_ADDCLICK) return;
    window.__DNT_BOUND_ADDCLICK = true;
    document.body.addEventListener("click", (ev)=>{
      if (!isKanbanRoute()) return;
      const addBtn = ev.target.closest?.(".kanban-column .add-card");
      if (!addBtn) return;

      const col = addBtn.closest(".kanban-column");
      const columnLabel =
        col?.querySelector?.(".kanban-column-header .kanban-title")?.textContent?.trim()
        || col?.getAttribute("data-column-value") || "";

      const boardName = getBoardName();
      const map = BOARD[boardName];
      window.__DNT_KANBAN_CTX = { ts: Date.now(), boardName, columnLabel, ...(map||{}) };
    }, true);
  }

  function applyDefaultsFromCtx(frm, opts={}){
    try {
      if (!frm || frm.doc.doctype !== CFG.caseDoctype) return;
      if (!frm.is_new()) return;

      const ctx = window.__DNT_KANBAN_CTX;
      if (!ctx || !ctx.flag || !ctx.status) return;

      const fresh = (Date.now() - (ctx.ts||0)) < 10*60*1000;
      if (!fresh) return;

      if (!frm.doc[ctx.flag]) frm.set_value(ctx.flag, 1);

      if (ctx.columnLabel) {
        const fieldname = ctx.status;
        const df = frm.fields_dict[fieldname]?.df;
        let allowed = true;
        if (df?.options) {
          const opts = (typeof df.options === "string") ? df.options.split("\n") : df.options;
          if (Array.isArray(opts)) allowed = opts.includes(ctx.columnLabel);
        }
        if (allowed && frm.doc[fieldname] !== ctx.columnLabel) {
          frm.set_value(fieldname, ctx.columnLabel);
        }
      }
      if (!opts.keep) setTimeout(()=> { delete window.__DNT_KANBAN_CTX; }, 0);
    } catch(_) {}
  }

  function registerFormHooks(){
    if (window.__DNT_FORM_HOOKS) return;
    window.__DNT_FORM_HOOKS = true;
    frappe.ui.form.on(CFG.caseDoctype, {
      onload(frm){  applyDefaultsFromCtx(frm); },
      refresh(frm){ applyDefaultsFromCtx(frm); },
      before_save(frm){ applyDefaultsFromCtx(frm, { keep:false }); }
    });
  }

  // страховка: серверный add_card без формы — ставим show_* вручную + держим карточку видимой
  function keepCardTemporarilyVisible(docname){
    if (!docname) return;
    const deadline = Date.now() + CFG.keepShowSecs * 1000;
    const mark = () => {
      const wrap = document.querySelector(`.kanban-card-wrapper[data-name="${CSS.escape(docname)}"]`);
      if (wrap) {
        wrap.setAttribute("data-dnt-keep-show","1");
        // снимем флаг по истечении окна
        setTimeout(()=> wrap.removeAttribute("data-dnt-keep-show"), CFG.keepShowSecs*1000);
        return true;
      }
      return false;
    };
    // несколько попыток, т.к. DOM может перерисовываться
    const it = setInterval(()=>{
      if (mark() || Date.now() > deadline) clearInterval(it);
    }, 120);
  }

  function patchAddCardCall(){
    if (frappe.__dnt_add_card_defaults_v24p2) return;
    frappe.__dnt_add_card_defaults_v24p2 = true;

    const origCall = frappe.call;
    frappe.call = function(opts){
      const isObj  = opts && typeof opts === "object";
      const method = isObj ? (opts.method || "") : "";
      const args   = isObj ? (opts.args   || {}) : {};
      const p = origCall.apply(this, arguments);

      if (method === "frappe.desk.doctype.kanban_board.kanban_board.add_card") {
        const boardName = getBoardName();
        const map = BOARD[boardName];

        Promise.resolve(p).then(async (r)=>{
          try {
            const docname =
              args?.docname ||
              r?.message?.docname ||
              r?.message?.card?.docname ||
              r?.message?.doc?.name ||
              null;

            if (!docname) return;

            // 1) сразу держим карточку видимой в DOM
            keepCardTemporarilyVisible(docname);

            // 2) выставим show_* флаг, если он есть в карте борда
            if (map?.flag) {
              await frappe.call({
                method: "frappe.client.set_value",
                args: { doctype: CFG.caseDoctype, name: docname, fieldname: map.flag, value: 1 }
              });
            }

            // 3) освежим список, апгрейдним и ещё раз пометим на всякий случай
            try { window.cur_list?.refresh(); } catch {}
            setTimeout(()=> { enhanceCards(); keepCardTemporarilyVisible(docname); }, 50);
          } catch(_) {}
        }).catch(()=>{});
      }
      return p;
    };
  }

  /* ====== [J] perms ====== */
  function applyPermClasses(){
    const allowColor = userHasAny(CFG.rolesCanColor);
    const allowMenu  = userHasAny(CFG.rolesColumnMenu);
    document.documentElement.classList.toggle("no-color", !allowColor);
    document.documentElement.classList.toggle("no-column-menu", !allowMenu);
  }

  /* ====== [K] boot ====== */
  // быстрый ранний CSS для минимизации «перекраски»
  injectCSS();

  const mo = new MutationObserver(()=>{
    if(isKanbanRoute()) enhanceCards();
  });

  function run(){
    if(!isKanbanRoute()){
      document.documentElement.classList.remove(CFG.htmlClass,"no-color","no-column-menu");
      document.querySelectorAll(`#${CFG.settingsBtnId}`).forEach(el => el.remove());
      return;
    }
    document.documentElement.classList.add(CFG.htmlClass);
    applyPermClasses();

    // максимально ранняя апгрейд-отрисовка
    enhanceCards();

    ensureSettingsBtnSticky();
    patchSettingsDialogWrapper();

    bindKanbanAddClickSniffer();
    registerFormHooks();
    patchAddCardCall();

    mo.disconnect();
    mo.observe(document.body||document.documentElement,{ childList:true, subtree:true });
  }

  if (frappe?.after_ajax) frappe.after_ajax(run); else document.addEventListener("DOMContentLoaded", run);
  frappe?.router?.on && frappe.router.on("change", run);
})();