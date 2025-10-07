/* ========================================================================
   Global Form Cleanup (role-based, applies to all Form/*)
   — Tabs: hide "Connections" & "Settings" (headers + panes) for restricted
   — Common blocks (ALL restricted, incl. super): hide
       · .form-assignments, .form-shared, .form-sidebar-stats, .form-follow
   — Timeline / Comments / Meta UL:
       · superRole: show (with parents unhidden)
       · other restricted: hide
   — Timeline actions: hide "New Email" for ALL restricted (incl. super)
   — Privileged role (System Manager) is untouched
   — Robust: route guard + debounced MutationObserver (no heavy loops)
   ======================================================================== */
(function () {
  // ===== CONFIG (переименуй роли под другой проект) =====
  const CONFIG = {
    privilegedRole: "System Manager",
    restrictedRoles: [
      "AIHub Super Admin", "AIHub Admin", "AIHub Demo",
      "AIHub User", "AIHub Manager", "AIHub Doctor",
      "AIHub Assistant", "Super Admin"
    ],
    superRole: "AIHub Super Admin",

    // ids для style
    cssInstantId: "rbac-form-INSTANT-css",
    cssTabsId: "rbac-form-tabs-css",

    // заголовки вкладок, которые скрываем (нижний регистр)
    targetTabNames: ["connections", "settings"],
  };

  // ===== ROLE HELPERS =====
  function roles() { return (window.frappe?.boot?.user?.roles) || []; }
  function is_privileged() {
    const rs = roles();
    if (window.frappe?.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.privilegedRole); } catch {} }
    return rs.includes(CONFIG.privilegedRole);
  }
  function in_restricted_group() { return roles().some(r => CONFIG.restrictedRoles.includes(r)); }
  function is_super() { return roles().includes(CONFIG.superRole); }
  function restricted_active() { return in_restricted_group() && !is_privileged(); }

  // ===== ROUTE GUARD (любой Form/*) =====
  function on_any_form_route() {
    const rt = (window.frappe?.get_route && frappe.get_route()) || [];
    if (rt[0] === "Form") return true;
    const dr = document.body?.getAttribute("data-route") || "";
    return /^Form\//i.test(dr);
  }

  // ===== CSS HELPERS =====
  function add_css_once(id, css) {
    if (document.getElementById(id)) return;
    const s = document.createElement("style");
    s.id = id;
    s.textContent = css;
    document.documentElement.appendChild(s);
  }
  function remove_css(id) { const s = document.getElementById(id); if (s) s.remove(); }

  // ===== INSTANT CSS (анти-фликер для общих скрытий + табов) =====
  // Вешаем очень рано: мигания нет, SM потом всё «вернём» JS'ом, если нужно.
  (function inject_instant_css() {
    const INSTANT = `
      /* Common hides for ALL restricted (примут эффект, пока JS не разрулит роль) */
      body[data-route^="Form/"] .form-assignments,
      body[data-route^="Form/"] .form-shared,
      body[data-route^="Form/"] .form-sidebar-stats,
      body[data-route^="Form/"] .form-sidebar .form-follow { display: none !important; }

      /* Tabs anti-flicker: базовые селекторы по id/attrs */
      .form-tabs .nav-link[id$="connections_tab-tab"],
      .form-tabs .nav-link[aria-controls*="connections" i],
      .form-tabs .nav-link[id$="settings_tab-tab"],
      .form-tabs .nav-link[aria-controls*="settings" i] { display: none !important; }

      .tab-content [id$="connections_tab"],
      .tab-content [data-fieldname="connections_tab"],
      .tab-content [id$="settings_tab"],
      .tab-content [data-fieldname="settings_tab"] { display: none !important; }
    `;
    add_css_once(CONFIG.cssInstantId, INSTANT);
  })();

  // ===== SMALL DOM HELPERS =====
  const hide = el => { if (!el) return; el.style.display = "none"; el.setAttribute("aria-hidden","true"); };
  const show_imp = (el, display="block") => {
    if (!el) return;
    el.style.setProperty("display", display, "important");
    el.style.setProperty("visibility", "visible", "important");
    el.style.setProperty("opacity", "1", "important");
    el.removeAttribute("aria-hidden");
    el.classList.remove("hidden","hide");
  };
  const norm = s => (s || "").replace(/\s+/g, " ").trim().toLowerCase();

  // ===== CORE: APPLY ONCE =====
  function apply_once() {
    if (!on_any_form_route()) return;

    // 1) Привилегированные — ничего не скрываем, максимально «распускаем»
    if (!restricted_active()) {
      // вернуть видимость общих блоков (чтобы отменить anti-flicker)
      [
        ".form-assignments",
        ".form-shared",
        ".form-sidebar-stats",
        ".form-sidebar .form-follow"
      ].forEach(sel => document.querySelectorAll(sel).forEach(el => {
        el.style.removeProperty("display");
        el.removeAttribute("aria-hidden");
        el.classList.remove("hidden","hide");
      }));

      // вернуть вкладки, если анти-фликер задел не-restricted контекст
      document.querySelectorAll(".form-tabs .nav-link, .form-tabs button").forEach(btn => {
        const t = norm(btn.textContent || btn.getAttribute("aria-label"));
        if (CONFIG.targetTabNames.includes(t)) {
          const li = btn.closest(".nav-item") || btn;
          li.style.removeProperty("display");
          li.removeAttribute("aria-hidden");
        }
      });
      document.querySelectorAll('.tab-content [role="tabpanel"]').forEach(pane => {
        const label = (pane.getAttribute("aria-labelledby") || "").toLowerCase();
        const controls = (pane.getAttribute("aria-controls") || "").toLowerCase();
        const id = (pane.id || "").toLowerCase();
        if (CONFIG.targetTabNames.some(x => label.includes(x) || controls.includes(x) || id.includes(x + "_tab") || id.endsWith(x))) {
          pane.style.removeProperty("display");
          pane.removeAttribute("aria-hidden");
        }
      });
      return;
    }

    // 2) Restricted — Tabs: скрыть по тексту/aria надёжно
    document.querySelectorAll(".form-tabs .nav-link, .form-tabs button").forEach(btn => {
      const t = norm(btn.textContent || btn.getAttribute("aria-label"));
      if (CONFIG.targetTabNames.includes(t)) hide(btn.closest(".nav-item") || btn);
    });
    document.querySelectorAll('.tab-content [role="tabpanel"]').forEach(pane => {
      const label = (pane.getAttribute("aria-labelledby") || "").toLowerCase();
      const controls = (pane.getAttribute("aria-controls") || "").toLowerCase();
      const id = (pane.id || "").toLowerCase();
      if (CONFIG.targetTabNames.some(x => label.includes(x) || controls.includes(x) || id.includes(x + "_tab") || id.endsWith(x))) {
        hide(pane);
      }
    });

    // 3) Common hides для всех restricted (в т.ч. super) — уже спрятаны CSS'ом; JS не нужен

    // 4) Timeline / Comments / Meta:
    const meta = document.querySelector('ul.list-unstyled.sidebar-menu.text-muted');
    const timeline   = document.querySelector(".new-timeline");
    const commentBox = document.querySelector(".form-footer .comment-box");
    const commentBtn = document.querySelector(".form-footer .btn-comment");
    const side = document.querySelector(".form-sidebar, .layout-side-section, .overlay-sidebar");
    const hrBeforeMeta = meta ? meta.previousElementSibling : null;

    if (is_super()) {
      show_imp(meta, "block");
      if (meta) {
        let p = meta.parentElement;
        while (p && p !== document.documentElement) {
          if (p.matches(".form-sidebar, .overlay-sidebar, .layout-side-section, .layout-side-section-wrapper")) {
            show_imp(p, "block");
          }
          p = p.parentElement;
        }
      }
      show_imp(timeline, "block");
      show_imp(commentBox, "block");
      show_imp(commentBtn, "inline-block");
      if (hrBeforeMeta && hrBeforeMeta.tagName === "HR") show_imp(hrBeforeMeta, "block");
      if (side) show_imp(side, "block");
    } else {
      hide(meta); hide(timeline); hide(commentBox); hide(commentBtn);
    }

    // 5) Timeline actions — спрятать "New Email" для всех restricted (включая super)
    document.querySelectorAll(".timeline-content .action-buttons .action-btn, .new-timeline .action-buttons .action-btn")
      .forEach(btn => { if (norm(btn.textContent || btn.getAttribute("aria-label")).includes("new email")) hide(btn); });
  }

  // ===== DEBOUNCED APPLY =====
  let scheduled = false;
  function schedule_apply() {
    if (scheduled) return;
    scheduled = true;
    setTimeout(() => { scheduled = false; apply_once(); }, 60); // лёгкий debounce
  }

  // ===== OBSERVER (лёгкий) =====
  function observe_dom() {
    try {
      new MutationObserver(() => { if (on_any_form_route()) schedule_apply(); })
        .observe(document.body || document.documentElement, { childList: true, subtree: true });
    } catch (_) {}
  }

  // ===== ROUTER HOOK =====
  function hook_router() {
    if (window.frappe?.router?.on) frappe.router.on("change", () => { if (on_any_form_route()) schedule_apply(); });
  }

  // ===== BOOT =====
  function boot() {
    apply_once();
    observe_dom();
    hook_router();
  }
  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
