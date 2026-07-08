# Stage 1: Build static React bundles
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./

# Optimize npm registry to use a fast mirror and increase timeouts
RUN npm config set registry https://registry.npmmirror.com && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000 && \
    npm install

COPY . .
RUN npm run build

# Stage 2: Deploy bundles on Nginx web server
FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
