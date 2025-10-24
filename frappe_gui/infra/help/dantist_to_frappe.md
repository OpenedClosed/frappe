Проект: Dantist

Цель: развернуть и поддерживать кастомную ERPNext/Frappé-среду для приложения "Dantist". 
Основной фокус — фронтенд-часть и кастомные DocType/настройки в собственном приложении фреймворка Frappé.

Репозитории (fork-и):
- Frappé:  https://github.com/OpenedClosed/frappe  (ветка: dantist)
- ERPNext: https://github.com/OpenedClosed/erpnext (ветка: dantist)

Структура в репо:
- bench:      ./frappe_gui
- submodules: ./frappe_gui/apps/frappe, ./frappe_gui/apps/erpnext
- сайт:       dantist.localhost
- БД:         dantist_db
- моё приложение: dantist_app

Что уже сделано/правки:
- Настроены сабмодули на форки + upstream.
- Скрипт start.sh: 
  - создаёт/переустанавливает сайт,
  - автоматом добавляет DB-пользователя и под хост 'localhost' (для bootstrap), и под '%' (для TCP),
  - ставит ERPNext и dantist_app, выставляет default_site.

