// rbac_form_v4.js — итог: поведение как в v2 для Super Admin, плюс строгая маскировка вкладок и whitelist языков
(function () {
  const CONFIG = {
    privilegedRole: "System Manager",                 // видит всё, никаких ограничений
    superRole: "AIHub Super Admin",                   // как в v2: вкладки Settings/Connections скрыты, остальное видно
    restrictedRoles: [
      "AIHub Super Admin", "AIHub Admin", "AIHub Demo",
      "AIHub User", "AIHub Manager", "AIHub Doctor",
      "AIHub Assistant", "Super Admin"
    ],
    // что скрываем (нижний регистр)
    targetTabNames: ["connections", "settings"],
    targetTabFieldnames: ["connections_tab", "settings_tab"],

    // Разрешённые языки для всех, КРОМЕ System Manager:
    // ru (рус), uk (укр), be (бел), ka (груз), pl (пол), en (англ)
    allowedLanguages: ["ru", "uk", "be", "ka", "pl", "en"],

    DEBUG: false
  };

  // ---- helpers ----
  const log = (...a) => CONFIG.DEBUG && console.log("[RBAC]", ...a);
  const norm = s => (s || "").replace(/\s+/g, " ").trim().toLowerCase();

  function get_roles() {
    return (window.frappe && frappe.boot && frappe.boot.user && Array.isArray(frappe.boot.user.roles))
      ? frappe.boot.user.roles : [];
  }
  function has_role(name) {
    try { if (window.frappe?.user?.has_role) return !!frappe.user.has_role(name); } catch (_) {}
    return get_roles().includes(name);
  }
  function is_privileged() { return has_role(CONFIG.privilegedRole); }
  function is_super() { return has_role(CONFIG.superRole); }
  function in_restricted_group() { return get_roles().some(r => CONFIG.restrictedRoles.includes(r)); }
  function restricted_active() { return in_restricted_group() && !is_privileged(); }

  function on_form_route() {
    const rt = (window.frappe && frappe.get_route && frappe.get_route()) || [];
    if (rt[0] === "Form") return true;
    const dr = (document.body && document.body.getAttribute("data-route")) || "";
    return /^Form\//i.test(dr);
  }

  // ---- строгая маскировка вкладок Settings/Connections (и кнопок, и панелей) ----
  function hide_settings_connections_tabs() {
    const tabNames = CONFIG.targetTabNames.map(norm);
    const tabFns   = CONFIG.targetTabFieldnames.map(norm);
    let hiddenSomething = false;

    // Верхние табы (кнопки)
    document.querySelectorAll(".form-tabs .nav-item, .form-tabs .nav-link, .form-tabs button").forEach(el => {
      const text = norm(el.textContent || el.getAttribute("aria-label"));
      const fn   = norm(el.getAttribute("data-fieldname"));
      const href = norm(el.getAttribute("href"));
      const id   = norm(el.id);
      let match = false;

      if (fn)   match = match || tabFns.includes(fn);
      if (href) match = match || tabFns.some(x => href.includes(x));
      if (id)   match = match || tabFns.some(x => id.includes(x));
      if (text) match = match || tabNames.some(x => text.includes(x) || (x === "settings" && /настройк/.test(text)) || (x === "connections" && /соединен/.test(text)));

      if (match) {
        const li = el.closest(".nav-item") || el;
        li.style.display = "none";
        li.setAttribute("aria-hidden", "true");
        hiddenSomething = true;
      }
    });

    // Содержимое вкладок (панели)
    document.querySelectorAll('.tab-content [role="tabpanel"]').forEach(pane => {
      const byLabel    = norm(pane.getAttribute("aria-labelledby"));
      const byControls = norm(pane.getAttribute("aria-controls"));
      const id         = norm(pane.id || "");
      const match = tabFns.some(x => byLabel.includes(x) || byControls.includes(x) || id.includes(x));
      if (match) {
        pane.style.display = "none";
        pane.setAttribute("aria-hidden", "true");
      }
    });

    // Если активная была скрыта — переключиться на первую видимую
    if (hiddenSomething) {
      const activeBtn = document.querySelector(".form-tabs .nav-link.active");
      if (activeBtn && activeBtn.closest(".nav-item")?.style.display === "none") {
        const firstVisible = Array.from(document.querySelectorAll(".form-tabs .nav-link"))
          .find(btn => btn.closest(".nav-item")?.style.display !== "none");
        if (firstVisible) firstVisible.click();
      }
    }
  }

  // ---- ограничение выбора языка (Link: Language) ----
  function restrict_language_link(frm) {
    try {
      if (!frm || frm.doctype !== "User") return;

      if (is_privileged()) {
        // System Manager — без ограничений
        frm.set_query("language", () => ({}));
        log("Language: unrestricted (System Manager)");
        return;
      }

      const wl = CONFIG.allowedLanguages.slice();
      frm.set_query("language", () => ({ filters: { name: ["in", wl] } }));
      log("Language: restricted to", wl);

      // Если уже выбран язык вне whitelist — мягкое предупреждение
      const cur = frm.doc?.language;
      if (cur && !wl.includes(cur)) {
        const $ctrl = frm.get_field?.("language")?.$wrapper;
        if ($ctrl && !$ctrl.querySelector(".rbac-lang-note")) {
          $ctrl.classList.add("rbac-lang-warning");
          const note = document.createElement("div");
          note.className = "rbac-lang-note text-warning small mt-1";
          note.textContent = "Текущий язык вне разрешённого списка. Выберите из доступных.";
          $ctrl.append(note);
        }
      }
    } catch (e) {
      log("Language restriction error:", e);
    }
  }

  // ---- основное применение (как в v2 по ролям) ----
  function apply() {
    if (!on_form_route()) return;

    if (is_privileged()) { // System Manager — ничего не скрываем
      log("privileged → noop");
      return;
    }

    if (restricted_active()) {
      // Скрываем вкладки Settings/Connections для всех, кто в restricted (включая Super Admin)
      hide_settings_connections_tabs();

      // Общие блоки (скрываем)
      [".form-shared", ".form-sidebar-stats", ".form-sidebar .form-follow"]
        .forEach(sel => document.querySelectorAll(sel).forEach(el => {
          el.style.display = "none";
          el.setAttribute("aria-hidden", "true");
        }));

      // Таймлайн/комменты/мета — как в v2:
      const assign = document.querySelector(".form-assignments");
      const meta = document.querySelector("ul.list-unstyled.sidebar-menu.text-muted");
      const timeline   = document.querySelector(".new-timeline");
      const commentBox = document.querySelector(".form-footer .comment-box");
      const commentBtn = document.querySelector(".form-footer .btn-comment");

      if (is_super()) {
        // Super Admin: вернуть видимость как раньше
        [assign, meta, timeline, commentBox, commentBtn].forEach(el => { if (!el) return; el.style.display = ""; el.removeAttribute("aria-hidden"); });
        // раскрыть боковую, если схлопнута
        let p = meta && meta.parentElement;
        while (p && p !== document.documentElement) {
          if (p.matches(".form-sidebar, .overlay-sidebar, .layout-side-section, .layout-side-section-wrapper")) {
            p.style.display = "";
            p.removeAttribute("aria-hidden");
          }
          p = p && p.parentElement;
        }
      } else {
        // Прочие из restricted: скрыть
        [meta, timeline, commentBox, commentBtn].forEach(el => { if (!el) return; el.style.display = "none"; el.setAttribute("aria-hidden","true"); });
      }

      // Убрать "New Email" в таймлайне
      const txt = t => norm(t || "");
      document.querySelectorAll(".timeline-content .action-buttons .action-btn, .new-timeline .action-buttons .action-btn")
        .forEach(btn => { if (txt(btn.textContent || btn.getAttribute("aria-label")).includes("new email")) btn.style.display = "none"; });

      log("applied (restricted; tabs hidden; super admin extras restored)");
    } else {
      log("not restricted → noop");
    }

    // Ограничение языка — на форме User
    try {
      const frm = (window.cur_frm && window.cur_frm.doctype === "User") ? window.cur_frm : null;
      if (frm) restrict_language_link(frm);
    } catch (e) { log("frm hook error:", e); }
  }

  // ---- надёжные хуки Frappe, чтобы set_query не терялся ----
  function install_frm_hooks() {
    if (!window.frappe?.ui?.form?.on) return;
    frappe.ui.form.on("User", {
      onload:  function(frm){ restrict_language_link(frm); },
      refresh: function(frm){ restrict_language_link(frm); }
    });
  }

  // ---- ждём роли и наблюдаем DOM ----
  function wait_roles_and_apply(maxMs = 4000) {
    const start = Date.now();
    (function tick(){
      const rs = get_roles();
      if (rs.length) { log("roles:", rs); apply(); return; }
      if (Date.now() - start > maxMs) { log("roles timeout, applying anyway"); apply(); return; }
      setTimeout(tick, 80);
    })();
  }

  function observe() {
    try {
      new MutationObserver(() => { if (on_form_route()) apply(); })
        .observe(document.body || document.documentElement, { childList: true, subtree: true });
    } catch (_) {}
    if (window.frappe?.router?.on) {
      frappe.router.on("change", () => { if (on_form_route()) apply(); });
    }
  }

  // ---- boot ----
  function boot() {
    install_frm_hooks();
    wait_roles_and_apply();
    observe();
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);

  // ручная проверка в консоли
  window.__rbac_debug = () => ({
    roles: get_roles(),
    restricted: restricted_active(),
    privileged: is_privileged(),
    super: is_super()
  });

  // лёгкая подсветка, если язык вне whitelist
  const style = document.createElement("style");
  style.textContent = `.rbac-lang-warning .control-input{outline:2px dashed #e0a800;outline-offset:2px;border-radius:4px}`;
  document.documentElement.appendChild(style);
})();