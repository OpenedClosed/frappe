// === DNT Kanban Plus (Frappe v15) — vT18 ===
// • Board switcher: СРАЗУ ПОД .page-head-content (не внутри). Кнопки — в один ряд; active: темнее (light) / светлее (dark).
// • Left/Right fly: списки строго в ОДИН столбец.
// • Assignees: расширенная диагностика — подробные логи по каждой карточке (attrs, dataset, classList, rect, text len, HTML сниппет, tokens/sources).
// • Анти-дребезг свитчера: перерисовка только при изменении.

(() => {
  if (window.__DNT_KANBAN_PLUS_T18) return;
  window.__DNT_KANBAN_PLUS_T18 = true;

  const CFG = {
    ids: {
      css: "dnt-kanban-plus-t18-css",
      rightEdge: "dnt-fly-edge-right",
      leftEdge: "dnt-fly-edge-left",
      rightFly: "dnt-fly-right",
      leftFly: "dnt-fly-left",
      boardsWrap: "dnt-board-switcher-wrap"
    },
    edgeW: 14,
    flyW: 336,
    z: 2147483000,
    fadeMs: 140,
    debug: (localStorage.getItem("dnt.kanban.debug") ?? "1") === "1",
    log_prefix: "[DNT+T18]",
    STATIC_BOARDS: [
      "Leads – Contact Center",
      "Deals – Contact Center",
      "Patients – Care Department"
    ],
    html_snippet_limit: 1600
  };

  // ===== Utils =====
  const dbg = (...a)=>{ try{ if(CFG.debug) console.log(CFG.log_prefix, ...a);}catch{} };
  const group = (title, payload)=>{ try{
    if(!CFG.debug) return;
    console.groupCollapsed(CFG.log_prefix+" "+title);
    if (payload!==undefined) console.log(payload);
    console.groupEnd();
  }catch{} };
  const CLEAN = s => (s||"").replace(/\u00A0/g," ").replace(/\s+/g," ").trim();
  const esc = (s)=> (frappe?.utils?.escape_html ? frappe.utils.escape_html(String(s)) : String(s||"").replace(/[&<>"']/g, m=>({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[m])));
  const t = (s)=>{ try{ if (typeof __ === "function") return __(s); const d = frappe?._messages; return (d && d[s]) || s; }catch{ return s; } };

  const getRoute = ()=> (frappe?.get_route?.() || []);
  const isKanbanRoute = () => {
    try {
      const r = getRoute();
      if (r[0] === "List" && (r[2] === "Kanban" || r[2] === "Kanban Board")) return true;
      return (location.pathname||"").includes("/view/kanban/");
    } catch { return false; }
  };
  const getDoctype = () =>
    window.cur_list?.doctype
    || window.cur_list?.board?.reference_doctype
    || window.cur_list?.kanban_board?.reference_doctype
    || getRoute()?.[1]
    || "";

  const getBoardName = () => {
    try {
      const r = getRoute();
      return r?.[3] ? decodeURIComponent(r[3]) :
             (window.cur_list?.board?.name || window.cur_list?.kanban_board?.name || "");
    } catch { return ""; }
  };

  // жёсткий переход (без SPA-хуков)
  const routeToBoard = (dt, boardTitle)=>{
    if (!dt || !boardTitle) return;
    const slug = (frappe?.router?.slug?.(dt)) || (dt||"").toLowerCase().replace(/\s+/g,"-");
    window.location.assign(`/app/${encodeURIComponent(slug)}/view/kanban/${encodeURIComponent(boardTitle)}`);
  };

  // ===== Theme flag (для плоского активного состояния)
  function hex_to_rgb(h){
    const m = (h||"").trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
    if (!m) return null;
    let s = m[1]; if (s.length===3) s = s.split("").map(x=>x+x).join("");
    const r = parseInt(s.slice(0,2),16), g = parseInt(s.slice(2,4),16), b = parseInt(s.slice(4,6),16);
    return [r,g,b];
  }
  function css_to_rgb(s){
    if (!s) return null;
    const m = s.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
    if (m) return [+m[1],+m[2],+m[3]];
    const h = s.trim();
    if (h.startsWith("#")) return hex_to_rgb(h);
    return null;
  }
  function rel_lum([r,g,b]){ // WCAG
    const sr = r/255, sg=g/255, sb=b/255;
    const l = [sr,sg,sb].map(v=> v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4));
    return 0.2126*l[0]+0.7152*l[1]+0.0722*l[2];
  }
  function update_theme_flag(){
    try{
      const cs = getComputedStyle(document.documentElement);
      const bgVar = cs.getPropertyValue("--bg-color").trim() || cs.getPropertyValue("--card-bg").trim() || getComputedStyle(document.body).backgroundColor;
      const rgb = css_to_rgb(bgVar) || css_to_rgb(getComputedStyle(document.body).backgroundColor) || [255,255,255];
      const dark = rel_lum(rgb) < 0.5;
      document.documentElement.classList.toggle("dnt-theme-dark", dark);
      document.documentElement.classList.toggle("dnt-theme-light", !dark);
      dbg("theme", dark ? "dark" : "light", bgVar);
    }catch{}
  }

  // ===== CSS =====
  (function inject_css(){
    if (document.getElementById(CFG.ids.css)) return;
    const s=document.createElement("style");
    s.id = CFG.ids.css;
    s.textContent = `
      #${CFG.ids.leftEdge}, #${CFG.ids.rightEdge}{
        position: fixed; top: 0; bottom: 0; z-index:${CFG.z};
        width:${CFG.edgeW}px; opacity:0; pointer-events:auto;
      }
      #${CFG.ids.leftEdge}{ left:0; }
      #${CFG.ids.rightEdge}{ right:0; }

      .dnt-fly{
        position: fixed; top:0; width:${CFG.flyW}px; height:calc(100vh - 20px); margin:10px;
        background: color-mix(in oklab, var(--card-bg) 8%, transparent);
        backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(2px);
        z-index:${CFG.z};
        transition: transform ${CFG.fadeMs}ms ease, opacity ${CFG.fadeMs}ms ease;
        opacity:0; pointer-events:none; display:flex; flex-direction:column;
        border: 1px solid color-mix(in oklab, var(--border-color) 40%, transparent);
        border-radius: 14px;
      }
      .dnt-fly.show{ opacity:1; pointer-events:auto; }
      #${CFG.ids.rightFly}{ right:0; transform: translateX(16px); }
      #${CFG.ids.leftFly}{ left:0; transform: translateX(-16px); }
      .dnt-fly.show#${CFG.ids.rightFly}{ transform: translateX(0); }
      .dnt-fly.show#${CFG.ids.leftFly}{ transform: translateX(0); }

      .dnt-fly-head{
        display:flex; align-items:center; justify-content:space-between;
        padding:10px 12px;
        border-bottom:1px dashed color-mix(in oklab, var(--border-color) 45%, transparent);
        background: color-mix(in oklab, var(--card-bg) 10%, transparent);
        border-top-left-radius: 14px; border-top-right-radius: 14px;
      }
      .dnt-fly-body{ padding:12px; overflow:auto; gap:10px; display:flex; flex-direction:column; }
      .dnt-fly-title{ font-weight:700; letter-spacing:.2px; }

      /* Board switcher: СРАЗУ ПОД .page-head-content (полная ширина контейнера) */
      #${CFG.ids.boardsWrap}{
        margin:8px 0 0;
        width:100%;
      }
      #${CFG.ids.boardsWrap} .dnt-boards-grid{
        display:flex; flex-direction:row; flex-wrap:nowrap; gap:8px; align-items:center; justify-content:flex-start;
        overflow:auto;
      }
      #${CFG.ids.boardsWrap} .dnt-board-btn{
        display:flex; align-items:center;
        padding:8px 14px; border-radius:12px; font-weight:600; line-height:1;
        border:1px solid color-mix(in oklab, var(--border-color) 60%, transparent);
        background: color-mix(in oklab, var(--card-bg) 6%, transparent);
        color: var(--text-color); text-decoration:none; cursor:pointer;
        transition: background .12s ease, border-color .12s ease;
        white-space:nowrap;
      }
      #${CFG.ids.boardsWrap} .dnt-board-btn:hover{
        background: color-mix(in oklab, var(--fg-hover-color) 18%, transparent);
        border-color: color-mix(in oklab, var(--border-color) 80%, transparent);
      }
      /* активная — плоское выделение: светлее на тёмной, темнее на светлой */
      html.dnt-theme-light #${CFG.ids.boardsWrap} .dnt-board-btn.active{
        background: color-mix(in oklab, var(--card-bg) 78%, black 22%);
        border-color: color-mix(in oklab, var(--border-color) 70%, black 30%);
      }
      html.dnt-theme-dark #${CFG.ids.boardsWrap} .dnt-board-btn.active{
        background: color-mix(in oklab, var(--card-bg) 72%, white 28%);
        border-color: color-mix(in oklab, var(--border-color) 60%, white 40%);
      }

      /* Workspace — ОДИН столбец */
      .dnt-left-block{ display:flex; flex-direction:column; gap:8px; }
      .dnt-left-h{ font-size:11px; text-transform:uppercase; letter-spacing:.6px; color:var(--text-muted); margin:6px 0 2px; }
      .dnt-left-links{ display:flex; flex-direction:column; gap:8px; }
      .dnt-left-links a{
        display:flex; align-items:center; gap:8px; padding:6px 10px; border-radius:10px; text-decoration:none;
        color: var(--text-color);
        border:1px solid color-mix(in oklab, var(--border-color) 55%, transparent);
        background: color-mix(in oklab, var(--card-bg) 4%, transparent);
        transition: background .12s ease, border-color .12s ease;
      }
      .dnt-ws-ico, .sidebar-item-icon{ width:20px; height:20px; border-radius:6px; display:inline-flex; align-items:center; justify-content:center; }

      /* Right fly — пользователи ОДИН столбец + diagnostics */
      .dnt-user-grid{ display:flex; flex-direction:column; gap:6px; }
      .dnt-user{ display:flex; align-items:center; gap:8px; padding:6px 8px; border-radius:10px; border:1px solid color-mix(in oklab, var(--border-color) 55%, transparent); background: color-mix(in oklab, var(--card-bg) 4%, transparent); cursor:pointer; }
      .dnt-ava{ width:24px; height:24px; border-radius:50%; background: var(--control-bg); display:flex; align-items:center; justify-content:center; font-weight:700; overflow:hidden; }
      .dnt-ava img{ width:24px; height:24px; border-radius:50%; object-fit:cover; display:block; }
      .dnt-name{ font-size:12px; }

      .dnt-diag-head{ margin-top:8px; font-size:11px; text-transform:uppercase; letter-spacing:.6px; color:var(--text-muted); }
      .dnt-diag-card{ border:1px dashed color-mix(in oklab, var(--border-color) 55%, transparent); border-radius:10px; padding:8px; margin-top:6px; }
      .dnt-diag-card .doc{ font-weight:600; }
      .dnt-tag{ display:inline-block; padding:2px 6px; border-radius:999px; border:1px solid color-mix(in oklab, var(--border-color) 55%, transparent); margin:2px 4px 0 0; font-size:11px; background: color-mix(in oklab, var(--control-bg) 25%, transparent); }
    `;
    document.head.appendChild(s);
    dbg("CSS injected");
  })();

  // ===== helpers: текущая живая доска =====
  const getKanbanRoot = () => {
    const roots = Array.from(document.querySelectorAll(".kanban"));
    return roots.find(r => r && r.getClientRects().length) || roots[0] || null;
  };

  // ===== Right flyout (Assignees + Diagnostics) =====
  const EMAIL_RE = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;

  function parse_card_ts(el){
    const ds = (el?.dataset)||{};
    const candidates = [ds.modified, ds.modifiedOn, ds.updated, ds.creation, ds.timestamp];
    for (const v of candidates){
      const d = v && new Date(v);
      if (d && !isNaN(+d)) return +d;
    }
    return 0;
  }
  function get_docname(wrap){
    if (!wrap) return "";
    const direct = wrap.getAttribute?.("data-name");
    if (direct) return direct;
    const inner = wrap.querySelector?.(".kanban-card[data-name]");
    if (inner) return inner.getAttribute("data-name") || "";
    const hidden = wrap.querySelector?.('input[name="name"], [data-document-name]');
    return hidden?.value || hidden?.getAttribute?.("data-document-name") || "";
  }
  function is_placeholder_card(wrap){
    if (!wrap) return true;
    if (wrap.querySelector('textarea[name="title"]')) return true;
    const name = get_docname(wrap);
    if (!name) return true;
    return false;
  }

  // полный лог по карточке
  function log_card_full(wrap, idx, tokens, sources){
    if (!CFG.debug) return;
    try{
      const rect = wrap.getBoundingClientRect?.() || {};
      const attrs = Array.from(wrap.attributes||[]).map(a=>[a.name, a.value]);
      const dataset = {...(wrap.dataset||{})};
      const classes = Array.from(wrap.classList||[]);
      const text = (wrap.textContent||"").replace(/\s+/g," ").trim();
      const html = (wrap.outerHTML||"");
      const snippet = html.length>CFG.html_snippet_limit ? html.slice(0, CFG.html_snippet_limit) + "…(trimmed)" : html;

      group(`CARD#${idx} FULL`, {
        docname: get_docname(wrap) || "—",
        rect: {x: Math.round(rect.x||0), y: Math.round(rect.y||0), w: Math.round(rect.width||0), h: Math.round(rect.height||0)},
        attrs_count: attrs.length, attrs,
        dataset,
        classList: classes,
        text_len: text.length,
        html_len: html.length,
        html_snippet: snippet,
        tokens, sources
      });
    }catch(e){ dbg("log_card_full error", e); }
  }

  // сбор токенов исполнителей
  function collect_user_tokens(wrap){
    const tokens = new Set();

    // data-* атрибуты
    wrap.querySelectorAll('[data-user],[data-username],[data-owner],[data-user-id],[data-assignee],[data-assignees],.avatar-inner[data-user]').forEach(n=>{
      const v = n.getAttribute('data-user') || n.getAttribute('data-username') || n.getAttribute('data-owner') || n.getAttribute('data-user-id') || n.getAttribute('data-assignee') || n.getAttribute('data-assignees');
      if (v) (v.split(/[,\s;]+/).filter(Boolean)).forEach(x=>tokens.add(x));
    });

    // по классам, содержащим "assign"
    wrap.querySelectorAll('[class*="assign"]').forEach(n=>{
      const tit = n.getAttribute('title') || n.getAttribute('data-original-title') || "";
      if (tit) {
        const m = tit.match(EMAIL_RE); if (m) tokens.add(m[0]);
        const m2 = /\(([^)@]+@[^)]+)\)/.exec(tit); if (m2) tokens.add(m2[1]);
      }
      const txt = (n.textContent||"").trim();
      const m3 = txt && txt.match(EMAIL_RE); if (m3) m3.forEach(e=>tokens.add(e));
    });

    // аватарки/группы
    wrap.querySelectorAll('.avatar, .avatar-small, .avatar-medium, .avatar-group, .avatar-group *').forEach(n=>{
      const tit = n.getAttribute?.('title') || n.getAttribute?.('data-original-title') || "";
      const m = tit && tit.match(EMAIL_RE); if (m) tokens.add(m[0]);
      const e = n.getAttribute?.('data-user') || n.getAttribute?.('data-username') || "";
      if (e) tokens.add(e);
      const m2 = tit && /\(([^)@]+@[^)]+)\)/.exec(tit); if (m2) tokens.add(m2[1]);
    });

    // любые title/data-original-title
    wrap.querySelectorAll('[title],[data-original-title]').forEach(n=>{
      const tit = n.getAttribute('title') || n.getAttribute('data-original-title') || "";
      const m = tit && tit.match(EMAIL_RE); if (m) m.forEach(e=>tokens.add(e));
    });

    // ссылки на пользователя
    wrap.querySelectorAll('a[href*="/app/user/"]').forEach(a=>{
      const u = decodeURIComponent((a.getAttribute('href')||"").split("/app/user/")[1]||"").trim();
      if (u) tokens.add(u);
    });

    return Array.from(tokens).filter(Boolean);
  }

  function resolve_user_info(token){
    const info = (typeof frappe?.user_info === "function") ? frappe.user_info(token) : null;
    if (info && (info.fullname || info.name || info.email)) return info;
    if (EMAIL_RE.test(token)) return { name: token, fullname: token, email: token, image: "" };
    return { name: token, fullname: token, email: "", image: "" };
  }

  function gather_assignees_from_wrap(wrap, idx){
    const tokens = collect_user_tokens(wrap);
    const docname = get_docname(wrap) || "—";

    const sources = [];
    wrap.querySelectorAll('[data-user],[data-username],[data-owner],[data-user-id],[data-assignee],[data-assignees]').forEach(n=>{
      const attr = ['data-user','data-username','data-owner','data-user-id','data-assignee','data-assignees'].find(k=>n.hasAttribute(k));
      const v = attr ? n.getAttribute(attr) : "";
      if (v) sources.push([attr, v]);
    });
    wrap.querySelectorAll('[title],[data-original-title]').forEach(n=>{
      const tit = n.getAttribute('title') || n.getAttribute('data-original-title') || "";
      if (tit) sources.push(['title', tit]);
    });
    wrap.querySelectorAll('a[href*="/app/user/"]').forEach(a=>{
      sources.push(['link', a.getAttribute('href')||""]);
    });

    log_card_full(wrap, idx, tokens, sources);
    return { docname, tokens, sources };
  }

  function scan_assignees(){
    const root = getKanbanRoot();
    const cards = root
      ? Array.from(root.querySelectorAll(".kanban-column .kanban-card, .kanban-card-wrapper .kanban-card, .kanban .kanban-card"))
      : [];
    const live = cards.filter(c=> !is_placeholder_card(c));

    console.groupCollapsed?.(`${CFG.log_prefix} scan_assignees: cards_total=${cards.length} cards_live=${live.length}`);

    let found = 0;
    const seen = new Map(); // token -> best ts
    const diag = [];
    live.forEach((wrap, idx)=>{
      const ts = parse_card_ts(wrap) || (Date.now() - idx);
      const { docname, tokens, sources } = gather_assignees_from_wrap(wrap, idx);
      diag.push({ docname, tokens, sources });
      tokens.forEach(tok=>{
        found += 1;
        const prev = seen.get(tok) || 0;
        if (ts > prev) seen.set(tok, ts);
      });
    });
    console.groupEnd?.();

    const ordered = Array.from(seen.entries()).sort((a,b)=> b[1]-a[1]).map(([tok])=> tok);
    const list = ordered.map(tok => resolve_user_info(tok));
    group("assignees result", { unique: list.length, total_hits: found, diag_count: diag.length });
    return { list, diag, total: cards.length, live: live.length };
  }

  function render_right_fly(force_scan=false){
    if (!isKanbanRoute()) return;
    const root = document.getElementById(CFG.ids.rightFly);
    if (!root) return;
    const body = root.querySelector(".dnt-fly-body");
    const head = root.querySelector(".dnt-fly-title");
    head.textContent = t("Assignees");

    const res = force_scan ? scan_assignees() : { list:[], diag:[], total:0, live:0 };
    body.innerHTML = `<div class="dnt-user-grid"></div>`;
    const grid = body.querySelector(".dnt-user-grid");

    if (!res.list.length){
      grid.innerHTML = `<div class="text-muted">${t("No assignees")}</div>`;
    } else {
      grid.innerHTML = res.list.map(info=>{
        const img = info?.image ? `<img src="${esc(info.image)}" loading="lazy">` : "";
        const nm  = esc(info?.fullname || info?.name || "");
        const inits = (nm?.[0]||"A").toUpperCase();
        const uname = esc(info?.name || info?.email || "");
        return `
          <div class="dnt-user" data-open-user="${uname}">
            <div class="dnt-ava">${img || inits}</div>
            <div class="dnt-name" title="${nm}">${nm}</div>
          </div>`;
      }).join("");
      grid.querySelectorAll("[data-open-user]").forEach(el=>{
        el.addEventListener("click",(e)=>{
          e.preventDefault(); e.stopPropagation();
          const u = el.getAttribute("data-open-user");
          dbg("open user:", u);
          if (u) frappe.set_route("Form","User", u);
        });
      });
    }

    // diagnostics (всегда)
    const diagHead = document.createElement("div");
    diagHead.className = "dnt-diag-head";
    diagHead.textContent = `Diagnostics · scanned: ${res.live}/${res.total}`;
    body.appendChild(diagHead);

    const diagBox = document.createElement("div");
    res.diag.forEach(row=>{
      const srcTags = row.sources.slice(0, 12).map(([k,v])=>{
        const vv = (v||"").toString();
        const short = vv.length > 80 ? vv.slice(0,80) + "…" : vv;
        return `<span class="dnt-tag">${esc(k)}: ${esc(short)}</span>`;
      }).join("");
      const tokTags = row.tokens.slice(0, 10).map(tok=> `<span class="dnt-tag">${esc(tok)}</span>`).join("");
      diagBox.insertAdjacentHTML("beforeend",
        `<div class="dnt-diag-card">
          <div class="doc">${esc(row.docname)}</div>
          <div>${tokTags || `<span class="text-muted">${t("no tokens")}</span>`}</div>
          <div style="margin-top:4px">${srcTags}</div>
        </div>`
      );
    });
    body.appendChild(diagBox);

    dbg("render_right_fly: rendered", res.list.length, "assignees; diag cards:", res.diag.length);
  }

  // ===== Left flyout (Workspaces) — только Public, My скрыт =====
  function CLEAN_TEXT(n){ return CLEAN(n.textContent||"") || n.getAttribute?.("title") || ""; }

  function collect_sidebar_items_from_dom(){
    const containers = Array.from(document.querySelectorAll(".sidebar-item-container[item-name]"));
    const items = containers.map(cnt => {
      const hidden = cnt.getAttribute("item-is-hidden");
      if (hidden === "1") return null;
      const is_public = (cnt.getAttribute("item-public") === "1");
      const a = cnt.querySelector("a.item-anchor[href]");
      if (!a) return null;
      const label = CLEAN_TEXT(a);
      if (!label) return null;
      const href = a.getAttribute("href") || "#";
      let iconHTML = "";
      const iconSpan = cnt.querySelector(".sidebar-item-icon");
      if (iconSpan) iconHTML = iconSpan.outerHTML;
      else {
        const itemIcon = cnt.getAttribute("item-icon") || a.querySelector(".sidebar-item-icon")?.getAttribute("item-icon");
        if (itemIcon) {
          iconHTML = `<span class="sidebar-item-icon" item-icon="${esc(itemIcon)}"><svg class="icon icon-md" aria-hidden="true"><use href="#icon-${esc(itemIcon)}"></use></svg></span>`;
        }
      }
      return { href, label, iconHTML, is_public, src: "dom" };
    }).filter(Boolean);
    return items;
  }

  function collect_workspaces_from_boot(){
    const srcs = [
      ...(frappe?.boot?.allowed_workspaces || []),
      ...(frappe?.boot?.workspaces || []),
      ...(frappe?.boot?.all_workspaces || []),
      ...(frappe?.boot?.public_workspaces || []),
    ].filter(Boolean);
    const out = [];
    for (const it of srcs){
      const label = CLEAN(it.title || it.label || it.name || "");
      if (!label) continue;
      const is_hidden = !!(it.hidden || it.is_hidden || it.hide_in_sidebar || it.is_hidden_in_sidebar);
      if (is_hidden) continue;
      const route = (it.route && String(it.route)) || ("/app/" + encodeURIComponent(label.toLowerCase().replace(/\s+/g,"-")));
      const icon = it.icon_html || it.icon || it.icon_class || it.icon_name || it.icon_label || "";
      let iconHTML = "";
      if (icon && /</.test(icon)) {
        const tmp = document.createElement("div"); tmp.innerHTML = icon;
        const first = tmp.querySelector("svg, i, span");
        iconHTML = first ? `<span class="sidebar-item-icon">${first.outerHTML}</span>` : "";
      } else if (icon && /[a-z-]{2,}/i.test(icon)) {
        iconHTML = `<span class="sidebar-item-icon"><svg class="icon icon-md" aria-hidden="true"><use href="#icon-${esc(icon)}"></use></svg></span>`;
      }
      const is_public = !!(it.public || it.is_public);
      out.push({ href: route, label, iconHTML, is_public, src: "boot" });
    }
    const seen = new Set();
    return out.filter(x=>{
      const key = (x.href||"") + "||" + (x.label||"");
      if (seen.has(key)) return false; seen.add(key); return true;
    });
  }

  function render_left_fly(){
    if (!isKanbanRoute()) return;
    const root = document.getElementById(CFG.ids.leftFly);
    if (!root) return;
    const pubBox = root.querySelector('.dnt-left-links[data-ws="public"]');
    if (!pubBox) return;

    let all = collect_sidebar_items_from_dom();
    if (!all.length) all = collect_workspaces_from_boot();

    const pub = all.filter(x=> x.is_public);
    pubBox.innerHTML = "";
    if (!pub.length) return;

    const frag = document.createDocumentFragment();
    pub.slice(0, 200).forEach(it=>{
      const a = document.createElement("a");
      a.href = it.href || "#";
      a.innerHTML = `${it.iconHTML || `<span class="dnt-ws-ico">${esc((it.label||" ")[0].toUpperCase())}</span>`} <span>${esc(it.label)}</span>`;
      a.addEventListener("click",(e)=>{
        e.preventDefault(); e.stopPropagation();
        const href = it.href || "";
        dbg("open workspace:", { href, label: it.label });
        if (href.startsWith("#")) frappe.set_route(href.substring(1));
        else window.location.assign(href);
      });
      frag.appendChild(a);
    });
    pubBox.replaceChildren(frag);

    // секцию My Workspaces не рендерим (оставлено в DOM скрытым)
    const prvBlock = Array.from(root.querySelectorAll('.dnt-left-block'))[1];
    if (prvBlock) prvBlock.style.display = "none";
  }

  // ===== Board switcher — СРАЗУ ПОД .page-head-content =====
  let last_switcher_hash = "";

  function ensure_board_switcher(){
    if (!isKanbanRoute()) {
      const prev = document.getElementById(CFG.ids.boardsWrap);
      if (prev) prev.remove();
      last_switcher_hash = "";
      return;
    }
    const head = document.querySelector(".page-head-content") || document.querySelector(".page-head");
    if (!head) return;
    if (document.getElementById(CFG.ids.boardsWrap)) return;

    const wrap = document.createElement("div");
    wrap.id = CFG.ids.boardsWrap;
    wrap.innerHTML = `<div class="dnt-boards-grid"></div>`;

    // ВСТАВИТЬ ПОСЛЕ БЛОКА ШАПКИ
    head.insertAdjacentElement("afterend", wrap);

    render_board_switcher();
  }

  function render_board_switcher(){
    const wrap = document.getElementById(CFG.ids.boardsWrap);
    if (!wrap || !isKanbanRoute()) return;
    const grid = wrap.querySelector(".dnt-boards-grid");
    const dt = getDoctype();
    const active = CLEAN(getBoardName());
    const boards = CFG.STATIC_BOARDS;

    if (!dt) { grid.innerHTML = ""; return; }

    const html = boards.map(title=>{
      const isActive = CLEAN(title) === active;
      return `<a href="#" class="dnt-board-btn${isActive?" active":""}" data-board="${esc(title)}">${esc(title)}</a>`;
    }).join("");

    const new_hash = `${dt}|${active}|${html}`;
    if (new_hash === last_switcher_hash) return;
    last_switcher_hash = new_hash;

    grid.innerHTML = html;
    grid.querySelectorAll(".dnt-board-btn").forEach(btn=>{
      btn.addEventListener("click",(e)=>{
        e.preventDefault(); e.stopPropagation();
        const title = btn.getAttribute("data-board");
        dbg("switch board (hard):", { dt, title });
        routeToBoard(dt, title);
      });
    });

    group("board switcher rendered", { dt, active, boards });
  }

  // ===== Flyouts & edges (Kanban-only) =====
  function remove_edges_and_flyouts(){
    [CFG.ids.rightEdge, CFG.ids.leftEdge, CFG.ids.rightFly, CFG.ids.leftFly].forEach(id=>{
      const el = document.getElementById(id);
      if (el) el.remove();
    });
  }

  function ensure_edges_and_flyouts(){
    if (!isKanbanRoute()) { remove_edges_and_flyouts(); return; }
    if (document.getElementById(CFG.ids.rightEdge)) return;

    const rightEdge = document.createElement("div");
    rightEdge.id = CFG.ids.rightEdge;
    const leftEdge  = document.createElement("div");
    leftEdge.id = CFG.ids.leftEdge;
    document.body.appendChild(rightEdge);
    document.body.appendChild(leftEdge);

    const rightFly = document.createElement("div");
    rightFly.id = CFG.ids.rightFly;
    rightFly.className = "dnt-fly";
    rightFly.innerHTML = `
      <div class="dnt-fly-head">
        <div class="dnt-fly-title">${t("Assignees")}</div>
        <div class="text-muted" style="font-size:12px">${t("hover out to close")}</div>
      </div>
      <div class="dnt-fly-body"><div class="dnt-user-grid"></div></div>
    `;
    const leftFly = document.createElement("div");
    leftFly.id = CFG.ids.leftFly;
    leftFly.className = "dnt-fly";
    leftFly.innerHTML = `
      <div class="dnt-fly-head">
        <div class="dnt-fly-title">${t("Workspace")}</div>
        <div class="text-muted" style="font-size:12px">${t("hover out to close")}</div>
      </div>
      <div class="dnt-fly-body">
        <div class="dnt-left-block">
          <div class="dnt-left-h">${t("Public")}</div>
          <div class="dnt-left-links" data-ws="public"></div>
        </div>
        <div class="dnt-left-block" style="display:none">
          <div class="dnt-left-h">${t("My Workspaces")}</div>
          <div class="dnt-left-links" data-ws="private"></div>
        </div>
      </div>
    `;
    document.body.appendChild(rightFly);
    document.body.appendChild(leftFly);
    dbg("flyouts created");

    const hover = { rightEdge:false, rightFly:false, leftEdge:false, leftFly:false };
    const updateFly = (side)=>{
      const fly = document.getElementById(side==="right"?CFG.ids.rightFly:CFG.ids.leftFly);
      const on = hover[side+"Edge"] || hover[side+"Fly"];
      if (on) fly.classList.add("show"); else fly.classList.remove("show");
    };

    document.addEventListener("mousemove", (e)=>{
      if (!isKanbanRoute()) return;
      const w = window.innerWidth;
      const nearLeft = e.clientX <= CFG.edgeW;
      const nearRight = (w - e.clientX) <= CFG.edgeW;
      if (nearLeft !== hover.leftEdge){ hover.leftEdge = nearLeft; if (nearLeft) { render_left_fly(); } updateFly("left"); }
      if (nearRight !== hover.rightEdge){ hover.rightEdge = nearRight; if (nearRight) { render_right_fly(true); } updateFly("right"); }
    }, {passive:true});

    rightEdge.addEventListener("mouseenter", ()=>{ if (!isKanbanRoute()) return; hover.rightEdge = true; render_right_fly(true); updateFly("right"); });
    rightEdge.addEventListener("mouseleave", ()=>{ hover.rightEdge = false; updateFly("right"); });
    leftEdge.addEventListener("mouseenter", ()=>{ if (!isKanbanRoute()) return; hover.leftEdge = true; render_left_fly(); updateFly("left"); });
    leftEdge.addEventListener("mouseleave", ()=>{ hover.leftEdge = false; updateFly("left"); });

    rightFly.addEventListener("mouseenter", ()=>{ hover.rightFly = true; updateFly("right"); });
    rightFly.addEventListener("mouseleave", ()=>{ hover.rightFly = false; updateFly("right"); });
    leftFly.addEventListener("mouseenter", ()=>{ hover.leftFly = true; updateFly("left"); });
    leftFly.addEventListener("mouseleave", ()=>{ hover.leftFly = false; updateFly("left"); });
  }

  // ===== Boot / Route handling =====
  function run(){
    update_theme_flag();
    if (!isKanbanRoute()){
      remove_edges_and_flyouts();
      const bs = document.getElementById(CFG.ids.boardsWrap); if (bs) bs.remove();
      last_switcher_hash = "";
      return;
    }
    ensure_edges_and_flyouts();
    ensure_board_switcher();
    setTimeout(()=>{ update_theme_flag(); render_board_switcher(); }, 120);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
  else run();

  frappe?.router?.on && frappe.router.on("change", run);

  // watchdog (редко)
  let wd_i = 0;
  setInterval(()=> {
    wd_i = (wd_i+1)%4;
    if (!wd_i) { dbg("watchdog route:", getRoute().join(" / ")); update_theme_flag(); }
  }, 3000);
})();