/* ===== AIHub Toolbar Notifications Hide (same style as others) ===== */
(function () {
  const CONFIG = {
    systemManagerRole: "System Manager",
    aihubRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    lsKey: "aihub_hide_toolbar_notifications"
  };

  /* ===== Role checks ===== */
  function roles() { return (frappe?.boot?.user?.roles) || []; }
  function isSystemManager() {
    const r = roles();
    if (frappe.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.systemManagerRole); } catch {} }
    return r.includes(CONFIG.systemManagerRole);
  }
  function hasAIHubRole() { return roles().some(r => CONFIG.aihubRoles.includes(r)); }
  function shouldFilter() { return hasAIHubRole() && !isSystemManager(); }

  /* ===== Helpers ===== */
  function hide(el){ if (!el) return; el.style.display="none"; el.setAttribute("aria-hidden","true"); }
  function show(el){ if (!el) return; el.style.removeProperty("display"); el.removeAttribute("aria-hidden"); el.classList.remove("hidden","hide"); }
  const q = (root, sel) => root.querySelector(sel);
  const qa = (root, sel) => Array.from(root.querySelectorAll(sel));

  function filterOneMenu(menu) {
    if (!menu || !shouldFilter()) return;

    // Убрать "Notification Settings" (шестерёнка)
    qa(menu, '.notification-settings[data-action="go_to_settings"]').forEach(hide);

    // Tabs header
    const tabsUl = q(menu, ".notification-item-tabs");
    if (tabsUl) {
      // оставить только li#notifications
      qa(tabsUl, "li.notifications-category").forEach(li => {
        const id = li.id || "";
        if (id === "notifications") {
          show(li);
          li.classList.add("active");
        } else {
          hide(li);
          li.classList.remove("active");
        }
      });
    }

    // Panels body
    const panelNotifications = q(menu, ".panel-notifications");
    const panelEvents        = q(menu, ".panel-events");
    const panelChangelog     = q(menu, ".panel-changelog-feed");

    show(panelNotifications);
    hide(panelEvents);
    hide(panelChangelog);

    // На всякий — скрыть любые body-блоки, которые не notifications
    qa(menu, ".notification-list-body > div").forEach(div => {
      const cls = div.className || "";
      if (/\bpanel-notifications\b/.test(cls)) show(div);
      else hide(div);
    });
  }

  function scanAll() {
    if (!shouldFilter()) return;
    document
      .querySelectorAll(".dropdown-menu.notifications-list")
      .forEach(filterOneMenu);
  }

  // подстраховка на момент открытия выпадашки (дорисовка DOM)
  function armOpenHook() {
    document.addEventListener("click", () => {
      if (!shouldFilter()) return;
      let tries = 0;
      const t = setInterval(() => {
        tries++;
        scanAll();
        if (tries > 10) clearInterval(t);
      }, 30);
    }, true);
  }

  function observe() {
    new MutationObserver(muts => {
      for (const m of muts) {
        (m.addedNodes || []).forEach(n => {
          if (n.nodeType !== 1) return;
          if (n.matches?.(".dropdown-menu.notifications-list") || n.querySelector?.(".dropdown-menu.notifications-list")) {
            filterOneMenu(n.matches?.(".dropdown-menu.notifications-list") ? n : n.querySelector(".dropdown-menu.notifications-list"));
          }
        });
        if (m.type === "attributes" && m.target?.matches?.(".dropdown-menu.notifications-list")) {
          filterOneMenu(m.target);
        }
      }
    }).observe(document.body || document.documentElement, {
      childList:true, subtree:true, attributes:true, attributeFilter:["class","style"]
    });
  }

  function hookRouter(){ if (frappe.router?.on) frappe.router.on("change", scanAll); }

  /* ===== Boot ===== */
  function boot() {
    const need = shouldFilter();
    try { localStorage.setItem(CONFIG.lsKey, need ? "1" : "0"); } catch {}
    if (need) { scanAll(); armOpenHook(); observe(); hookRouter(); }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
