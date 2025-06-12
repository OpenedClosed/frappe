FROM node:lts-alpine3.18 as base

WORKDIR /frontend

COPY package*.json .
COPY yarn.lock .

RUN yarn

FROM base as prod
COPY . .
COPY public ./public  
RUN yarn build