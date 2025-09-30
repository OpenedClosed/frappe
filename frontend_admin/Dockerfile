FROM node:lts-alpine3.18 as base

WORKDIR /frontend

COPY package*.json .
COPY yarn.lock .

RUN yarn

FROM base as prod
COPY public ./public  
COPY . .
RUN yarn build