FROM dmgnx/nginx-naxsi

RUN mkdir -p /certbot

RUN mkdir -p /app

RUN apk update && apk add --no-cache certbot certbot-nginx

WORKDIR /app

COPY . .

RUN chmod +x ./certbot_script.sh

COPY certbot_renew.sh /etc/periodic/daily/
RUN chmod +x /etc/periodic/daily/certbot_renew.sh

COPY templates/error.html /usr/share/nginx/html/error.html

COPY naxsi_core.rules /etc/nginx/naxsi_core.rules
COPY naxsi.rules /etc/nginx/naxsi.rules





