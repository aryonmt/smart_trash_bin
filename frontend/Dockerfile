# Stage 1: Build static React bundles
FROM node:20-alpine AS build
WORKDIR /app

# Copy package manifests to leverage Docker layer caching.
# package-lock.json ensures a completely deterministic and stable build via 'npm ci'.
COPY package.json package-lock.json ./

# Use the default public npm registry. Retry configurations below force transient
# network drops to fail fast instead of hanging indefinitely.
RUN npm config set fetch-retries 3 && \
    npm config set fetch-retry-mintimeout 15000 && \
    npm config set fetch-retry-maxtimeout 60000 && \
    npm ci --progress=false --no-audit --no-fund

COPY . .
RUN npm run build

# Stage 2: Deploy bundles on Nginx web server
FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
