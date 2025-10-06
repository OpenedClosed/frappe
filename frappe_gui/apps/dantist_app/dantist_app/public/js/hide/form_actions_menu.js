/* ===== AIHub Form Actions Menu Trim (blacklist, scoped) ===== */
(function () {
  const CONFIG = {
    systemManagerRole: "System Manager",
    aihubRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    lsKey: "aihub_hide_form_actions_menu",

    // Что оставляем всегда
    keepExact: ["delete", "undo", "redo"],
    keepPrefix: ["new"],                 // "New", "New User", "New …"
    keepShortcuts: ["⇧+⌘+D","⌘+Z","⌘+Y"],

    // Что убираем (чёрный список)
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
    // подстроки (надёжно ловят "Permissions > …", "Password > Reset Password" и т.п.)
    removeContains: [
      "permissions >",     // "Permissions > Set User Permissions", …
      "password >",        // "Password > Reset Password"
      "create user email"  // может встречаться с подсветкой alt-underline
    ],
    // шорткаты, которые хотим убрать (если встретятся)
    removeShortcuts: ["⌘+E","⌘+J"],

    // жёстко ограничиваем только реальные «меню действий формы»
    formMenuContainers: [".page-actions", ".form-actions"],
    // контексты, которые никогда не трогаем
    excludeContexts: [".navbar", ".notifications-list", "#toolbar-user"]
  };

  /* ===== Roles ===== */
  function roles() { return (frappe?.boot?.user?.roles) || []; }
  function isSystemManager() {
    const r = roles();
    if (frappe.user?.has_role) { try { return !!frappe.user.has_role(CONFIG.systemManagerRole); } catch {} }
    return r.includes(CONFIG.systemManagerRole);
  }
  function hasAIHubRole() { return roles().some(r => CONFIG.aihubRoles.includes(r)); }
  function shouldFilter() { return hasAIHubRole() && !isSystemManager(); }

  /* ===== Utils ===== */
  const norm = t => (t || "").replace(/\s+/g, " ").trim().toLowerCase();

  function getItemLabel(li) {
    const lbl = li.querySelector(".menu-item-label");
    const data = lbl?.getAttribute("data-label") || "";
    if (data) { try { return norm(decodeURIComponent(data)); } catch { return norm(data); } }
    const txt = lbl ? lbl.textContent : li.textContent;
    return norm(txt);
  }

  function hasShortcut(li, list) {
    const keys = Array.from(li.querySelectorAll("kbd, kbd span")).map(k => (k.textContent || "").trim());
    return keys.some(k => list.includes(k));
  }

  function isFormActionsMenu(ul) {
    if (!ul || !ul.matches("ul.dropdown-menu")) return false;
    for (const sel of CONFIG.excludeContexts) if (ul.closest(sel)) return false;
    for (const sel of CONFIG.formMenuContainers) if (ul.closest(sel)) return true;
    // Доп. страховка: экшен-меню чаще всего содержит .menu-item-label
    if (ul.querySelector(".menu-item-label")) return true;
    return false;
  }

  function isKept(li) {
    if (li.classList.contains("dropdown-divider")) return true;
    const t = getItemLabel(li);
    if (!t) return false;
    if (CONFIG.keepExact.includes(t)) return true;
    if (CONFIG.keepPrefix.some(p => t === p || t.startsWith(p + " "))) return true;
    if (hasShortcut(li, CONFIG.keepShortcuts)) return true;
    return false;
  }

  function isRemoved(li) {
    if (li.classList.contains("dropdown-divider")) return false;
    const t = getItemLabel(li);
    if (!t) return false;

    // точные совпадения
    if (CONFIG.removeExact.includes(t)) return true;

    // подстроки/шаблоны
    if (CONFIG.removeContains.some(sub => t.includes(sub))) return true;

    // горячие клавиши
    if (hasShortcut(li, CONFIG.removeShortcuts)) return true;

    return false;
  }

  function cleanDividers(ul) {
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

  function trimOneMenu(ul) {
    if (!shouldFilter() || !isFormActionsMenu(ul)) return;

    Array.from(ul.children).forEach(li => {
      if (isKept(li)) {
        li.style.removeProperty("display");
        li.removeAttribute("aria-hidden");
        return;
      }
      if (isRemoved(li)) {
        li.style.display = "none";
        li.setAttribute("aria-hidden", "true");
      } else {
        // нейтральные пункты оставляем как есть
        li.style.removeProperty("display");
        li.removeAttribute("aria-hidden");
      }
    });

    cleanDividers(ul);
  }

  function scanVisibleMenus() {
    if (!shouldFilter()) return;
    document.querySelectorAll("ul.dropdown-menu.show, ul.dropdown-menu[role='menu']").forEach(trimOneMenu);
  }

  // Точечно срабатываем при открытии дропдауна
  function hookOpen() {
    document.addEventListener("click", () => {
      let tries = 0;
      const t = setInterval(() => {
        tries++;
        scanVisibleMenus();
        if (tries > 10) clearInterval(t);
      }, 30);
    }, true);
  }

  function observe() {
    new MutationObserver(muts => {
      muts.forEach(m => {
        if (m.type === "childList") {
          m.addedNodes && m.addedNodes.forEach(n => {
            if (n.nodeType !== 1) return;
            if (n.matches?.("ul.dropdown-menu")) trimOneMenu(n);
            n.querySelectorAll?.("ul.dropdown-menu.show, ul.dropdown-menu[role='menu']").forEach(trimOneMenu);
          });
        } else if (m.type === "attributes" && m.target?.matches?.("ul.dropdown-menu")) {
          trimOneMenu(m.target);
        }
      });
    }).observe(document.body || document.documentElement, {
      childList: true, subtree: true, attributes: true, attributeFilter: ["class","style"]
    });
  }

  function hookRouter(){ if (frappe.router?.on) frappe.router.on("change", scanVisibleMenus); }

  /* ===== Boot ===== */
  function boot() {
    const need = shouldFilter();
    try { localStorage.setItem(CONFIG.lsKey, need ? "1" : "0"); } catch {}
    if (need) { hookOpen(); observe(); hookRouter(); }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
