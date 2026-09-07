FROM node:20-alpine AS build
WORKDIR /app

# Vite bakes these into the static bundle at build time (it's a client-side
# SPA - there is no runtime env injection), so they're build args, not
# Container App env vars. Supplied by .github/workflows/cd.yml.
ARG VITE_ENTRA_CLIENT_ID
ARG VITE_ENTRA_TENANT_ID
ARG VITE_API_SCOPE
ARG VITE_API_BASE_URL
ARG VITE_DISABLE_AUTH=false
ENV VITE_ENTRA_CLIENT_ID=$VITE_ENTRA_CLIENT_ID \
    VITE_ENTRA_TENANT_ID=$VITE_ENTRA_TENANT_ID \
    VITE_API_SCOPE=$VITE_API_SCOPE \
    VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_DISABLE_AUTH=$VITE_DISABLE_AUTH

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1
