# Базовый образ MariaDB
FROM mariadb:10.6

# Тюнинги для Frappe/MariaDB
COPY my.cnf /etc/mysql/conf.d/frappe.cnf

# Скрипт первичной инициализации (однократно на пустом volume)
COPY init-db.sh /docker-entrypoint-initdb.d/10-init-remote-root.sh
RUN chmod +x /docker-entrypoint-initdb.d/10-init-remote-root.sh