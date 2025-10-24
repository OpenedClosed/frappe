# Базовый образ MariaDB
FROM mariadb:10.6

# Тюнинги для Frappe
COPY my.cnf /etc/mysql/conf.d/frappe.cnf

COPY init-db.sh       /docker-entrypoint-initdb.d/init-db.sh
RUN chmod +x /docker-entrypoint-initdb.d/init-db.sh
