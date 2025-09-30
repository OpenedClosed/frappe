#!/bin/sh

echo "HOST is: $HOST"
echo "CERTBOT_EMAIL is: $CERTBOT_EMAIL"

echo "Substituting env vars into Nginx config..."
envsubst '$HOST' < /app/nginx.prod.conf > /etc/nginx/nginx.conf


echo "Check final config:"
# cat /etc/nginx/conf.d/default.conf
cat /etc/nginx/nginx.conf

echo "Starting Nginx in background..."
nginx -g 'daemon on;'  # или nginx &

if [ ! -d "/etc/letsencrypt/live/$HOST/" ]; then
    echo "Certs not found, requesting from Certbot..."
    certbot certonly --nginx --email "$CERTBOT_EMAIL" --agree-tos -d "$HOST"
else
    echo "Certs found, try to renew..."
    certbot renew
fi

echo "Stopping Nginx background instance..."
nginx -s stop

echo "Starting Nginx in foreground..."
exec nginx -g 'daemon off;'
