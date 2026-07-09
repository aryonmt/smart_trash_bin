# Stage 1: Build static React bundles
FROM node:20-alpine AS build
WORKDIR /app

# Copy ONLY package.json (no lockfile required)
COPY package.json ./

# Switch to Liara's high-speed domestic Iranian NPM mirror.
# Bypasses international routing/filtering and caps sockets to prevent WSL2 deadlocks.
RUN npm config set registry https://package-mirror.liara.ir/repository/npm/ && \
    npm config set maxsockets 3 && \
    npm install --progress=false --no-audit --no-fund --verbose

COPY . .
RUN npm run build

# Stage 2: Deploy bundles on Nginx web server
FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
