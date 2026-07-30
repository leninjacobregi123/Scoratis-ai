# Multi-stage build: compile the Vite SPA, then serve it as static files via nginx.
# nginx also reverse-proxies API paths to the backend (see nginx.conf.template),
# mirroring vite.config.js's dev-server proxy so frontend code needs no changes.

FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# BACKEND_URL must be the backend's base URL reachable from this container,
# e.g. http://backend:8000 in docker-compose, or the backend Fly app's
# public URL on Fly/Render. nginx:1.27's entrypoint envsubst's *.template
# files in /etc/nginx/templates/ into /etc/nginx/conf.d/ on startup.
#
# DNS_RESOLVER: 127.0.0.11 is Docker Compose's embedded DNS (resolves both
# service names like "backend" and public hostnames) - the right default for
# docker-compose. Fly/Render deploys have no such resolver; override with a
# public one there, e.g. `fly secrets set DNS_RESOLVER=1.1.1.1` /
# the equivalent Render env var, alongside a BACKEND_URL that's a public URL.
ENV BACKEND_URL=http://backend:8000
ENV DNS_RESOLVER=127.0.0.11

EXPOSE 8080

# 127.0.0.1, not localhost - nginx's `listen 8080` only binds IPv4, but
# /etc/hosts lists ::1 first, and busybox wget doesn't fall back to IPv4 on
# an IPv6 connection refusal the way curl does - it just fails every check.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/ || exit 1
