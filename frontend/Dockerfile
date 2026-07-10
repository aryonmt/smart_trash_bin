# Stage 1: Build static React bundles
FROM node:20-alpine AS build
WORKDIR /app

# Copy both the manifest and the lockfile to ensure deterministic builds (npm ci)
COPY package.json package-lock.json ./

# Configure the default public registry with fast-failing retry parameters
# to prevent infinite hanging under restricted networks.
RUN npm config set fetch-retries 3 && \
    npm config set fetch-retry-mintimeout 15000 && \
    npm config set fetch-retry-maxtimeout 60000 && \
    npm ci --progress=false --no-audit --no-fund

COPY . .
RUN npm run build

# Stage 2: Deploy bundles on Nginx web server
FROM nginx:1.25-alpine
# Copy custom Nginx configuration to support SPA routing (Fixes 404 on refresh)
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
