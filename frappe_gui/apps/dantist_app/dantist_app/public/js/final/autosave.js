// === dnt_autosave_f15_force.js (guarded) ===
// Frappe v15 — автосохранение + корректная логика Save без дёрганий.
// ВАЖНО: работает ТОЛЬКО на страницах Form. На Kanban/List/Report — полностью бездействует.
// Правила:
// • Создание (frm.is_new() === true): кнопку Save не трогаем, автосейва нет.
// • Редактирование (frm.is_new() === false): скрываем/не создаём Save, автосейв активен.
// • Ничего не ломаем вне форм: патчи и наблюдатели включаются только на Form.

(function () {
  if (window.__DNT_AUTOSAVE_F15_FORCE) return;
  window.__DNT_AUTOSAVE_F15_FORCE = true;

  const CFG = {
    exclude: new Set([
      "DocType","Customize Form","Report","Print Format",
      "Dashboard","Dashboard Chart","Workspace"
    ]),
    debounce_ms: 700,
    min_gap_ms: 1100,
    log_prefix: "[DNT-AUTOSAVE]"
  };

  // === CSS: только анти-дёргание на время автосохранения ===
  (function ensure_css(){
    if (document.getElementById("dnt-autosave-css")) return;
    const s = document.createElement("style");
    s.id = "dnt-autosave-css";
    s.textContent = `
      .dnt-saving * { transition: none !important; animation: none !important; }
      .dnt-saving .page-head { min-height: 56px; }
      .dnt-saving .page-head .indicator-pill { visibility: hidden !important; }
      .dnt-saving .form-message { display: none !important; }
    `;
    document.head.appendChild(s);
  })();

  // === Утилиты ===
  const get_route = () => (window.frappe?.get_route?.() || []);

  const is_kanban_route = () => {
    try {
      const r = get_route() || [];
      if (r.some(x => x === "Kanban" || x === "Kanban Board")) return true;
      const p = ((location.pathname||"") + " " + (location.hash||""));
      return p.includes("/view/kanban/") || p.includes("Kanban%20Board");
    } catch { return false; }
  };

  const is_form_route = () => {
    try {
      const r = get_route();
      if (!r || r[0] !== "Form") return false;
      const page = window.cur_frm?.page;
      const host = page && (page.wrapper?.[0] || page.wrapper);
      return !!(host && host.isConnected && document.contains(host));
    } catch { return false; }
  };

  function page_root(frm){
    try {
      const w = frm?.page?.wrapper;
      return (w && (w[0] || w)) || null;
    } catch { return null; }
  }

  function is_new_doc(frm){
    try {
      if (!frm || !frm.doc) return false;
      if (typeof frm.is_new === "function") return frm.is_new();
      return !!frm.doc.__islocal;
    } catch { return false; }
  }

  function supported_autosave(frm){
    try{
      if (!is_form_route()) return false;
      if (is_kanban_route()) return false;
      if (!frm || !frm.doctype || !frm.doc) return false;
      if (frm.meta?.istable) return false;
      if (frm.doc.docstatus !== 0) return false;
      if (CFG.exclude.has(frm.doctype)) return false;
      if (frm.__dnt_autosave_disabled || frm.doc.__disable_autosave) return false;
      if (is_new_doc(frm)) return false; // на создании — без автосейва
      return true;
    } catch { return false; }
  }

  // === ПЕРЕХВАТ: не даём создать Save на редактировании (только на Form) ===
  (function patch_set_primary_action(){
    const try_patch = () => {
      const proto = window.frappe?.ui?.Page?.prototype;
      if (!proto) return false;
      if (proto.__dnt_patched_spa) return true;

      const orig = proto.set_primary_action;
      proto.set_primary_action = function(label, action, icon, btn_class){
        try {
          if (!is_form_route()) return orig.apply(this, arguments);
          const frm = window.cur_frm;
          if (frm && this === frm.page && !is_new_doc(frm)) {
            const lbl = (typeof label === "string" ? label : (label?.toString?.() || "")).toLowerCase();
            if (lbl.includes("save") || lbl.includes("сохран")) {
              try { this.clear_primary_action?.(); } catch {}
              try {
                const host = (this.wrapper && (this.wrapper[0] || this.wrapper)) || null;
                const std = host?.querySelector?.(".page-actions .standard-actions") || host;
                if (std) {
                  const btn = document.createElement("button");
                  btn.className = "btn btn-primary btn-sm primary-action dnt-suppressed-save";
                  btn.setAttribute("data-label", label || "");
                  btn.style.display = "none";
                  std.appendChild(btn);
                  return btn;
                }
              } catch {}
              return null;
            }
          }
        } catch {}
        return orig.apply(this, arguments);
      };

      proto.__dnt_patched_spa = true;
      return true;
    };
    if (!try_patch()) {
      const t = setInterval(() => { if (try_patch()) clearInterval(t); }, 100);
    }
  })();

  // === РЕЗЕРВ: если Save «подсунут» позже — скрываем (только внутри текущей формы) ===
  (function guard_save_presence(){
    let mo = null;

    function kill_save_in(container){
      const frm = window.cur_frm;
      if (!frm || !is_form_route() || is_new_doc(frm)) return;
      container.querySelectorAll('.primary-action').forEach(btn => {
        const label = ((btn.getAttribute("data-label") || btn.textContent || "") + "").toLowerCase();
        if (label.includes("save") || label.includes("сохран")) {
          btn.style.display = "none";
          btn.classList.add("dnt-suppressed-save");
        }
      });
    }

    function mount(){
      if (!is_form_route()) return false;
      const frm = window.cur_frm; if (!frm) return false;
      const host = page_root(frm);
      if (!host) return false;
      const container = host.querySelector(".page-actions");
      if (!container) return false;
      kill_save_in(container);
      mo = new MutationObserver(() => kill_save_in(container));
      mo.observe(container, { childList:true, subtree:true });
      return true;
    }

    function unmount(){ try { mo && mo.disconnect(); mo = null; } catch {} }

    if (!mount()) {
      const t = setInterval(() => { if (mount()) clearInterval(t); }, 200);
    }

    try { frappe?.router?.on && frappe.router.on("change", () => { unmount(); setTimeout(mount, 50); }); } catch {}
  })();

  // === Анти-дёргание курсора/скролла при автосохранении ===
  function capture_ui_state(frm){
    const state = {};
    try {
      const active = document.activeElement;
      const fieldwrap = active && active.closest?.(".frappe-control");
      state.fieldname = fieldwrap?.getAttribute?.("data-fieldname") || null;
      try { if (active && ("selectionStart" in active) && ("selectionEnd" in active)) { state.caret = [active.selectionStart, active.selectionEnd]; } } catch {}
      const root_el = page_root(frm);
      const main = root_el?.querySelector?.(".layout-main-section");
      state.scroll_el = main || document.scrollingElement || document.documentElement;
      state.scroll_top = state.scroll_el ? state.scroll_el.scrollTop : null;
    } catch {}
    return state;
  }

  function restore_ui_state(frm, state){
    try {
      if (state?.scroll_el && typeof state.scroll_top === "number") state.scroll_el.scrollTop = state.scroll_top;
      if (state?.fieldname) {
        const ctrl = frm.get_field?.(state.fieldname);
        let input = ctrl?.$input?.length ? ctrl.$input.get(0) : null;
        if (!input) {
          const root_el = page_root(frm);
          input = root_el?.querySelector(
            `.frappe-control[data-fieldname="${CSS.escape(state.fieldname)}"] input,
             .frappe-control[data-fieldname="${CSS.escape(state.fieldname)}"] textarea,
             .frappe-control[data-fieldname="${CSS.escape(state.fieldname)}"] select`
          );
        }
        if (input) {
          input.focus({ preventScroll: true });
          try { if (state.caret) input.setSelectionRange(state.caret[0], state.caret[1]); } catch {}
        }
      }
    } catch {}
  }

  function attach_grid_listeners(frm, schedule){
    try{
      Object.values(frm.fields_dict || {}).forEach(f => {
        if (f?.grid && !f.grid.__dnt_autosave_bound){
          f.grid.on("data-change", schedule);
          f.grid.on("row-move", schedule);
          f.grid.on("grid-row-removed", schedule);
          f.grid.__dnt_autosave_bound = true;
        }
      });
    } catch {}
  }

  // === Автосохранение ===
  function bind_autosave(frm){
    if (frm.__dnt_autosave_bound) return;
    if (!supported_autosave(frm)) return;

    frm.__dnt_autosave_bound = true;

    let timer = null;
    let saving = false;
    let pending = false;
    let last_saved = 0;

    const is_dirty = () => !!frm.doc.__unsaved || (typeof frm.is_dirty === "function" && frm.is_dirty());

    const schedule = () => {
      if (!supported_autosave(frm)) return;
      pending = true;
      if (timer) clearTimeout(timer);
      timer = setTimeout(flush, CFG.debounce_ms);
      try { console.debug(CFG.log_prefix, "scheduled"); } catch {}
    };

    const flush = async () => {
      if (!supported_autosave(frm)) { pending = false; return; }
      if (saving) return;
      if (!is_dirty()) { pending = false; return; }

      const now = Date.now();
      const wait = CFG.min_gap_ms - (now - last_saved);
      if (wait > 0) { timer = setTimeout(flush, wait); return; }

      saving = true;

      const old_alert = frappe.show_alert;
      const old_sound = frappe.utils?.play_sound;
      frappe.show_alert = function (msg) {
        try {
          const txt = typeof msg === "string" ? msg : (msg && (msg.message || msg.title)) || "";
          const t = String(txt).toLowerCase();
          if (t.includes("saved") || t.includes("сохран")) return;
        } catch {}
        return old_alert.apply(this, arguments);
      };
      if (frappe.utils) frappe.utils.play_sound = function () {};

      const ui = capture_ui_state(frm);
      const root = page_root(frm);

      if (root) root.classList.add("dnt-saving");

      try {
        console.log(CFG.log_prefix, "saving…", frm.doctype, frm.docname || frm.doc.name);
        await frm.save("Save");
        last_saved = Date.now();
        console.log(CFG.log_prefix, "saved ✓", new Date(last_saved).toLocaleTimeString());
      } catch (e){
        console.warn(CFG.log_prefix, "save failed:", e?.message || e);
      } finally {
        if (frappe.utils && old_sound) frappe.utils.play_sound = old_sound;
        if (old_alert) frappe.show_alert = old_alert;
        requestAnimationFrame(() => {
          restore_ui_state(frm, ui);
          if (root) root.classList.remove("dnt-saving");
        });
        saving = false;
        pending = false;
      }
    };

    // перехват frm.set_value
    const orig_set_value = frm.set_value.bind(frm);
    frm.set_value = async function(){
      const out = await orig_set_value(...arguments);
      schedule();
      return out;
    };

    // DOM-инпуты (захватом) — строго на корне формы
    const root = page_root(frm);
    if (root && !frm.__dnt_dom_bound){
      const dom_on_change = frappe.utils?.debounce ? frappe.utils.debounce(schedule, 50) : schedule;
      root.addEventListener("input", dom_on_change, true);
      root.addEventListener("change", dom_on_change, true);
      root.addEventListener("blur", dom_on_change, true);
      frm.__dnt_dom_bound = true;
    }

    attach_grid_listeners(frm, schedule);

    const late = () => { flush(); };
    document.addEventListener("visibilitychange", () => { if (document.hidden) flush(); });
    window.addEventListener("pagehide", late);
    window.addEventListener("freeze", late);
    try { frappe.router.on("change", () => { if (frm && (frm.doc.__unsaved || pending)) flush(); }); } catch {}

    frm.dnt_autosave_schedule = schedule;
    frm.dnt_autosave_flush = flush;
  }

  // === Патч frappe.model.set_value для child-таблиц (только триггер автосейва) ===
  (function patch_model_set_value_when_ready(){
    const try_patch = () => {
      const m = frappe?.model;
      if (!m || !m.set_value) return false;
      if (m.__dnt_patched) return true;
      const orig = m.set_value.bind(m);
      m.set_value = async function(doctype, name, fieldname, value, df){
        const out = await orig(doctype, name, fieldname, value, df);
        try {
          const frm = cur_frm;
          if (frm && supported_autosave(frm) && frm.dnt_autosave_schedule) frm.dnt_autosave_schedule();
        } catch {}
        return out;
      };
      m.__dnt_patched = true;
      try { console.debug(CFG.log_prefix, "patched frappe.model.set_value"); } catch {}
      return true;
    };
    if (!try_patch()) {
      const t = setInterval(() => { if (try_patch()) clearInterval(t); }, 200);
    }
  })();

  // === Хуки форм: включаем автосейв только на Form ===
  frappe.ui.form.on("*", {
    setup(frm){ if (supported_autosave(frm)) bind_autosave(frm); },
    onload_post_render(frm){ if (supported_autosave(frm)) bind_autosave(frm); },
    refresh(frm){ if (supported_autosave(frm)) bind_autosave(frm); },
  });

  // === Safety-биндер: если не успели привязаться — дожмём, но только на Form ===
  setInterval(() => {
    try {
      if (!is_form_route() || is_kanban_route()) return;
      const frm = cur_frm;
      if (frm && supported_autosave(frm)) bind_autosave(frm);
    } catch {}
  }, 800);

  // Утилита для консоли
  window.dnt_autosave_flush_all = async () => {
    try { if (cur_frm?.dnt_autosave_flush) await cur_frm.dnt_autosave_flush(); } catch {}
  };
})();