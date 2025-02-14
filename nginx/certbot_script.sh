cp /app/nginx.prod.conf /etc/nginx/nginx.conf
envsubst < /app/nginx.prod.conf > /etc/nginx/conf.d/default.conf


nginx -g 'daemon on;'


if [ ! -d "/etc/letsencrypt/live/$HOST/" ]; then
    echo "Сертификаты не найдены, запускаем Certbot для получения сертификатов..."
    certbot certonly --nginx --email $CERTBOT_EMAIL --agree-tos -d $HOST
else
    echo "Сертификаты найдены, проверяем необходимость обновления..."
    certbot renew
fi

nginx -s stop

nginx -g 'daemon off;'