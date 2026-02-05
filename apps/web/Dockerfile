# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies (no lock file, use npm install)
COPY package.json ./
RUN npm install

# Copy source and build
COPY . .
RUN npm run build -- --configuration=production

# Production stage - copies built files to volume
FROM alpine:3.20

# Copy built files from builder
COPY --from=builder /app/dist/web/browser /app/dist

# Copy files to volume mount point on start
CMD ["sh", "-c", "cp -r /app/dist/* /out/ 2>/dev/null || true && echo 'Frontend build copied to volume' && sleep infinity"]
