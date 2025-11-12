// === DNT Kanban Plus (Frappe v15) — vT19 (final) ===
// Right flyout (Assignees) — only on Kanban. Left flyout (Workspaces) — global except /app and /app/home.
// Fixes: clickable assignees → User profile, no "scanned" line, CSS fully scoped (no sidebar icon shrink), left flyout independent of base menu.

(() => {
  if (window.__DNT_KANBAN_PLUS_T19) return;
  window.__DNT_KANBAN_PLUS_T19 = true;

  const CFG = {
    ids: {
      css: "dnt-kanban-plus-t19-css",
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
    log_prefix: "[DNT+T19]",
    STATIC_BOARDS: [
      "Leads – Contact Center",
      "Deals – Contact Center",
      "Patients – Care Department"
    ],
    html_snippet_limit: 1600
  };

  // ===== Utils
  const dbg = (...a)=>{ try{ if(CFG.debug) console.log(CFG.log_prefix, ...a);}catch{} };
  const group = (title, payload)=>{ try{ if(!CFG.debug) return; console.groupCollapsed(CFG.log_prefix+" "+title); if (payload!==undefined) console.log(payload); console.groupEnd(); }catch{} };
  const CLEAN = s => (s||"").replace(/\u00A0/g," ").replace(/\s+/g," ").trim();
  const esc = (s)=> (frappe?.utils?.escape_html ? frappe.utils.escape_html(String(s)) : String(s||"").replace(/[&<>"']/g, m=>({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[m])));
  const t = (s)=>{ try{ if (typeof __ === "function") return __(s); const d = frappe?._messages; return (d && d[s]) || s; }catch{ return s; } };

  const getRoute = ()=> (frappe?.get_route?.() || []);
  const isKanbanRoute = () => {
    try { const r = getRoute(); if (r[0] === "List" && (r[2] === "Kanban" || r[2] === "Kanban Board")) return true; return (location.pathname||"").includes("/view/kanban/"); } catch { return false; }
  };
  const isWorkspaceHubRoute = () => {
    try { const p = location.pathname || ""; if (p === "/app" || p === "/app/home") return true; const r = getRoute(); return r[0] === "Workspaces"; } catch { return false; }
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
      return r?.[3] ? decodeURIComponent(r[3]) : (window.cur_list?.board?.name || window.cur_list?.kanban_board?.name || "");
    } catch { return ""; }
  };

  const routeToBoard = (dt, boardTitle)=>{
    if (!dt || !boardTitle) return;
    const slug = (frappe?.router?.slug?.(dt)) || (dt||"").toLowerCase().replace(/\s+/g,"-");
    window.location.assign(`/app/${encodeURIComponent(slug)}/view/kanban/${encodeURIComponent(boardTitle)}`);
  };

  // ===== Theme flag
  function hex_to_rgb(h){ const m = (h||"").trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i); if (!m) return null; let s = m[1]; if (s.length===3) s = s.split("").map(x=>x+x).join(""); return [parseInt(s.slice(0,2),16), parseInt(s.slice(2,4),16), parseInt(s.slice(4,6),16)]; }
  function css_to_rgb(s){ if (!s) return null; const m = s.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i); if (m) return [+m[1],+m[2],+m[3]]; const h = s.trim(); if (h.startsWith("#")) return hex_to_rgb(h); return null; }
  function rel_lum([r,g,b]){ const sr=r/255, sg=g/255, sb=b/255; const l=[sr,sg,sb].map(v=> v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4)); return 0.2126*l[0]+0.7152*l[1]+0.0722*l[2]; }
  function update_theme_flag(){ try{ const cs = getComputedStyle(document.documentElement); const bgVar = cs.getPropertyValue("--bg-color").trim() || cs.getPropertyValue("--card-bg").trim() || getComputedStyle(document.body).backgroundColor; const rgb = css_to_rgb(bgVar) || css_to_rgb(getComputedStyle(document.body).backgroundColor) || [255,255,255]; const dark = rel_lum(rgb) < 0.5; document.documentElement.classList.toggle("dnt-theme-dark", dark); document.documentElement.classList.toggle("dnt-theme-light", !dark); dbg("theme", dark ? "dark" : "light", bgVar); }catch{} }

  // ===== CSS (scoped)
  (function inject_css(){
    if (document.getElementById(CFG.ids.css)) return;
    const s=document.createElement("style");
    s.id = CFG.ids.css;
    s.textContent = `
      #${CFG.ids.leftEdge}, #${CFG.ids.rightEdge}{ position: fixed; top: 0; bottom: 0; z-index:${CFG.z}; width:${CFG.edgeW}px; opacity:0; pointer-events:auto; }
      #${CFG.ids.leftEdge}{ left:0; }
      #${CFG.ids.rightEdge}{ right:0; }

      .dnt-fly{ position: fixed; top:0; width:${CFG.flyW}px; height:calc(100vh - 20px); margin:10px; background: color-mix(in oklab, var(--card-bg) 8%, transparent); backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(2px); z-index:${CFG.z}; transition: transform ${CFG.fadeMs}ms ease, opacity ${CFG.fadeMs}ms ease; opacity:0; pointer-events:none; display:flex; flex-direction:column; border: 1px solid color-mix(in oklab, var(--border-color) 40%, transparent); border-radius: 14px; }
      .dnt-fly.show{ opacity:1; pointer-events:auto; }
      #${CFG.ids.rightFly}{ right:0; transform: translateX(16px); }
      #${CFG.ids.leftFly}{ left:0; transform: translateX(-16px); }
      .dnt-fly.show#${CFG.ids.rightFly}{ transform: translateX(0); }
      .dnt-fly.show#${CFG.ids.leftFly}{ transform: translateX(0); }

      .dnt-fly-head{ display:flex; align-items:center; justify-content:space-between; padding:10px 12px; border-bottom:1px dashed color-mix(in oklab, var(--border-color) 45%, transparent); background: color-mix(in oklab, var(--card-bg) 10%, transparent); border-top-left-radius: 14px; border-top-right-radius: 14px; }
      .dnt-fly-body{ padding:12px; overflow:auto; gap:10px; display:flex; flex-direction:column; }
      .dnt-fly-title{ font-weight:700; letter-spacing:.2px; }

      /* Board switcher */
      #${CFG.ids.boardsWrap}{ margin:8px 0 0; width:100%; }
      #${CFG.ids.boardsWrap} .dnt-boards-grid{ display:flex; flex-direction:row; flex-wrap:nowrap; gap:8px; align-items:center; justify-content:flex-start; overflow:auto; }
      #${CFG.ids.boardsWrap} .dnt-boards-grid.dnt-seg{ gap:0; padding:4px; border-radius:14px; border:1px solid color-mix(in oklab, var(--border-color) 60%, transparent); background: color-mix(in oklab, var(--card-bg) 8%, transparent); }
      #${CFG.ids.boardsWrap} .dnt-boards-grid.dnt-seg .dnt-board-btn{ border:none; background:transparent; border-radius:10px; margin:0 2px; }
      #${CFG.ids.boardsWrap} .dnt-board-btn{ display:flex; align-items:center; padding:8px 14px; border-radius:12px; font-weight:600; line-height:1; border:1px solid color-mix(in oklab, var(--border-color) 60%, transparent); background: color-mix(in oklab, var(--card-bg) 6%, transparent); color: var(--text-color); text-decoration:none; cursor:pointer; transition: background .12s ease, border-color .12s ease; white-space:nowrap; }
      #${CFG.ids.boardsWrap} .dnt-board-btn:hover{ background: color-mix(in oklab, var(--fg-hover-color) 18%, transparent); border-color: color-mix(in oklab, var(--border-color) 80%, transparent); }
      html.dnt-theme-light #${CFG.ids.boardsWrap} .dnt-board-btn.active{ background: color-mix(in oklab, var(--card-bg) 72%, black 28%); border-color: color-mix(in oklab, var(--border-color) 70%, black 30%); color: color-mix(in oklab, var(--text-color) 85%, white 15%); }
      html.dnt-theme-dark #${CFG.ids.boardsWrap} .dnt-board-btn.active{ background: color-mix(in oklab, var(--card-bg) 68%, white 32%); border-color: color-mix(in oklab, var(--border-color) 60%, white 40%); color: color-mix(in oklab, var(--text-color) 85%, black 15%); }

      /* Left */
      .dnt-left-block{ display:flex; flex-direction:column; gap:8px; }
      .dnt-left-h{ font-size:11px; text-transform:uppercase; letter-spacing:.6px; color:var(--text-muted); margin:6px 0 2px; }
      .dnt-left-links{ display:flex; flex-direction:column; gap:8px; }
      .dnt-left-links a{ display:flex; align-items:center; gap:8px; padding:6px 10px; border-radius:10px; text-decoration:none; color: var(--text-color); border:1px solid color-mix(in oklab, var(--border-color) 55%, transparent); background: color-mix(in oklab, var(--card-bg) 4%, transparent); transition: background .12s ease, border-color .12s ease; }
      .dnt-ws-ico, .dnt-fly .sidebar-item-icon{ width:20px; height:20px; border-radius:6px; display:inline-flex; align-items:center; justify-content:center; }

      /* Right */
      .dnt-user-grid{ display:flex; flex-direction:column; gap:6px; }
      .dnt-user{ display:flex; align-items:center; gap:8px; padding:6px 8px; border-radius:10px; border:1px solid color-mix(in oklab, var(--border-color) 55%, transparent); background: color-mix(in oklab, var(--card-bg) 4%, transparent); cursor:pointer; }
      .dnt-ava{ width:24px; height:24px; border-radius:50%; background: var(--control-bg); display:flex; align-items:center; justify-content:center; font-weight:700; overflow:hidden; }
      .dnt-ava img{ width:24px; height:24px; border-radius:50%; object-fit:cover; display:block; }
      .dnt-name{ font-size:12px; }
    `;
    document.head.appendChild(s);
    dbg("CSS injected");
  })();

  // ===== helpers
  const getKanbanRoot = () => { const roots = Array.from(document.querySelectorAll(".kanban")); return roots.find(r => r && r.getClientRects().length) || roots[0] || null; };

  // ===== Right flyout (Assignees)
  const EMAIL_RE = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;

  function parse_card_ts(el){ const ds = (el?.dataset)||{}; const candidates = [ds.modified, ds.modifiedOn, ds.updated, ds.creation, ds.timestamp]; for (const v of candidates){ const d = v && new Date(v); if (d && !isNaN(+d)) return +d; } return 0; }
  function get_card_container(node){ if (!node) return null; return node.closest?.(".kanban-card-wrapper") || node; }
  function get_docname(wrap){ if (!wrap) return ""; const self = wrap.getAttribute?.("data-name"); if (self) return self; const up = wrap.closest?.(".kanban-card-wrapper[data-name]"); if (up?.getAttribute) return up.getAttribute("data-name") || ""; const inner = wrap.querySelector?.(".kanban-card[data-name], .kanban-card-wrapper[data-name]"); if (inner?.getAttribute) return inner.getAttribute("data-name") || ""; const hidden = wrap.querySelector?.('input[name="name"], [data-document-name]'); if (hidden) return hidden.value || hidden.getAttribute?.("data-document-name") || ""; return ""; }
  function is_placeholder_card(wrap){ const box = get_card_container(wrap); if (!box) return true; if (box.querySelector('textarea[name="title"]')) return true; const name = get_docname(box); if (name) return false; const title = CLEAN(box.querySelector(".kanban-card-title, .kanban-title-area, .kanban-card .title")?.textContent || ""); if (title && title.length > 1) return false; const rect = box.getBoundingClientRect?.() || {}; return (rect.width||0) < 20 || (rect.height||0) < 20; }

  function log_card_full(wrap, idx, tokens, sources){ if (!CFG.debug) return; try{ const rect = wrap.getBoundingClientRect?.() || {}; const attrs = Array.from(wrap.attributes||[]).map(a=>[a.name, a.value]); const dataset = {...(wrap.dataset||{})}; const classes = Array.from(wrap.classList||[]); const text = (wrap.textContent||"").replace(/\s+/g," ").trim(); const html = (wrap.outerHTML||""); const snippet = html.length>CFG.html_snippet_limit ? html.slice(0, CFG.html_snippet_limit) + "…(trimmed)" : html; group(`CARD#${idx} FULL`, { docname: get_docname(wrap) || "—", rect: {x: Math.round(rect.x||0), y: Math.round(rect.y||0), w: Math.round(rect.width||0), h: Math.round(rect.height||0)}, attrs_count: attrs.length, attrs, dataset, classList: classes, text_len: text.length, html_len: html.length, html_snippet: snippet, tokens, sources }); }catch(e){ dbg("log_card_full error", e); } }

  function collect_user_tokens(wrap){
    const tokens = new Set();

    wrap.querySelectorAll('[data-user],[data-username],[data-owner],[data-user-id],[data-assignee],[data-assignees],[data-assignments],.avatar-inner[data-user]')
      .forEach(n=>{ const attrs = ['data-user','data-username','data-owner','data-user-id','data-assignee','data-assignees','data-assignments']; const v = attrs.map(a=>n.getAttribute(a)).filter(Boolean).join(','); if (v) v.split(/[\,\s;]+/).filter(Boolean).forEach(x=>tokens.add(x)); });

    wrap.querySelectorAll('.kanban-card-meta .avatar-group [title], .kanban-card-meta .avatar[title], .kanban-card-meta .frappe-avatar[title], .frappe-avatar[title]')
      .forEach(n=>{ const tt = n.getAttribute('title') || n.getAttribute('data-original-title') || ''; if (!tt) return; const m = tt.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/ig); if (m) m.forEach(e=>tokens.add(e)); });

    wrap.querySelectorAll('[title],[data-original-title]').forEach(n=>{ const tit = n.getAttribute('title') || n.getAttribute('data-original-title') || ''; const m = tit && tit.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/ig); if (m) m.forEach(e=>tokens.add(e)); });

    wrap.querySelectorAll('a[href*="/app/user/"]').forEach(a=>{ const u = decodeURIComponent((a.getAttribute('href')||'').split('/app/user/')[1]||'').trim(); if (u) tokens.add(u); });

    wrap.querySelectorAll('.frappe-avatar[data-user], .avatar[data-user]').forEach(n=>{ const u = n.getAttribute('data-user'); if (u) tokens.add(u); });

    return Array.from(tokens).filter(Boolean);
  }

  function resolve_user_info(token){ const info = (typeof frappe?.user_info === "function") ? frappe.user_info(token) : null; if (info && (info.fullname || info.name || info.email)) return info; if (EMAIL_RE.test(token)) return { name: token, fullname: token, email: token, image: "" }; return { name: token, fullname: token, email: "", image: "" }; }

  function gather_assignees_from_wrap(wrap, idx){
    const tokens = collect_user_tokens(wrap);
    const docname = get_docname(wrap) || "—";

    const sources = [];
    wrap.querySelectorAll('[data-user],[data-username],[data-owner],[data-user-id],[data-assignee],[data-assignees],[data-assignments]').forEach(n=>{ const attr = ['data-user','data-username','data-owner','data-user-id','data-assignee','data-assignees','data-assignments'].find(k=>n.hasAttribute(k)); const v = attr ? n.getAttribute(attr) : ""; if (v) sources.push([attr, v]); });
    wrap.querySelectorAll('[title],[data-original-title]').forEach(n=>{ const tit = n.getAttribute('title') || n.getAttribute('data-original-title') || ""; if (tit) sources.push(['title', tit]); });
    wrap.querySelectorAll('a[href*="/app/user/"]').forEach(a=>{ sources.push(['link', a.getAttribute('href')||""]); });

    log_card_full(wrap, idx, tokens, sources);
    return { docname, tokens, sources };
  }

  function scan_assignees_dom(){
    const root = getKanbanRoot();
    const raw = root ? Array.from(root.querySelectorAll(
      ".kanban-card-wrapper, .kanban-cards > .kanban-card, .kanban .kanban-card"
    )) : [];

    const containers = []; const seen = new Set();
    raw.forEach(n => { const box = get_card_container(n); if (!box) return; if (seen.has(box)) return; seen.add(box); containers.push(box); });

    const live = containers.filter(c => !is_placeholder_card(c));

    console.groupCollapsed?.(`${CFG.log_prefix} scan_assignees: cards_total=${containers.length} cards_live=${live.length}`);

    let found = 0; const uniq = new Map(); const diag = [];

    live.forEach((box, idx)=>{ const ts = parse_card_ts(box) || (Date.now() - idx); const { docname, tokens, sources } = gather_assignees_from_wrap(box, idx); diag.push({ docname, tokens, sources }); tokens.forEach(tok=>{ found += 1; const prev = uniq.get(tok) || 0; if (ts > prev) uniq.set(tok, ts); }); });
    console.groupEnd?.();

    if (!live.length && containers.length){ dbg("scan_assignees: live=0 — вероятно, data-name на wrap отсутствует."); }

    const ordered = Array.from(uniq.entries()).sort((a,b)=> b[1]-a[1]).map(([tok])=> tok);
    const list = ordered.map(tok => resolve_user_info(tok));
    group("assignees result", { unique: list.length, total_hits: found, diag_count: diag.length });
    return { list, diag, total: containers.length, live: live.length };
  }

  function get_live_card_containers(){ const root = getKanbanRoot(); const raw = root ? Array.from(root.querySelectorAll('.kanban-card-wrapper, .kanban-cards > .kanban-card, .kanban .kanban-card')) : []; const containers = []; const seen = new Set(); raw.forEach(n=>{ const box = get_card_container(n); if (box && !seen.has(box)) { seen.add(box); containers.push(box); } }); return containers.filter(c => !is_placeholder_card(c)); }
  function collect_docnames_from_cards(containers){ return containers.map(get_docname).filter(Boolean); }
  async function fetch_assignees_batch(dt, names){ try{ if (!dt || !names?.length) return []; const resp = await frappe.call({ method: 'frappe.client.get_list', args: { doctype: 'ToDo', fields: ['allocated_to','reference_name'], filters: [ ['ToDo','status','!=','Cancelled'], ['ToDo','reference_type','=', dt], ['ToDo','reference_name','in', names] ], limit_page_length: 500 } }); const out = []; (resp?.message||[]).forEach(row=>{ const who = row.allocated_to; if (who) out.push(who); }); return out; }catch(e){ dbg('fetch_assignees_batch error', e); return []; } }

  async function scan_assignees(){
    const dom = scan_assignees_dom();
    if (dom.list.length) return dom;
    if (dom.live > 0){
      const dt = getDoctype();
      const names = collect_docnames_from_cards(get_live_card_containers());
      const uniq = new Map();
      const allocated = await fetch_assignees_batch(dt, names);
      allocated.forEach(tok => { const prev = uniq.get(tok) || 0; if (0 >= prev) uniq.set(tok, 0); });
      const ordered = Array.from(uniq.keys());
      const list = ordered.map(tok => resolve_user_info(tok));
      return { list, diag: dom.diag, total: dom.total, live: dom.live };
    }
    return dom;
  }

  async function render_right_fly(force_scan=false){
    if (!isKanbanRoute()) return; // right fly only on Kanban
    const root = document.getElementById(CFG.ids.rightFly); if (!root) return;
    const body = root.querySelector('.dnt-fly-body');
    const head = root.querySelector('.dnt-fly-title'); head.textContent = t('Assignees');

    body.innerHTML = `<div class="dnt-user-grid"><div class="text-muted">${t('Scanning…')}</div></div>`;
    const res = force_scan ? await scan_assignees() : { list:[], diag:[], total:0, live:0 };

    const grid = document.createElement('div');
    grid.className = 'dnt-user-grid';
    if (!res.list.length){ grid.innerHTML = `<div class="text-muted">${t('No assignees')}</div>`; }
    else {
      grid.innerHTML = res.list.map(info=>{
        const img = info?.image ? `<img src="${esc(info.image)}" loading="lazy">` : '';
        const nm  = esc(info?.fullname || info?.name || '');
        const inits = (nm?.[0]||'A').toUpperCase();
        const uname = esc(info?.name || info?.email || '');
        return `
          <div class="dnt-user" data-open-user="${uname}">
            <div class="dnt-ava">${img || inits}</div>
            <div class="dnt-name" title="${nm}">${nm}</div>
          </div>`;
      }).join('');
    }
    body.innerHTML = '';
    body.appendChild(grid);

    // Delegated click → open User profile
    grid.addEventListener('click', (e)=>{
      const el = e.target && (e.target.closest ? e.target.closest('[data-open-user]') : null);
      if (!el) return;
      e.preventDefault(); e.stopPropagation();
      const u = el.getAttribute('data-open-user');
      dbg('open user:', u);
      if (u) frappe.set_route('Form','User', u);
    });
  }

  // ===== Left flyout (Workspaces) — global except hub
  function CLEAN_TEXT(n){ return CLEAN(n.textContent||"") || n.getAttribute?.("title") || ""; }

  function collect_sidebar_items_from_dom(){
    const containers = Array.from(document.querySelectorAll(".sidebar-item-container[item-name]"));
    const items = containers.map(cnt => {
      const hidden = cnt.getAttribute("item-is-hidden"); if (hidden === "1") return null;
      const is_public = (cnt.getAttribute("item-public") === "1");
      const a = cnt.querySelector("a.item-anchor[href]"); if (!a) return null;
      const label = CLEAN_TEXT(a); if (!label) return null;
      const href = a.getAttribute("href") || "#";
      let iconHTML = "";
      const iconSpan = cnt.querySelector(".sidebar-item-icon");
      if (iconSpan) iconHTML = iconSpan.outerHTML;
      else {
        const itemIcon = cnt.getAttribute("item-icon") || a.querySelector(".sidebar-item-icon")?.getAttribute("item-icon");
        if (itemIcon) iconHTML = `<span class="sidebar-item-icon" item-icon="${esc(itemIcon)}"><svg class="icon icon-md" aria-hidden="true"><use href="#icon-${esc(itemIcon)}"></use></svg></span>`;
      }
      return { href, label, iconHTML, is_public, src: "dom" };
    }).filter(Boolean);
    return items;
  }

  function collect_workspaces_from_boot(){
    const srcs = [ ...(frappe?.boot?.allowed_workspaces || []), ...(frappe?.boot?.workspaces || []), ...(frappe?.boot?.all_workspaces || []), ...(frappe?.boot?.public_workspaces || []), ].filter(Boolean);
    const out = [];
    for (const it of srcs){
      const label = CLEAN(it.title || it.label || it.name || ""); if (!label) continue;
      const is_hidden = !!(it.hidden || it.is_hidden || it.hide_in_sidebar || it.is_hidden_in_sidebar); if (is_hidden) continue;
      const route = (it.route && String(it.route)) || ("/app/" + encodeURIComponent(label.toLowerCase().replace(/\s+/g,"-")));
      const icon = it.icon_html || it.icon || it.icon_class || it.icon_name || it.icon_label || "";
      let iconHTML = "";
      if (icon && /</.test(icon)) { const tmp = document.createElement("div"); tmp.innerHTML = icon; const first = tmp.querySelector("svg, i, span"); iconHTML = first ? `<span class="sidebar-item-icon">${first.outerHTML}</span>` : ""; }
      else if (icon && /[a-z-]{2,}/i.test(icon)) { iconHTML = `<span class="sidebar-item-icon"><svg class="icon icon-md" aria-hidden="true"><use href="#icon-${esc(icon)}"></use></svg></span>`; }
      const is_public = !!(it.public || it.is_public);
      out.push({ href: route, label, iconHTML, is_public, src: "boot" });
    }
    const seen = new Set();
    return out.filter(x=>{ const key = (x.href||"") + "||" + (x.label||""); if (seen.has(key)) return false; seen.add(key); return true; });
  }

  function render_left_fly(){
    if (isWorkspaceHubRoute()) return; // not on hub
    const root = document.getElementById(CFG.ids.leftFly); if (!root) return;
    const pubBox = root.querySelector('.dnt-left-links[data-ws="public"]'); if (!pubBox) return;

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
      a.addEventListener("click",(e)=>{ e.preventDefault(); e.stopPropagation(); const href = it.href || ""; dbg("open workspace:", { href, label: it.label }); if (href.startsWith("#")) frappe.set_route(href.substring(1)); else window.location.assign(href); });
      frag.appendChild(a);
    });
    pubBox.replaceChildren(frag);

    const prvBlock = Array.from(root.querySelectorAll('.dnt-left-block'))[1];
    if (prvBlock) prvBlock.style.display = "none";
  }

  // ===== Board switcher (Kanban only)
  let last_switcher_hash = "";

  function ensure_board_switcher(){
    if (!isKanbanRoute()) {
      const prev = document.getElementById(CFG.ids.boardsWrap); if (prev) prev.remove(); last_switcher_hash = ""; return;
    }
    const head = document.querySelector(".page-head-content") || document.querySelector(".page-head"); if (!head) return;
    if (document.getElementById(CFG.ids.boardsWrap)) return;

    const wrap = document.createElement("div");
    wrap.id = CFG.ids.boardsWrap;
    wrap.innerHTML = `<div class="dnt-boards-grid dnt-seg"></div>`;
    head.insertAdjacentElement("afterend", wrap);

    render_board_switcher();
  }

  function render_board_switcher(){
    const wrap = document.getElementById(CFG.ids.boardsWrap); if (!wrap || !isKanbanRoute()) return;
    const grid = wrap.querySelector(".dnt-boards-grid");
    const dt = getDoctype();
    const active = CLEAN(getBoardName());
    const boards = CFG.STATIC_BOARDS;

    if (!dt) { grid.innerHTML = ""; return; }

    const html = boards.map(title=>{ const isActive = CLEAN(title) === active; return `<a href="#" class="dnt-board-btn${isActive?" active":""}" data-board="${esc(title)}">${esc(title)}</a>`; }).join("");

    const new_hash = `${dt}|${active}|${html}`;
    if (new_hash === last_switcher_hash) return;
    last_switcher_hash = new_hash;

    grid.innerHTML = html;
    grid.querySelectorAll(".dnt-board-btn").forEach(btn=>{
      btn.addEventListener("click",(e)=>{ e.preventDefault(); e.stopPropagation(); const title = btn.getAttribute("data-board"); dbg("switch board (hard):", { dt, title }); routeToBoard(dt, title); });
    });

    group("board switcher rendered", { dt, active, boards });
  }

  // ===== Flyouts & edges (split left/right)
  function remove_left(){ [CFG.ids.leftEdge, CFG.ids.leftFly].forEach(id=>{ const el = document.getElementById(id); if (el) el.remove(); }); }
  function remove_right(){ [CFG.ids.rightEdge, CFG.ids.rightFly].forEach(id=>{ const el = document.getElementById(id); if (el) el.remove(); }); }

  function ensure_left(){
    if (isWorkspaceHubRoute()) { remove_left(); return; }
    if (document.getElementById(CFG.ids.leftEdge)) return;

    const leftEdge  = document.createElement("div");
    leftEdge.id = CFG.ids.leftEdge;
    document.body.appendChild(leftEdge);

    const leftFly = document.createElement("div");
    leftFly.id = CFG.ids.leftFly; leftFly.className = "dnt-fly";
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
    document.body.appendChild(leftFly);

    const hover = { leftEdge:false, leftFly:false };
    const update = ()=>{ const fly = document.getElementById(CFG.ids.leftFly); if (!fly) return; const on = hover.leftEdge || hover.leftFly; if (on) fly.classList.add("show"); else fly.classList.remove("show"); };

    document.addEventListener("mousemove", (e)=>{ if (isWorkspaceHubRoute()) return; const nearLeft = e.clientX <= CFG.edgeW; if (nearLeft !== hover.leftEdge){ hover.leftEdge = nearLeft; if (nearLeft) render_left_fly(); update(); } }, {passive:true});
    leftEdge.addEventListener("mouseenter", ()=>{ if (isWorkspaceHubRoute()) return; hover.leftEdge = true; render_left_fly(); update(); });
    leftEdge.addEventListener("mouseleave", ()=>{ hover.leftEdge = false; update(); });
    leftFly.addEventListener("mouseenter", ()=>{ hover.leftFly = true; update(); });
    leftFly.addEventListener("mouseleave", ()=>{ hover.leftFly = false; update(); });

    dbg("left flyouts created");
  }

  function ensure_right(){
    if (!isKanbanRoute()) { remove_right(); return; }
    if (document.getElementById(CFG.ids.rightEdge)) return;

    const rightEdge = document.createElement("div"); rightEdge.id = CFG.ids.rightEdge; document.body.appendChild(rightEdge);

    const rightFly = document.createElement("div"); rightFly.id = CFG.ids.rightFly; rightFly.className = "dnt-fly";
    rightFly.innerHTML = `
      <div class="dnt-fly-head">
        <div class="dnt-fly-title">${t("Assignees")}</div>
        <div class="text-muted" style="font-size:12px">${t("hover out to close")}</div>
      </div>
      <div class="dnt-fly-body"><div class="dnt-user-grid"></div></div>
    `;
    document.body.appendChild(rightFly);

    const hover = { rightEdge:false, rightFly:false };
    const update = ()=>{ const fly = document.getElementById(CFG.ids.rightFly); if (!fly) return; const on = hover.rightEdge || hover.rightFly; if (on) fly.classList.add("show"); else fly.classList.remove("show"); };

    document.addEventListener("mousemove", (e)=>{ if (!isKanbanRoute()) return; const w = window.innerWidth; const nearRight = (w - e.clientX) <= CFG.edgeW; if (nearRight !== hover.rightEdge){ hover.rightEdge = nearRight; if (nearRight) render_right_fly(true); update(); } }, {passive:true});
    rightEdge.addEventListener("mouseenter", ()=>{ if (!isKanbanRoute()) return; hover.rightEdge = true; render_right_fly(true); update(); });
    rightEdge.addEventListener("mouseleave", ()=>{ hover.rightEdge = false; update(); });
    rightFly.addEventListener("mouseenter", ()=>{ hover.rightFly = true; update(); });
    rightFly.addEventListener("mouseleave", ()=>{ hover.rightFly = false; update(); });

    dbg("right flyouts created");
  }

  // ===== Boot / Route
  function run(){
    update_theme_flag();

    // Left is global except hub
    ensure_left();

    // Right only on Kanban
    ensure_right();

    // Board switcher only on Kanban
    if (!isKanbanRoute()) {
      const bs = document.getElementById(CFG.ids.boardsWrap); if (bs) bs.remove();
      last_switcher_hash = "";
    } else {
      ensure_board_switcher();
      setTimeout(()=>{ update_theme_flag(); render_board_switcher(); }, 120);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
  else run();

  frappe?.router?.on && frappe.router.on("change", run);

  let wd_i = 0;
  setInterval(()=> { wd_i = (wd_i+1)%4; if (!wd_i) { dbg("watchdog route:", getRoute().join(" / ")); update_theme_flag(); } }, 3000);
})();