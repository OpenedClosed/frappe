/* Dantist Kanban skin — v17 */
(() => {
  const CFG = {
    cssId: "dantist-kanban-skin-css",
    htmlClass: "dantist-kanban-skin",
    rolesSettings: ["AIHub Super Admin", "System Manager"],
    rolesDelete:   ["AIHub Super Admin", "System Manager", "AIHub Admin"],
    rolesCanColor: ["AIHub Super Admin", "System Manager"],
    rolesColumnMenu:["AIHub Super Admin", "System Manager"],
  };

  /* ---------- helpers ---------- */
  const isKanbanRoute = () => {
    const r = frappe.get_route?.() || [];
    if (r[0] === "List" && (r[2] === "Kanban" || r[2] === "Kanban Board")) return true;
    return (location.pathname||"").includes("/view/kanban/");
  };
  const userHasAny = (roles) => { try { return roles.some((r)=>frappe.user.has_role(r)); } catch { return false; } };
  const getBoardName = () => {
    try { const r = frappe.get_route(); if (r?.[3]) return decodeURIComponent(r[3]); } catch {}
    try { const seg=(location.pathname||"").split("/").filter(Boolean); if(seg[1]==="kanban"&&seg[3]) return decodeURIComponent(seg[3]); } catch {}
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

  /* ---------- CSS ---------- */
  function injectCSS(){
    if(document.getElementById(CFG.cssId)) return;
    const s=document.createElement("style"); s.id=CFG.cssId;
    s.textContent = `
      /* каркас карточки */
      html.${CFG.htmlClass} .kanban-card.content{
        border-radius:14px; border:1px solid var(--border-color,rgba(0,0,0,.06));
        background:#fff; padding:12px; box-shadow:0 1px 2px rgba(0,0,0,.06);
        transition:transform .12s, box-shadow .12s;
        display:flex !important; flex-direction:column; gap:0; /* управляем отступами блоков индивидуально */
      }
      html.${CFG.htmlClass} .kanban-card.content:hover{ transform:translateY(-1px); box-shadow:0 8px 22px rgba(0,0,0,.08); }

      /* шапка */
      html.${CFG.htmlClass} .kanban-card .dnt-head{
        display:flex; align-items:center; justify-content:space-between; gap:12px; min-width:0;
        margin-bottom:10px; /* +воздух над гибкими полями */
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

      /* заголовок */
      html.${CFG.htmlClass} .kanban-card .kanban-card-title{ 
        font-weight:600; line-height:1.25; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
      }
      html.${CFG.htmlClass} .kanban-card .kanban-title-area{ margin:0 !important; min-width:0; }
      html.${CFG.htmlClass} .kanban-card .kanban-title-area a{ text-decoration:none; color:inherit; }

      /* «мета» в шапке — тут останутся всё, КРОМЕ assignment/like */
      html.${CFG.htmlClass} .kanban-card .kanban-card-meta{
        margin-left:auto; display:flex; align-items:center; gap:8px; flex-shrink:0;
      }

      /* гибкие поля */
      html.${CFG.htmlClass} .kanban-card .kanban-card-doc{
        display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:6px 10px; padding:0;
      }
      @media (max-width:640px){
        html.${CFG.htmlClass} .kanban-card .kanban-card-doc{ grid-template-columns:1fr; }
      }
      html.${CFG.htmlClass} .kanban-card .kanban-card-doc .text-truncate>span{
        display:inline-block; max-width:100%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
        background:#f3f4f6; border:1px solid #e5e7eb; border-radius:8px; padding:3px 6px; font-size:12px;
      }

      /* нижний блок: Assignments + Like */
      html.${CFG.htmlClass} .kanban-card .dnt-foot{
        margin-top:10px; display:flex; align-items:center; justify-content:space-between; gap:10px;
      }
      html.${CFG.htmlClass} .kanban-card .dnt-foot .kanban-assignments{ order:1; }
      html.${CFG.htmlClass} .kanban-card .dnt-foot .like-action{ order:2; }

      /* плавающие действия на карточке */
      html.${CFG.htmlClass} .kanban-card-wrapper{ position:relative; }
      html.${CFG.htmlClass} .dnt-card-actions{
        position:absolute; top:12px; right:12px; /* опустил чуть ниже */
        display:flex; gap:6px; opacity:0; pointer-events:none; transition:opacity .12s;
      }
      html.${CFG.htmlClass} .kanban-card-wrapper:hover .dnt-card-actions{ opacity:1; pointer-events:auto; }
      html.${CFG.htmlClass} .dnt-icon-btn{
        height:28px; min-width:28px; padding:0 6px; display:grid; place-items:center;
        border-radius:8px; border:1px solid rgba(0,0,0,.12); background:#f8f9fa; cursor:pointer;
      }
      html.${CFG.htmlClass} .dnt-icon-btn:hover{ background:#fff; box-shadow:0 2px 8px rgba(0,0,0,.08); }

      /* права на цвет и меню столбца */
      html.${CFG.htmlClass}.no-color .kanban-column .column-options .button-group{ display:none !important; }
      html.${CFG.htmlClass}.no-column-menu .kanban-column .kanban-column-header .menu, 
      html.${CFG.htmlClass}.no-column-menu .kanban-column .kanban-column-header .dropdown,
      html.${CFG.htmlClass}.no-column-menu .kanban-column .kanban-column-header .kanban-column-actions{
        display:none !important;
      }

      /* аккуратные отступы у колонок и стека карточек */
      html.${CFG.htmlClass} .kanban-column{ padding:8px; }
      html.${CFG.htmlClass} .kanban-cards{ display:grid; gap:8px; }
    `;
    document.head.appendChild(s);
  }

  /* ---------- Перестройка DOM карточки ---------- */
  function upgradeCard(wrapper){
    const card = wrapper?.querySelector?.(".kanban-card.content");
    if(!card || card.dataset.dntUpgraded==="1") return;

    const body  = card.querySelector(".kanban-card-body");
    const img   = card.querySelector(":scope > .kanban-image"); // обычно вне body
    const title = body?.querySelector(".kanban-title-area");
    const meta  = body?.querySelector(".kanban-card-meta");
    const doc   = body?.querySelector(".kanban-card-doc");

    if(!body) return;

    // шапка
    let head = body.querySelector(".dnt-head");
    if(!head){
      head = document.createElement("div");
      head.className = "dnt-head";
      body.prepend(head);
    }
    let left = head.querySelector(".dnt-head-left");
    if(!left){
      left = document.createElement("div");
      left.className = "dnt-head-left";
      head.prepend(left);
    }

    // переносим аватар и title
    if (img && !left.contains(img)) left.prepend(img);
    if (title) {
      title.querySelectorAll("br").forEach(br=>br.remove());
      if(!left.contains(title)) left.appendChild(title);
    }

    // мета — временно в шапке (потом вынесем оттуда assignment/like вниз)
    if (meta && meta.parentElement !== head) head.appendChild(meta);

    // гибкие поля — сразу под шапкой
    if (doc && doc.previousElementSibling !== head) body.insertBefore(doc, head.nextSibling);

    // нижний блок под гибкими полями
    let foot = body.querySelector(".dnt-foot");
    if(!foot){
      foot = document.createElement("div");
      foot.className = "dnt-foot";
      body.appendChild(foot);
    }

    // выносим assignment и like вниз
    const assign = (meta || body).querySelector(".kanban-assignments");
    const like   = (meta || body).querySelector(".like-action");
    if(assign && !foot.contains(assign)) foot.appendChild(assign);
    if(like   && !foot.contains(like))   foot.appendChild(like);

    // если в meta после этого пусто — убираем, иначе оставляем прочее в шапке
    if(meta && !meta.children.length) meta.remove();

    card.dataset.dntUpgraded = "1";
  }

  function upgradeAll(){
    document.querySelectorAll(".kanban-card-wrapper").forEach(upgradeCard);
  }

  /* ---------- действия на карточке ---------- */
  function addActions(wrapper){
    if(!wrapper || wrapper.querySelector(".dnt-card-actions")) return;
    const name = wrapper.getAttribute("data-name");
    const doctype = window.cur_list?.doctype || window.cur_list?.board?.reference_doctype;
    if(!name || !doctype) return;

    const row = document.createElement("div");
    row.className="dnt-card-actions";

    const mkBtn = (iconName, title, onClick) => {
      const b=document.createElement("div");
      b.className="dnt-icon-btn";
      b.setAttribute("data-toggle","tooltip");
      b.setAttribute("data-placement","bottom");
      b.title = __(title);
      b.appendChild(stdIcon(iconName,"sm"));
      b.addEventListener("click",(e)=>{ e.stopPropagation(); onClick&&onClick(); });
      try { window.jQuery && jQuery(b).tooltip({ boundary:"viewport", container:"body" }); } catch {}
      return b;
    };

    row.appendChild(mkBtn("external-link","Open",()=>frappe.set_route("Form", doctype, name)));
    row.appendChild(mkBtn("edit","Edit",()=>frappe.set_route("Form", doctype, name)));
    if (userHasAny(CFG.rolesDelete)) {
      row.appendChild(mkBtn("delete","Delete",()=>{
        frappe.confirm(__("Delete this document?"),()=>{
          frappe.call({
            method:"frappe.client.delete",
            args:{ doctype, name },
            callback:()=>{ frappe.show_alert(__("Deleted")); try{window.cur_list?.refresh();}catch{} }
          });
        });
      }));
    }

    wrapper.appendChild(row);
  }
  const enhanceCards = () => document.querySelectorAll(".kanban-card-wrapper").forEach(w=>{ addActions(w); upgradeCard(w); });

  /* ---------- кнопка настроек ---------- */
  function injectSettingsBtn(){
    const id="dnt-kanban-settings"; document.getElementById(id)?.remove();
    if(!isKanbanRoute() || !userHasAny(CFG.rolesSettings)) return;
    const anchor=document.querySelector(".standard-actions .page-icon-group"); const bname=getBoardName();
    if(!anchor || !bname) return;
    const btn=document.createElement("button");
    btn.id=id; btn.className="btn btn-default icon-btn";
    btn.setAttribute("data-toggle","tooltip"); btn.setAttribute("data-placement","bottom");
    btn.title=__("Kanban settings");
    btn.appendChild(stdIcon("edit","sm"));
    btn.addEventListener("click",()=>frappe.set_route(`/app/kanban-board/${encodeURIComponent(bname)}`));
    try { window.jQuery && jQuery(btn).tooltip({ boundary:"viewport", container:"body" }); } catch {}
    anchor.insertAdjacentElement("afterend", btn);
  }

  /* ---------- фикc «Unknown Column: [» ---------- */
  function coerceFieldsList(dt, any){
    let arr=[]; if(Array.isArray(any)) arr=any;
    else if(typeof any==="string" && any.trim()){ try{ const j=JSON.parse(any); if(Array.isArray(j)) arr=j; } catch{ arr=any.split(/[,\s]+/).filter(Boolean); } }
    const meta=frappe.get_meta(dt);
    const valid=new Set((meta?.fields||[]).map(f=>f.fieldname).concat((frappe.model.std_fields||[]).map(f=>f.fieldname)).concat(["name"]));
    return arr.filter(f=>typeof f==="string" && valid.has(f.trim())).map(f=>f.trim());
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

  /* ---------- права ---------- */
  function applyPermClasses(){
    const allowColor = userHasAny(CFG.rolesCanColor);
    const allowMenu  = userHasAny(CFG.rolesColumnMenu);
    document.documentElement.classList.toggle("no-color", !allowColor);
    document.documentElement.classList.toggle("no-column-menu", !allowMenu);
  }

  /* ---------- boot ---------- */
  const mo = new MutationObserver(()=>{ if(isKanbanRoute()) enhanceCards(); });

  function run(){
    if(!isKanbanRoute()){
      document.documentElement.classList.remove(CFG.htmlClass,"no-color","no-column-menu");
      return;
    }
    injectCSS();
    document.documentElement.classList.add(CFG.htmlClass);
    applyPermClasses();
    enhanceCards();
    injectSettingsBtn();
    patchSettingsDialog();

    mo.disconnect();
    mo.observe(document.body||document.documentElement,{ childList:true, subtree:true });
  }

  if (frappe?.after_ajax) frappe.after_ajax(run); else document.addEventListener("DOMContentLoaded", run);
  frappe?.router?.on && frappe.router.on("change", run);
})();