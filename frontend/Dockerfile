# ==============================================================================
# CreditMera Frontend - Production Multi-Stage Dockerfile
# Stage 1: Build Vite / React SPA with Node.js
# Stage 2: Serve optimized bundle through Nginx with reverse proxy
# ==============================================================================

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency specifications and install cleanly
COPY package.json package-lock.json ./
RUN npm ci

# Copy application source code and configuration
COPY . .

# Build production bundle (relative API base URL proxied through Nginx)
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# Stage 2: Production Nginx Server
FROM nginx:1.27-alpine AS production

# Remove default boilerplate configuration
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy custom reverse-proxy configuration
COPY nginx.conf /etc/nginx/conf.d/creditmera.conf

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80

# Health check verifying web server responds
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
