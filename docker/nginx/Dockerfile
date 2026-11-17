# syntax=docker/dockerfile:1
# Build the SPA, then serve it from nginx with the API/storage proxy config.
FROM node:20-alpine AS build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:alpine

COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /srv/frontend

EXPOSE 80
