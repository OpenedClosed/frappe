#!/bin/sh

certbot renew
nginx -s reload 