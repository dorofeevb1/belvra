# Multi-stage build for Angular
FROM node:20-alpine as builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build -- --configuration=production

# Production image with nginx
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist/beauty-style-service/browser /usr/share/nginx/html

# Copy nginx config for SPA
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
