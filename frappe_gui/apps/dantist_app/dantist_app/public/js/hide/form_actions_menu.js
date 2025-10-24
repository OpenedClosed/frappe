/* ========================================================================
   Form Actions Menu Trim (blacklist, scoped, role-based)
   — Keeps only: Delete / Undo / Redo / any "New …"
   — Removes noisy items (print/email/duplicate/... + submenu patterns)
   — Scoped strictly to real form action menus; doesn't touch navbar/notifications
   — Privileged role is always untouched
   ======================================================================== */
(function () {
  // ===== CONFIG (rename for other projects) =====
  const CONFIG = {
    privilegedRole: "System Manager",
    restrictedRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    lsKey: "rbac_hide_form_actions_menu",

    // keep rules
    keepExact: ["delete", "undo", "redo"],
    keepPrefix: ["new"],                 // e.g., "New", "New User", ...
    keepShortcuts: ["⇧+⌘+D","⌘+Z","⌘+Y"],

    // remove rules (exact)
    removeExact: [
      "print",
      "email",
      "jump to field",
      "links",
      "duplicate",
      "copy to clipboard",
      "rename",
      "reload",
      "remind me",
      "customize",
      "edit doctype"
    ],
    // remove rules (contains)
    removeContains: [
      "permissions >",     // "Permissions > Set User Permissions", …
      "password >",        // "Password > Reset Password"
      "create user email"
    ],
    // remove by shortcuts (if any)
    removeShortcuts: ["⌘+E","⌘+J"],

    // scope: only these containers are treated as "form actions" context
    formMenuContainers: [".page-actions", ".form-actions"],
    // exclusions: never touch menus inside these
    excludeContexts: [".navbar", ".notifications-list", "#toolbar-user"]
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

  // ===== UTILS =====
  const norm = t => (t || "").replace(/\s+/g, " ").trim().toLowerCase();

  function get_item_label(li) {
    const lbl = li.querySelector(".menu-item-label");
    const data = lbl?.getAttribute("data-label") || "";
    if (data) { try { return norm(decodeURIComponent(data)); } catch { return norm(data); } }
    const txt = lbl ? lbl.textContent : li.textContent;
    return norm(txt);
  }

  function has_shortcut(li, list) {
    const keys = Array.from(li.querySelectorAll("kbd, kbd span")).map(k => (k.textContent || "").trim());
    return keys.some(k => list.includes(k));
  }

  function is_form_actions_menu(ul) {
    if (!ul || !ul.matches("ul.dropdown-menu")) return false;
    for (const sel of CONFIG.excludeContexts) if (ul.closest(sel)) return false;
    for (const sel of CONFIG.formMenuContainers) if (ul.closest(sel)) return true;
    // extra heuristic: most action menus contain .menu-item-label
    if (ul.querySelector(".menu-item-label")) return true;
    return false;
  }

  function is_kept(li) {
    if (li.classList.contains("dropdown-divider")) return true;
    const t = get_item_label(li);
    if (!t) return false;
    if (CONFIG.keepExact.includes(t)) return true;
    if (CONFIG.keepPrefix.some(p => t === p || t.startsWith(p + " "))) return true;
    if (has_shortcut(li, CONFIG.keepShortcuts)) return true;
    return false;
  }

  function is_removed(li) {
    if (li.classList.contains("dropdown-divider")) return false;
    const t = get_item_label(li);
    if (!t) return false;

    if (CONFIG.removeExact.includes(t)) return true;
    if (CONFIG.removeContains.some(sub => t.includes(sub))) return true;
    if (has_shortcut(li, CONFIG.removeShortcuts)) return true;

    return false;
  }

  function clean_dividers(ul) {
    const items = Array.from(ul.children).filter(li => li.style.display !== "none");
    for (let i = 0; i < items.length; i++) {
      if (!items[i].classList.contains("dropdown-divider")) continue;
      const prev = items[i - 1], next = items[i + 1];
      if (!prev || !next || prev.classList.contains("dropdown-divider") || next.classList.contains("dropdown-divider")) {
        items[i].style.display = "none";
        items[i].setAttribute("aria-hidden", "true");
      }
    }
  }

  function trim_one_menu(ul) {
    if (!should_filter() || !is_form_actions_menu(ul)) return;

    Array.from(ul.children).forEach(li => {
      if (is_kept(li)) {
        li.style.removeProperty("display");
        li.removeAttribute("aria-hidden");
        return;
      }
      if (is_removed(li)) {
        li.style.display = "none";
        li.setAttribute("aria-hidden", "true");
      } else {
        li.style.removeProperty("display");
        li.removeAttribute("aria-hidden");
      }
    });

    clean_dividers(ul);
  }

  function scan_visible_menus() {
    if (!should_filter()) return;
    document.querySelectorAll("ul.dropdown-menu.show, ul.dropdown-menu[role='menu']").forEach(trim_one_menu);
  }

  // trigger shortly after any click (dropdowns opening)
  function hook_open() {
    document.addEventListener("click", () => {
      let tries = 0;
      const t = setInterval(() => {
        tries++;
        scan_visible_menus();
        if (tries > 10) clearInterval(t);
      }, 30);
    }, true);
  }

  function observe() {
    try {
      new MutationObserver(muts => {
        muts.forEach(m => {
          if (m.type === "childList") {
            m.addedNodes && m.addedNodes.forEach(n => {
              if (n.nodeType !== 1) return;
              if (n.matches?.("ul.dropdown-menu")) trim_one_menu(n);
              n.querySelectorAll?.("ul.dropdown-menu.show, ul.dropdown-menu[role='menu']").forEach(trim_one_menu);
            });
          } else if (m.type === "attributes" && m.target?.matches?.("ul.dropdown-menu")) {
            trim_one_menu(m.target);
          }
        });
      }).observe(document.body || document.documentElement, {
        childList: true, subtree: true, attributes: true, attributeFilter: ["class","style"]
      });
    } catch (_) {}
  }

  function hook_router(){ if (window.frappe?.router?.on) frappe.router.on("change", scan_visible_menus); }

  // ===== BOOT =====
  function boot() {
    const need = should_filter();
    try { localStorage.setItem(CONFIG.lsKey, need ? "1" : "0"); } catch {}
    if (need) { hook_open(); observe(); hook_router(); }
  }
  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
