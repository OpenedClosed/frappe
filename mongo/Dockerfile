FROM mongo:latest

# COPY mongo-init.js /docker-entrypoint-initdb.d/mongo-init.js

CMD ["/usr/bin/mongod", "--replSet", "rs0", "--bind_ip_all"]