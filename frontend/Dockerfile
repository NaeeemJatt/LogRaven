# LogRaven — Production frontend image
#
# Stage 1: build the Vite bundle. VITE_* vars are baked in at build time;
# leave VITE_API_URL empty so the app calls same-origin paths that nginx
# proxies to the API container.
FROM node:20-alpine AS builder

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG VITE_API_URL=""
ARG VITE_AWS_ACCOUNT_ID=""
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_AWS_ACCOUNT_ID=$VITE_AWS_ACCOUNT_ID
RUN npm run build

# Stage 2: nginx serves the static bundle and reverse-proxies the API.
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1
