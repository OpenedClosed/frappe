/* ===== AIHub Toolbar User Menu Hide (same style) ===== */
(function () {
  const CONFIG = {
    systemManagerRole: "System Manager",
    aihubRoles: ["AIHub Super Admin", "AIHub Admin", "AIHub Demo"],
    lsKey: "aihub_hide_toolbar_user_menu",
    // разрешённые ярлыки (нормализуем к lower-case)
    allowedLabels: ["my profile", "my settings", "toggle theme", "log out"]
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

  const norm = t => (t || "").replace(/\s+/g, " ").trim().toLowerCase();

  function isAllowedEl(el) {
    // 1) по тексту
    const label = norm(el.textContent);
    if (CONFIG.allowedLabels.includes(label)) return true;

    // 2) по атрибутам (fallback)
    const href = el.getAttribute?.("href") || "";
    const oc  = el.getAttribute?.("onclick") || "";

    if (href === "/app/user-profile") return true; // My Profile
    if (/frappe\.ui\.toolbar\.route_to_user\(\)/.test(oc)) return true; // My Settings
    if (/new\s+frappe\.ui\.ThemeSwitcher\(\)\.show\(\)/.test(oc)) return true; // Toggle Theme
    if (/frappe\.app\.logout\(\)/.test(oc)) return true; // Log out

    return false;
  }

  function cleanDividers(menu) {
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

  function filterToolbarUserMenu() {
    if (!shouldFilter()) return;
    const menu = document.getElementById("toolbar-user");
    if (!menu || !menu.classList.contains("dropdown-menu")) return;

    // вернём базовую видимость на всякий
    menu.querySelectorAll(".dropdown-item, .btn-reset.dropdown-item").forEach(i => {
      i.style.removeProperty("visibility");
    });

    menu.querySelectorAll(".dropdown-item, .btn-reset.dropdown-item").forEach(el => {
      if (isAllowedEl(el)) {
        el.style.removeProperty("display");
        el.removeAttribute("aria-hidden");
      } else {
        el.style.display = "none";
        el.setAttribute("aria-hidden", "true");
      }
    });

    cleanDividers(menu);
  }

  // Пытаемся несколько раз после клика на аватар (когда меню открывают)
  function armOpenHook() {
    // слушаем любые клики по тулбару
    document.addEventListener("click", (e) => {
      // через тик/два меню уже в DOM и с классом .show
      let tries = 0;
      const t = setInterval(() => {
        tries++;
        filterToolbarUserMenu();
        const menu = document.getElementById("toolbar-user");
        if (tries > 10 || (menu && menu.classList.contains("show"))) clearInterval(t);
      }, 30);
    }, true);
  }

  function observe() {
    new MutationObserver(() => filterToolbarUserMenu())
      .observe(document.body || document.documentElement, { childList:true, subtree:true, attributes:true, attributeFilter:["class"] });
  }
  function hookRouter(){ if (frappe.router?.on) frappe.router.on("change", filterToolbarUserMenu); }

  function boot() {
    const need = shouldFilter();
    try { localStorage.setItem(CONFIG.lsKey, need ? "1" : "0"); } catch {}
    if (need) { armOpenHook(); observe(); hookRouter(); }
  }

  if (window.frappe?.after_ajax) frappe.after_ajax(boot);
  else document.addEventListener("DOMContentLoaded", boot);
})();
