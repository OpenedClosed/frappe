FROM node:lts-alpine3.18 as base

WORKDIR /frontend

COPY package*.json .
COPY yarn.lock .

RUN yarn

FROM base as prod
COPY . .
RUN yarn build