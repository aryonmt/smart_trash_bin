# Stage 1: Build static React bundles
FROM node:20-alpine AS build
WORKDIR /app

# Copy ONLY package.json (no lockfile required)
COPY package.json ./

# Limit parallel downloads (maxsockets) to 3 to prevent WSL2 virtual network deadlocks.
# Disable progress bars and audits, and enable verbose logs.
RUN npm config set registry https://registry.npmmirror.com && \
    npm config set maxsockets 3 && \
    npm install --progress=false --no-audit --no-fund --verbose

COPY . .
RUN npm run build

# Stage 2: Deploy bundles on Nginx web server
FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
