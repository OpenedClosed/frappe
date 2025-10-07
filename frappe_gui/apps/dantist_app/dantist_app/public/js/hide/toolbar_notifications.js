/* ========================================================================
   Toolbar Notifications Cleanup (role-based)
   — Leaves only the "Notifications" tab
   — Hides Events, What's New, and the "settings" gear
   — Privileged role is always untouched
   ======================================================================== */
(function () {
  // ===== CONFIG (rename for other projects) =====
  const CONFIG = {
    privilegedRole: "System Manager",
    restrictedRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    lsKey: "rbac_hide_toolbar_notifications"
  };

  // ===== ROLE HELPERS =====
  function roles() { return (window.frappe?.boot?.user?.roles) || []; }
  function is_privileged() {
    const r = roles();
    if (window.frappe?.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.privilegedRole); } catch {} }
    return r.includes(CONFIG.privilegedRole);
  }
  function in_restricted_group() { return roles().some(r => CONFIG.restrictedRoles.includes(r)); }
  function should_filter() { return in_restricted_group() && !is_privileged(); }

  // ===== HELPERS =====
  function hide(el){ if (!el) return; el.style.display="none"; el.setAttribute("aria-hidden","true"); }
  function show(el){ if (!el) return; el.style.removeProperty("display"); el.removeAttribute("aria-hidden"); el.classList.remove("hidden","hide"); }
  const q = (root, sel) => root.querySelector(sel);
  const qa = (root, sel) => Array.from(root.querySelectorAll(sel));

  function filter_one_menu(menu) {
    if (!menu || !should_filter()) return;

    // remove "Notification Settings" (gear)
    qa(menu, '.notification-settings[data-action="go_to_settings"]').forEach(hide);

    // Tabs header: keep only the Notifications tab
    const tabsUl = q(menu, ".notification-item-tabs");
    if (tabsUl) {
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

    // extra safety: show only the notifications body
    qa(menu, ".notification-list-body > div").forEach(div => {
      const cls = div.className || "";
      if (/\bpanel-notifications\b/.test(cls)) show(div); else hide(div);
    });
  }

  function scan_all() {
    if (!should_filter()) return;
    document.querySelectorAll(".dropdown-menu.notifications-list").forEach(filter_one_menu);
  }

  // try multiple times right after opening the dropdown (DOM renders in waves)
  function arm_open_hook() {
    document.addEventListener("click", () => {
      if (!should_filter()) return;
      let tries = 0;
      const t = setInterval(() => {
        tries++;
        scan_all();
        if (tries > 10) clearInterval(t);
      }, 30);
    }, true);
  }

  function observe() {
    try {
      new MutationObserver(muts => {
        for (const m of muts) {
          (m.addedNodes || []).forEach(n => {
            if (n.nodeType !== 1) return;
            if (n.matches?.(".dropdown-menu.notifications-list")) {
              filter_one_menu(n);
            } else if (n.querySelector?.(".dropdown-menu.notifications-list")) {
              filter_one_menu(n.querySelector(".dropdown-menu.notifications-list"));
            }
          });
          if (m.type === "attributes" && m.target?.matches?.(".dropdown-menu.notifications-list")) {
            filter_one_menu(m.target);
          }
        }
      }).observe(document.body || document.documentElement, {
        childList:true, subtree:true, attributes:true, attributeFilter:["class","style"]
      });
    } catch (_) {}
  }

  function hook_router(){ if (window.frappe?.router?.on) frappe.router.on("change", scan_all); }

  // ===== BOOT =====
  function boot() {
    const need = should_filter();
    try { localStorage.setItem(CONFIG.lsKey, need ? "1" : "0"); } catch {}
    if (need) { scan_all(); arm_open_hook(); observe(); hook_router(); }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
