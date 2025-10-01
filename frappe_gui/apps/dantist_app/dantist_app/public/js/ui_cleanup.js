// Безопасная подчистка DOM: скрытие пунктов меню, «лупы», активностей и т.п.
(() => {
  const HIDDEN_CLASS = 'hidden-by-dantist';

  const ALWAYS_HIDE = [
    // Меню пользователя
    '#toolbar-user button[onclick*="setup_session_defaults"]',
    '#toolbar-user button[onclick*="view_website"]',
    '#toolbar-user a[href="/apps"]',

    // Профиль: активность/графики/соц
    '.user-stats-detail',
    '.user-stats',
    '.performance-graphs',
    '.heatmap-container',
    '.percentage-chart-container',
    '.line-chart-container',
    '.recent-activity',
    '.new-timeline',
    '.timeline',
    '.dashboard-graph',
    '.activity-graph',
    '.user-activity',
    '.form-sidebar .form-sidebar-stats',
    '.form-sidebar .followed-by-section',
    '.form-sidebar .document-follow',
    '.form-sidebar .form-shared',
  ];

  const USERS_ONLY_HIDE = [
    // «Change User» — показываем только System Manager/Administrator
    'button[data-label="Change User"]',
    'button[data-label="Change%20User"]',
    'button:has(use[href="#icon-change"])',

    // Левая панель списка: фильтры и теги
    '.layout-side-section .list-sidebar .views-section',
    '.layout-side-section .list-sidebar .filter-section',
    '.layout-side-section .list-sidebar .list-tags',
    '.layout-side-section .list-sidebar .save-filter-section',
    'button.filter-button',
    'button.filter-x-button',

    // Поиск в навбаре: лупа/иконки
    '#navbar-search',
  ];

  // Доп. селекторы для профиля (жёстче, чтобы в Firefox не «проскакивало»)
  const PROFILE_EXTRA = [
    '.user-profile-sidebar .user-image-container',
    '.user-profile-sidebar .detail-item.user-stats-detail',
    '.profile-details .detail-item .user-stats',
    '.profile-details .detail-item .dashboard-graph',
    '.profile-details .detail-item .activity-graph',
    '.profile-details .detail-item .recent-activity',
    '.user-profile-sidebar .heatmap-container',
    '.user-profile-sidebar .performance-graphs',
    '.user-profile-sidebar .percentage-chart-container',
    '.user-profile-sidebar .line-chart-container',
    '.profile-links .leaderboard-link',
  ];

  function hide_nodes(selectors) {
    selectors.forEach((sel) => {
      document.querySelectorAll(sel).forEach((el) => {
        el.classList.add(HIDDEN_CLASS);
        el.setAttribute('aria-hidden', 'true');
      });
    });
  }

  function cleanup_once() {
    hide_nodes(ALWAYS_HIDE);
    hide_nodes(PROFILE_EXTRA);

    const html = document.documentElement;
    const is_user = html.classList.contains('is-user');
    const is_admin = html.classList.contains('is-admin');

    if (is_user) hide_nodes(USERS_ONLY_HIDE);

    // «Change User» — вернуть для админа
    if (is_admin) {
      document.querySelectorAll('button[data-label="Change User"], button[data-label="Change%20User"]').forEach((el) => {
        el.classList.remove(HIDDEN_CLASS);
        el.removeAttribute('aria-hidden');
      });
    }
  }

  // Повторяем мягко, чтобы накрыть поздние рендеры
  let scheduled = false;
  function schedule_cleanup() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      cleanup_once();
      setTimeout(cleanup_once, 50);
      setTimeout(cleanup_once, 250);
      setTimeout(cleanup_once, 700);
    });
  }

  const boot = () => schedule_cleanup();

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();

  frappe?.router?.on?.('change', () => schedule_cleanup());
  frappe?.after_ajax && frappe.after_ajax(() => schedule_cleanup());

  // На всякий: если меню открыли уже после навешивания
  document.addEventListener('click', (e) => {
    const within_toolbar = e.target.closest?.('#toolbar-user');
    const opened_menu = document.querySelector('#toolbar-user.show');
    if (within_toolbar || opened_menu) schedule_cleanup();
  });

  window.dantist_ui_cleanup = boot;
})();
