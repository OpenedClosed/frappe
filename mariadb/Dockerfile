# ===== MariaDB for Frappe (no seed, no site_config copy) =====
FROM mariadb:10.6

# Тюнинг под Frappe/ERPNext
COPY my.cnf /etc/mysql/conf.d/frappe.cnf

# Разрешить root-доступ из соседних контейнеров (bench new-site будет подключаться как root)
COPY 01-remote-root.sh /docker-entrypoint-initdb.d/01-remote-root.sh
RUN chmod +x /docker-entrypoint-initdb.d/01-remote-root.sh