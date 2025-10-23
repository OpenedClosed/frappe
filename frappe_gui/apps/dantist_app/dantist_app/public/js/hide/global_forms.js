// rbac_form_v2.js — минималистично и надёжно
(function () {
  const CONFIG = {
    privilegedRole: "System Manager",
    restrictedRoles: [
      "AIHub Super Admin", "AIHub Admin", "AIHub Demo",
      "AIHub User", "AIHub Manager", "AIHub Doctor",
      "AIHub Assistant", "Super Admin"
      // добавь свои роли сюда при необходимости
    ],
    superRole: "AIHub Super Admin",
    targetTabNames: ["connections", "settings"], // нижний регистр
    DEBUG: false // переключи в true для логов
  };

  // ---- helpers ----
  const log = (...a) => CONFIG.DEBUG && console.log("[RBAC]", ...a);
  const norm = s => (s || "").replace(/\s+/g, " ").trim().toLowerCase();

  function get_roles() {
    return (window.frappe && frappe.boot && frappe.boot.user && Array.isArray(frappe.boot.user.roles))
      ? frappe.boot.user.roles : [];
  }
  function has_role(name) {
    try {
      if (window.frappe && frappe.user && typeof frappe.user.has_role === "function") {
        return !!frappe.user.has_role(name);
      }
    } catch (_) {}
    const rs = get_roles();
    return rs.includes(name);
  }
  function is_privileged() { return has_role(CONFIG.privilegedRole); }
  function in_restricted_group() { return get_roles().some(r => CONFIG.restrictedRoles.includes(r)); }
  function is_super() { return has_role(CONFIG.superRole); }
  function restricted_active() { return in_restricted_group() && !is_privileged(); }

  function on_form_route() {
    const rt = (window.frappe && frappe.get_route && frappe.get_route()) || [];
    if (rt[0] === "Form") return true;
    const dr = (document.body && document.body.getAttribute("data-route")) || "";
    return /^Form\//i.test(dr);
  }

  // ---- основное применение ----
  function apply() {
    if (!on_form_route()) return;
    if (is_privileged()) { log("privileged → noop"); return; }

    // Tabs: Connections / Settings
    if (restricted_active()) {
      document.querySelectorAll(".form-tabs .nav-link, .form-tabs button").forEach(btn => {
        const t = norm(btn.textContent || btn.getAttribute("aria-label"));
        if (CONFIG.targetTabNames.includes(t)) {
          const li = btn.closest(".nav-item") || btn;
          li.style.display = "none";
          li.setAttribute("aria-hidden", "true");
        }
      });
      document.querySelectorAll('.tab-content [role="tabpanel"]').forEach(pane => {
        const label = (pane.getAttribute("aria-labelledby") || "").toLowerCase();
        const controls = (pane.getAttribute("aria-controls") || "").toLowerCase();
        const id = (pane.id || "").toLowerCase();
        if (CONFIG.targetTabNames.some(x => label.includes(x) || controls.includes(x) || id.includes(x + "_tab") || id.endsWith(x))) {
          pane.style.display = "none";
          pane.setAttribute("aria-hidden", "true");
        }
      });

      // Common blocks
      [".form-shared", ".form-sidebar-stats", ".form-sidebar .form-follow"]
        .forEach(sel => document.querySelectorAll(sel).forEach(el => {
          el.style.display = "none";
          el.setAttribute("aria-hidden", "true");
        }));

      // Timeline / comments
      const assign = document.querySelector('.form-assignments');
      const meta = document.querySelector('ul.list-unstyled.sidebar-menu.text-muted');
      const timeline   = document.querySelector(".new-timeline");
      const commentBox = document.querySelector(".form-footer .comment-box");
      const commentBtn = document.querySelector(".form-footer .btn-comment");
      if (is_super()) {
        [assign, meta, timeline, commentBox, commentBtn].forEach(el => { if (!el) return; el.style.display = ""; el.removeAttribute("aria-hidden"); });
        // раскрываем боковую панель если надо
        let p = meta && meta.parentElement;
        while (p && p !== document.documentElement) {
          if (p.matches(".form-sidebar, .overlay-sidebar, .layout-side-section, .layout-side-section-wrapper")) {
            p.style.display = "";
            p.removeAttribute("aria-hidden");
          }
          p = p && p.parentElement;
        }
      } else {
        [meta, timeline, commentBox, commentBtn].forEach(el => { if (!el) return; el.style.display = "none"; el.setAttribute("aria-hidden","true"); });
      }

      // Убрать "New Email" из действий таймлайна
      document.querySelectorAll(".timeline-content .action-buttons .action-btn, .new-timeline .action-buttons .action-btn")
        .forEach(btn => { if (norm(btn.textContent || btn.getAttribute("aria-label")).includes("new email")) btn.style.display = "none"; });

      log("applied (restricted)");
    } else {
      log("not restricted → noop");
    }
  }

  // ---- ждём пока появятся роли (frappe.boot) ----
  function wait_roles_and_apply(maxMs = 4000) {
    const start = Date.now();
    (function tick(){
      const rs = get_roles();
      if (rs.length) { log("roles:", rs); apply(); return; }
      if (Date.now() - start > maxMs) { log("roles timeout, applying anyway"); apply(); return; }
      setTimeout(tick, 80);
    })();
  }

  // ---- наблюдатель (легкий) ----
  function observe() {
    try {
      new MutationObserver(() => { if (on_form_route()) apply(); })
        .observe(document.body || document.documentElement, { childList: true, subtree: true });
    } catch (_) {}
    if (window.frappe && frappe.router && typeof frappe.router.on === "function") {
      frappe.router.on("change", () => { if (on_form_route()) apply(); });
    }
  }

  // ---- boot ----
  function boot() {
    wait_roles_and_apply();
    observe();
  }

  if (window.frappe && frappe.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);

  // ручная проверка в консоли:
  window.__rbac_debug = () => ({ roles: get_roles(), restricted: restricted_active(), privileged: is_privileged(), super: is_super() });
})();
