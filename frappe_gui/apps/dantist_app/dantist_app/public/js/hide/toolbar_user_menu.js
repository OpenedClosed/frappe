/* ========================================================================
   Toolbar User Menu Whitelist (role-based)
   — Leaves only: My Profile, My Settings, Toggle Theme, Log out
   — Privileged role is always untouched
   — Scoped strictly to #toolbar-user menu
   ======================================================================== */
(function () {
  // ===== CONFIG (rename for other projects) =====
  const CONFIG = {
    privilegedRole: "System Manager",
    restrictedRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    lsKey: "rbac_hide_toolbar_user_menu",

    // allowed labels (normalized to lower-case)
    allowedLabels: ["my profile", "my settings", "toggle theme", "log out"]
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

  // ===== MENU FILTER =====
  const norm = t => (t || "").replace(/\s+/g, " ").trim().toLowerCase();

  function is_allowed_el(el) {
    // 1) by text
    const label = norm(el.textContent);
    if (CONFIG.allowedLabels.includes(label)) return true;

    // 2) by attributes (fallback for different locales/templates)
    const href = el.getAttribute?.("href") || "";
    const oc  = el.getAttribute?.("onclick") || "";
    if (href === "/app/user-profile") return true;                     // My Profile
    if (/frappe\.ui\.toolbar\.route_to_user\(\)/.test(oc)) return true; // My Settings
    if (/new\s+frappe\.ui\.ThemeSwitcher\(\)\.show\(\)/.test(oc)) return true; // Toggle Theme
    if (/frappe\.app\.logout\(\)/.test(oc)) return true;               // Log out

    return false;
  }

  function clean_dividers(menu) {
    const items = Array.from(menu.children);
    // leading/trailing
    while (items[0] && items[0].classList.contains("dropdown-divider")) { items[0].style.display = "none"; items.shift(); }
    while (items[items.length-1] && items[items.length-1].classList.contains("dropdown-divider")) { items[items.length-1].style.display = "none"; items.pop(); }
    // doubles
    for (let i=1;i<items.length;i++){
      if (items[i].classList.contains("dropdown-divider") && items[i-1].classList.contains("dropdown-divider")) {
        items[i].style.display = "none";
      }
    }
  }

  function filter_toolbar_user_menu() {
    if (!should_filter()) return;
    const menu = document.getElementById("toolbar-user");
    if (!menu || !menu.classList.contains("dropdown-menu")) return;

    menu.querySelectorAll(".dropdown-item, .btn-reset.dropdown-item").forEach(el => {
      if (is_allowed_el(el)) {
        el.style.removeProperty("display");
        el.removeAttribute("aria-hidden");
      } else {
        el.style.display = "none";
        el.setAttribute("aria-hidden", "true");
      }
    });

    clean_dividers(menu);
  }

  // try multiple times right after opening the dropdown
  function arm_open_hook() {
    document.addEventListener("click", () => {
      let tries = 0;
      const t = setInterval(() => {
        tries++;
        filter_toolbar_user_menu();
        const menu = document.getElementById("toolbar-user");
        if (tries > 10 || (menu && menu.classList.contains("show"))) clearInterval(t);
      }, 30);
    }, true);
  }

  function observe() {
    try {
      new MutationObserver(() => filter_toolbar_user_menu())
        .observe(document.body || document.documentElement, {
          childList:true, subtree:true, attributes:true, attributeFilter:["class"]
        });
    } catch (_) {}
  }
  function hook_router(){ if (window.frappe?.router?.on) frappe.router.on("change", filter_toolbar_user_menu); }

  // ===== BOOT =====
  function boot() {
    const need = should_filter();
    try { localStorage.setItem(CONFIG.lsKey, need ? "1" : "0"); } catch {}
    if (need) { arm_open_hook(); observe(); hook_router(); }
  }
  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
