// === dnt_autosave_f15_force.js ===
// Frappe v15 — автосохранение на любых изменениях + скрытие Save (docstatus=0) + анти-дёргание UI.
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

  // CSS: прячем Save и фиксируем макет во время сохранения (без анимаций)
  (function ensure_css(){
    if (document.getElementById("dnt-autosave-css")) return;
    const s = document.createElement("style");
    s.id = "dnt-autosave-css";
    s.textContent = `
      .page-actions .primary-action[data-label="Save"],
      .page-head   .primary-action[data-label="Save"],
      .page-actions .primary-action[data-label="Сохранить"],
      .page-head   .primary-action[data-label="Сохранить"] { display:none !important; }

      .dnt-saving * { transition: none !important; animation: none !important; }
      .dnt-saving .page-head { min-height: 56px; }
      .dnt-saving .page-head .indicator-pill { visibility: hidden !important; } /* место сохраняем */
      .dnt-saving .form-message { display: none !important; } /* убираем всплывающие системные подсказки */
    `;
    document.head.appendChild(s);
  })();

  function page_root(frm){
    return (frm?.page?.wrapper && (frm.page.wrapper[0] || frm.page.wrapper)) || null;
  }

  function supported(frm){
    try{
      if (!frm || !frm.doctype || !frm.doc) return false;
      if (frm.meta?.istable) return false;
      if (frm.doc.docstatus !== 0) return false;
      if (CFG.exclude.has(frm.doctype)) return false;
      if (frm.__dnt_autosave_disabled || frm.doc.__disable_autosave) return false;
      return true;
    } catch { return false; }
  }

  function hide_save_ui_strict(frm){
    try { frm.disable_save?.(); } catch {}
    try { frm.page?.clear_primary_action?.(); } catch {}
    try {
      const btn = frm.page?.btn_primary;
      if (btn && typeof btn.addClass === "function") btn.addClass("hide");
    } catch {}
    try {
      const root = page_root(frm);
      if (root && !root.__dnt_actions_obs){
        const acts = root.querySelector(".page-actions");
        if (acts){
          const mo = new MutationObserver(() => {
            try { frm.page?.clear_primary_action?.(); } catch {}
            try {
              const b = frm.page?.btn_primary;
              if (b && typeof b.addClass === "function") b.addClass("hide");
            } catch {}
          });
          mo.observe(acts, { childList:true, subtree:true });
          root.__dnt_actions_obs = mo;
        }
      }
    } catch {}
  }

  // --- Анти-дёргание: сохраняем/восстанавливаем фокус, каретку и скролл ---
  function capture_ui_state(frm){
    const state = {};
    try {
      const root = page_root(frm) || document;
      const active = document.activeElement;
      const fieldwrap = active && active.closest?.(".frappe-control");
      const fieldname = fieldwrap?.getAttribute?.("data-fieldname");
      state.fieldname = fieldname || null;

      // каретка
      try {
        if (active && ("selectionStart" in active) && ("selectionEnd" in active)) {
          state.caret = [active.selectionStart, active.selectionEnd];
        }
      } catch {}

      // скроллы
      const main = (page_root(frm) || document).querySelector?.(".layout-main-section");
      state.scroll_el = main || document.scrollingElement || document.documentElement;
      state.scroll_top = state.scroll_el ? state.scroll_el.scrollTop : null;
    } catch {}
    return state;
  }

  function restore_ui_state(frm, state){
    try {
      // скролл
      if (state?.scroll_el && typeof state.scroll_top === "number") {
        state.scroll_el.scrollTop = state.scroll_top;
      }
      // фокус
      if (state?.fieldname) {
        const ctrl = frm.get_field?.(state.fieldname);
        let input = null;
        if (ctrl?.$input?.length) input = ctrl.$input.get(0);
        if (!input) {
          input = (page_root(frm) || document).querySelector(
            `.frappe-control[data-fieldname="${CSS.escape(state.fieldname)}"] input, 
             .frappe-control[data-fieldname="${CSS.escape(state.fieldname)}"] textarea, 
             .frappe-control[data-fieldname="${CSS.escape(state.fieldname)}"] select`
          );
        }
        if (input) {
          input.focus({ preventScroll: true });
          try {
            if (state.caret) input.setSelectionRange(state.caret[0], state.caret[1]);
          } catch {}
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

  function bind_autosave(frm){
    if (frm.__dnt_autosave_bound) return;
    frm.__dnt_autosave_bound = true;

    if (!supported(frm)) return;

    hide_save_ui_strict(frm);

    let timer = null;
    let saving = false;
    let pending = false;
    let last_saved = 0;

    const is_dirty = () => !!frm.doc.__unsaved || (typeof frm.is_dirty === "function" && frm.is_dirty());

    const schedule = () => {
      if (!supported(frm)) return;
      pending = true;
      if (timer) clearTimeout(timer);
      timer = setTimeout(flush, CFG.debounce_ms);
      try { console.debug(CFG.log_prefix, "scheduled"); } catch {}
    };

    const flush = async () => {
      if (!supported(frm)) { pending = false; return; }
      if (saving) return;
      if (!is_dirty()) { pending = false; return; }

      const now = Date.now();
      const wait = CFG.min_gap_ms - (now - last_saved);
      if (wait > 0) { timer = setTimeout(flush, wait); return; }

      saving = true;

      // глушим звук/тост на время автосейва
      const old_alert = frappe.show_alert;
      const old_sound = frappe.utils?.play_sound;
      frappe.show_alert = function (msg, seconds) {
        try {
          const txt = typeof msg === "string" ? msg : (msg && (msg.message || msg.title)) || "";
          const t = String(txt).toLowerCase();
          if (t.includes("saved") || t.includes("сохран")) return;
        } catch {}
        return old_alert.apply(this, arguments);
      };
      if (frappe.utils) frappe.utils.play_sound = function () {};

      // анти-дёргание
      const ui = capture_ui_state(frm);
      const root = page_root(frm) || document.body;
      root.classList.add("dnt-saving");

      try {
        console.log(CFG.log_prefix, "saving…", frm.doctype, frm.docname || frm.doc.name);
        await frm.save("Save");
        last_saved = Date.now();
        console.log(CFG.log_prefix, "saved ✓", new Date(last_saved).toLocaleTimeString());
      } catch (e){
        console.warn(CFG.log_prefix, "save failed:", e?.message || e);
      } finally {
        // вернуть звук/алерт
        if (frappe.utils && old_sound) frappe.utils.play_sound = old_sound;
        if (old_alert) frappe.show_alert = old_alert;

        // восстановить UI
        requestAnimationFrame(() => {
          restore_ui_state(frm, ui);
          root.classList.remove("dnt-saving");
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

    // DOM-инпуты (захватом): Select/Data/Date/etc.
    const root = page_root(frm) || document;
    if (!frm.__dnt_dom_bound){
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

  // Патчим frappe.model.set_value (для grid/child)
  (function patch_model_set_value_when_ready(){
    const try_patch = () => {
      if (!frappe?.model?.set_value || frappe.model.__dnt_patched) return false;
      const orig = frappe.model.set_value.bind(frappe.model);
      frappe.model.set_value = async function(doctype, name, fieldname, value, df){
        const out = await orig(doctype, name, fieldname, value, df);
        try {
          const frm = cur_frm;
          if (frm && supported(frm) && frm.dnt_autosave_schedule) frm.dnt_autosave_schedule();
        } catch {}
        return out;
      };
      frappe.model.__dnt_patched = true;
      try { console.debug(CFG.log_prefix, "patched frappe.model.set_value"); } catch {}
      return true;
    };
    if (!try_patch()) {
      const t = setInterval(() => { if (try_patch()) clearInterval(t); }, 200);
    }
  })();

  // Хук на все формы
  frappe.ui.form.on("*", {
    setup(frm){ if (supported(frm)) bind_autosave(frm); },
    onload_post_render(frm){ if (supported(frm)) bind_autosave(frm); },
    refresh(frm){
      if (supported(frm)) {
        bind_autosave(frm);
        hide_save_ui_strict(frm);
      } else {
        try { page_root(frm)?.classList.remove("dnt-hide-save"); } catch {}
      }
    },
  });

  // Страховка: перепривязка к текущей форме
  setInterval(() => {
    try {
      const frm = cur_frm;
      if (frm && supported(frm)) bind_autosave(frm);
    } catch {}
  }, 800);

  // Утилита для консоли
  window.dnt_autosave_flush_all = async () => {
    try { if (cur_frm?.dnt_autosave_flush) await cur_frm.dnt_autosave_flush(); } catch {}
  };
})();