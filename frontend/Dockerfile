# Stage 1: Build static React bundles
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm config set registry https://package-mirror.liara.ir/repository/npm/ && \
    npm config set maxsockets 3 && \
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
